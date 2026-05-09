"""
Q-Agent 核心模块

这个模块包含了Agent的核心实现，包括：
- Agent主类：实现Agent Loop循环
- Memory系统：管理短期和长期记忆
- Context管理：处理上下文窗口

学习重点：
1. 理解Agent Loop的工作原理
2. 掌握Memory系统的设计思路
3. 学习如何管理上下文窗口
"""

# 导入核心类，方便外部使用
from .agent import Agent
from .memory import Memory
from .context import ContextManager
# core 只可以导出 __all__ 列表里的三个对象
__all__ = ['Agent', 'Memory', 'ContextManager']
