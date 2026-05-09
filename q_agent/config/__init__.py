"""
配置模块

这个模块负责管理项目的配置：
- 配置文件加载
- 环境变量管理
- 数据库连接
- 日志配置

学习重点：
1. 理解配置管理的重要性
2. 掌握多种配置源的加载方法
3. 学习数据库连接池的使用
"""

from .config import Config
from .database import DatabaseManager

__all__ = ['Config', 'DatabaseManager']
