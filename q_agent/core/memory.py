"""
重构后的 Memory - 长期存储和检索系统

职责：
1. 持久化存储所有历史消息
2. 提供检索功能（搜索历史记录）
3. 支持导入导出（备份恢复）
4. 不再管理短期记忆（由 ContextManager 负责）

设计原则：
- 只负责长期存储，不参与当前上下文管理
- 支持持久化到文件或数据库
- 提供检索和分析功能
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import json


class Message:
    """
    消息类 - 记忆的基本单元
    
    每条消息记录了对话中的角色、内容、时间等信息。
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
    Memory主类 - 管理长期记忆和检索
    
    核心职责：
    - 持久化存储所有历史消息
    - 提供检索功能（关键词搜索）
    - 支持导入导出（备份恢复）
    - 不再管理短期记忆（由 ContextManager 负责）
    
    设计原则：
    - 与 ContextManager 职责分离
    - 专注于长期存储和检索
    - 支持持久化到文件或数据库
    """
    
    def __init__(self, storage_file: Optional[str] = None):
        """
        初始化记忆系统
        
        参数：
            storage_file (str): 可选的持久化文件路径
            
        设计说明：
        - 移除了短期记忆（由 ContextManager 管理）
        - 只保留长期记忆用于持久化
        - 支持从文件加载历史数据
        """
        # 长期记忆：持久化的历史消息
        self.long_term_memory = []
        
        # 持久化文件路径
        self.storage_file = storage_file
        
        # 记忆统计信息
        self.stats = {
            "total_messages": 0,
            "user_messages": 0,
            "assistant_messages": 0,
            "system_messages": 0
        }
        
        # 如果指定了存储文件，尝试加载
        if storage_file:
            self._load_from_file(storage_file)
        
        print("✅ Memory系统初始化完成（长期存储模式）")
    
    def save_message(
        self, 
        role: str, 
        content: str, 
        metadata: Optional[Dict] = None
    ):
        """
        保存消息到长期记忆
        
        参数：
            role (str): 消息角色（user/assistant/system）
            content (str): 消息内容
            metadata (dict): 可选的元数据
            
        功能：
        - 创建消息对象
        - 保存到长期记忆
        - 更新统计信息
        - 可选：持久化到文件
        
        设计思路：
        - 所有消息都会被持久化
        - 不再区分重要与否（由 ContextManager 管理优先级）
        - 支持异步持久化（后续优化）
        """
        # 创建消息对象
        message = Message(role, content, metadata)
        
        # 保存到长期记忆
        self.long_term_memory.append(message)
        
        # 更新统计信息
        self.stats["total_messages"] += 1
        if role == "user":
            self.stats["user_messages"] += 1
        elif role == "assistant":
            self.stats["assistant_messages"] += 1
        elif role == "system":
            self.stats["system_messages"] += 1
        
        # 可选：实时持久化
        if self.storage_file:
            self._append_to_file(message)
    
    def search(self, keyword: str) -> List[Dict]:
        """
        搜索历史记忆
        
        参数：
            keyword (str): 搜索关键词
            
        返回：
            List[Dict]: 匹配的消息列表
            
        功能：
        在长期记忆中搜索包含关键词的消息
        
        设计思路：
        - 简单的关键词匹配
        - 后续可以增强为语义搜索
        - 支持模糊匹配
        """
        results = []
        
        for msg in self.long_term_memory:
            if keyword.lower() in msg.content.lower():
                results.append(msg.to_dict())
        
        print(f"🔍 搜索 '{keyword}'，找到 {len(results)} 条记录")
        return results
    
    def get_recent(self, count: int = 10) -> List[Dict]:
        """
        获取最近的消息
        
        参数：
            count (int): 要获取的消息数量
            
        返回：
            List[Dict]: 消息列表（字典格式）
            
        用途：
        - 查看最近的对话历史
        - 分析对话模式
        """
        messages = self.long_term_memory[-count:]
        return [msg.to_dict() for msg in messages]
    
    def get_all(self) -> List[Dict]:
        """
        获取所有历史消息
        
        返回：
            List[Dict]: 所有消息列表
            
        用途：
        - 完整历史查看
        - 数据分析
        - 导出备份
        """
        return [msg.to_dict() for msg in self.long_term_memory]
    
    def clear(self):
        """
        清空长期记忆
        
        用途：
        - 开始全新会话
        - 释放内存
        - 重置状态
        """
        self.long_term_memory.clear()
        self.stats = {
            "total_messages": 0,
            "user_messages": 0,
            "assistant_messages": 0,
            "system_messages": 0
        }
        print("🗑️  长期记忆已清空")
    
    def get_summary(self) -> str:
        """
        获取记忆摘要
        
        返回：
            str: 记忆的文本摘要
            
        用途：
        - 调试
        - 状态监控
        - 日志记录
        """
        summary = f"""
记忆系统状态：
- 长期记忆: {len(self.long_term_memory)} 条
- 总消息数: {self.stats['total_messages']}
  - 用户消息: {self.stats['user_messages']}
  - 助手消息: {self.stats['assistant_messages']}
  - 系统消息: {self.stats['system_messages']}
- 持久化文件: {self.storage_file or '未设置'}
"""
        return summary
    
    def export_to_file(self, filepath: str):
        """
        导出记忆到文件
        
        参数：
            filepath (str): 导出文件路径
            
        用途：
        - 备份
        - 迁移
        - 分析
        """
        data = {
            "long_term": [msg.to_dict() for msg in self.long_term_memory],
            "stats": self.stats
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 记忆已导出到: {filepath}")
    
    def import_from_file(self, filepath: str):
        """
        从文件导入记忆
        
        参数：
            filepath (str): 导入文件路径
            
        用途：
        - 恢复
        - 迁移
        - 测试
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 清空现有记忆
        self.long_term_memory.clear()
        
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
        
        print(f"✅ 从 {filepath} 导入记忆成功")
    
    def _load_from_file(self, filepath: str):
        """
        从文件加载记忆（初始化时）
        
        参数：
            filepath (str): 文件路径
        """
        try:
            self.import_from_file(filepath)
        except FileNotFoundError:
            print(f"⚠️  文件 {filepath} 不存在，将创建新文件")
        except Exception as e:
            print(f"⚠️  加载记忆文件失败: {e}")
    
    def _append_to_file(self, message: Message):
        """
        追加消息到文件（实时持久化）
        
        参数：
            message (Message): 消息对象
            
        说明：
        - 简化版本：每次都重写整个文件
        - 后续可以优化为追加模式
        """
        try:
            data = {
                "long_term": [msg.to_dict() for msg in self.long_term_memory],
                "stats": self.stats
            }
            
            with open(self.storage_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️  持久化失败: {e}")


# 使用示例
if __name__ == "__main__":
    """
    Memory系统使用示例
    
    演示如何使用重构后的记忆系统：
    1. 保存消息
    2. 检索消息
    3. 导出/导入记忆
    """
    
    print("=" * 60)
    print("Memory系统使用示例（重构后）")
    print("=" * 60)
    
    # 创建记忆系统
    memory = Memory()
    
    # 保存一些消息
    memory.save_message("user", "你好，我想学习AI Agent")
    memory.save_message("assistant", "你好！我很乐意帮助你学习AI Agent")
    memory.save_message("user", "什么是Agent Loop？")
    memory.save_message("assistant", "Agent Loop是思考-决策-行动的循环过程")
    memory.save_message("user", "这个很重要，请记住：Agent Loop是核心概念")
    
    # 查看记忆摘要
    print(memory.get_summary())
    
    # 获取最近的消息
    print("\n最近的消息：")
    for msg in memory.get_recent(3):
        print(f"  [{msg['role']}]: {msg['content']}")
    
    # 搜索记忆
    print("\n搜索 'Agent Loop'：")
    results = memory.search("Agent Loop")
    for msg in results:
        print(f"  [{msg['role']}]: {msg['content']}")
    
    # 导出记忆
    print("\n导出记忆数据...")
    memory.export_to_file("/tmp/memory_backup.json")
    
    print("\n" + "=" * 60)
    print("示例执行完成！")
    print("=" * 60)
