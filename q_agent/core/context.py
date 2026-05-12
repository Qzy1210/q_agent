"""
重构后的 ContextManager - 完整的上下文管理系统

职责：
1. 管理当前会话的活跃消息
2. Token 限制和优化
3. 优先级保护机制
4. 上下文压缩和摘要
5. 提供构建 LLM prompt 的接口
"""

import re
from collections import deque
from typing import List, Dict, Any, Optional


class ContextManager:
    """
    Context管理器 - 负责当前上下文管理
    
    核心职责：
    - 管理当前会话的活跃消息（用于构建LLM prompt）
    - Token限制和优化（确保不超过LLM限制）
    - 优先级保护（重要消息不被压缩）
    - 上下文压缩（智能移除不相关内容）
    
    设计原则：
    - 这是Agent构建prompt的唯一数据源
    - 自动管理Token，无需手动干预
    - 高优先级消息始终保留
    """
    
    def __init__(
        self,
        max_tokens: int = 4000,
        compression_threshold: float = 0.8
    ):
        """
        初始化上下文管理器
        
        参数：
            max_tokens (int): 最大Token数量，默认4000
            compression_threshold (float): 触发压缩的阈值，默认0.8
        """
        self.max_tokens = max_tokens
        self.compression_threshold = compression_threshold
        self.current_tokens = 0
        
        # 当前上下文窗口（活跃消息）
        self.context_window = deque()
        
        # 高优先级消息（不会被压缩）
        self.priority_messages = {}
        
        # 当前任务和工具
        self.current_task = None
        self.tools = []
        
        # 统计信息
        self.stats = {
            "total_messages": 0,
            "compressed_count": 0,
            "removed_count": 0,
            "priority_count": 0
        }
        
        print(f"✅ Context管理器初始化完成，最大Token数: {max_tokens}")
    
    def add_message(
        self,
        role: str,
        content: str,
        priority: int = 0,
        metadata: Optional[Dict] = None
    ) -> bool:
        """
        添加消息到当前上下文
        
        参数：
            role (str): 消息角色（user/assistant/system）
            content (str): 消息内容
            priority (int): 优先级（0=普通，1=高优先级）
            metadata (dict): 额外元数据
            
        返回：
            bool: 是否成功添加
        """
        # 计算Token数
        tokens = self._estimate_tokens(content)
        
        # 创建消息对象
        message = {
            "role": role,
            "content": content,
            "tokens": tokens,
            "priority": priority,
            "metadata": metadata or {}
        }
        
        # 检查是否会超出限制
        if self.current_tokens + tokens > self.max_tokens:
            # 尝试压缩或移除旧消息
            if not self._make_room(tokens):
                print(f"⚠️ 无法添加消息，上下文窗口已满")
                return False
        
        # 添加到窗口
        self.context_window.append(message)
        self.current_tokens += tokens
        self.stats["total_messages"] += 1
        
        # 如果是高优先级消息，单独存储
        if priority > 0:
            msg_id = f"priority_{len(self.priority_messages)}"
            self.priority_messages[msg_id] = message
            self.stats["priority_count"] += 1
        
        return True
    
    def set_task(self, task: str):
        """
        设置当前任务
        
        参数：
            task (str): 任务描述
            
        功能：
        - 将任务作为高优先级消息添加到上下文
        - 确保任务信息不会被压缩
        """
        # 添加任务作为高优先级系统消息
        self.add_message(
            role="system",
            content=f"当前任务: {task}",
            priority=1,  # 高优先级
            metadata={"type": "task"}
        )
        self.current_task = task
        print(f"✅ 已设置任务: {task[:50]}...")
    
    def set_tools(self, tools: List[Any]):
        """
        设置可用工具
        
        参数：
            tools (List): 工具列表
        """
        self.tools = tools
        print(f"✅ 已设置 {len(tools)} 个工具")
    
    def get_context(self, include_priority: bool = True) -> List[Dict[str, str]]:
        """
        获取当前上下文（用于构建LLM prompt）
        
        参数：
            include_priority (bool): 是否包含高优先级消息
            
        返回：
            List[Dict]: 消息列表，格式为[{"role": ..., "content": ...}]
        """
        messages = []
        
        # 添加高优先级消息
        if include_priority:
            for msg in self.priority_messages.values():
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
        
        # 添加窗口中的消息
        for msg in self.context_window:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        return messages
    
    def get_context_for_llm(self) -> List[Dict[str, str]]:
        """
        获取优化后的上下文（专门用于LLM调用）
        
        返回：
            List[Dict]: 优化后的消息列表
            
        功能：
        - 自动检查Token使用率
        - 如果超过阈值，自动压缩
        - 返回适合LLM的格式
        """
        # 检查是否需要压缩
        if self.current_tokens / self.max_tokens >= self.compression_threshold:
            print("🔄 上下文接近上限，自动压缩...")
            self.compress_context()
        
        return self.get_context()
    
    def add_interaction(self, action: Any, result: str):
        """
        添加交互记录（Agent执行工具后的记录）
        
        参数：
            action: Agent的行动对象
            result (str): 执行结果
        """
        # 添加助手消息
        self.add_message(
            role="assistant",
            content=f"执行 {action.tool_name}: {action.reasoning}"
        )
        
        # 添加系统消息（执行结果）
        self.add_message(
            role="system",
            content=f"执行结果: {result}"
        )
    
    def clear_context(self, keep_priority: bool = True):
        """
        清空上下文窗口
        
        参数：
            keep_priority (bool): 是否保留高优先级消息
        """
        if not keep_priority:
            self.priority_messages.clear()
            self.stats["priority_count"] = 0
        
        self.context_window.clear()
        self.current_tokens = 0
        print("✅ 上下文已清空")
    
    def compress_context(self) -> int:
        """
        压缩上下文
        
        返回：
            int: 压缩后节省的Token数
            
        压缩策略：
        1. 移除最旧的非优先消息
        2. 合并连续的短消息
        3. 摘要长消息
        """
        if len(self.context_window) == 0:
            return 0
        
        saved_tokens = 0
        
        # 策略1: 移除最旧的20%消息
        remove_count = max(1, len(self.context_window) // 5)
        for _ in range(remove_count):
            if len(self.context_window) > 0:
                removed_msg = self.context_window.popleft()
                self.current_tokens -= removed_msg["tokens"]
                saved_tokens += removed_msg["tokens"]
                self.stats["removed_count"] += 1
        
        # 策略2: 压缩长消息（保留前半部分）
        for msg in self.context_window:
            if msg["tokens"] > 200:  # 长消息才压缩
                compressed_content = msg["content"][:len(msg["content"])//2] + "...[已压缩]"
                old_tokens = msg["tokens"]
                msg["content"] = compressed_content
                msg["tokens"] = self._estimate_tokens(compressed_content)
                saved_tokens += old_tokens - msg["tokens"]
                self.stats["compressed_count"] += 1
        
        self.current_tokens -= saved_tokens
        print(f"✅ 上下文压缩完成，节省 {saved_tokens} tokens")
        return saved_tokens
    
    def optimize_for_task(self, task: str):
        """
        根据任务优化上下文
        
        参数：
            task (str): 任务描述
            
        功能：
        - 提取任务关键词
        - 保留与任务相关的上下文
        - 移除不相关的信息
        """
        # 提取任务中的关键词
        keywords = set(re.findall(r'\w+', task.lower()))
        
        # 重新排序上下文，相关性高的在前
        relevant_messages = []
        other_messages = []
        
        for msg in self.context_window:
            content_keywords = set(re.findall(r'\w+', msg["content"].lower()))
            # 如果消息包含任务关键词，视为相关
            if keywords & content_keywords:
                relevant_messages.append(msg)
            else:
                other_messages.append(msg)
        
        # 重新组织上下文
        self.context_window.clear()
        
        # 先添加相关消息
        for msg in relevant_messages:
            self.context_window.append(msg)
        
        # 再添加其他消息（如果还有空间）
        for msg in other_messages:
            if self.current_tokens + msg["tokens"] <= self.max_tokens:
                self.context_window.append(msg)
            else:
                self.current_tokens -= msg["tokens"]
                self.stats["removed_count"] += 1
        
        print(f"✅ 上下文优化完成，保留 {len(self.context_window)} 条相关消息")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        返回：
            dict: 包含各种统计数据
        """
        return {
            **self.stats,
            "current_tokens": self.current_tokens,
            "max_tokens": self.max_tokens,
            "usage_ratio": f"{self.current_tokens / self.max_tokens:.1%}",
            "window_size": len(self.context_window),
            "priority_size": len(self.priority_messages)
        }
    
    def _estimate_tokens(self, text: str) -> int:
        """
        估算文本的Token数量
        
        参数：
            text (str): 文本内容
        返回：
            int: 估算的Token数
        """
        # 简单估算：平均3字符/token
        return len(text) // 3 + 1
    
    def _make_room(self, needed_tokens: int) -> bool:
        """
        为新消息腾出空间
        
        参数：
            needed_tokens (int): 需要的Token数
        返回：
            bool: 是否成功腾出空间
        """
        # 检查是否超过阈值
        if self.current_tokens / self.max_tokens >= self.compression_threshold:
            # 尝试压缩
            saved = self.compress_context()
            if saved >= needed_tokens:
                return True
        
        # 移除最旧的消息
        while (self.current_tokens + needed_tokens > self.max_tokens 
               and len(self.context_window) > 0):
            removed_msg = self.context_window.popleft()
            self.current_tokens -= removed_msg["tokens"]
            self.stats["removed_count"] += 1
        
        return self.current_tokens + needed_tokens <= self.max_tokens


if __name__ == "__main__":
    """测试重构后的 ContextManager"""
    print("=" * 60)
    print("ContextManager 测试")
    print("=" * 60)
    
    # 创建上下文管理器
    context = ContextManager(max_tokens=1000)
    
    # 设置任务
    context.set_task("帮我创建一个test.txt文件")
    
    # 添加一些消息
    context.add_message("user", "你好，我想学习AI Agent")
    context.add_message("assistant", "你好！我很乐意帮助你学习AI Agent")
    
    # 获取上下文
    print("\n当前上下文：")
    for msg in context.get_context():
        print(f"  [{msg['role']}]: {msg['content'][:50]}...")
    
    # 查看统计信息
    print("\n统计信息：")
    stats = context.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)
