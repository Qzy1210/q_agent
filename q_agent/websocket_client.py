"""
Agent WebSocket客户端
将Python Agent核心连接到WebSocket平台

消息处理逻辑：
1. 新消息 → 保存到数据库 → Agent执行 → 保存响应 → 发送给前端
2. 历史消息请求 → 直接查询数据库返回 → 不重新执行
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

    消息类型区分：
    - text: 新消息，需要Agent处理
    - history: 历史消息请求，直接返回数据库记录
    """

    def __init__(
        self,
        agent: Any,
        ws_url: str = "ws://localhost:8088",
        client_id: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        message_store: Optional[Any] = None
    ):
        """
        初始化Agent WebSocket客户端

        Args:
            agent: Agent实例（需要有run方法）
            ws_url: WebSocket服务器地址
            client_id: 客户端ID（可选，自动生成）
            user_id: 用户ID（可选，自动生成）
            session_id: 会话ID（可选，自动生成）
            message_store: 消息存储实例（用于保存历史）
        """
        self.agent = agent
        self.ws_url = ws_url
        self.client_id = client_id or f"agent_{uuid.uuid4().hex[:8]}"
        self.user_id = user_id or f"user_{uuid.uuid4().hex[:8]}"
        self.session_id = session_id or f"session_{uuid.uuid4().hex[:8]}"
        self.message_store = message_store  # 消息存储

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
        logger.info("=" * 50)
        logger.info("WebSocket 连接中...")
        logger.info(f"  服务器地址: {self.ws_url}")
        logger.info(f"  客户端ID: {self.client_id}")
        logger.info(f"  用户ID: {self.user_id}")
        logger.info(f"  会话ID: {self.session_id}")
        logger.info(f"  完整URL: {url}")
        logger.info("=" * 50)

        try:
            self.ws = await websockets.connect(url)
            self.running = True
            logger.info("✓ WebSocket 连接成功，开始监听消息...")

            # 启动消息处理循环
            await self.message_loop()
        except Exception as e:
            logger.error(f"✗ WebSocket 连接失败: {e}")
            raise

    async def disconnect(self) -> None:
        """
        断开WebSocket连接
        """
        logger.info("WebSocket 断开连接中...")
        self.running = False
        if self.ws:
            await self.ws.close()
            self.ws = None
        logger.info("✓ WebSocket 已断开连接")

    async def message_loop(self) -> None:
        """
        消息处理循环
        接收WebSocket消息并处理
        """
        if not self.ws:
            logger.error("WebSocket not connected")
            return

        logger.info(f"消息处理循环已启动，等待消息... (client_id={self.client_id})")

        try:
            async for message in self.ws:
                if not self.running:
                    break

                try:
                    await self.handle_message(message)
                except Exception as e:
                    logger.error(f"处理消息时出错: {e}")
        except websockets.ConnectionClosed as e:
            logger.warning(f"WebSocket 连接已关闭: code={e.code}, reason={e.reason}")
            self.running = False
        except Exception as e:
            logger.error(f"消息循环出错: {e}")
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
            logger.error(f"消息JSON解析失败: {e}")
            return

        # 处理双重JSON编码的情况：解析后可能是字符串
        if isinstance(message, str):
            logger.warning("检测到双重JSON编码，尝试再次解析...")
            try:
                message = json.loads(message)
            except json.JSONDecodeError as e:
                logger.error(f"二次JSON解析失败: {e}")
                return

        # 确保message是字典类型
        if not isinstance(message, dict):
            logger.error(f"消息格式错误: 期望dict，得到 {type(message).__name__}: {message}")
            return

        msg_type = message.get("type", "")
        msg_id = message.get("id", "")
        msg_from = message.get("from", "")
        msg_session = message.get("session_id", "")

        logger.info(f"📥 收到消息: type={msg_type}, id={msg_id}, from={msg_from}, session={msg_session}")

        # 处理不同类型的消息
        if msg_type == "text":
            await self.handle_text_message(message)
        elif msg_type == "history":
            # 历史消息请求 - 直接返回数据库记录，不重新执行
            await self.handle_history_request(message)
        elif msg_type == "status":
            # 状态消息，记录日志
            content = message.get("content", {})
            # 处理 content 是 JSON 字符串的情况
            if isinstance(content, str):
                try:
                    content = json.loads(content)
                except json.JSONDecodeError:
                    content = {}
            if not isinstance(content, dict):
                content = {}
            status = content.get("status", "")
            status_msg = content.get("message", "")
            logger.info(f"📊 状态消息: {status} - {status_msg}")
        elif msg_type == "heartbeat":
            # 心跳消息，忽略（但记录debug日志）
            logger.debug("💓 收到心跳消息")
        elif msg_type == "tool_call":
            await self.handle_tool_call(message)
        else:
            logger.warning(f"⚠️ 未知消息类型: {msg_type}")

    async def handle_text_message(self, message: dict) -> None:
        """
        处理文本消息
        调用Agent处理并返回结果

        流程：
        1. 保存用户消息到数据库
        2. 调用Agent处理
        3. 保存Agent响应到数据库
        4. 发送响应给前端

        Args:
            message: 消息字典
        """
        content = message.get("content", {})

        # 处理 content 是 JSON 字符串的情况（双重编码）
        if isinstance(content, str):
            try:
                content = json.loads(content)
            except json.JSONDecodeError as e:
                logger.error(f"content JSON解析失败: {e}")
                content = {}

        # 确保 content 是字典类型
        if not isinstance(content, dict):
            logger.warning(f"content 格式异常: {type(content).__name__}")
            content = {}

        text = content.get("text", "")
        from_client = message.get("from", "")
        msg_id = message.get("id", "")
        session_id = message.get("session_id", self.session_id)
        user_id = message.get("user_id", self.user_id)

        if not text:
            return

        logger.info(f"💬 处理文本消息: from={from_client}, msg_id={msg_id}")
        logger.info(f"   消息内容: {text[:100]}{'...' if len(text) > 100 else ''}")

        # 1. 保存用户消息到数据库
        if self.message_store:
            self.message_store.save_message(
                session_id=session_id,
                role="user",
                content=text,
                user_id=user_id
            )
            logger.debug(f"   用户消息已保存到数据库")

        # 2. 调用Agent处理
        try:
            logger.info(f"   调用Agent处理...")
            result = await self.process_with_agent(text)

            # 处理不同类型的响应
            if isinstance(result, dict):
                # AgentResult.to_dict() 返回的字典
                result_text = result.get("result", "")
                logger.info(f"   Agent返回结果: {result_text[:100]}{'...' if len(result_text) > 100 else ''}")

                # 3. 保存Agent响应到数据库（只保存文本结果）
                if self.message_store:
                    self.message_store.save_message(
                        session_id=session_id,
                        role="assistant",
                        content=result_text,
                        user_id=user_id
                    )
                    logger.debug(f"   Agent响应已保存到数据库")

                # 4. 发送完整结果回WebSocket（包含工具调用信息）
                await self.send_agent_response(result, session_id=session_id)
            else:
                # 字符串响应
                logger.info(f"   Agent返回结果: {result[:100]}{'...' if len(result) > 100 else ''}")

                # 3. 保存Agent响应到数据库
                if self.message_store:
                    self.message_store.save_message(
                        session_id=session_id,
                        role="assistant",
                        content=result,
                        user_id=user_id
                    )
                    logger.debug(f"   Agent响应已保存到数据库")

                # 4. 发送结果回WebSocket
                await self.send_text_response(result, session_id=session_id)

            logger.info(f"✓ 已发送响应消息")

        except Exception as e:
            logger.error(f"✗ Agent处理失败: {e}")
            await self.send_text_response(f"处理失败: {str(e)}", session_id=session_id)

    async def handle_history_request(self, message: dict) -> None:
        """
        处理历史消息请求

        直接从数据库查询历史消息返回，不重新执行Agent

        Args:
            message: 消息字典
        """
        content = message.get("content", {})

        # 处理 content 是 JSON 字符串的情况（双重编码）
        if isinstance(content, str):
            try:
                content = json.loads(content)
            except json.JSONDecodeError as e:
                logger.error(f"content JSON解析失败: {e}")
                content = {}

        if not isinstance(content, dict):
            content = {}

        session_id = content.get("session_id", self.session_id)
        limit = content.get("limit", 100)

        logger.info(f"📜 历史消息请求: session_id={session_id}")

        if not self.message_store:
            logger.warning("消息存储未初始化，无法获取历史")
            await self.send_history_response([], session_id)
            return

        # 从数据库查询历史消息
        history = self.message_store.get_session_history(session_id, limit=limit)
        logger.info(f"   查询到 {len(history)} 条历史消息")

        # 返回历史消息
        await self.send_history_response(history, session_id)

    async def handle_tool_call(self, message: dict) -> None:
        """
        处理工具调用消息

        Args:
            message: 消息字典
        """
        content = message.get("content", {})

        # 处理 content 是 JSON 字符串的情况（双重编码）
        if isinstance(content, str):
            try:
                content = json.loads(content)
            except json.JSONDecodeError as e:
                logger.error(f"content JSON解析失败: {e}")
                content = {}

        if not isinstance(content, dict):
            content = {}

        tool_name = content.get("tool_name", "")
        parameters = content.get("parameters", {})

        logger.info(f"🔧 工具调用请求: tool_name={tool_name}")
        logger.info(f"   参数: {parameters}")

        # 如果Agent有工具注册器，可以直接调用
        # 这里简化处理，返回提示信息
        await self.send_tool_result(tool_name, {"message": "工具调用已接收"})
        logger.info(f"✓ 工具调用响应已发送")

    async def process_with_agent(self, text: str) -> str:
        """
        使用Agent处理文本

        Args:
            text: 输入文本

        Returns:
            Agent的处理结果（字符串或字典）
        """
        # 检查Agent是否有run方法
        if hasattr(self.agent, 'run'):
            # 在线程池中运行同步的agent.run
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, self.agent.run, text)

            # 如果结果是 AgentResult 对象，返回完整信息
            if hasattr(result, 'to_dict'):
                return result.to_dict()
            return str(result)
        else:
            # 如果Agent是异步的
            if hasattr(self.agent, 'arun'):
                result = await self.agent.arun(text)
                if hasattr(result, 'to_dict'):
                    return result.to_dict()
                return str(result)
            else:
                return "Agent没有可用的运行方法"

    async def send_text_response(self, text: str, session_id: Optional[str] = None) -> None:
        """
        发送文本响应

        Args:
            text: 响应文本
            session_id: 会话ID（可选，默认使用实例的session_id）
        """
        message = {
            "id": str(uuid.uuid4()),
            "type": "text",
            "from": self.client_id,
            "session_id": session_id or self.session_id,
            "timestamp": int(time.time() * 1000),
            "content": {"text": text}
        }
        await self.send_message(message)

    async def send_agent_response(self, result: dict, session_id: Optional[str] = None) -> None:
        """
        发送 Agent 完整响应（包含工具调用信息）

        Args:
            result: AgentResult.to_dict() 返回的字典
            session_id: 会话ID
        """
        message = {
            "id": str(uuid.uuid4()),
            "type": "agent_result",
            "from": self.client_id,
            "session_id": session_id or self.session_id,
            "timestamp": int(time.time() * 1000),
            "content": result
        }
        await self.send_message(message)

    async def send_history_response(self, history: list, session_id: str) -> None:
        """
        发送历史消息响应

        Args:
            history: 历史消息列表
            session_id: 会话ID
        """
        message = {
            "id": str(uuid.uuid4()),
            "type": "history",
            "from": self.client_id,
            "session_id": session_id,
            "timestamp": int(time.time() * 1000),
            "content": {
                "messages": history,
                "total": len(history)
            }
        }
        await self.send_message(message)
        logger.info(f"📤 历史消息已发送: {len(history)} 条")

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
            logger.warning("WebSocket 未连接，无法发送消息")
            return

        try:
            await self.ws.send(json.dumps(message))
            logger.info(f"📤 消息已发送: type={message.get('type')}, id={message.get('id')}")
        except Exception as e:
            logger.error(f"✗ 发送消息失败: {e}")

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
    session_id: Optional[str] = None,
    message_store: Optional[Any] = None
) -> None:
    """
    运行Agent WebSocket客户端的便捷函数

    Args:
        agent: Agent实例
        ws_url: WebSocket服务器地址
        client_id: 客户端ID
        user_id: 用户ID
        session_id: 会话ID
        message_store: 消息存储实例（用于保存历史消息）
    """
    client = AgentWebSocketClient(
        agent=agent,
        ws_url=ws_url,
        client_id=client_id,
        user_id=user_id,
        session_id=session_id,
        message_store=message_store
    )

    try:
        await client.connect()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    finally:
        await client.disconnect()
