"""
工具模块

这个模块包含了Agent可用的工具：
- 工具基类：定义工具接口
- 工具注册器：管理工具集合
- 基础工具：文件操作、搜索、计算器等

学习重点：
1. 理解工具的设计模式
2. 掌握工具注册机制
3. 学习如何实现自定义工具
"""

from .base import Tool, ToolResult
from .registry import ToolRegistry
from .basic_tools import FileReadTool, CalculatorTool, SearchTool

__all__ = [
    'Tool', 
    'ToolResult', 
    'ToolRegistry',
    'FileReadTool',
    'CalculatorTool', 
    'SearchTool'
]
