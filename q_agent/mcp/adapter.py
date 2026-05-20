"""
MCP 工具适配器 - 将 MCP Tool 包装为 q_agent 的 Tool 接口

使 MCP 工具可以：
1. 被注册到 ToolRegistry
2. 被 Agent 直接调用
3. 与本地工具统一管理

学习重点：
1. 适配器模式的应用
2. MCP 工具与本地工具的统一
3. 异步转同步的处理
"""

from typing import Dict, Any, Optional
import asyncio

from ..tools.base import Tool, ToolResult
from .types import MCPToolDefinition, MCPToolResult
from .client import MCPClient


class MCPToolAdapter(Tool):
    """
    MCP 工具适配器

    将 MCP 工具包装为 q_agent 的 Tool，使其可以：
    - 被注册到 ToolRegistry
    - 被 Agent 直接调用
    - 与本地工具统一管理

    使用示例：
    ```python
    # 创建适配器
    adapter = MCPToolAdapter(
        mcp_client=client,
        server_name="filesystem",
        tool_definition=tool_def
    )

    # 注册到 ToolRegistry
    registry.register(adapter)

    # 像普通工具一样调用
    result = adapter.execute(path="/tmp/test.txt")
    ```
    """

    def __init__(
        self,
        mcp_client: MCPClient,
        server_name: str,
        tool_definition: MCPToolDefinition
    ):
        """
        初始化适配器

        参数：
            mcp_client: MCP 客户端实例
            server_name: MCP 服务器名称
            tool_definition: MCP 工具定义
        """
        self._mcp_client = mcp_client
        self._server_name = server_name
        self._tool_definition = tool_definition

    @property
    def name(self) -> str:
        """
        工具名称

        格式：{server_name}_{tool_name}
        添加服务器前缀以避免不同服务器的工具名冲突
        """
        original_name = self._tool_definition.name

        # 如果工具名已包含前缀，直接使用
        if "_" in original_name:
            return original_name

        # 添加服务器前缀
        return f"{self._server_name}_{original_name}"

    @property
    def description(self) -> str:
        """
        工具描述

        添加服务器来源信息
        """
        original_desc = self._tool_definition.description
        return f"[MCP:{self._server_name}] {original_desc}"

    @property
    def parameters(self) -> Dict[str, Any]:
        """
        参数定义

        映射 MCP 的 inputSchema 到 Tool 的 parameters
        """
        return self._tool_definition.inputSchema

    @property
    def server_name(self) -> str:
        """所属服务器名称"""
        return self._server_name

    @property
    def original_name(self) -> str:
        """MCP 工具原始名称（不带前缀）"""
        return self._tool_definition.name

    def execute(self, **kwargs) -> ToolResult:
        """
        执行工具

        将 q_agent 的 Tool 调用转换为 MCP 工具调用

        参数：
            **kwargs: 工具参数

        返回：
            ToolResult: 执行结果（统一格式）
        """
        try:
            # 在新的事件循环中运行异步调用
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                # 调用 MCP 工具
                mcp_result: MCPToolResult = loop.run_until_complete(
                    self._mcp_client.call_tool(
                        self._server_name,
                        self._tool_definition.name,
                        kwargs
                    )
                )
            finally:
                loop.close()

            # 转换结果格式：MCPToolResult → ToolResult
            if mcp_result.isError:
                error_text = mcp_result.get_text_content()
                return ToolResult(
                    success=False,
                    result=None,
                    error=error_text
                )

            # 成功结果
            content = mcp_result.get_text_content()
            return ToolResult(
                success=True,
                result=content,
                metadata={
                    "server": self._server_name,
                    "tool": self._tool_definition.name,
                    "is_mcp": True
                }
            )

        except Exception as e:
            return ToolResult(
                success=False,
                result=None,
                error=f"MCP 工具调用失败: {str(e)}"
            )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式（包含 MCP 信息）"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "type": "mcp_tool",
            "server": self._server_name,
            "original_name": self._tool_definition.name
        }


class MCPToolRegistry:
    """
    MCP 工具注册器

    自动发现 MCP 服务器的工具并注册到 ToolRegistry

    使用示例：
    ```python
    # 创建 MCP 客户端
    mcp_client = MCPClient()
    await mcp_client.connect_stdio("filesystem", "npx", ["-y", "@modelcontextprotocol/server-filesystem"])

    # 创建适配器注册器
    adapter_registry = MCPToolRegistry(mcp_client)

    # 注册所有 MCP 工具到 ToolRegistry
    tool_registry = ToolRegistry()
    adapter_registry.register_all_tools(tool_registry)
    ```
    """

    def __init__(self, mcp_client: MCPClient):
        """
        初始化

        参数：
            mcp_client: MCP 客户端实例
        """
        self.mcp_client = mcp_client
        self._adapters: Dict[str, MCPToolAdapter] = {}

        print("✅ MCP 工具适配器初始化完成")

    def register_all_tools(self, tool_registry: Any) -> int:
        """
        将所有 MCP 工具注册到 ToolRegistry

        参数：
            tool_registry: ToolRegistry 实例

        返回：
            int: 注册的工具数量
        """
        all_tools = self.mcp_client.get_all_tools()
        count = 0

        for server_name, tools in all_tools.items():
            for tool_def in tools:
                # 创建适配器
                adapter = MCPToolAdapter(
                    self.mcp_client,
                    server_name,
                    tool_def
                )

                # 注册到 ToolRegistry
                tool_registry.register(adapter)

                # 保存适配器引用
                self._adapters[adapter.name] = adapter
                count += 1

        print(f"✅ 已注册 {count} 个 MCP 工具")
        return count

    def register_tools_from_server(
        self,
        tool_registry: Any,
        server_name: str
    ) -> int:
        """
        注册指定服务器的工具

        参数：
            tool_registry: ToolRegistry 实例
            server_name: 服务器名称

        返回：
            int: 注册的工具数量
        """
        connection = self.mcp_client.get_server_info(server_name)
        if not connection:
            print(f"⚠️ 服务器 {server_name} 未连接")
            return 0

        count = 0
        for tool_def in connection.tools:
            adapter = MCPToolAdapter(
                self.mcp_client,
                server_name,
                tool_def
            )

            tool_registry.register(adapter)
            self._adapters[adapter.name] = adapter
            count += 1

        print(f"✅ 从服务器 {server_name} 注册了 {count} 个工具")
        return count

    def get_adapter(self, tool_name: str) -> Optional[MCPToolAdapter]:
        """
        获取适配器

        参数：
            tool_name: 工具名称

        返回：
            MCPToolAdapter: 适配器实例
        """
        return self._adapters.get(tool_name)

    def list_adapters(self) -> Dict[str, MCPToolAdapter]:
        """
        列出所有适配器

        返回：
            Dict[str, MCPToolAdapter]: 适配器字典
        """
        return self._adapters.copy()

    def get_adapter_count(self) -> int:
        """获取适配器数量"""
        return len(self._adapters)


# 使用示例
if __name__ == "__main__":
    """MCP 工具适配器示例"""

    print("=" * 60)
    print("MCP 工具适配器示例")
    print("=" * 60)

    print("\n📝 适配器使用示例:")
    print("""
    # 创建 MCP 客户端并连接
    client = MCPClient()
    await client.connect_stdio('filesystem', 'npx ['-y', '@modelcontextprotocol/server-filesystem'])

    # 创建适配器注册器
    adapter_registry = MCPToolRegistry(client)

    # 注册到 ToolRegistry
    tool_registry = ToolRegistry()
    adapter_registry.register_all_tools(tool_registry)

    # 现在 MCP 工具可以像本地工具一样使用
    result = tool_registry.execute_tool('filesystem_read_file', path='/tmp/test.txt')
    """)

    print("\n" + "=" * 60)
    print("示例执行完成！")
    print("=" * 60)