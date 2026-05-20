"""
MCP 客户端 - 连接和管理 MCP 服务器

MCP 客户端负责：
1. 连接 MCP 服务器（stdio 或 HTTP）
2. 执行 initialize 握手协议
3. 发现工具、资源、Prompts
4. 调用工具
5. 管理连接生命周期

学习重点：
1. MCP 握手协议的实现
2. 多服务器连接管理
3. 工具发现和调用
"""

from typing import Dict, Any, Optional, List
import asyncio

from .types import (
    MCPRequest, MCPResponse, MCPMethod,
    MCPToolDefinition, MCPToolResult,
    MCPResource, MCPPrompt,
    MCPServerInfo, MCPCapabilities, MCPServerConnection
)
from .transport import MCPTransport, StdioTransport, HTTPTransport


class MCPClient:
    """
    MCP 客户端

    功能：
    1. 连接和管理多个 MCP 服务器
    2. 自动执行 MCP 握手协议
    3. 自动发现服务器能力
    4. 提供统一的工具调用接口

    使用示例：
    ```python
    client = MCPClient()

    # 连接 stdio MCP 服务器
    await client.connect_stdio(
        "filesystem",
        "npx",
        ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
    )

    # 列出工具
    tools = await client.list_tools("filesystem")

    # 调用工具
    result = await client.call_tool(
        "filesystem",
        "read_file",
        {"path": "/tmp/test.txt"}
    )
    ```
    """

    def __init__(self):
        """
        初始化 MCP 客户端
        """
        self.connections: Dict[str, MCPServerConnection] = {}
        self.transports: Dict[str, MCPTransport] = {}
        self._initialized_servers: set = set()

        print("✅ MCP 客户端初始化完成")

    async def connect_stdio(
        self,
        server_name: str,
        command: str,
        args: Optional[List[str]] = None,
        env: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        通过 stdio 连接 MCP 服务器

        参数：
            server_name: 服务器名称（用于标识，如 "filesystem"）
            command: 启动命令（如 "npx", "python"）
            args: 命令参数
            env: 环境变量

        返回：
            bool: 是否成功连接
        """
        print(f"🔗 正在连接 MCP 服务器: {server_name}...")

        # 创建 stdio 传输
        transport = StdioTransport(command, args, env)

        # 启动进程
        if not await transport.connect():
            return False

        # 执行握手
        success = await self._initialize_server(server_name, transport)

        if success:
            self.transports[server_name] = transport
            print(f"✅ MCP 服务器 {server_name} 连接成功")
        else:
            await transport.close()
            print(f"❌ MCP 服务器 {server_name} 连接失败")

        return success

    async def connect_http(
        self,
        server_name: str,
        base_url: str,
        headers: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        通过 HTTP 连接 MCP 服务器

        参数：
            server_name: 服务器名称
            base_url: MCP 服务器 URL
            headers: HTTP 请求头

        返回：
            bool: 是否成功连接
        """
        print(f"🔗 正在连接 HTTP MCP 服务器: {server_name}...")

        # 创建 HTTP 传输
        transport = HTTPTransport(base_url, headers)

        # 测试连接
        if not await transport.connect():
            return False

        # 执行握手
        success = await self._initialize_server(server_name, transport)

        if success:
            self.transports[server_name] = transport
            print(f"✅ HTTP MCP 服务器 {server_name} 连接成功")
        else:
            await transport.close()
            print(f"❌ HTTP MCP 服务器 {server_name} 连接失败")

        return success

    async def _initialize_server(
        self,
        server_name: str,
        transport: MCPTransport
    ) -> bool:
        """
        执行 MCP 握手协议

        MCP 握手流程：
        1. 发送 initialize 请求
        2. 解析服务器信息和能力
        3. 发现工具、资源、Prompts

        参数：
            server_name: 服务器名称
            transport: 传输对象

        返回：
            bool: 是否成功初始化
        """
        # 发送 initialize 请求
        request = MCPRequest(
            method=MCPMethod.INITIALIZE.value,
            params={
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "q-agent",
                    "version": "1.0.0"
                }
            }
        )

        response = await transport.send(request)

        if response.is_error():
            print(f"❌ 初始化失败: {response.get_error_message()}")
            return False

        # 解析服务器信息
        result = response.result or {}
        server_info = MCPServerInfo.from_dict(result.get("serverInfo", {}))
        capabilities = MCPCapabilities.from_dict(result.get("capabilities", {}))

        print(f"  服务器: {server_info.name} v{server_info.version}")
        print(f"  协议版本: {server_info.protocolVersion}")

        # 发现工具
        tools = []
        if capabilities.has_tools():
            tools = await self._discover_tools(transport)
            print(f"  发现 {len(tools)} 个工具")

        # 发现资源
        resources = []
        if capabilities.has_resources():
            resources = await self._discover_resources(transport)
            print(f"  发现 {len(resources)} 个资源")

        # 发现 Prompts
        prompts = []
        if capabilities.has_prompts():
            prompts = await self._discover_prompts(transport)
            print(f"  发现 {len(prompts)} 个 Prompts")

        # 存储连接信息
        self.connections[server_name] = MCPServerConnection(
            info=server_info,
            capabilities=capabilities,
            tools=tools,
            resources=resources,
            prompts=prompts
        )

        self._initialized_servers.add(server_name)
        return True

    async def _discover_tools(self, transport: MCPTransport) -> List[MCPToolDefinition]:
        """
        发现 MCP 服务器提供的工具

        参数：
            transport: 传输对象

        返回：
            List[MCPToolDefinition]: 工具定义列表
        """
        request = MCPRequest(method=MCPMethod.LIST_TOOLS.value)
        response = await transport.send(request)

        if response.is_error():
            print(f"⚠️ 获取工具列表失败: {response.get_error_message()}")
            return []

        tools_data = response.result.get("tools", [])
        return [MCPToolDefinition.from_dict(t) for t in tools_data]

    async def _discover_resources(self, transport: MCPTransport) -> List[MCPResource]:
        """
        发现 MCP 服务器提供的资源

        参数：
            transport: 传输对象

        返回：
            List[MCPResource]: 资源列表
        """
        request = MCPRequest(method=MCPMethod.LIST_RESOURCES.value)
        response = await transport.send(request)

        if response.is_error():
            print(f"⚠️ 获取资源列表失败: {response.get_error_message()}")
            return []

        resources_data = response.result.get("resources", [])
        return [MCPResource.from_dict(r) for r in resources_data]

    async def _discover_prompts(self, transport: MCPTransport) -> List[MCPPrompt]:
        """
        发现 MCP 服务器提供的 Prompts

        参数：
            transport: 传输对象

        返回：
            List[MCPPrompt]: Prompt 列表
        """
        request = MCPRequest(method=MCPMethod.LIST_PROMPTS.value)
        response = await transport.send(request)

        if response.is_error():
            print(f"⚠️ 获取 Prompts 列表失败: {response.get_error_message()}")
            return []

        prompts_data = response.result.get("prompts", [])
        return [MCPPrompt.from_dict(p) for p in prompts_data]

    async def list_tools(self, server_name: str) -> List[MCPToolDefinition]:
        """
        获取指定服务器的工具列表

        参数：
            server_name: 服务器名称

        返回：
            List[MCPToolDefinition]: 工具定义列表
        """
        connection = self.connections.get(server_name)
        if not connection:
            print(f"⚠️ 服务器 {server_name} 未连接")
            return []

        return connection.tools

    async def call_tool(
        self,
        server_name: str,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> MCPToolResult:
        """
        调用 MCP 工具

        参数：
            server_name: 服务器名称
            tool_name: 工具名称
            arguments: 工具参数

        返回：
            MCPToolResult: 工具执行结果
        """
        transport = self.transports.get(server_name)
        if not transport:
            raise ValueError(f"服务器 {server_name} 未连接")

        request = MCPRequest(
            method=MCPMethod.CALL_TOOL.value,
            params={
                "name": tool_name,
                "arguments": arguments
            }
        )

        response = await transport.send(request)

        if response.is_error():
            return MCPToolResult(
                content=[{
                    "type": "text",
                    "text": response.get_error_message()
                }],
                isError=True
            )

        return MCPToolResult.from_dict(response.result or {})

    async def read_resource(self, server_name: str, uri: str) -> Any:
        """
        读取 MCP 资源

        参数：
            server_name: 服务器名称
            uri: 资源 URI

        返回：
            Any: 资源内容
        """
        transport = self.transports.get(server_name)
        if not transport:
            raise ValueError(f"服务器 {server_name} 未连接")

        request = MCPRequest(
            method=MCPMethod.READ_RESOURCE.value,
            params={"uri": uri}
        )

        response = await transport.send(request)
        return response.result

    async def get_prompt(
        self,
        server_name: str,
        prompt_name: str,
        arguments: Optional[Dict[str, str]] = None
    ) -> Any:
        """
        获取 MCP Prompt

        参数：
            server_name: 服务器名称
            prompt_name: Prompt 名称
            arguments: Prompt 参数

        返回：
            Any: Prompt 内容
        """
        transport = self.transports.get(server_name)
        if not transport:
            raise ValueError(f"服务器 {server_name} 未连接")

        request = MCPRequest(
            method=MCPMethod.GET_PROMPT.value,
            params={
                "name": prompt_name,
                "arguments": arguments or {}
            }
        )

        response = await transport.send(request)
        return response.result

    def get_all_tools(self) -> Dict[str, List[MCPToolDefinition]]:
        """
        获取所有服务器的工具

        返回：
            Dict[str, List]: {server_name: [tools]}
        """
        return {
            name: conn.tools
            for name, conn in self.connections.items()
        }

    def get_server_info(self, server_name: str) -> Optional[MCPServerConnection]:
        """
        获取服务器连接信息

        参数：
            server_name: 服务器名称

        返回：
            MCPServerConnection: 连接信息
        """
        return self.connections.get(server_name)

    def list_servers(self) -> List[str]:
        """
        列出所有已连接的服务器

        返回：
            List[str]: 服务器名称列表
        """
        return list(self.connections.keys())

    async def disconnect(self, server_name: str):
        """
        断开指定服务器连接

        参数：
            server_name: 服务器名称
        """
        transport = self.transports.pop(server_name, None)
        if transport:
            await transport.close()

        self.connections.pop(server_name, None)
        self._initialized_servers.discard(server_name)
        print(f"✅ 已断开 MCP 服务器 {server_name}")

    async def disconnect_all(self):
        """
        断开所有服务器连接
        """
        for server_name in list(self.transports.keys()):
            await self.disconnect(server_name)

        print("✅ 所有 MCP 服务器连接已断开")

    def is_connected(self, server_name: str) -> bool:
        """
        检查服务器是否已连接

        参数：
            server_name: 服务器名称

        返回：
            bool: 是否已连接
        """
        return server_name in self._initialized_servers


# 使用示例
if __name__ == "__main__":
    """MCP 客户端使用示例"""

    print("=" * 60)
    print("MCP 客户端示例")
    print("=" * 60)

    async def demo():
        # 创建客户端
        client = MCPClient()

        print("\n📝 连接 MCP 服务器示例:")
        print("  await client.connect_stdio('filesystem', 'npx', ['-y', '@modelcontextprotocol/server-filesystem'])")

        print("\n📝 获取工具列表示例:")
        print("  tools = await client.list_tools('filesystem')")

        print("\n📝 调用工具示例:")
        print("  result = await client.call_tool('filesystem', 'read_file', {'path': '/tmp/test.txt'})")

        print("\n" + "=" * 60)
        print("示例执行完成！")
        print("=" * 60)

    # 运行异步示例
    asyncio.run(demo())