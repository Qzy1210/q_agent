"""
MCP (Model Context Protocol) 模块

Anthropic 官方开放协议，用于 AI Agent 与外部工具/资源的交互。

协议版本：2024-11-05
规范文档：https://spec.modelcontextprotocol.io/

模块组成：
- types: MCP 类型定义（JSON-RPC 2.0）
- transport: 传输层（stdio + HTTP）
- client: MCP 客户端（连接管理、工具调用）
- adapter: 工具适配器（MCP Tool → q_agent Tool）
"""

from .types import (
    MCPMethod,
    MCPRequest,
    MCPResponse,
    MCPToolDefinition,
    MCPToolResult,
    MCPResource,
    MCPPrompt,
    MCPServerInfo,
    MCPCapabilities,
    MCPServerConnection,
)

from .transport import (
    MCPTransport,
    StdioTransport,
    HTTPTransport,
)

from .client import MCPClient

from .adapter import (
    MCPToolAdapter,
    MCPToolRegistry,
)


__all__ = [
    # 类型
    "MCPMethod",
    "MCPRequest",
    "MCPResponse",
    "MCPToolDefinition",
    "MCPToolResult",
    "MCPResource",
    "MCPPrompt",
    "MCPServerInfo",
    "MCPCapabilities",
    "MCPServerConnection",

    # 传输
    "MCPTransport",
    "StdioTransport",
    "HTTPTransport",

    # 客户端
    "MCPClient",

    # 适配器
    "MCPToolAdapter",
    "MCPToolRegistry",
]