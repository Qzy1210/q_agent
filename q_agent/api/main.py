"""
FastAPI主应用 - Agent API服务入口

这是API服务的主入口，提供RESTful接口供外部应用调用。
使用FastAPI框架，支持异步处理和自动文档生成。

学习重点：
1. FastAPI框架的基本使用
2. 如何将Agent核心能力暴露为API
3. 异步处理和错误处理
4. CORS配置（跨域资源共享）
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理

    替代已弃用的 on_event，使用 lifespan 上下文管理器。
    """
    # 启动时执行
    logger.info("Q-Agent API服务启动中...")
    # TODO: 初始化Agent实例
    # TODO: 初始化数据库连接

    yield  # 服务运行中

    # 关闭时执行
    logger.info("Q-Agent API服务关闭中...")
    # TODO: 清理资源


# 创建FastAPI应用实例
app = FastAPI(
    title="Q-Agent API",
    description="Agent API服务 - 提供智能对话能力",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# 配置CORS - 允许安卓应用跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 导入路由
from .routes import chat, health

# 注册路由
app.include_router(health.router, prefix="/api/v1", tags=["健康检查"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["对话"])


if __name__ == "__main__":
    """
    直接运行此文件启动服务

    使用方法：
        python -m q_agent.api.main

    访问文档：
        http://localhost:8089/docs
    """
    uvicorn.run(
        "q_agent.api.main:app",
        host="0.0.0.0",
        port=8089,
        reload=True,  # 开发模式自动重载
        log_level="info"
    )
