"""
对话路由

提供Agent对话相关的API接口。
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


class ChatMessage(BaseModel):
    """聊天消息模型"""
    role: str  # user, assistant, system
    content: str


class ChatRequest(BaseModel):
    """聊天请求模型"""
    message: str
    session_id: Optional[str] = None
    context: Optional[List[ChatMessage]] = None


class ChatResponse(BaseModel):
    """聊天响应模型"""
    response: str
    session_id: str
    success: bool = True
    error: Optional[str] = None


@router.post("/message", response_model=ChatResponse)
async def send_message(request: ChatRequest):
    """
    发送消息给Agent

    Args:
        request: 聊天请求，包含用户消息和可选的会话ID

    Returns:
        ChatResponse: Agent的响应
    """
    try:
        logger.info("=" * 40)
        logger.info(f"📨 收到聊天请求")
        logger.info(f"   会话ID: {request.session_id or 'default-session'}")
        logger.info(f"   消息长度: {len(request.message)} 字符")
        logger.info(f"   消息内容: {request.message[:100]}{'...' if len(request.message) > 100 else ''}")
        if request.context:
            logger.info(f"   上下文消息数: {len(request.context)}")

        # TODO: 调用Agent处理消息
        # 当前返回模拟响应
        response_text = f"收到您的消息: {request.message}"

        logger.info(f"✓ 聊天请求处理完成")
        logger.info("=" * 40)

        return ChatResponse(
            response=response_text,
            session_id=request.session_id or "default-session",
            success=True
        )

    except Exception as e:
        logger.error(f"✗ 处理聊天请求失败: {e}")
        return ChatResponse(
            response="",
            session_id=request.session_id or "default-session",
            success=False,
            error=str(e)
        )


@router.get("/sessions/{session_id}/history")
async def get_session_history(session_id: str):
    """
    获取会话历史

    Args:
        session_id: 会话ID

    Returns:
        dict: 会话历史记录
    """
    # TODO: 从数据库或内存中获取会话历史
    return {
        "session_id": session_id,
        "messages": [],
        "total": 0
    }


@router.delete("/sessions/{session_id}")
async def clear_session(session_id: str):
    """
    清除会话

    Args:
        session_id: 会话ID

    Returns:
        dict: 清除结果
    """
    # TODO: 清除会话相关的内存和数据库记录
    return {
        "session_id": session_id,
        "status": "cleared"
    }
