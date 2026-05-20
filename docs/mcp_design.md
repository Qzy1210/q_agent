# q_agent MCP 支持设计方案

> 版本: 1.0.0 | 日期: 2025-05-17

## 一、概述

### 1.1 MCP 简介

**MCP (Model Context Protocol)** 是 Anthropic 在 2024 年底开放的标准协议，用于 AI Agent 与外部工具/数据源的连接。

```
┌─────────────┐      MCP 协议       ┌─────────────┐
│   AI Agent  │ ◄─────────────────► │ MCP Server  │
│  (Client)   │    JSON-RPC 2.0     │  (Tool提供者) │
└─────────────┘                     └─────────────┘
```

**核心价值**：
1. **标准化** - 统一的工具调用接口，类似 AI 界的 "USB 接口"
2. **生态复用** - 社区开发的 MCP Server 可被任何 MCP Client 使用
3. **解耦** - Agent 不需要为每个工具写适配代码

### 1.2 MCP 协议版本

- **协议版本**: 2024-11-05
- **规范文档**: https://spec.modelcontextprotocol.io/

### 1.3 MCP 三大能力

| 能力 | 说明 | 示例 |
|------|------|------|
| **Tools** | 可调用的函数 | `read_file`, `search_web`, `create_issue` |
| **Resources** | 可读取的资源 | 文件、数据库记录、API 响应 |
| **Prompts** | 预定义的提示模板 | "请分析这段代码..." |

---

## 二、架构设计

### 2.1 模块结构

```
q_agent/
├── mcp/
│   ├── __init__.py           # 模块导出
│   ├── types.py              # MCP 协议类型定义
│   ├── transport.py          # 传输层 (stdio + HTTP)
│   ├── client.py             # MCP 客户端
│   └── adapter.py            # 工具适配器
│
└── config/
    └── mcp.yaml              # MCP 服务器配置
```

### 2.2 组件职责

| 组件 | 职责 |
|------|------|
| **types.py** | 定义 MCP 协议类型（Request, Response, Tool, Resource 等） |
| **transport.py** | 实现传输层（StdioTransport, HTTPTransport） |
| **client.py** | 管理 MCP 服务器连接、握手、能力发现、工具调用 |
| **adapter.py** | 将 MCP Tool 包装为 q_agent 的 Tool 接口 |

### 2.3 数据流

```
┌─────────────────────────────────────────────────────────────┐
│                         Agent                                │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────────┐    │
│  │  Tools  │  │ Skills  │  │ Memory  │  │ MCP Client  │    │
│  │ (本地)  │  │ (组合)  │  │         │  │  (远程)     │    │
│  └────┬────┘  └────┬────┘  └────┬────┘  └──────┬──────┘    │
│       │            │            │              │            │
│       └────────────┴────────────┴──────────────┘            │
│                         │                                    │
│                    统一接口                                  │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
              ┌──────────────────────┐
              │  MCPToolAdapter      │
              │  (包装 MCP Tool)     │
              └──────────────────────┘
                          │
                          ▼
              ┌──────────────────────┐
              │  MCPClient           │
              │  (协议通信)          │
              └──────────────────────┘
                          │
            ┌─────────────┴─────────────┐
            ▼                           ▼
    ┌───────────────┐           ┌───────────────┐
    │ StdioTransport│           │ HTTPTransport │
    │  (本地进程)   │           │  (远程服务)   │
    └───────────────┘           └───────────────┘
```

---

## 三、核心组件详解

### 3.1 类型定义 (`types.py`)

```python
from dataclasses import dataclass
from typing import Dict, Any, Optional, List

@dataclass
class MCPRequest:
    """MCP 请求 (JSON-RPC 2.0)"""
    jsonrpc: str = "2.0"
    id: Optional[int] = None
    method: str = ""
    params: Dict[str, Any] = None

@dataclass
class MCPResponse:
    """MCP 响应"""
    jsonrpc: str = "2.0"
    id: Optional[int] = None
    result: Optional[Any] = None
    error: Optional[Dict] = None

@dataclass
class MCPToolDefinition:
    """MCP 工具定义"""
    name: str
    description: str
    inputSchema: Dict[str, Any]    # JSON Schema

@dataclass
class MCPToolResult:
    """MCP 工具调用结果"""
    content: List[Dict]            # [{type: "text", text: "..."}]
    isError: bool = False
```

### 3.2 传输层 (`transport.py`)

```python
from abc import ABC, abstractmethod

class MCPTransport(ABC):
    """传输层抽象基类"""

    @abstractmethod
    async def send(self, request: MCPRequest) -> MCPResponse:
        """发送请求，返回响应"""
        pass

    @abstractmethod
    async def close(self):
        """关闭连接"""
        pass


class StdioTransport(MCPTransport):
    """
    Stdio 传输 - 本地子进程通信

    工作原理：
    1. 启动 MCP 服务器作为子进程
    2. 通过 stdin 发送 JSON 请求
    3. 从 stdout 读取 JSON 响应
    """

    def __init__(self, command: str, args: List[str], env: dict = None):
        # 启动子进程
        self.process = subprocess.Popen(
            [command] + args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            env=env
        )


class HTTPTransport(MCPTransport):
    """
    HTTP 传输 - 远程服务通信

    工作原理：
    1. POST /mcp 端点发送请求
    2. 接收 JSON 响应
    """

    def __init__(self, base_url: str, headers: dict = None):
        self.base_url = base_url
        self.headers = headers or {}
```

### 3.3 客户端 (`client.py`)

```python
class MCPClient:
    """MCP 客户端 - 管理多个 MCP Server 连接"""

    # ========== 连接管理 ==========
    async def connect_stdio(self, name: str, command: str,
                            args: List[str], env: dict = None):
        """通过 stdio 连接 MCP Server"""

    async def connect_http(self, name: str, base_url: str,
                           headers: dict = None):
        """通过 HTTP 连接 MCP Server"""

    async def disconnect(self, name: str):
        """断开指定服务器连接"""

    # ========== 能力发现 ==========
    async def list_tools(self, name: str) -> List[MCPToolDefinition]:
        """获取 MCP Server 提供的所有工具"""

    async def list_resources(self, name: str) -> List[MCPResource]:
        """获取 MCP Server 提供的所有资源"""

    # ========== 工具调用 ==========
    async def call_tool(self, name: str, tool_name: str,
                        arguments: dict) -> MCPToolResult:
        """调用 MCP 工具"""
```

### 3.4 工具适配器 (`adapter.py`)

```python
from q_agent.tools.base import Tool, ToolResult

class MCPToolAdapter(Tool):
    """
    MCP Tool → Agent Tool 适配器

    将 MCP 工具包装为 q_agent 的 Tool 接口
    """

    def __init__(self, mcp_client: MCPClient, server_name: str,
                 tool_def: MCPToolDefinition):
        self._mcp_client = mcp_client
        self._server_name = server_name
        self._tool_definition = tool_def

    @property
    def name(self) -> str:
        # 格式: {server}_{tool}，避免命名冲突
        return f"{self._server_name}_{self._tool_definition.name}"

    @property
    def description(self) -> str:
        return f"[MCP:{self._server_name}] {self._tool_definition.description}"

    @property
    def parameters(self) -> dict:
        return self._tool_definition.inputSchema

    def execute(self, **kwargs) -> ToolResult:
        # 调用 MCP 工具
        mcp_result = await self._mcp_client.call_tool(
            self._server_name,
            self._tool_definition.name,
            kwargs
        )

        # 转换为 Agent ToolResult
        return ToolResult(
            success=not mcp_result.isError,
            result=mcp_result.get_text_content(),
            error=None if not mcp_result.isError else mcp_result.get_text_content()
        )
```

---

## 四、Agent 集成

### 4.1 新增方法

```python
class Agent:
    def __init__(self, ...):
        # 初始化 MCP 系统
        self.mcp_client: Optional[MCPClient] = None
        self.mcp_tool_registry: Optional[MCPToolRegistry] = None

    async def connect_mcp_stdio(self, server_name: str, command: str,
                                args: List[str] = None,
                                env: Dict[str, str] = None) -> bool:
        """连接 MCP 服务器（stdio 方式）"""

    async def connect_mcp_http(self, server_name: str, base_url: str,
                               headers: Dict[str, str] = None) -> bool:
        """连接 MCP 服务器（HTTP 方式）"""

    def list_mcp_servers(self) -> List[str]:
        """列出已连接的 MCP 服务器"""

    def list_mcp_tools(self) -> Dict[str, List]:
        """列出所有 MCP 工具"""

    async def disconnect_mcp(self, server_name: str = None):
        """断开 MCP 连接"""
```

### 4.2 使用示例

```python
from q_agent.core import Agent

# 创建 Agent
agent = Agent(
    tools=[FileReadTool()],  # 本地工具
    skill_dirs=["~/.q_agent/skills"]
)

# 连接 MCP 服务器
await agent.connect_mcp_stdio(
    server_name="filesystem",
    command="npx",
    args=["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
)

# MCP 工具自动注册，可像本地工具一样使用
result = agent.run("读取 /tmp/test.txt 的内容")
```

---

## 五、配置文件

### 5.1 配置格式 (`config/mcp.yaml`)

```yaml
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

global:
  connection_timeout: 30
  tool_timeout: 60
  auto_register_tools: true
  auto_connect: false
```

---

## 六、官方 MCP Servers

| 服务器 | 功能 | 安装命令 |
|--------|------|----------|
| `server-filesystem` | 文件读写 | `npx -y @modelcontextprotocol/server-filesystem /path` |
| `server-github` | GitHub API | `npx -y @modelcontextprotocol/server-github` |
| `server-sqlite` | SQLite 数据库 | `npx -y @modelcontextprotocol/server-sqlite /path/to/db` |
| `server-puppeteer` | 浏览器自动化 | `npx -y @modelcontextprotocol/server-puppeteer` |
| `server-postgres` | PostgreSQL | `npx -y @modelcontextprotocol/server-postgres` |

---

## 七、与 Skill 的关系

### 7.1 功能定位

| 组件 | 来源 | 特点 |
|------|------|------|
| **Tool** | 本地定义 | 原子操作，单次执行 |
| **MCP Tool** | MCP Server | 远程工具，协议调用 |
| **Skill** | 用户定义 | 组合能力，SOP 流程 |

### 7.2 组合使用

Skill 的 `allowed-tools` 中可以包含 MCP 工具：

```yaml
allowed-tools:
  - file_read                    # 本地工具
  - filesystem_read_file         # MCP 工具 (filesystem server)
  - github_list_repos            # MCP 工具 (github server)
```

---

## 八、总结

| 组件 | 职责 |
|------|------|
| **types.py** | MCP 协议类型定义 |
| **transport.py** | 传输层实现（stdio + HTTP） |
| **client.py** | MCP 客户端（连接、发现、调用） |
| **adapter.py** | MCP Tool → Agent Tool 适配 |
| **Agent** | 集成入口，统一管理 |

**设计原则**：
1. **标准化** - 遵循 MCP 2024-11-05 规范
2. **可扩展** - 支持多种传输方式和服务器
3. **统一接口** - MCP 工具与本地工具使用方式一致
