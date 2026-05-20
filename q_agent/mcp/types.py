"""
MCP (Model Context Protocol) 类型定义

MCP 是 Anthropic 提出的开放协议，用于 AI 助手与外部工具/资源的交互。
协议版本：2024-11-05
规范：https://spec.modelcontextprotocol.io/

学习重点：
1. MCP 协议基于 JSON-RPC 2.0
2. 工具定义使用 JSON Schema
3. 支持工具、资源、Prompts 三种能力
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum


class MCPMethod(Enum):
    """MCP 支持的方法"""
    # 生命周期
    INITIALIZE = "initialize"
    INITIALIZED = "notifications/initialized"
    PING = "ping"

    # 工具
    LIST_TOOLS = "tools/list"
    CALL_TOOL = "tools/call"

    # 资源
    LIST_RESOURCES = "resources/list"
    READ_RESOURCE = "resources/read"

    # Prompts
    LIST_PROMPTS = "prompts/list"
    GET_PROMPT = "prompts/get"


@dataclass
class MCPRequest:
    """
    MCP 请求

    JSON-RPC 2.0 格式
    """
    jsonrpc: str = "2.0"
    id: Optional[int] = None
    method: str = ""
    params: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为 JSON 格式"""
        result = {
            "jsonrpc": self.jsonrpc,
            "method": self.method,
        }
        if self.id is not None:
            result["id"] = self.id
        if self.params:
            result["params"] = self.params
        return result

    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        import json
        return json.dumps(self.to_dict())


@dataclass
class MCPResponse:
    """
    MCP 响应

    JSON-RPC 2.0 格式
    """
    jsonrpc: str = "2.0"
    id: Optional[int] = None
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MCPResponse':
        """从字典创建响应对象"""
        return cls(
            jsonrpc=data.get("jsonrpc", "2.0"),
            id=data.get("id"),
            result=data.get("result"),
            error=data.get("error")
        )

    @classmethod
    def from_json(cls, json_str: str) -> 'MCPResponse':
        """从 JSON 字符串创建响应对象"""
        import json
        data = json.loads(json_str)
        return cls.from_dict(data)

    def is_error(self) -> bool:
        """检查是否为错误响应"""
        return self.error is not None

    def get_error_message(self) -> str:
        """获取错误消息"""
        if self.error:
            return self.error.get("message", "Unknown error")
        return ""


@dataclass
class MCPToolDefinition:
    """
    MCP 工具定义

    符合 MCP 规范的工具描述，包含：
    - name: 工具名称（唯一标识）
    - description: 工具描述
    - inputSchema: 参数定义（JSON Schema 格式）
    """
    name: str
    description: str
    inputSchema: Dict[str, Any]  # JSON Schema

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.inputSchema
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MCPToolDefinition':
        """从字典创建工具定义"""
        return cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            inputSchema=data.get("inputSchema", {})
        )


@dataclass
class MCPToolResult:
    """
    MCP 工具执行结果

    MCP 规定的返回格式：
    - content: 内容数组，每个元素包含 type 和 text/data
    - isError: 是否为错误结果
    """
    content: List[Dict[str, Any]]  # 内容数组
    isError: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "content": self.content,
            "isError": self.isError
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MCPToolResult':
        """从字典创建结果"""
        return cls(
            content=data.get("content", []),
            isError=data.get("isError", False)
        )

    def get_text_content(self) -> str:
        """提取文本内容"""
        texts = []
        for item in self.content:
            if item.get("type") == "text":
                texts.append(item.get("text", ""))
        return "\n".join(texts)


@dataclass
class MCPResource:
    """
    MCP 资源定义

    资源可以是文件、数据库记录、API 数据等
    """
    uri: str
    name: str
    description: Optional[str] = None
    mimeType: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = {
            "uri": self.uri,
            "name": self.name
        }
        if self.description:
            result["description"] = self.description
        if self.mimeType:
            result["mimeType"] = self.mimeType
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MCPResource':
        """从字典创建资源"""
        return cls(
            uri=data.get("uri", ""),
            name=data.get("name", ""),
            description=data.get("description"),
            mimeType=data.get("mimeType")
        )


@dataclass
class MCPPrompt:
    """
    MCP Prompt 定义

    Prompt 是预定义的提示模板
    """
    name: str
    description: str
    arguments: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "name": self.name,
            "description": self.description,
            "arguments": self.arguments
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MCPPrompt':
        """从字典创建 Prompt"""
        return cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            arguments=data.get("arguments", [])
        )


@dataclass
class MCPServerInfo:
    """
    MCP 服务器信息

    initialize 响应中返回的服务器信息
    """
    name: str
    version: str
    protocolVersion: str = "2024-11-05"

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "name": self.name,
            "version": self.version,
            "protocolVersion": self.protocolVersion
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MCPServerInfo':
        """从字典创建"""
        return cls(
            name=data.get("name", ""),
            version=data.get("version", ""),
            protocolVersion=data.get("protocolVersion", "2024-11-05")
        )


@dataclass
class MCPCapabilities:
    """
    MCP 服务器能力

    定义服务器支持的功能
    """
    tools: Optional[Dict[str, Any]] = None
    resources: Optional[Dict[str, Any]] = None
    prompts: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = {}
        if self.tools is not None:
            result["tools"] = self.tools
        if self.resources is not None:
            result["resources"] = self.resources
        if self.prompts is not None:
            result["prompts"] = self.prompts
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MCPCapabilities':
        """从字典创建"""
        return cls(
            tools=data.get("tools"),
            resources=data.get("resources"),
            prompts=data.get("prompts")
        )

    def has_tools(self) -> bool:
        """是否支持工具"""
        return self.tools is not None

    def has_resources(self) -> bool:
        """是否支持资源"""
        return self.resources is not None

    def has_prompts(self) -> bool:
        """是否支持 Prompts"""
        return self.prompts is not None


@dataclass
class MCPServerConnection:
    """
    MCP 服务器连接信息

    存储单个 MCP 服务器连接的所有信息
    """
    info: MCPServerInfo
    capabilities: MCPCapabilities
    tools: List[MCPToolDefinition] = field(default_factory=list)
    resources: List[MCPResource] = field(default_factory=list)
    prompts: List[MCPPrompt] = field(default_factory=list)


# 使用示例
if __name__ == "__main__":
    """MCP 类型使用示例"""

    print("=" * 60)
    print("MCP 类型定义示例")
    print("=" * 60)

    # 创建请求
    request = MCPRequest(
        method=MCPMethod.LIST_TOOLS.value,
        params={}
    )
    request.id = 1
    print(f"\n请求 JSON:\n{request.to_json()}")

    # 创建工具定义
    tool_def = MCPToolDefinition(
        name="read_file",
        description="读取文件内容",
        inputSchema={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "文件路径"
                }
            },
            "required": ["path"]
        }
    )
    print(f"\n工具定义:\n{tool_def.to_dict()}")

    # 创建工具结果
    result = MCPToolResult(
        content=[{"type": "text", "text": "Hello, World!"}],
        isError=False
    )
    print(f"\n工具结果:\n{result.to_dict()}")
    print(f"提取文本: {result.get_text_content()}")

    print("\n" + "=" * 60)
    print("示例执行完成！")
    print("=" * 60)