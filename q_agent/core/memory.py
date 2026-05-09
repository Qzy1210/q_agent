"""
Memory系统 - 管理Agent的记忆

记忆系统是Agent的重要组成部分，分为：
1. 短期记忆（Short-term Memory）：当前会话的上下文信息
2. 长期记忆（Long-term Memory）：持久化的知识和经验

学习重点：
1. 理解短期记忆和长期记忆的区别
2. 掌握记忆的存储和检索机制
3. 学习如何管理上下文窗口
4. 了解向量检索的基本原理（长期记忆）
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from collections import deque


class Message:
    """
    消息类 - 记忆的基本单元
    
    每条消息记录了对话中的角色、内容、时间等信息。
    这是记忆系统的最小单位。
    
    属性说明：
        role (str): 消息角色（user/assistant/system）
        content (str): 消息内容
        timestamp (datetime): 时间戳
        metadata (dict): 额外元数据（如token数、重要程度等）
    """
    
    def __init__(self, role: str, content: str, metadata: Optional[Dict] = None):
        """
        初始化消息
        
        参数：
            role (str): 消息角色
            content (str): 消息内容
            metadata (dict): 可选的元数据
        """
        self.role = role
        self.content = content
        self.timestamp = datetime.now()
        self.metadata = metadata or {}
        
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典格式
        
        返回：
            dict: 包含所有消息信息的字典
            
        用途：
        - 序列化存储
        - API传输
        - 日志记录
        """
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }
    
    def __repr__(self) -> str:
        """
        字符串表示
        
        返回：
            str: 消息的简短描述
        """
        return f"Message(role={self.role}, content={self.content[:50]}...)"


class Memory:
    """
    Memory主类 - 管理Agent的记忆系统
    
    这是记忆系统的核心类，负责：
    1. 管理短期记忆（当前会话）
    2. 管理长期记忆（持久化知识）
    3. 提供记忆检索功能
    4. 实现记忆压缩和摘要
    
    设计思路：
    - 短期记忆使用队列（FIFO），限制大小
    - 长期记忆使用列表，可扩展存储
    - 提供多种检索方式：关键词、时间、重要性
    - 支持记忆压缩，节省token
    
    学习重点：
    1. 记忆的存储结构
    2. 如何限制记忆大小
    3. 如何检索相关记忆
    4. 记忆的重要性排序
    """
    
    def __init__(self, max_short_term: int = 20):
        """
        初始化记忆系统
        
        参数：
            max_short_term (int): 短期记忆的最大条数
            
        设计说明：
        - 短期记忆使用deque（双端队列），自动淘汰旧记忆
        - 长期记忆使用列表，需要手动管理
        - 可以根据需要调整max_short_term
        """
        # 短期记忆：使用双端队列，先进先出
        self.short_term_memory = deque(maxlen=max_short_term)
        
        # 长期记忆：持久化的知识
        self.long_term_memory = []
        
        # 记忆统计信息
        self.stats = {
            "total_messages": 0,
            "user_messages": 0,
            "assistant_messages": 0,
            "system_messages": 0
        }
    
    def add_message(
        self, 
        role: str, 
        content: str, 
        metadata: Optional[Dict] = None
    ):
        """
        添加消息到记忆系统
        
        参数：
            role (str): 消息角色（user/assistant/system）
            content (str): 消息内容
            metadata (dict): 可选的元数据
            
        功能：
        1. 创建消息对象
        2. 添加到短期记忆
        3. 更新统计信息
        4. 根据重要性决定是否保存到长期记忆
        
        设计思路：
        - 所有消息先进入短期记忆
        - 重要消息同时保存到长期记忆
        - 自动维护统计信息
        """
        # 创建消息对象
        message = Message(role, content, metadata)
        
        # 添加到短期记忆（自动淘汰最旧的消息）
        self.short_term_memory.append(message)
        
        # 更新统计信息
        self.stats["total_messages"] += 1
        if role == "user":
            self.stats["user_messages"] += 1
        elif role == "assistant":
            self.stats["assistant_messages"] += 1
        elif role == "system":
            self.stats["system_messages"] += 1
        
        # 判断是否需要保存到长期记忆
        if self._is_important(message):
            self.long_term_memory.append(message)
            print(f"💾 重要消息已保存到长期记忆: {content[:50]}...")
    
    def get_recent_messages(self, count: Optional[int] = None) -> List[Dict]:
        """
        获取最近的消息
        
        参数：
            count (int): 要获取的消息数量，None表示获取全部
        返回：
            List[Dict]: 消息列表（字典格式）
        用途：
        - 构建上下文
        - 生成对话历史
        - 分析对话模式
        """
        if count is None:
            # 返回所有短期记忆
            return [msg.to_dict() for msg in self.short_term_memory]
        else:
            # 返回最近的N条消息
            messages = list(self.short_term_memory)[-count:]
            return [msg.to_dict() for msg in messages]
    
    def search_memory(self, keyword: str) -> List[Dict]:
        """
        搜索记忆
        
        参数：
            keyword (str): 搜索关键词
        返回：
            List[Dict]: 匹配的消息列表
        功能：
        在短期记忆和长期记忆中搜索包含关键词的消息
        
        设计思路：
        - 简单的关键词匹配
        - 后续可以增强为语义搜索
        - 支持模糊匹配
        """
        results = []
        
        # 搜索短期记忆
        for msg in self.short_term_memory:
            if keyword.lower() in msg.content.lower():
                results.append(msg.to_dict())
        
        # 搜索长期记忆
        for msg in self.long_term_memory:
            if keyword.lower() in msg.content.lower():
                results.append(msg.to_dict())
        
        return results
    
    def clear_short_term(self):
        """
        清空短期记忆
        
        用途：
        - 开始新任务
        - 释放内存
        - 重置状态

        说明：
        长期记忆不会被清空，保留重要信息
        """
        self.short_term_memory.clear()
        print("🗑️  短期记忆已清空")
    
    def get_memory_summary(self) -> str:
        """
        获取记忆摘要
        
        返回：
            str: 记忆的文本摘要
            
        功能：
        生成记忆系统的概览信息
        
        用途：
        - 调试
        - 状态监控
        - 日志记录
        """
        summary = f"""
记忆系统状态：
- 短期记忆: {len(self.short_term_memory)} 条
- 长期记忆: {len(self.long_term_memory)} 条
- 总消息数: {self.stats['total_messages']}
  - 用户消息: {self.stats['user_messages']}
  - 助手消息: {self.stats['assistant_messages']}
  - 系统消息: {self.stats['system_messages']}
"""
        return summary
    
    def _is_important(self, message: Message) -> bool:
        """
        判断消息是否重要
        
        参数：
            message (Message): 消息对象
            
        返回：
            bool: True表示重要，需要保存到长期记忆
            
        判断标准：
        1. 包含重要关键词
        2. 元数据中标记为重要
        3. 用户明确表示重要
        
        设计思路：
        - 简单规则判断
        - 后续可以用LLM判断重要性
        - 支持自定义规则
        """
        # 检查元数据中的重要性标记
        if message.metadata.get("important", False):
            return True
        
        # 检查关键词
        important_keywords = [
            "重要", "记住", "关键", "important", "remember", "key",
            "错误", "失败", "error", "failed"
        ]
        
        content_lower = message.content.lower()
        return any(keyword in content_lower for keyword in important_keywords)
    
    def export_memory(self) -> Dict[str, Any]:
        """
        导出记忆数据
        
        返回：
            dict: 包含所有记忆数据的字典
            
        用途：
        - 备份
        - 迁移
        - 分析
        """
        return {
            "short_term": [msg.to_dict() for msg in self.short_term_memory],
            "long_term": [msg.to_dict() for msg in self.long_term_memory],
            "stats": self.stats
        }
    
    def import_memory(self, data: Dict[str, Any]):
        """
        导入记忆数据
        
        参数：
            data (dict): 导出的记忆数据
            
        用途：
        - 恢复
        - 迁移
        - 测试
        """
        # 清空现有记忆
        self.short_term_memory.clear()
        self.long_term_memory.clear()
        
        # 导入短期记忆
        for msg_data in data.get("short_term", []):
            msg = Message(
                role=msg_data["role"],
                content=msg_data["content"],
                metadata=msg_data.get("metadata")
            )
            self.short_term_memory.append(msg)
        
        # 导入长期记忆
        for msg_data in data.get("long_term", []):
            msg = Message(
                role=msg_data["role"],
                content=msg_data["content"],
                metadata=msg_data.get("metadata")
            )
            self.long_term_memory.append(msg)
        
        # 导入统计信息
        self.stats = data.get("stats", {
            "total_messages": 0,
            "user_messages": 0,
            "assistant_messages": 0,
            "system_messages": 0
        })
        
        print("✅ 记忆数据导入成功")


# 使用示例
if __name__ == "__main__":
    """
    Memory系统使用示例
    
    演示如何使用记忆系统：
    1. 添加消息
    2. 检索消息
    3. 导出/导入记忆
    """
    
    print("=" * 60)
    print("Memory系统使用示例")
    print("=" * 60)
    
    # 创建记忆系统
    memory = Memory(max_short_term=10)
    
    # 添加一些消息
    memory.add_message("user", "你好，我想学习AI Agent")
    memory.add_message("assistant", "你好！我很乐意帮助你学习AI Agent")
    memory.add_message("user", "什么是Agent Loop？")
    memory.add_message("assistant", "Agent Loop是思考-决策-行动的循环过程")
    memory.add_message("user", "这个很重要，请记住：Agent Loop是核心概念", metadata={"important": True})
    
    # 查看记忆摘要
    print(memory.get_memory_summary())
    
    # 获取最近的消息
    print("\n最近的消息：")
    for msg in memory.get_recent_messages(3):
        print(f"  [{msg['role']}]: {msg['content']}")
    
    # 搜索记忆
    print("\n搜索 'Agent Loop'：")
    results = memory.search_memory("Agent Loop")
    for msg in results:
        print(f"  [{msg['role']}]: {msg['content']}")
    
    # 导出记忆
    print("\n导出记忆数据...")
    exported = memory.export_memory()
    print(f"导出数据大小: {len(str(exported))} 字符")
    
    print("\n" + "=" * 60)
    print("示例执行完成！")
    print("=" * 60)
