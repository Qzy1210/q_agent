# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository contains two independent projects:

1. **q_agent** (Python) - An AI Agent learning framework implementing the Agent Loop pattern
2. **websocket-platform** (Go) - A WebSocket communication platform for real-time messaging

---

## q_agent (Python Agent Framework)

A from-scratch AI Agent implementation for learning core Agent concepts: Agent Loop, Memory systems, Context management, and Tool calling.

### Commands

```bash
# Run the Agent example
python examples/simple_agent.py

# Run the LLM usage example
python examples/llm_usage_example.py

# Start the FastAPI server
python -m q_agent.api.main
# or
uvicorn q_agent.api.main:app --host 0.0.0.0 --port 8000

# Run tests
python -m pytest q_agent/tests/

# Run specific test file
python -m pytest q_agent/tests/test_memory.py -v
```

### Configuration

Copy `config.example.json` to `config.json` and configure:
- `llm.api_key`: Required for actual LLM calls (supports OpenAI, Anthropic, local models via Ollama)
- `llm.provider`: "openai", "anthropic", "ollama", or "custom"
- `llm.base_url`: For Ollama/local models (default: http://localhost:11434)
- `database.*`: MySQL connection settings

Environment variables override config file (prefix: `Q_AGENT_`):
- `Q_AGENT_LLM_API_KEY`
- `Q_AGENT_DATABASE_HOST`, etc.

### Architecture

**Core Components:**

- `q_agent/core/agent.py` - Main Agent class implementing the Agent Loop (think → act → observe cycle)
- `q_agent/core/memory.py` - Long-term memory storage with search/import/export
- `q_agent/core/context.py` - Context window management with token limits and compression
- `q_agent/core/llm_client.py` - Multi-provider LLM client (OpenAI, Anthropic, Ollama, custom)

**Tool System:**

- `q_agent/tools/base.py` - Abstract Tool base class with JSON Schema parameter validation
- `q_agent/tools/registry.py` - Tool registry pattern for managing available tools

**Supporting:**

- `q_agent/config/config.py` - Configuration management with env var support
- `q_agent/api/main.py` - FastAPI REST API entry point

**Key Patterns:**

- **Agent Loop**: `run()` → `_think()` → `_act()` → `_observe()` → repeat until complete
- **Tool Pattern**: Inherit from `Tool` base class, implement `name`, `description`, `parameters` (JSON Schema), and `execute()`
- **Memory vs Context**: Memory = long-term storage; Context = active window for LLM prompts

### Creating New Tools

```python
from q_agent.tools.base import Tool, ToolResult

class MyTool(Tool):
    @property
    def name(self) -> str:
        return "my_tool"

    @property
    def description(self) -> str:
        return "Description of what this tool does"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "param1": {"type": "string", "description": "Parameter description"}
            },
            "required": ["param1"]
        }

    def execute(self, **kwargs) -> ToolResult:
        is_valid, error = self.validate_parameters(**kwargs)
        if not is_valid:
            return ToolResult(success=False, result=None, error=error)
        # Implement tool logic
        return ToolResult(success=True, result="output")
```

---

## websocket-platform (Go WebSocket Server)

A Gin-based WebSocket platform implementing message routing between App clients and Agent services (similar to Feishu/OpenClaw architecture).

### Commands

```bash
cd websocket-platform

# Install dependencies
make deps

# Run the server
make run

# Build binary
make build

# Run tests
make test

# Format code
make fmt

# Run linter
make lint
```

Server runs at `http://localhost:8080` by default.

### Architecture

**Three-Layer Design:**
- App Layer: Chat clients (Web/Mobile)
- Platform Layer: WebSocket server (message routing)
- Agent Layer: Local Agent services

**Provider Pattern:**

All service components implement the Provider interface:
```go
type Provider interface {
    Name() string
    Init() error
    Boot() error
    Close() error
}
```

Provider lifecycle: Register → Init → Boot → Run → Close

**Key Directories:**

- `cmd/server/main.go` - HTTP server entry point
- `framework/` - Core framework (app container, providers, WebSocket, HTTP, logging)
- `internal/` - Business logic (controllers, models, session management)
- `conf/` - YAML configuration files

**WebSocket Endpoints:**

- `/ws/app?client_id=...&user_id=...&session_id=...` - App client connection
- `/ws/agent?client_id=...&user_id=...&session_id=...` - Agent client connection

**Message Format:**
```json
{
  "id": "msg_id",
  "type": "text|file|tool_call|tool_result|heartbeat|status",
  "from": "sender_id",
  "to": "receiver_id",
  "session_id": "session_id",
  "timestamp": 1234567890,
  "content": {"text": "message content"}
}
```

### Database Setup

Create MySQL database:
```sql
CREATE DATABASE websocket_platform CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

Configure in `conf/includes/mysql/dev.yml`. Tables are auto-created on startup.

---

## Development Notes

**For q_agent Python code:**
- Python 3.10+ required (uses type hints and modern syntax)
- Extensive comments throughout - the codebase is designed as learning material
- All classes have detailed docstrings explaining design decisions
- LLM calls fail gracefully with mock responses when API key is not configured

**For websocket-platform Go code:**
- Go 1.21+ required
- Uses Gin, gorilla/websocket, Viper, Zap, GORM
- Provider registration order matters (dependencies must be registered first)
- All errors must be handled and propagated up
