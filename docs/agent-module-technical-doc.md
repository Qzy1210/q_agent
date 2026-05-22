# Q-Agent Agent 模块技术详解文档

> 本文档深入剖析 Q-Agent 项目中 agent 模块的实现逻辑，适合需要理解系统架构、扩展功能或二次开发的开发者。

---

## 目录

1. [整体架构概览](#1-整体架构概览)
2. [核心组件关系图](#2-核心组件关系图)
3. [Agent Loop 核心循环](#3-agent-loop-核心循环)
4. [LLM 客户端体系](#4-llm-客户端体系)
5. [记忆系统 Memory](#5-记忆系统-memory)
6. [上下文管理 ContextManager](#6-上下文管理-contextmanager)
7. [工具系统 Tool System](#7-工具系统-tool-system)
8. [Skill 技能系统](#8-skill-技能系统)
9. [MCP 协议集成](#9-mcp-协议集成)
10. [配置管理](#10-配置管理)
11. [WebSocket 客户端](#11-websocket-客户端)
12. [REST API 层](#12-rest-api-层)
13. [数据流全景](#13-数据流全景)
14. [关键设计模式](#14-关键设计模式)

---

## 1. 整体架构概览

Q-Agent 是一个**从零手搓的 AI Agent 框架**，核心思想是实现 **Agent Loop**（思考-决策-行动循环）。

```
┌─────────────────────────────────────────────────────────┐
│                    用户 (User)                           │
└──────────┬──────────────────────────────────────────────┘
           │
     ┌─────▼──────┐    ┌─────────────┐    ┌──────────────┐
     │  REST API  │    │  WebSocket  │    │  直接调用     │
     │  (FastAPI) │    │  (实时通信)  │    │  (agent.run)  │
     └─────┬──────┘    └──────┬──────┘    └──────┬───────┘
           │                 │                   │
           └─────────────────┼───────────────────┘
                             │
                    ┌────────▼────────┐
                    │   Agent 核心     │
                    │  (Agent Loop)   │
                    └──┬──┬──┬──┬──┬─┘
                       │  │  │  │  │
                  ┌────▼┐│ ┌▼┐│ ┌▼────────┐
                  │ LLM ││ │M││ │  Skill   │
                  │Client││ │C││ │  System  │
                  └─────┘│ │P││ └──────────┘
                         │ └┬┘│
                  ┌──────▼──▼─▼──────┐
                  │   Tool System    │
                  │  (Registry+Base) │
                  └──────┬─────┬─────┘
                         │     │
                  ┌──────▼┐ ┌──▼──────┐
                  │Memory │ │ Context │
                  │(长期)  │ │(短期)   │
                  └───────┘ └─────────┘
```

### 模块文件清单

| 模块 | 核心文件 | 职责 |
|------|----------|------|
| **Agent 核心** | `q_agent/core/agent.py` | Agent Loop 循环实现 |
| **LLM 客户端** | `q_agent/core/llm_client.py` | 多厂商 LLM 统一接口 |
| **记忆系统** | `q_agent/core/memory.py` | 长期记忆存储与检索 |
| **上下文管理** | `q_agent/core/context.py` | 短期上下文窗口管理 |
| **工具系统** | `q_agent/tools/base.py`, `registry.py`, `basic_tools.py` | 工具定义、注册、执行 |
| **Skill 系统** | `q_agent/skills/` 整个目录 | 声明式技能定义与执行 |
| **MCP 集成** | `q_agent/mcp/` 整个目录 | MCP 协议客户端 |
| **配置管理** | `q_agent/config/config.py` | 多源配置加载 |
| **WebSocket** | `q_agent/websocket_client.py` | 实时通信客户端 |
| **REST API** | `q_agent/api/main.py`, `routes/` | FastAPI HTTP 接口 |

---

## 2. 核心组件关系图

```
Agent (agent.py)
  ├── Memory ──────────── 长期记忆，持久化存储所有历史消息
  ├── ContextManager ──── 短期上下文，构建 LLM prompt 的活跃消息窗口
  ├── LLMClient ───────── 调用大语言模型的统一接口
  ├── Tools (List) ────── 可用工具列表（通过 ToolRegistry 管理）
  ├── SkillSystem ─────── 技能系统（Router → Executor）
  │   ├── SkillRegistry ─ 技能注册
  │   ├── SkillLoader ──── 从 skill.md 文件加载
  │   ├── SkillParser ──── 解析 YAML frontmatter + Markdown SOP
  │   ├── SkillRouter ──── 根据用户输入匹配 Skill
  │   └── SkillExecutor ── 执行 Skill 的 SOP 流程
  ├── MCPClient ────────── MCP 协议客户端（连接外部 MCP 服务器）
  └── Config ───────────── 配置管理器
```

---

## 3. Agent Loop 核心循环

这是整个项目的**核心中的核心**，理解了这个循环就理解了 Agent 的本质。

### 3.1 执行流程图

```
用户输入: "帮我计算 123+456"
         │
         ▼
    ┌─────────┐
    │  run()  │ ← 入口方法
    └────┬────┘
         │
    ┌────▼──────────────────────┐
    │ 尝试路由到 Skill           │
    │ skill_router.route(task)  │
    └────┬──────────────────────┘
         │
    ┌────▼────┐
    │ 匹配?   │
    └─┬───┬───┘
      │Y  │N
      ▼   ▼
  ┌─────┐ ┌────────────────────┐
  │执行  │ │ _run_agent_loop()  │ ← 普通 Agent Loop
  │Skill│ │                    │
  └─────┘ │ ┌──────────────┐   │
          │ │ initialize   │   │
          │ │ (初始化任务)  │   │
          │ └──────┬───────┘   │
          │        │           │
          │ ┌──────▼───────┐   │
          │ │ _should_     │   │
          │ │ continue()?  │   │ ← 检查是否继续循环
          │ └──┬───────┬───┘   │
          │    │Y      │N      │
          │    ▼       │       │
          │ ┌──────┐   │       │
          │ │_think│   │       │ ← 思考: 调用 LLM 决策下一步
          │ │()    │   │       │
          │ └──┬───┘   │       │
          │    │       │       │
          │ ┌──▼───┐   │       │
          │ │_act()│   │       │ ← 行动: 执行工具
          │ └──┬───┘   │       │
          │    │       │       │
          │ ┌──▼────┐  │       │
          │ │_observe│  │       │ ← 观察: 记录结果到记忆
          │ │()     │  │       │
          │ └──┬────┘  │       │
          │    └────────┘       │
          │        │            │
          │ ┌──────▼───────┐   │
          │ │ _get_final_  │   │
          │ │ result()     │   │ ← 返回最终结果
          │ └──────────────┘   │
          └────────────────────┘
```

### 3.2 Agent Loop 三步骤详解

#### Step 1: `_think()` — 思考决策

```python
def _think(self) -> Optional[AgentAction]:
    # 1. 从 ContextManager 获取当前上下文消息列表
    messages = self.context_manager.get_context()
    
    # 2. 调用 LLM，传入上下文
    response = self._call_llm(messages)
    
    # 3. 解析 LLM 的 JSON 响应为 AgentAction
    action = self._parse_response_to_action(response)
    
    # 4. 检测重复调用（防无限循环）
    if action 和上一次 action 完全相同:
        return None  # 强制结束
    
    return action
```

**关键设计：**
- LLM 必须返回**结构化 JSON**：
  ```json
  {
    "thinking": "我的思考过程",
    "action": "工具名称 或 finish",
    "parameters": {"参数": "值"},
    "reasoning": "选择这个行动的理由"
  }
  ```
- `action="finish"` 时，`_parse_response_to_action` 返回 `None`，循环终止
- **重复检测**：如果连续两次调用同一工具同一参数，强制结束

#### Step 2: `_act()` — 执行工具

```python
def _act(self, action: AgentAction) -> str:
    # 1. 在工具列表中查找对应工具
    tool = self._find_tool(action.tool_name)
    
    # 2. 调用工具的 execute() 方法
    result = tool.execute(**action.parameters)
    
    # 3. 记录到 _tools_called 轨迹
    self._tools_called.append(ToolCall(...))
    
    # 4. 返回结果字符串
    return str(result.result)
```

#### Step 3: `_observe()` — 观察记录

```python
def _observe(self, action: AgentAction, result: str):
    # 1. 保存到长期记忆
    self.memory.save_message("assistant", f"执行 {action.tool_name}: {result}")
    
    # 2. 添加到短期上下文（供下一轮 LLM 使用）
    self.context_manager.add_message("assistant", f"我执行了 {action.tool_name}，结果是: {result}")
```

**重要设计原则：工具执行成功 ≠ 任务完成**
- 任务完成由 LLM 在下一轮 `_think()` 中决定（返回 `action="finish"`）
- 不在 `_observe()` 中根据关键词判断是否完成

### 3.3 循环终止条件

```python
def _should_continue(self) -> bool:
    # 条件1: 状态为 COMPLETED 或 FAILED → 停止
    if self.state in [COMPLETED, FAILED]:
        return False
    
    # 条件2: 迭代次数达到上限 → 停止
    if self.iteration_count >= self.max_iterations:
        return False
    
    # 条件3: _think() 返回 None（LLM 决定完成或检测到重复）→ 停止
    # （由主循环中 action is None 判断）
    
    return True
```

### 3.4 System Prompt 构建

`_build_system_prompt()` 是 Agent 能力的核心定义，包含：
1. **角色定义**：`你是一个智能助手 {self.name}`
2. **可用工具列表**：遍历 `self.tools`，动态生成每个工具的名称、描述、参数定义（JSON Schema 格式）
3. **可用高级能力（Skill）**：渐进式披露——仅注入 name + description 索引，按需加载完整 SOP
4. **工作流程**：分析 → 选工具 → 执行 → 继续/完成
5. **完成规则**：何时返回 `finish`
6. **输出格式**：严格的 JSON 格式要求 + 转义规则

```python
# 工具描述生成示例
"- calculator: 执行数学计算\n  参数:\n    - expression (string)（必需）: 数学表达式字符串"
```

> **注意**：工具列表是**动态构建**的。只要工具注册到 `self.tools`，系统提示词就会自动包含它们，**无需手动更新模板**。

---

## 4. LLM 客户端体系

### 4.1 架构设计

采用**工厂模式 + 抽象基类**实现多厂商统一接口：

```
BaseLLMClient (ABC)
    ├── OpenAIClient      → GPT-3.5, GPT-4
    ├── AnthropicClient   → Claude 系列
    ├── QwenClient        → 通义千问
    ├── ZhipuClient       → 智谱 AI
    ├── OllamaClient      → 本地模型
    └── CustomClient      → 自定义 API 端点

LLMClientFactory.create(config) → 根据 provider 字段自动选择
```

### 4.2 统一响应格式

所有厂商统一返回 `LLMResponse` dataclass：

```python
@dataclass
class LLMResponse:
    content: str                      # 响应文本
    usage: Dict[str, int]             # token 统计
    model: str                        # 模型名
    provider: str                     # 厂商名
    raw_response: Any                 # 原始响应（调试用）
```

### 4.3 JSON 解析与修复

Agent 依赖 LLM 返回 JSON，但 LLM 可能输出格式不完美。系统实现了三层容错：

```python
def safe_json_loads(json_str) -> (dict, error):
    # 第1层: 直接解析
    try: return json.loads(json_str), None
    except: pass
    
    # 第2层: 从文本中提取 JSON（处理 markdown 代码块、前后缀文本）
    extracted = extract_json(json_str)
    
    # 第3层: 修复常见错误后解析
    fixed = repair_json(extracted)
    # 修复: 无效转义序列、尾部逗号、未终止字符串
```

### 4.4 结构化输出支持

不同厂商的结构化输出方式不同：

| 厂商 | 方式 |
|------|------|
| OpenAI | `response_format={"type": "json_object"}` |
| Anthropic | 通过 system prompt 约束 |
| Ollama | 通过 prompt 约束 |
| Custom | 可配置请求格式 |

---

## 5. 记忆系统 Memory

### 5.1 职责定位

Memory 负责**长期持久化存储**，与 ContextManager 职责完全分离：

| | Memory（长期） | ContextManager（短期） |
|---|---|---|
| 存储范围 | 所有历史消息 | 当前活跃的对话窗口 |
| 持久化 | 可保存到文件 | 不持久化 |
| 用途 | 历史检索、备份 | 构建 LLM prompt |
| Token 限制 | 无 | 有（max_tokens） |

### 5.2 核心操作

```python
class Memory:
    long_term_memory: List[Message]   # 内存中的消息列表
    storage_file: Optional[str]       # 持久化文件路径
    
    save_message(role, content)       # 保存消息（可选实时持久化）
    search(keyword)                   # 关键词搜索
    get_recent(count)                 # 获取最近 N 条
    get_all()                         # 获取全部
    export_to_file(filepath)          # 导出备份
    import_from_file(filepath)        # 导入恢复
```

### 5.3 Message 数据模型

```python
class Message:
    role: str              # "user" | "assistant" | "system"
    content: str           # 消息内容
    timestamp: datetime    # 自动记录时间
    metadata: Dict         # 扩展元数据
```

---

## 6. 上下文管理 ContextManager

### 6.1 核心职责

ContextManager 是 **Agent 构建 LLM prompt 的唯一数据源**。

```python
class ContextManager:
    context_window: deque         # 当前活跃消息（FIFO 队列）
    priority_messages: Dict       # 高优先级消息（不被压缩）
    max_tokens: int               # Token 上限（默认 4000）
    current_tokens: int           # 当前已用 Token
    compression_threshold: float  # 压缩触发阈值（默认 0.8）
```

### 6.2 关键方法

| 方法 | 功能 |
|------|------|
| `add_message(role, content, priority)` | 添加消息，自动计算 Token |
| `get_context()` | 获取完整上下文（优先级消息 + 窗口消息） |
| `get_context_for_llm()` | 获取优化后上下文（自动检查是否需要压缩） |
| `compress_context()` | 压缩：移除最旧 20% + 截断长消息 |
| `optimize_for_task(task)` | 按任务相关性重排序消息 |
| `clear_context(keep_priority)` | 清空上下文 |
| `_estimate_tokens(text)` | Token 估算（简化：字符数 / 3 + 1） |

### 6.3 Token 管理策略

```
添加消息 → 检查空间 → 不足时触发压缩 → 仍不足时移除旧消息
```

1. **优先级保护**：`priority > 0` 的消息永远不被移除
2. **阈值触发**：使用率达到 `compression_threshold` 时自动压缩
3. **压缩策略**：
   - 移除最旧的 20% 非优先消息
   - 截断超过 200 token 的长消息（保留前半）
4. **相关性优化**：`optimize_for_task()` 按关键词匹配度排序

---

## 7. 工具系统 Tool System

### 7.1 工具抽象基类

所有工具必须继承 `Tool` 抽象基类，实现四个核心属性/方法：

```python
class Tool(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...              # 工具唯一名称
    
    @property
    @abstractmethod
    def description(self) -> str: ...       # 功能描述
    
    @property
    @abstractmethod
    def parameters(self) -> Dict: ...       # JSON Schema 参数定义
    
    @abstractmethod
    def execute(self, **kwargs) -> ToolResult: ...  # 执行逻辑
```

### 7.2 工具注册器

```python
class ToolRegistry:
    tools: Dict[str, Tool]        # 工具字典
    enabled_tools: set            # 启用集合
    
    register(tool)                # 注册工具
    get_tool(name)                # 获取工具实例
    get_tools()                   # 获取工具列表（给 Agent 用）
    list_tools()                  # 获取工具信息（给 Prompt 用）
    execute_tool(name, **kwargs)  # 直接执行工具
    enable_tool(name)             # 启用
    disable_tool(name)            # 禁用
```

### 7.3 内置工具

#### 7.3.1 原有工具（3 个）

| 工具 | 名称 | 功能 |
|------|------|------|
| FileReadTool | `file_read` | 读取文本文件（1MB 限制） |
| CalculatorTool | `calculator` | 数学表达式计算（安全 eval） |
| SearchTool | `search` | 文本关键词搜索 |

#### 7.3.2 新增工具（10 个，2026-05-22）

| 工具 | 名称 | 功能 | 优先级 |
|------|------|------|--------|
| FileWriteTool | `file_write` | 创建/写入文件，支持覆盖/追加模式，自动创建父目录 | 🔴 核心 |
| FileEditTool | `file_edit` | 精确查找替换，唯一匹配检查 | 🔴 核心 |
| ShellTool | `shell` | 执行 Shell 命令，超时控制，stdout/stderr 捕获 | 🔴 核心 |
| FileListTool | `file_list` | 列出目录内容，支持递归和隐藏文件 | 🔴 核心 |
| WebFetchTool | `web_fetch` | 抓取网页内容，编码处理，长度限制 | 🟡 增强 |
| WebSearchTool | `web_search` | DuckDuckGo 搜索，返回标题+URL+摘要 | 🟡 增强 |
| UrlFetchTool | `url_fetch` | 下载 URL 资源到本地，流式下载 | 🟡 增强 |
| DateTimeTool | `date_time` | 获取当前时间，时区支持 | 🟢 辅助 |
| ImageAnalyzeTool | `image_analyze` | Pillow 图片信息分析，无 Pillow 时 fallback | 🟢 辅助 |
| MemorySaveTool | `memory_save` | JSON 持久化记忆，键值管理 | 🟢 辅助 |

### 7.4 工具返回格式

```python
@dataclass
class ToolResult:
    success: bool
    result: Any
    error: Optional[str] = None
    metadata: Optional[Dict] = None
```

---

## 8. Skill 技能系统

Skill 系统是 Q-Agent 的**高级能力抽象**，允许通过声明式文件（`skill.md`）定义 Agent 的专门能力。

### 8.1 Skill 文件结构

```markdown
---
name: code_review
description: 代码审查技能
version: 1.0.0
author: Qzy
triggers:
  - type: command
    pattern: "^/review"
  - type: intent
    keywords: ["代码审查", "review", "检查代码质量"]
    confidence: 0.6
allowed_tools: ["file_read", "search"]
output:
  type: text
hooks:
  PreExecute:
    - type: command
      command: "echo '开始代码审查'"
---

# 代码审查 SOP

1. 读取用户指定的代码文件
2. 分析代码结构和命名规范
3. 检查潜在的错误和性能问题
4. 输出审查报告
```

### 8.2 Skill 系统组件关系

```
SkillLoader → 扫描目录 → 找到 skill.md 文件
    │
    ▼
SkillParser → 解析 YAML frontmatter + Markdown SOP
    │
    ▼
SkillRegistry → 注册所有 Skill 对象
    │
    ▼
SkillRouter → 用户输入 → 匹配 Skill（命令/意图）
    │
    ▼
SkillExecutor → 执行 SOP → 调用 LLM → 处理工具调用 → 返回结果
```

### 8.3 路由机制

```python
# 路由优先级：显式命令 > 意图匹配
def route(user_input) -> (skill, cleaned_input, confidence):
    # 1. 命令匹配: 正则匹配，置信度 = 1.0
    for skill in skills:
        for trigger in skill.triggers:
            if trigger.type == COMMAND:
                if re.match(trigger.pattern, user_input):
                    return (skill, cleaned, 1.0)
    
    # 2. 意图匹配: 关键词匹配，置信度 = 匹配数/总数
    for skill in skills:
        for trigger in skill.triggers:
            if trigger.type == INTENT:
                confidence = matched_keywords / total_keywords
                if confidence >= trigger.confidence:
                    return (skill, user_input, confidence)
    
    # 3. 无匹配
    return (None, user_input, 0.0)
```

### 8.4 执行流程

```python
# SkillExecutor.execute()
1. 执行 PreExecute hooks
2. 构建 system prompt（Skill 名 + 描述 + SOP + 工具列表 + 输出格式）
3. 构建 user prompt（用户请求）
4. 准备消息 → 调用 LLM
5. 处理响应（可能包含工具调用）
6. 执行 PostExecute hooks
7. 返回 SkillResult
```

### 8.5 Hook 系统

支持的事件类型：

| 事件 | 触发时机 |
|------|----------|
| PreExecute | Skill 执行前 |
| PostExecute | Skill 执行后 |
| OnError | 发生错误时 |
| PreToolUse | 工具调用前 |
| PostToolUse | 工具调用后 |

Hook 类型：
- **command**: 执行 shell 命令（支持 `$VAR` 变量替换）
- **callback**: Python 回调函数（TODO）

---

## 9. MCP 协议集成

MCP (Model Context Protocol) 是 Anthropic 提出的标准协议，允许 Agent 连接外部工具服务器。

### 9.1 MCP 架构

```
Q-Agent ── MCPClient ── StdioTransport ── MCP Server (stdio)
                   │
                   └── HTTPTransport ── MCP Server (HTTP)
```

### 9.2 连接流程

```
1. connect_stdio() / connect_http() → 建立传输
2. _initialize_server() → MCP 握手
   ├── 发送 initialize 请求
   ├── 解析服务器信息和能力
   ├── 发现工具 (list_tools)
   ├── 发现资源 (list_resources)
   └── 发现 Prompts (list_prompts)
3. _register_mcp_tools() → 将 MCP 工具注册到 Agent 的工具列表
```

### 9.3 MCP 握手协议

```
Client: {"method": "initialize", "params": {"protocolVersion": "2024-11-05", ...}}
Server: {"result": {"serverInfo": {...}, "capabilities": {...}}}

Client: {"method": "notifications/initialized"}
→ 握手完成
```

### 9.4 工具自动注册

连接成功后，MCP 工具会自动通过 `MCPToolAdapter` 适配为 Agent 的 Tool 对象，追加到 `self.tools` 列表中，Agent 可以像调用普通工具一样调用 MCP 工具。

---

## 10. 配置管理

### 10.1 配置优先级

```
环境变量 > 配置文件 > 默认值
```

### 10.2 配置源

| 源 | 示例 |
|---|---|
| 默认值 | 代码中硬编码的默认配置 |
| 配置文件 | `config.json`（JSON/YAML） |
| 环境变量 | `Q_AGENT_LLM_API_KEY`, `Q_AGENT_DATABASE_HOST` 等 |

### 10.3 配置结构

```python
config = {
    "database": {
        "host": "49.233.105.26",
        "port": 3306,
        "user": "root",
        "password": "qzy123",
        "database": "q_agent",
    },
    "llm": {
        "provider": "custom",
        "model": "z-ai/glm-5",
        "api_key": "...",
        "temperature": 0.7,
        "max_tokens": 2000,
    },
    "agent": {
        "max_iterations": 10,
        "timeout": 300,
        "memory_size": 20,
        "context_window": 4000,
    },
    "log": {
        "level": "INFO",
        "file": "logs/q_agent.log",
    }
}
```

### 10.4 嵌套键访问

```python
config.get("llm.api_key")          # → 点号分隔的嵌套访问
config.set("agent.max_iterations", 20)  # → 运行时修改
```

---

## 11. WebSocket 客户端

### 11.1 角色定位

`AgentWebSocketClient` 是 Agent 核心与 **WebSocket 平台**之间的桥梁：

```
前端 App ── WebSocket ── 平台层 ── WebSocket ── AgentWebSocketClient ── Agent核心
```

### 11.2 消息处理流程

```
收到消息 → 解析 JSON → 判断类型 → 分发处理

消息类型:
├── "text"        → handle_text_message() → 调用 Agent.run() → 返回响应
├── "history"     → handle_history_request() → 查询数据库 → 返回历史
├── "tool_call"   → handle_tool_call() → 接收工具调用请求
├── "status"      → 记录状态日志
└── "heartbeat"   → 忽略（心跳）
```

### 11.3 文本消息处理详细流程

```python
async def handle_text_message(message):
    # 1. 提取文本内容
    text = message["content"]["text"]
    
    # 2. 保存用户消息到数据库（MessageStore）
    message_store.save_message(session_id, role="user", content=text)
    
    # 3. 调用 Agent（同步 run 在线程池中执行）
    result = await loop.run_in_executor(None, agent.run, text)
    
    # 4. 保存 Agent 响应到数据库
    message_store.save_message(session_id, role="assistant", content=result_text)
    
    # 5. 发送响应回 WebSocket
    await send_agent_response(result, session_id)
```

### 11.4 连接参数

```
ws://host:8080/ws/agent?client_id=xxx&user_id=xxx&session_id=xxx
```

---

## 12. REST API 层

### 12.1 技术栈

- **框架**: FastAPI
- **服务器**: Uvicorn (ASGI)
- **端口**: 8089
- **文档**: Swagger UI (`/docs`) + ReDoc (`/redoc`)

### 12.2 路由结构

```
/api/v1/
├── health          → 健康检查
└── chat/           → 对话接口
```

### 12.3 CORS 配置

默认允许所有源（`allow_origins=["*"]`），生产环境应限制具体域名。

---

## 13. 数据流全景

### 13.1 完整请求-响应流程

```
用户输入: "帮我读取 config.json 并解释内容"
    │
    ▼
┌─ 1. 任务初始化 ────────────────────────────────────┐
│   - context_manager.clear_context(keep_priority=False) │
│   - memory.save_message("user", task)              │
│   - context_manager.add_message("system", prompt)  │
│   - context_manager.add_message("user", task)      │
└────────────────────────────────────────────────────┘
    │
┌─ 2. 迭代 1: Think ─────────────────────────────────┐
│   - 获取上下文 messages                            │
│   - 调用 LLM(messages)                             │
│   - LLM 返回: action="file_read",                  │
│       parameters={"file_path": "config.json"}       │
└────────────────────────────────────────────────────┘
    │
┌─ 3. 迭代 1: Act ───────────────────────────────────┐
│   - 查找 file_read 工具                            │
│   - 执行 tool.execute(file_path="config.json")     │
│   - 返回文件内容                                   │
└────────────────────────────────────────────────────┘
    │
┌─ 4. 迭代 1: Observe ───────────────────────────────┐
│   - memory.save_message("assistant", "执行 file_read: ...") │
│   - context_manager.add_message("assistant", "我执行了...") │
└────────────────────────────────────────────────────┘
    │
┌─ 5. 迭代 2: Think ─────────────────────────────────┐
│   - 获取上下文（包含工具执行结果）                  │
│   - 调用 LLM(messages)                             │
│   - LLM 返回: action="finish",                     │
│       parameters={"result": "配置文件包含..."}        │
└────────────────────────────────────────────────────┘
    │
┌─ 6. 任务完成 ──────────────────────────────────────┐
│   - _parse_response_to_action 检测到 finish → 返回 None │
│   - 循环终止                                      │
│   - 返回 AgentResult(result="...", success=True)   │
└────────────────────────────────────────────────────┘
```

### 13.2 上下文消息流转

```
时间线    ContextManager (短期)              Memory (长期)
───────────────────────────────────────────────────────────
初始      [system prompt]                    [user: task]
          [user: task]                       
                                                  
迭代1后   [system prompt]                    [user: task]
          [user: task]                       [assistant: 执行 file_read: ...]
          [assistant: 我执行了 file_read...]  
                                                  
迭代2后   [system prompt]                    [user: task]
          [user: task]                       [assistant: 执行 file_read: ...]
          [assistant: 我执行了 file_read...]  [assistant: 最终答案: ...]
          [assistant: 最终答案: ...]          
```

---

## 14. 关键设计模式

### 14.1 模式总结

| 模式 | 应用位置 | 说明 |
|------|----------|------|
| **工厂模式** | LLMClientFactory | 根据 provider 配置创建对应客户端 |
| **策略模式** | 各 LLM Client | 不同厂商的不同调用策略 |
| **注册器模式** | ToolRegistry, SkillRegistry | 统一管理工具/技能的注册和查找 |
| **适配器模式** | MCPToolAdapter | 将 MCP 工具适配为 Agent Tool 接口 |
| **依赖注入** | Agent 构造函数 | 所有组件通过参数注入 |
| **模板方法** | Tool 基类 | 定义工具标准接口，子类实现具体逻辑 |
| **观察者模式** | Skill Hooks | 在特定事件触发时执行钩子 |

### 14.2 依赖注入关系

```python
agent = Agent(
    name="Q-Agent",
    max_iterations=10,
    llm_client=LLMClientFactory.create(llm_config),  # LLM 客户端
    tools=tool_registry.get_tools(),                   # 工具列表
    memory=Memory(),                                   # 记忆系统
    context_manager=ContextManager(max_tokens=4000),   # 上下文管理
    config=Config(config_file="config.json"),          # 配置
    skill_dirs=["~/.q_agent/skills"],                  # 技能目录
)
```

### 14.3 错误处理策略

| 场景 | 处理方式 |
|------|----------|
| LLM 调用失败 | 开发环境 → mock 降级；生产环境 → 抛出异常 |
| 工具不存在 | 返回错误结果，不中断循环 |
| 工具执行异常 | 捕获异常，记录到 _tools_called |
| JSON 解析失败 | 自动修复 → 提取 → 重试 → 失败则跳过 |
| 重复工具调用 | 检测到连续相同调用 → 强制结束 |
| 超过最大迭代 | 自动终止循环 |

---

## 附录：项目扩展指南

### A. 添加新工具

```python
# 1. 创建工具类
from q_agent.tools.base import Tool, ToolResult

class MyTool(Tool):
    @property
    def name(self) -> str:
        return "my_tool"
    
    @property
    def description(self) -> str:
        return "我的工具描述"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "param1": {"type": "string", "description": "参数1描述"}
            },
            "required": ["param1"]
        }
    
    def execute(self, **kwargs) -> ToolResult:
        is_valid, error = self.validate_parameters(**kwargs)
        if not is_valid:
            return ToolResult(success=False, result=None, error=error)
        # 实现你的逻辑
        return ToolResult(success=True, result="结果")

# 2. 注册到 Agent
tool_registry.register(MyTool())
# 或在 Agent 初始化时传入 tools 参数
```

### B. 添加新 Skill

在 skill 目录下创建 `skill.md` 文件即可，系统会自动扫描加载。

### C. 添加新 LLM 提供商

```python
# 1. 继承 BaseLLMClient
class MyLLMClient(BaseLLMClient):
    def call(self, messages, **kwargs) -> LLMResponse:
        # 实现你的调用逻辑
        pass

# 2. 注册到工厂
LLMClientFactory.PROVIDERS["my_provider"] = MyLLMClient
```

---

*文档生成时间: 2026-05-21*
*基于分支: lx_dev (main 分支创建)*
*项目版本: 1.0.0*
