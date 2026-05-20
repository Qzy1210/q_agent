"""
MCP (Model Context Protocol) 使用示例

演示如何使用 q_agent 的 MCP 支持：
1. 连接 MCP 服务器
2. 发现和使用 MCP 工具
3. Agent 集成 MCP 工具
4. 配置文件加载

前置条件：
- 安装 Node.js 和 npx
- 运行: npm install -g @modelcontextprotocol/server-filesystem

文档：https://modelcontextprotocol.io/
"""

import sys
import os
import asyncio

# 添加项目根目录到 Python 路径 (从 q_agent/q_agent/agents/ 上升到 q_agent/)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from q_agent.core import Agent
from q_agent.tools import FileReadTool
from q_agent.mcp import MCPClient, MCPToolRegistry


async def example_basic_mcp():
    """
    示例 1: 基本使用 - 直接使用 MCPClient
    """
    print("=" * 60)
    print("示例 1: 基本使用 - 直接使用 MCPClient")
    print("=" * 60)

    # 创建 MCP 客户端
    client = MCPClient()

    print("\n提示: 此示例需要安装 Node.js 和 MCP 服务器")
    print("运行: npm install -g @modelcontextprotocol/server-filesystem\n")

    try:
        # 连接 filesystem MCP 服务器
        success = await client.connect_stdio(
            server_name="filesystem",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
        )

        if success:
            # 列出可用工具
            tools = await client.list_tools("filesystem")
            print(f"\n发现 {len(tools)} 个工具:")
            for tool in tools:
                print(f"  - {tool.name}: {tool.description}")

            # 调用工具
            print("\n调用 read_file 工具读取 /tmp/test.txt...")
            # 先创建测试文件
            import subprocess
            subprocess.run(["sh", "-c", "echo 'Hello, MCP!' > /tmp/test.txt"])

            result = await client.call_tool(
                "filesystem",
                "read_file",
                {"path": "/tmp/test.txt"}
            )

            print(f"结果: {result.get_text_content()}")

            # 断开连接
            await client.disconnect("filesystem")

    except Exception as e:
        print(f"⚠️ 示例执行失败: {e}")
        print("请确保已安装 Node.js 和 MCP 服务器")

    print()


async def example_agent_with_mcp():
    """
    示例 2: Agent 集成 MCP
    """
    print("=" * 60)
    print("示例 2: Agent 集成 MCP")
    print("=" * 60)

    # 创建 Agent
    agent = Agent(
        name="MCP Agent",
        tools=[FileReadTool()]  # 本地工具
    )

    print("\n提示: 此示例需要安装 Node.js 和 MCP 服务器\n")

    try:
        # 连接 MCP 服务器
        success = await agent.connect_mcp_stdio(
            server_name="filesystem",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
        )

        if success:
            # 列出 MCP 工具
            mcp_tools = agent.list_mcp_tools()
            print(f"\nMCP 工具: {list(mcp_tools.keys())}")

            # 现在 Agent 可以同时使用本地工具和 MCP 工具
            print("\nAgent 工具列表:")
            for tool in agent.tools:
                print(f"  - {tool.name}")

            # 断开连接
            await agent.disconnect_mcp()

    except Exception as e:
        print(f"⚠️ 示例执行失败: {e}")

    print()


async def example_tool_adapter():
    """
    示例 3: 使用 MCP 工具适配器
    """
    print("=" * 60)
    print("示例 3: 使用 MCP 工具适配器")
    print("=" * 60)

    # 创建 MCP 客户端
    client = MCPClient()

    print("\n提示: 此示例需要安装 Node.js 和 MCP 服务器\n")

    try:
        success = await client.connect_stdio(
            server_name="filesystem",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
        )

        if success:
            # 创建工具适配器注册器
            from q_agent.tools import ToolRegistry
            tool_registry = ToolRegistry()

            adapter_registry = MCPToolRegistry(client)
            count = adapter_registry.register_all_tools(tool_registry)

            print(f"\n已注册 {count} 个 MCP 工具到 ToolRegistry")

            # 列出所有适配器
            for name, adapter in adapter_registry.list_adapters().items():
                print(f"  - {name}: {adapter.description[:50]}...")

            # 断开连接
            await client.disconnect("filesystem")

    except Exception as e:
        print(f"⚠️ 示例执行失败: {e}")

    print()


def example_config_file():
    """
    示例 4: 配置文件格式
    """
    print("=" * 60)
    print("示例 4: MCP 配置文件格式")
    print("=" * 60)

    config_yaml = """
# q_agent/config/mcp.yaml

mcp_servers:
  # 文件系统 MCP Server
  - name: filesystem
    transport: stdio
    command: npx
    args:
      - "-y"
      - "@modelcontextprotocol/server-filesystem"
      - "/tmp"
    enabled: true

  # GitHub MCP Server
  - name: github
    transport: stdio
    command: npx
    args:
      - "-y"
      - "@modelcontextprotocol/server-github"
    env:
      GITHUB_TOKEN: ${GITHUB_TOKEN}
    enabled: false

  # 自定义 HTTP MCP Server
  - name: custom_api
    transport: http
    base_url: https://api.example.com/mcp
    headers:
      Authorization: Bearer ${API_TOKEN}
    enabled: false
"""

    print(config_yaml)
    print()


async def example_multiple_servers():
    """
    示例 5: 连接多个 MCP 服务器
    """
    print("=" * 60)
    print("示例 5: 连接多个 MCP 服务器")
    print("=" * 60)

    client = MCPClient()

    print("\n提示: 此示例需要安装 Node.js 和多个 MCP 服务器\n")

    try:
        # 连接 filesystem 服务器
        print("连接 filesystem 服务器...")
        await client.connect_stdio(
            "filesystem",
            "npx",
            ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
        )

        # 连接 github 服务器（需要 GITHUB_TOKEN）
        # await client.connect_stdio(
        #     "github",
        #     "npx",
        #     ["-y", "@modelcontextprotocol/server-github"]
        # )

        # 列出所有服务器
        servers = client.list_servers()
        print(f"\n已连接的服务器: {servers}")

        # 获取所有工具
        all_tools = client.get_all_tools()
        for server_name, tools in all_tools.items():
            print(f"\n{server_name} 工具:")
            for tool in tools:
                print(f"  - {tool.name}")

        # 断开所有连接
        await client.disconnect_all()

    except Exception as e:
        print(f"⚠️ 示例执行失败: {e}")

    print()


async def main():
    """运行所有示例"""
    print("\n" + "=" * 60)
    print("q_agent MCP 使用示例")
    print("=" * 60 + "\n")

    # 显示配置文件示例（不需要 MCP 服务器）
    example_config_file()

    # 需要安装 MCP 服务器的示例
    await example_basic_mcp()
    await example_agent_with_mcp()
    await example_tool_adapter()
    await example_multiple_servers()

    print("=" * 60)
    print("所有示例执行完成！")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
