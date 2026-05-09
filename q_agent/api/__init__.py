"""
API模块 - 提供RESTful接口供外部调用

这个模块实现了FastAPI接口，将Agent核心能力暴露给外部应用。
"""

from .main import app
from .routes import chat, health

__all__ = ['app', 'chat', 'health']
