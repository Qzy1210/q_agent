# q_agent Skill 体系设计方案

> 版本: 1.0.0 | 日期: 2025-05-17

## 一、概述

### 1.1 背景

q_agent 已实现的核心功能：
- Agent Loop (think → act → observe)
- Tool 系统 (基类 + 注册器 + 内置工具)
- Memory (长期存储与检索)
- Context Manager (上下文窗口管理)
- LLM Client (多厂商支持)

缺失部分：
- **Skill 体系** - 可插拔、可组合、可独立执行的任务能力单元
- **MCP 支持** - Model Context Protocol，接入 Anthropic 开放标准生态

### 1.2 Skill 定义

Skill 是 Agent 的**可插拔、可组合、可独立执行的任务能力单元**：

| 特性 | 说明 |
|------|------|
| **格式** | 声明式配置文件 (YAML frontmatter + Markdown) |
| **元信息** | name, description, version, author |
| **触发条件** | 显式命令 + 意图匹配 |
| **SOP 执行流程** | Markdown 编写的标准化操作流程 |
| **工具调用** | allowed-tools 声明可用工具 |
| **输出格式** | 结构化输出定义 |
| **异常处理** | Hooks 定义事件处理逻辑 |

### 1.3 Skill vs Tool

```
┌─────────────────────────────────────────────────────────┐
│                        Tool                              │
│  • 原子操作，单次执行                                    │
│  • 无状态，输入 → 输出                                   │
│  • 示例：file_read, calculator, search                   │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│                        Skill                             │
│  • 组合能力，可调用多个 Tool + LLM                       │
│  • 有执行上下文和状态追踪                                │
│  • 声明式定义，用户可自定义                              │
│  • 示例：code_review, summarize, project_analysis        │
└─────────────────────────────────────────────────────────┘
```

### 1.4 Agent 职责

```
用户输入 → 意图理解 → Skill 路由 → 执行 Skill SOP → 返回结果
```

---

## 二、Skill 文件格式

### 2.1 完整示例

```yaml
---
# ========== 元信息 ==========
name: code_review
description: 审查代码质量，返回结构化报告
version: "1.0.0"
author: "user"

# ========== 触发条件 ==========
triggers:
  - type: command          # 显式调用：/code_review
    pattern: "^/review"
  - type: intent           # 意图匹配
    keywords: ["审查", "review", "代码质量", "代码分析"]
    confidence: 0.8

# ========== 工具声明 ==========
allowed-tools:
  - file_read
  - file_write
  - search
  - bash

# ========== 输出格式 ==========
output:
  type: structured
  schema:
    score: integer
    issues: array
    suggestions: array

# ========== Hooks（事件钩子）==========
hooks:
  PreExecute:
    - type: command
      command: "echo 'Starting code review...'"
  PostExecute:
    - type: command
      command: "echo 'Code review completed.'"
  OnError:
    - type: command
      command: "echo 'Error occurred: $ERROR'"

# ========== 元数据 ==========
metadata:
  category: development
  tags: [code, quality, review]
---

# Code Review Skill

## 执行流程 (SOP)

### Phase 1: 读取目标文件
1. 使用 `file_read` 工具读取用户指定的文件
2. 如果文件不存在，返回错误并提示用户

### Phase 2: 代码分析
1. 检查代码质量指标：
   - 代码复杂度
   - 命名规范
   - 注释覆盖率
2. 检查安全问题：
   - SQL 注入风险
   - XSS 风险
   - 敏感信息泄露

### Phase 3: 生成报告
输出结构化报告：

```json
{
  "score": 85,
  "issues": [
    {"line": 10, "type": "warning", "message": "变量命名不规范"}
  ],
  "suggestions": [
    "建议添加更多注释",
    "考虑拆分大函数"
  ]
}
```

## 异常处理

| 异常类型 | 处理方式 |
|---------|---------|
| 文件不存在 | 提示用户并提供文件路径建议 |
| 文件过大 | 分段读取，逐段分析 |
| 不支持的文件类型 | 跳过语法分析，仅做基础检查 |
```

### 2.2 字段说明

#### 元信息字段

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | string | ✅ | Skill 唯一标识 |
| `description` | string | ✅ | Skill 功能描述 |
| `version` | string | ❌ | 版本号，默认 "1.0.0" |
| `author` | string | ❌ | 作者信息 |

#### 触发条件 (triggers)

| 类型 | 字段 | 说明 |
|------|------|------|
| `command` | `pattern` | 正则表达式，匹配命令前缀 |
| `intent` | `keywords` | 关键词列表 |
| `intent` | `confidence` | 匹配置信度阈值 (0.0-1.0) |

#### 工具声明 (allowed-tools)

```yaml
allowed-tools:
  - file_read      # 引用 tool_registry 中的工具
  - file_write
  - search
```

#### 输出格式 (output)

```yaml
output:
  type: structured    # text | structured | file
  schema:             # structured 类型时的 JSON Schema
    score: integer
    issues: array
```

#### Hooks

| 事件 | 触发时机 |
|------|----------|
| `PreExecute` | Skill 执行前 |
| `PostExecute` | Skill 执行后 |
| `OnError` | 发生错误时 |
| `PreToolUse` | 工具调用前 |
| `PostToolUse` | 工具调用后 |

---

## 三、目录结构

### 3.1 用户 Skill 目录

```
~/.q_agent/skills/                    # 用户自定义 Skill 目录
├── code_review/
│   ├── skill.md                      # Skill 主文件
│   └── templates/
│       └── report.md                 # 报告模板
│
├── summarize/
│   └── skill.md
│
└── github_automation/
    ├── skill.md
    └── scripts/
        └── check_ci.sh               # 辅助脚本
```

### 3.2 项目级 Skill 目录

```
./skills/                             # 项目级 Skill 目录
└── project_specific/
    └── skill.md
```

### 3.3 q_agent 模块目录

```
q_agent/
├── skills/
│   ├── __init__.py           # 导出公共接口
│   ├── types.py              # Skill 类型定义
│   ├── parser.py             # Skill 文件解析器
│   ├── registry.py           # Skill 注册器
│   ├── router.py             # Skill 路由器（意图匹配）
│   ├── executor.py           # Skill 执行器
│   └── loader.py             # Skill 加载器（扫描目录）
│
└── config/
    └── config.py             # 配置中添加 skill_dirs 字段
```

---

## 四、核心组件设计

### 4.1 类型定义 (`types.py`)

```python
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum

class TriggerType(Enum):
    COMMAND = "command"      # 显式命令调用
    INTENT = "intent"        # 意图匹配

@dataclass
class SkillTrigger:
    type: TriggerType
    pattern: Optional[str] = None      # command 类型用
    keywords: List[str] = None         # intent 类型用
    confidence: float = 0.8            # 匹配置信度阈值

@dataclass
class SkillHook:
    type: str               # command, callback
    command: Optional[str] = None
    condition: Optional[str] = None

@dataclass
class SkillOutput:
    type: str               # structured, text, file
    schema: Optional[Dict] = None
    template: Optional[str] = None

@dataclass
class SkillMeta:
    """Skill 元信息（从 YAML frontmatter 解析）"""
    name: str
    description: str
    version: str = "1.0.0"
    author: str = ""
    triggers: List[SkillTrigger] = field(default_factory=list)
    allowed_tools: List[str] = field(default_factory=list)
    output: Optional[SkillOutput] = None
    hooks: Dict[str, List[SkillHook]] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Skill:
    """完整的 Skill 定义"""
    meta: SkillMeta                    # 元信息
    sop: str                           # SOP 执行流程 (Markdown)
    source_path: str                   # 文件来源路径

@dataclass
class SkillResult:
    """Skill 执行结果"""
    success: bool
    result: Any
    error: Optional[str] = None
    execution_trace: List[Dict] = field(default_factory=list)
    output_format: str = "text"

@dataclass
class SkillContext:
    """Skill 执行上下文"""
    tool_registry: 'ToolRegistry'
    llm_client: 'BaseLLMClient'
    memory: 'Memory'
    context_manager: 'ContextManager'
    user_input: str
    variables: Dict[str, Any] = field(default_factory=dict)
```

### 4.2 解析器 (`parser.py`)

职责：解析 skill.md 文件，提取 YAML frontmatter 和 Markdown SOP

核心方法：
- `parse_file(file_path)` - 解析文件
- `parse_content(content)` - 解析内容字符串
- `_parse_meta(data)` - 解析 YAML 元信息

### 4.3 加载器 (`loader.py`)

职责：扫描目录，加载所有 skill.md 文件

核心方法：
- `load_from_directory(directory, recursive=True)` - 从单个目录加载
- `load_from_directories(directories)` - 从多个目录加载

### 4.4 注册器 (`registry.py`)

职责：存储、管理 Skill 实例

核心方法：
- `register(skill, enable=True)` - 注册 Skill
- `unregister(name)` - 注销 Skill
- `get(name)` - 获取 Skill
- `get_all(enabled_only=True)` - 获取所有 Skill
- `enable(name)` / `disable(name)` - 启用/禁用

### 4.5 路由器 (`router.py`)

职责：根据用户输入匹配 Skill

核心方法：
- `route(user_input)` - 路由用户输入
  - 先检查显式命令匹配 (command pattern)
  - 再检查意图匹配 (intent keywords)
  - 返回 (skill, cleaned_input, confidence)

### 4.6 执行器 (`executor.py`)

职责：执行 Skill SOP

执行流程：
1. 执行 PreExecute hooks
2. 构建系统提示 (SOP + allowed-tools)
3. 调用 LLM 执行 SOP
4. 处理工具调用
5. 执行 PostExecute hooks
6. 返回 SkillResult

---

## 五、Agent 集成

### 5.1 执行结果类型

Agent 执行后返回 `AgentResult` 对象，包含完整的执行信息：

```python
@dataclass
class ToolCall:
    """工具调用记录"""
    tool_name: str              # 工具名称
    parameters: Dict[str, Any]  # 调用参数
    result: str                 # 执行结果
    reasoning: str = ""         # 调用理由
    success: bool = True        # 是否成功

@dataclass
class AgentResult:
    """Agent 执行结果"""
    result: str                         # 最终结果文本
    success: bool = True                # 是否成功
    source: str = "agent_loop"          # 来源: "skill", "agent_loop", "mcp"
    skill_name: str = ""                # Skill 名称（当 source 为 skill）
    tools_called: List[ToolCall]        # 调用的工具列表
    iterations: int = 0                 # Agent Loop 迭代次数
    error: str = ""                     # 错误信息

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典，用于 JSON 序列化"""
        return {
            "result": self.result,
            "success": self.success,
            "source": self.source,
            "skill_name": self.skill_name,
            "tools_called": [...],
            "iterations": self.iterations,
            "error": self.error
        }

    def __str__(self) -> str:
        """字符串表示，直接返回 result"""
        return self.result
```

### 5.2 Agent 初始化

```python
class Agent:
    def __init__(
        self,
        llm_client,
        tools: List[Tool] = None,
        skill_dirs: List[str] = None,    # Skill 目录列表
        config: Config = None,
        ...
    ):
        # 状态管理
        self._tools_called: List[ToolCall] = []  # 执行轨迹

        # 初始化 Skill 系统
        self.skill_registry = SkillRegistry()
        self.skill_loader = SkillLoader()
        self.skill_executor = SkillExecutor(...)

        # 加载 Skills
        skill_dirs = skill_dirs or self.config.get("skill_dirs", [])
        if skill_dirs:
            skills = self.skill_loader.load_from_directories(skill_dirs)
            for skill in skills:
                self.skill_registry.register(skill)

        self.skill_router = SkillRouter(self.skill_registry.get_all())
```

### 5.3 Agent 主循环

```python
def run(self, user_input: str) -> AgentResult:
    """Agent 主循环"""

    # 重置执行轨迹
    self._tools_called = []
    self.iteration_count = 0

    # 1. 尝试路由到 Skill
    skill, cleaned_input, confidence = self.skill_router.route(user_input)

    if skill and confidence > 0:
        # 2. 执行 Skill
        context = self._build_skill_context(user_input)
        result = self.skill_executor.execute(skill, cleaned_input, context)

        if result.success:
            return AgentResult(
                result=self._format_output(result),
                success=True,
                source="skill",
                skill_name=skill.meta.name,
                tools_called=self._tools_called
            )
        else:
            return AgentResult(
                result=f"Skill 执行失败: {result.error}",
                success=False,
                source="skill",
                skill_name=skill.meta.name,
                error=result.error
            )

    # 3. 无匹配 Skill，走普通 Agent Loop
    return self._run_agent_loop(user_input)
```

### 5.4 工具调用记录

Agent 在执行工具时会记录调用轨迹：

```python
def _act(self, action: AgentAction) -> str:
    """执行工具，并记录调用"""
    tool = self._find_tool(action.tool_name)

    if tool is None:
        # 记录失败的调用
        self._tools_called.append(ToolCall(
            tool_name=action.tool_name,
            parameters=action.parameters,
            result=f"工具不存在",
            reasoning=action.reasoning,
            success=False
        ))
        return "错误: 工具不存在"

    try:
        tool_result = tool.execute(**action.parameters)

        # 记录成功的调用
        self._tools_called.append(ToolCall(
            tool_name=action.tool_name,
            parameters=action.parameters,
            result=str(tool_result.result),
            reasoning=action.reasoning,
            success=tool_result.success
        ))

        return str(tool_result.result)
    except Exception as e:
        # 记录异常
        self._tools_called.append(ToolCall(
            tool_name=action.tool_name,
            parameters=action.parameters,
            result=str(e),
            reasoning=action.reasoning,
            success=False
        ))
        return f"执行失败: {e}"
```

---

## 六、配置支持

### 6.1 配置文件示例

`config.json`:

```json
{
  "skill_dirs": [
    "~/.q_agent/skills",
    "./skills"
  ],
  "skills": {
    "auto_load": true,
    "recursive": true
  }
}
```

### 6.2 环境变量

```bash
Q_AGENT_SKILL_DIRS=~/.q_agent/skills:/path/to/other/skills
```

---

## 七、内置 Skill 示例

### 7.1 Code Review Skill

```yaml
---
name: code_review
description: 审查代码质量，返回结构化报告
version: "1.0.0"
triggers:
  - type: command
    pattern: "^/review"
  - type: intent
    keywords: ["审查", "review", "代码质量"]
    confidence: 0.6
allowed-tools:
  - file_read
  - search
output:
  type: structured
  schema:
    score: integer
    issues: array
    suggestions: array
---

# Code Review Skill

## 执行流程

### Phase 1: 读取文件
使用 file_read 读取目标文件内容。

### Phase 2: 分析代码
- 检查命名规范
- 检查代码复杂度
- 检查安全问题

### Phase 3: 生成报告
返回结构化的审查报告，包含分数、问题列表、改进建议。
```

### 7.2 Summarize Skill

```yaml
---
name: summarize
description: 总结文本内容
version: "1.0.0"
triggers:
  - type: command
    pattern: "^/summarize"
  - type: intent
    keywords: ["总结", "summarize", "概括", "摘要"]
    confidence: 0.7
allowed-tools:
  - file_read
output:
  type: text
---

# Summarize Skill

## 执行流程

### Phase 1: 获取内容
读取用户指定的文件或直接使用用户提供的文本。

### Phase 2: 分析内容
- 识别关键主题
- 提取核心观点
- 确定内容结构

### Phase 3: 生成摘要
生成简洁的文本摘要，保留核心信息。
```

---

## 八、使用示例

### 8.1 创建自定义 Skill

```bash
# 创建 Skill 目录
mkdir -p ~/.q_agent/skills/my_skill

# 创建 Skill 文件
cat > ~/.q_agent/skills/my_skill/skill.md << 'EOF'
---
name: my_skill
description: 我的自定义 Skill
version: "1.0.0"
triggers:
  - type: command
    pattern: "^/my"
allowed-tools:
  - file_read
---

# My Skill

## 执行流程
1. 读取文件
2. 处理内容
3. 返回结果
EOF
```

### 8.2 使用 Skill

```python
from q_agent.core import Agent

agent = Agent(
    llm_client=llm_client,
    tools=[FileReadTool()],
    skill_dirs=["~/.q_agent/skills"]
)

# 显式调用
result = await agent.run("/review src/main.py")

# 意图匹配
result = await agent.run("帮我审查一下代码质量")
```

---

## 九、扩展点

### 9.1 未来增强

- **Skill 组合**: Skill 调用其他 Skill
- **Skill 版本管理**: 多版本共存与切换
- **Skill 市场**: 共享和下载社区 Skill
- **Skill 热重载**: 运行时更新 Skill

### 9.2 与 MCP 集成

Skill 的 `allowed-tools` 中可以包含 MCP 工具：

```yaml
allowed-tools:
  - file_read                    # 本地工具
  - github_list_repos            # MCP 工具 (github server)
  - filesystem_read_file         # MCP 工具 (filesystem server)
```
