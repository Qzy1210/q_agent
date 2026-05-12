"""
健康检查路由

提供服务健康状态检查接口，用于：
1. 服务监控
2. 负载均衡健康检查
3. Kubernetes存活探针
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    """
    健康检查接口

    Returns:
        dict: 服务健康状态
    """
    return {
        "status": "healthy",
        "service": "q-agent-api",
        "version": "1.0.0"
    }


@router.get("/ready")
async def readiness_check():
    """
    就绪检查接口

    用于检查服务是否准备好接收请求。

    Returns:
        dict: 服务就绪状态
    """
    # TODO: 检查数据库连接、Agent实例等是否就绪
    return {
        "status": "ready",
        "checks": {
            "database": "ok",
            "agent": "ok"
        }
    }
