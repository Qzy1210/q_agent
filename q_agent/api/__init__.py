"""
API模块 - 提供RESTful接口供外部调用

这个模块实现了FastAPI接口，将Agent核心能力暴露给外部应用。
"""

# 注意：不要在这里导入 app，会导致循环导入问题
# 使用时请：from q_agent.api.main import app

__all__ = ['app']
