#!/usr/bin/env python3
"""
Agent WebSocket客户端集成示例

演示如何将Python Agent核心连接到WebSocket平台

使用方法:
    python examples/agent_websocket.py

环境变量:
    Q_AGENT_LLM_API_KEY: LLM API密钥（可选，不设置则使用模拟模式）
    Q_AGENT_LLM_PROVIDER: LLM提供商（可选，默认openai）
    WS_URL: WebSocket服务器地址（可选，默认ws://localhost:8080）
"""

import asyncio
import logging
import os
import sys
import uuid

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from q_agent.core.agent import Agent
from q_agent.core.memory import Memory
from q_agent.core.context import ContextManager
from q_agent.core.llm_client import LLMClientFactory
from q_agent.tools import ToolRegistry, CalculatorTool, FileReadTool, SearchTool
from q_agent.websocket_client import AgentWebSocketClient, run_agent_client

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_agent() -> Agent:
    """
    创建并配置Agent实例

    Returns:
        配置好的Agent实例
    """
    # 创建记忆和上下文管理器
    memory = Memory(storage_type="memory")
    context_manager = ContextManager(max_tokens=4000)

    # 创建工具注册器并注册工具
    tool_registry = ToolRegistry()
    tool_registry.register(CalculatorTool())
    tool_registry.register(FileReadTool())
    tool_registry.register(SearchTool())

    # 创建LLM客户端
    llm_client = None
    api_key = os.environ.get("Q_AGENT_LLM_API_KEY", "")
    provider = os.environ.get("Q_AGENT_LLM_PROVIDER", "openai")

    if api_key:
        try:
            llm_client = LLMClientFactory.create({
                "provider": provider,
                "api_key": api_key,
                "model": "gpt-3.5-turbo" if provider == "openai" else "claude-3-sonnet-20240229"
            })
            logger.info(f"LLM client created: provider={provider}")
        except Exception as e:
            logger.warning(f"Failed to create LLM client: {e}")
            logger.info("Running in mock mode (no LLM)")
    else:
        logger.info("No API key provided, running in mock mode")

    # 创建Agent
    agent = Agent(
        memory=memory,
        context_manager=context_manager,
        tools=tool_registry.list_tools(),
        llm_client=llm_client
    )

    return agent


class MockAgent:
    """
    模拟Agent（用于测试，不需要LLM API）
    """

    def __init__(self):
        self.name = "MockAgent"

    def run(self, task: str) -> str:
        """简单的模拟响应"""
        logger.info(f"MockAgent processing: {task[:50]}...")

        # 简单的规则响应
        task_lower = task.lower()

        if "你好" in task or "hello" in task_lower:
            return "你好！我是AI助手，有什么可以帮助你的吗？"

        if "计算" in task:
            # 尝试提取数学表达式
            import re
            match = re.search(r'(\d+)\s*([+\-*/])\s*(\d+)', task)
            if match:
                a, op, b = match.groups()
                try:
                    result = eval(f"{a}{op}{b}")
                    return f"计算结果是: {a} {op} {b} = {result}"
                except:
                    pass
            return "请告诉我你想计算什么，例如：计算 123 + 456"

        if "时间" in task or "time" in task_lower:
            from datetime import datetime
            return f"现在的时间是: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

        if "天气" in task:
            return "抱歉，我暂时无法查询天气信息。"

        # 默认响应
        return f"我收到了你的消息: \"{task}\"。我是模拟Agent，请在环境变量中设置Q_AGENT_LLM_API_KEY以启用真正的AI功能。"


async def main():
    """
    主函数：启动Agent WebSocket客户端
    """
    # 获取配置
    ws_url = os.environ.get("WS_URL", "ws://localhost:8080")
    client_id = os.environ.get("CLIENT_ID", f"agent_{uuid.uuid4().hex[:8]}")
    user_id = os.environ.get("USER_ID", "demo_user")
    session_id = os.environ.get("SESSION_ID", "demo_session")

    # 检查是否使用模拟Agent
    use_mock = os.environ.get("USE_MOCK", "true").lower() == "true"
    api_key = os.environ.get("Q_AGENT_LLM_API_KEY", "")

    if use_mock or not api_key:
        logger.info("Using MockAgent (set USE_MOCK=false and Q_AGENT_LLM_API_KEY to use real Agent)")
        agent = MockAgent()
    else:
        logger.info("Creating real Agent with LLM")
        agent = create_agent()

    # 打印连接信息
    print("\n" + "=" * 60)
    print("Agent WebSocket客户端启动")
    print("=" * 60)
    print(f"WebSocket服务器: {ws_url}")
    print(f"客户端ID: {client_id}")
    print(f"用户ID: {user_id}")
    print(f"会话ID: {session_id}")
    print(f"Agent类型: {'MockAgent' if isinstance(agent, MockAgent) else 'RealAgent'}")
    print("=" * 60)
    print("\n等待消息中... (Ctrl+C 退出)\n")

    # 创建并运行客户端
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
        print("\n\n正在断开连接...")
    finally:
        await client.disconnect()
        print("已断开连接，再见！")


if __name__ == "__main__":
    asyncio.run(main())
