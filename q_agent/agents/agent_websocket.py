#!/usr/bin/env python3
"""
Agent WebSocket客户端集成示例

演示如何将Python Agent核心连接到WebSocket平台

使用方法:
    python agents/agent_websocket.py

配置文件:
    config.json - 项目根目录配置文件，包含LLM、WebSocket等所有配置
"""

import asyncio
import logging
import os
import sys
import uuid

# 添加项目根目录到路径 (从 q_agent/q_agent/agents/ 上升到 q_agent/)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from q_agent.config.config import Config
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


def create_agent(config: Config) -> Agent:
    """
    创建并配置Agent实例

    Args:
        config: 配置管理器实例，从config.json加载

    Returns:
        配置好的Agent实例
    """
    # 从配置获取Agent参数
    max_tokens = config.get("agent.context_window", 4000)
    memory_size = config.get("agent.memory_size", 20)
    max_iterations = config.get("agent.max_iterations", 10)
    timeout = config.get("agent.timeout", 300)

    # 创建记忆和上下文管理器
    memory = Memory()
    context_manager = ContextManager(max_tokens=max_tokens)

    # 创建工具注册器并注册工具
    tool_registry = ToolRegistry()
    tool_registry.register(CalculatorTool())
    tool_registry.register(FileReadTool())
    tool_registry.register(SearchTool())

    # 从配置创建LLM客户端
    llm_client = None
    api_key = config.get("llm.api_key", "")
    provider = config.get("llm.provider", "openai")
    model = config.get("llm.model", "")
    base_url = config.get("llm.base_url", "")
    temperature = config.get("llm.temperature", 0.7)
    llm_max_tokens = config.get("llm.max_tokens", 2000)

    if api_key:
        try:
            llm_config = {
                "provider": provider,
                "api_key": api_key,
                "model": model,
                "temperature": temperature,
                "max_tokens": llm_max_tokens,
            }
            if base_url:
                llm_config["base_url"] = base_url

            llm_client = LLMClientFactory.create(llm_config)
            logger.info(f"LLM client created: provider={provider}, model={model}")
        except Exception as e:
            logger.warning(f"Failed to create LLM client: {e}")
            logger.info("Running in mock mode (no LLM)")
    else:
        logger.info("No API key configured, running in mock mode")
    # 创建Agent
    agent = Agent(
        memory=memory,
        context_manager=context_manager,
        tools=tool_registry.get_tools(),  # 使用get_tools()返回Tool对象列表
        llm_client=llm_client,
        skill_dirs=config.get("skill.dirs", [""]),
        config=config,
    )

    return agent

async def main():
    """
    主函数：启动Agent WebSocket客户端
    """
    # 加载配置文件 (从 q_agent/q_agent/agents/ 上升到 q_agent/ 项目根目录)
    config_file = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "config.json"
    )
    config = Config(config_file=config_file)

    # 从配置获取WebSocket参数
    ws_url = config.get("websocket.url", "ws://localhost:8088")
    client_id = config.get("websocket.client_id", f"agent_{uuid.uuid4().hex[:8]}")
    user_id = config.get("websocket.user_id", "demo_user")
    session_id = config.get("websocket.session_id", "demo_session")

    agent = create_agent(config)

    # 打印连接信息
    print("\n" + "=" * 60)
    print("Agent WebSocket客户端启动")
    print("=" * 60)
    print(f"配置文件: {config_file}")
    print(f"WebSocket服务器: {ws_url}")
    print(f"客户端ID: {client_id}")
    print(f"用户ID: {user_id}")
    print(f"会话ID: {session_id}")
    print(f"LLM Provider: {config.get('llm.provider')}")
    print(f"LLM Model: {config.get('llm.model')}")
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
