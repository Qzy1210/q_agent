# q_agent 更新日志

## [2026-05-22] 渐进式 Skill 披露 + Agent Loop 自主决策

### 架构变更：从"Router 前置路由"升级为"LLM 自主决策"

#### 问题

原有设计中，Skill 执行完全绕过 LLM：
- `SkillRouter.route()` 在 `run()` 入口处做关键词/语义匹配
- 匹配成功 → 直接执行 Skill SOP（LLM 被排除）
- 匹配失败 → 进入 Agent Loop（但 LLM 不知道 Skill 的存在）

**LLM 的能力感知和系统实际能力之间存在断层。**

#### 解决方案：渐进式披露（Progressive Disclosure）

```
用户输入
    ↓
┌─ 以 / 开头？─ 是 → Router 匹配 → 直接执行 Skill（快速通道，保留）
│
否 → Agent Loop（LLM 思考）
         ↓
    LLM 看到系统提示词中的:
    - 基础工具列表 (file_read, calculator, search)
    - Skill 索引 (仅 name + description)
         ↓
    LLM 自主决策:
    ├─ action="file_read" → 执行工具
    ├─ action="use_skill", skill_name="code-review" → 加载完整 SOP → 执行
    └─ action="finish" → 返回结果
```

### 具体改动

| 改动 | 说明 |
|------|------|
| **新增 `_build_skill_index_text()`** | 构建轻量 Skill 索引，仅暴露 name + description |
| **修改 `_build_system_prompt()`** | 末尾追加 Skill 索引，LLM 可见可用高级能力 |
| **修改 `_act()` 方法** | 新增 `use_skill` 动作处理，按需加载完整 SOP |
| **修改 `run()` 入口逻辑** | `/command` 保留快速通道，普通意图走 Agent Loop |

### 系统提示词优化

- 重构为 Markdown 分级结构（角色 → 核心原则 → 工作流 → 工具 → 输出格式 → 示例）
- 新增完成判断标准（✅/❌ 对照表）
- 示例从 1 个增加到 3 个（计算/文件/多步骤）

### 修改文件

| 文件 | 修改内容 |
|------|----------|
| `q_agent/core/agent.py` | 新增 `_build_skill_index_text()`；修改 `_build_system_prompt()`；修改 `_act()` 支持 `use_skill`；修改 `run()` 入口逻辑 |
| `docs/skill_design.md` | 新增渐进式披露架构说明，更新 Agent 集成章节 |
| `docs/agent-module-technical-doc.md` | 更新 Agent Loop 和 Skill 系统章节 |

---

## [2025-05-19] AgentResult 与工具调用轨迹

### 新增功能

#### 1. AgentResult 数据类

Agent 执行结果现在返回结构化的 `AgentResult` 对象，包含完整的执行信息：

```python
@dataclass
class AgentResult:
    result: str                         # 最终结果文本
    success: bool = True                # 是否成功
    source: str = "agent_loop"          # 来源: "skill", "agent_loop", "mcp"
    skill_name: str = ""                # Skill 名称
    tools_called: List[ToolCall]        # 调用的工具列表
    iterations: int = 0                 # 迭代次数
    error: str = ""                     # 错误信息
```

#### 2. ToolCall 数据类

记录每次工具调用的完整信息：

```python
@dataclass
class ToolCall:
    tool_name: str              # 工具名称
    parameters: Dict[str, Any]  # 调用参数
    result: str                 # 执行结果
    reasoning: str = ""         # 调用理由
    success: bool = True        # 是否成功
```

#### 3. WebSocket 消息类型 `agent_result`

新增消息类型，用于返回完整的 Agent 执行结果：

```json
{
  "type": "agent_result",
  "content": {
    "result": "最终结果...",
    "success": true,
    "source": "skill",
    "skill_name": "code_review",
    "tools_called": [...],
    "iterations": 2
  }
}
```

### 修改文件

| 文件 | 修改内容 |
|------|----------|
| `q_agent/core/agent.py` | 新增 `AgentResult`、`ToolCall` 数据类；`run()` 返回 `AgentResult`；`_act()` 记录工具调用 |
| `q_agent/core/__init__.py` | 导出新增的类型 |
| `q_agent/websocket_client.py` | 新增 `send_agent_response()`；处理字典类型响应 |
| `websocket-platform/docs/message_format.md` | 新增 `agent_result` 消息类型文档 |
| `docs/skill_design.md` | 新增 `AgentResult` 和工具调用记录文档 |

### 前端更新

- 新增 `.type-agent_result` 消息类型样式
- 新增 `.tool-calls-info` 工具调用折叠面板
- `addMessage()` 函数支持渲染 `agent_result` 类型消息

### 使用示例

```python
from q_agent.core import Agent, AgentResult

agent = Agent(...)
result = agent.run("帮我审查代码")

# 访问结果
print(result.result)           # 最终结果文本
print(result.success)          # 是否成功
print(result.source)           # "skill" 或 "agent_loop"
print(result.skill_name)       # Skill 名称
print(result.tools_called)     # 工具调用列表
print(result.iterations)       # 迭代次数

# 转为字典（用于 JSON 序列化）
data = result.to_dict()

# 直接打印，返回 result
print(result)  # 等同于 print(result.result)
```

### 兼容性

- `AgentResult` 实现了 `__str__` 方法，现有代码 `print(agent.run(task))` 仍然可以正常工作
- WebSocket 客户端自动检测返回类型，兼容字符串和字典响应

---

## [2025-05-18] JSON 解析优化

### 问题描述

LLM 生成的 JSON 可能包含无效转义序列（如 `\以`、`\*`），导致解析失败。

### 解决方案

#### 1. LLM 结构化输出（OpenAI）

```python
# OpenAI 自动启用 json_object 模式
response = client.call(messages, response_format={"type": "json_object"})
```

#### 2. 通用 JSON 修复工具

```python
from q_agent.core.llm_client import safe_json_loads, repair_json

# 安全解析，自动修复
data, error = safe_json_loads(json_str)
```

#### 3. 增强 System Prompt

添加严格的 JSON 格式规则，明确告知 LLM 正确的转义方式。

### 修改文件

| 文件 | 修改内容 |
|------|----------|
| `q_agent/core/llm_client.py` | 新增 `repair_json()`、`safe_json_loads()`、`extract_json()` |
| `q_agent/core/agent.py` | `_call_llm()` 支持结构化输出；增强 system prompt |

---

## [2025-05-18] WebSocket 消息大小限制

### 问题描述

WebSocket 关闭码 1009 (Message Too Big)，原配置 `max_message_size: 8192` (8KB) 太小。

### 解决方案

修改配置文件 `websocket-platform/conf/includes/websocket/dev.yml`：

```yaml
websocket:
  max_message_size: 1048576  # 1MB
```

---

## [2025-05-18] list_skills Skill

### 新增功能

新增 `list_skills` Skill，用于列出所有已加载的 Skill。

### 触发方式

- 显式命令：`/skills`
- 意图匹配：`skill`、`技能`、`有哪些skill`、`有什么能力`

### 修改文件

| 文件 | 修改内容 |
|------|----------|
| `q_agent/skills/builtin/list_skills/skill.md` | 新增 Skill 定义 |
| `q_agent/skills/executor.py` | 新增 `_handle_list_skills()` 方法 |
| `q_agent/core/agent.py` | 调整初始化顺序，传入 `skill_registry` |

---

## [2025-05-17] 流式输出开发计划

### 新增文档

`docs/stream_output_plan.md` - 流式输出完整开发计划

### 概要

| Phase | 内容 | 工时 |
|-------|------|------|
| 1 | LLM 客户端流式接口 | 2h |
| 2-4 | OpenAI/Anthropic/Ollama 实现 | 3h |
| 5 | SkillExecutor 流式支持 | 1.5h |
| 6 | Agent 流式支持 | 1h |
| 7 | WebSocket 流式推送 | 1h |
| 8 | 测试与文档 | 1h |

---

## [2025-05-17] Markdown 渲染支持

### 新增功能

前端消息支持 Markdown 渲染和代码高亮。

### 修改文件

| 文件 | 修改内容 |
|------|----------|
| `websocket-platform/web/index.html` | 引入 marked.js 和 highlight.js；新增 Markdown 样式 |

---

## [2025-05-17] 移除双端模式

### 修改内容

- 移除双端模式切换开关
- 客户端类型固定为 `app`
- 移除连接列表标签页

### 修改文件

| 文件 | 修改内容 |
|------|----------|
| `websocket-platform/web/index.html` | 移除双端模式 UI 和相关代码 |
