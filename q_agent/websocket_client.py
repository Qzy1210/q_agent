"""
Agent WebSocket客户端
将Python Agent核心连接到WebSocket平台
"""

import asyncio
import json
import time
import uuid
from typing import Optional, Callable, Any
import logging

try:
    import websockets
except ImportError:
    print("请安装websockets库: pip install websockets")
    raise

logger = logging.getLogger(__name__)


class AgentWebSocketClient:
    """
    Agent WebSocket客户端

    作为桥梁连接Python Agent核心和WebSocket平台：
    - 连接到WebSocket平台的Agent端点
    - 接收来自App的消息
    - 调用Agent处理消息
    - 将结果发送回WebSocket平台
    """

    def __init__(
        self,
        agent: Any,
        ws_url: str = "ws://localhost:8080",
        client_id: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ):
        """
        初始化Agent WebSocket客户端

        Args:
            agent: Agent实例（需要有run方法）
            ws_url: WebSocket服务器地址
            client_id: 客户端ID（可选，自动生成）
            user_id: 用户ID（可选，自动生成）
            session_id: 会话ID（可选，自动生成）
        """
        self.agent = agent
        self.ws_url = ws_url
        self.client_id = client_id or f"agent_{uuid.uuid4().hex[:8]}"
        self.user_id = user_id or f"user_{uuid.uuid4().hex[:8]}"
        self.session_id = session_id or f"session_{uuid.uuid4().hex[:8]}"

        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.running = False
        self._message_handler: Optional[Callable] = None

        logger.info(f"AgentWebSocketClient initialized: client_id={self.client_id}")

    def get_connection_url(self) -> str:
        """
        获取完整的WebSocket连接URL

        Returns:
            完整的WebSocket URL，包含查询参数
        """
        return (
            f"{self.ws_url}/ws/agent"
            f"?client_id={self.client_id}"
            f"&user_id={self.user_id}"
            f"&session_id={self.session_id}"
        )

    async def connect(self) -> None:
        """
        连接到WebSocket服务器
        """
        url = self.get_connection_url()
        logger.info(f"Connecting to WebSocket: {url}")

        try:
            self.ws = await websockets.connect(url)
            self.running = True
            logger.info("WebSocket connected successfully")

            # 启动消息处理循环
            await self.message_loop()
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            raise

    async def disconnect(self) -> None:
        """
        断开WebSocket连接
        """
        self.running = False
        if self.ws:
            await self.ws.close()
            self.ws = None
            logger.info("WebSocket disconnected")

    async def message_loop(self) -> None:
        """
        消息处理循环
        接收WebSocket消息并处理
        """
        if not self.ws:
            logger.error("WebSocket not connected")
            return

        try:
            async for message in self.ws:
                if not self.running:
                    break

                try:
                    await self.handle_message(message)
                except Exception as e:
                    logger.error(f"Error handling message: {e}")
        except websockets.ConnectionClosed as e:
            logger.warning(f"WebSocket connection closed: {e}")
            self.running = False
        except Exception as e:
            logger.error(f"Error in message loop: {e}")
            self.running = False

    async def handle_message(self, raw_message: str) -> None:
        """
        处理接收到的消息

        Args:
            raw_message: 原始JSON消息字符串
        """
        try:
            message = json.loads(raw_message)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse message: {e}")
            return

        msg_type = message.get("type", "")
        msg_id = message.get("id", "")

        logger.debug(f"Received message: type={msg_type}, id={msg_id}")

        # 处理不同类型的消息
        if msg_type == "text":
            await self.handle_text_message(message)
        elif msg_type == "status":
            # 状态消息，记录日志
            content = message.get("content", {})
            status = content.get("status", "")
            status_msg = content.get("message", "")
            logger.info(f"Status: {status} - {status_msg}")
        elif msg_type == "heartbeat":
            # 心跳消息，忽略
            pass
        elif msg_type == "tool_call":
            await self.handle_tool_call(message)
        else:
            logger.warning(f"Unknown message type: {msg_type}")

    async def handle_text_message(self, message: dict) -> None:
        """
        处理文本消息
        调用Agent处理并返回结果

        Args:
            message: 消息字典
        """
        content = message.get("content", {})
        text = content.get("text", "")
        from_client = message.get("from", "")

        if not text:
            return

        logger.info(f"Processing text from {from_client}: {text[:50]}...")

        # 调用Agent处理
        try:
            result = await self.process_with_agent(text)

            # 发送结果回WebSocket
            await self.send_text_response(result)

        except Exception as e:
            logger.error(f"Agent processing failed: {e}")
            await self.send_text_response(f"处理失败: {str(e)}")

    async def handle_tool_call(self, message: dict) -> None:
        """
        处理工具调用消息

        Args:
            message: 消息字典
        """
        content = message.get("content", {})
        tool_name = content.get("tool_name", "")
        parameters = content.get("parameters", {})

        logger.info(f"Tool call: {tool_name} with {parameters}")

        # 如果Agent有工具注册器，可以直接调用
        # 这里简化处理，返回提示信息
        await self.send_tool_result(tool_name, {"message": "工具调用已接收"})

    async def process_with_agent(self, text: str) -> str:
        """
        使用Agent处理文本

        Args:
            text: 输入文本

        Returns:
            Agent的处理结果
        """
        # 检查Agent是否有run方法
        if hasattr(self.agent, 'run'):
            # 在线程池中运行同步的agent.run
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, self.agent.run, text)
            return str(result)
        else:
            # 如果Agent是异步的
            if hasattr(self.agent, 'arun'):
                result = await self.agent.arun(text)
                return str(result)
            else:
                return "Agent没有可用的运行方法"

    async def send_text_response(self, text: str) -> None:
        """
        发送文本响应

        Args:
            text: 响应文本
        """
        message = {
            "id": str(uuid.uuid4()),
            "type": "text",
            "from": self.client_id,
            "session_id": self.session_id,
            "timestamp": int(time.time() * 1000),
            "content": {"text": text}
        }
        await self.send_message(message)

    async def send_tool_result(
        self,
        tool_name: str,
        result: Any,
        error: str = ""
    ) -> None:
        """
        发送工具调用结果

        Args:
            tool_name: 工具名称
            result: 工具结果
            error: 错误信息
        """
        message = {
            "id": str(uuid.uuid4()),
            "type": "tool_result",
            "from": self.client_id,
            "session_id": self.session_id,
            "timestamp": int(time.time() * 1000),
            "content": {
                "tool_name": tool_name,
                "result": result,
                "error": error
            }
        }
        await self.send_message(message)

    async def send_message(self, message: dict) -> None:
        """
        发送消息到WebSocket

        Args:
            message: 消息字典
        """
        if not self.ws or not self.running:
            logger.warning("WebSocket not connected, cannot send message")
            return

        try:
            await self.ws.send(json.dumps(message))
            logger.debug(f"Sent message: type={message.get('type')}")
        except Exception as e:
            logger.error(f"Failed to send message: {e}")

    def set_message_handler(self, handler: Callable) -> None:
        """
        设置自定义消息处理器

        Args:
            handler: 异步消息处理函数
        """
        self._message_handler = handler


async def run_agent_client(
    agent: Any,
    ws_url: str = "ws://localhost:8080",
    client_id: Optional[str] = None,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None
) -> None:
    """
    运行Agent WebSocket客户端的便捷函数

    Args:
        agent: Agent实例
        ws_url: WebSocket服务器地址
        client_id: 客户端ID
        user_id: 用户ID
        session_id: 会话ID
    """
    client = AgentWebSocketClient(
        agent=agent,
        ws_url=ws_url,
        client_id=client_id,
        user_id=user_id,
        session_id=session_id
    )

    try:
        await client.connect()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    finally:
        await client.disconnect()
