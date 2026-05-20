# q_agent Skill 体系开发计划

> **状态: ✅ 已完成** (2026-05-17)
>
> 版本: 1.0.0 | 日期: 2025-05-17

## 一、开发阶段概览

| Phase | 内容 | 预计工时 | 依赖 |
|-------|------|----------|------|
| Phase 1 | 类型定义与解析器 | 2h | 无 |
| Phase 2 | 加载器与注册器 | 2h | Phase 1 |
| Phase 3 | 路由器 | 1.5h | Phase 2 |
| Phase 4 | 执行器 | 3h | Phase 2 |
| Phase 5 | Agent 集成 | 2h | Phase 3, 4 |
| Phase 6 | 配置与测试 | 1.5h | Phase 5 |
| Phase 7 | 内置 Skill 示例 | 1h | Phase 5 |

**总计**: 约 13 小时

---

## 二、Phase 1: 类型定义与解析器

### 2.1 目标

- 定义 Skill 相关的数据类型
- 实现 skill.md 文件解析器

### 2.2 文件清单

| 文件 | 说明 |
|------|------|
| `q_agent/skills/__init__.py` | 模块导出 |
| `q_agent/skills/types.py` | 类型定义 |
| `q_agent/skills/parser.py` | 文件解析器 |

### 2.3 详细任务

#### Task 1.1: 创建类型定义 (`types.py`)

```python
# 实现以下类型
- TriggerType (Enum)
- SkillTrigger (dataclass)
- SkillHook (dataclass)
- SkillOutput (dataclass)
- SkillMeta (dataclass)
- Skill (dataclass)
- SkillResult (dataclass)
- SkillContext (dataclass)
```

#### Task 1.2: 创建解析器 (`parser.py`)

```python
class SkillParser:
    - FRONTMATTER_PATTERN: 正则表达式
    - parse_file(file_path) -> Skill
    - parse_content(content, source_path) -> Skill
    - _parse_meta(data) -> SkillMeta
    - _parse_triggers(triggers_data) -> List[SkillTrigger]
    - _parse_hooks(hooks_data) -> Dict[str, List[SkillHook]]
    - _parse_output(output_data) -> SkillOutput
```

#### Task 1.3: 创建模块导出 (`__init__.py`)

```python
from .types import (
    Skill, SkillMeta, SkillResult, SkillContext,
    SkillTrigger, SkillHook, SkillOutput, TriggerType
)
from .parser import SkillParser

__all__ = [...]
```

### 2.4 验收标准

- [x] 类型定义完整，包含所有字段
- [x] 解析器能正确解析 YAML frontmatter
- [x] 解析器能正确提取 Markdown SOP
- [x] 单元测试通过

---

## 三、Phase 2: 加载器与注册器

### 3.1 目标

- 实现目录扫描和 Skill 加载
- 实现 Skill 注册和管理

### 3.2 文件清单

| 文件 | 说明 |
|------|------|
| `q_agent/skills/loader.py` | Skill 加载器 |
| `q_agent/skills/registry.py` | Skill 注册器 |

### 3.3 详细任务

#### Task 2.1: 创建加载器 (`loader.py`)

```python
class SkillLoader:
    - __init__()
    - load_from_file(file_path) -> Skill
    - load_from_directory(directory, recursive=True) -> List[Skill]
    - load_from_directories(directories) -> List[Skill]
    - _scan_directory(directory, recursive) -> List[Path]
```

#### Task 2.2: 创建注册器 (`registry.py`)

```python
class SkillRegistry:
    - __init__()
    - register(skill, enable=True)
    - unregister(name) -> bool
    - get(name) -> Optional[Skill]
    - get_all(enabled_only=True) -> List[Skill]
    - enable(name)
    - disable(name)
    - exists(name) -> bool
    - count() -> int
    - list_skills() -> List[dict]  # 返回简要信息
```

### 3.4 验收标准

- [x] 加载器能扫描指定目录
- [x] 加载器能递归扫描子目录
- [x] 加载器能正确加载多个 skill.md
- [x] 注册器能正确管理 Skill
- [x] 支持启用/禁用功能
- [x] 单元测试通过

---

## 四、Phase 3: 路由器

### 4.1 目标

- 实现用户输入到 Skill 的路由
- 支持显式命令和意图匹配两种方式

### 4.2 文件清单

| 文件 | 说明 |
|------|------|
| `q_agent/skills/router.py` | Skill 路由器 |

### 4.3 详细任务

#### Task 3.1: 创建路由器 (`router.py`)

```python
class SkillRouter:
    - __init__(skills: List[Skill])
    - route(user_input: str) -> Tuple[Optional[Skill], str, float]
    - _match_command(user_input, trigger) -> Tuple[bool, str]
    - _match_intent(user_input, trigger) -> float
    - add_skill(skill)
    - remove_skill(name)
```

### 4.4 路由逻辑

```
route(user_input):
    1. 遍历所有 Skill 的 triggers
    2. 优先检查 command 类型触发器
       - 正则匹配 pattern
       - 匹配成功返回 (skill, cleaned_input, 1.0)
    3. 检查 intent 类型触发器
       - 计算关键词匹配置信度
       - 超过阈值则记录候选
    4. 返回置信度最高的 Skill
    5. 无匹配返回 (None, user_input, 0.0)
```

### 4.5 验收标准

- [x] 显式命令匹配正确
- [x] 意图匹配计算正确
- [x] 返回正确的 cleaned_input
- [x] 无匹配时返回 None
- [x] 单元测试通过

---

## 五、Phase 4: 执行器

### 5.1 目标

- 实现 Skill SOP 执行
- 支持工具调用和 Hooks

### 5.2 文件清单

| 文件 | 说明 |
|------|------|
| `q_agent/skills/executor.py` | Skill 执行器 |

### 5.3 详细任务

#### Task 4.1: 创建执行器 (`executor.py`)

```python
class SkillExecutor:
    - __init__(tool_registry, llm_client, memory, context_manager)
    - execute(skill, user_input, context) -> SkillResult
    - _build_system_prompt(skill) -> str
    - _build_sop_prompt(skill, user_input) -> str
    - _get_allowed_tools(skill) -> List[dict]
    - _run_hooks(skill, event, context, **kwargs)
    - _process_tool_calls(response, skill, trace) -> Any
    - _format_output(result, skill) -> str
```

### 5.4 执行流程

```
execute(skill, user_input, context):
    1. 执行 PreExecute hooks
    2. 构建系统提示
       - 包含 Skill 描述
       - 包含 SOP 流程
       - 包含可用工具列表
    3. 调用 LLM
       - 传入 allowed-tools 定义
       - tool_choice = "auto"
    4. 处理 LLM 响应
       - 如果有工具调用，执行工具
       - 记录执行轨迹
    5. 格式化输出
    6. 执行 PostExecute hooks
    7. 返回 SkillResult
```

### 5.5 Hooks 执行

```python
_run_hooks(skill, event, context):
    for hook in skill.meta.hooks.get(event, []):
        if hook.type == "command":
            # 执行 shell 命令
            subprocess.run(hook.command, shell=True)
        elif hook.type == "callback":
            # 调用 Python 回调
            ...
```

### 5.6 验收标准

- [x] 正确构建系统提示
- [x] 正确调用 LLM
- [x] 正确处理工具调用
- [x] Hooks 执行正确
- [x] 返回正确的 SkillResult
- [x] 单元测试通过

---

## 六、Phase 5: Agent 集成

### 6.1 目标

- 将 Skill 系统集成到 Agent
- 修改 Agent 主循环

### 6.2 文件清单

| 文件 | 说明 |
|------|------|
| `q_agent/core/agent.py` | Agent 类修改 |

### 6.3 详细任务

#### Task 5.1: 修改 Agent 初始化

```python
class Agent:
    def __init__(
        self,
        llm_client,
        tools: List[Tool] = None,
        skill_dirs: List[str] = None,  # 新增
        config: Config = None,
        ...
    ):
        # 现有初始化...
        
        # 新增: Skill 系统初始化
        self._init_skill_system(skill_dirs)
```

#### Task 5.2: 实现 Skill 系统初始化

```python
def _init_skill_system(self, skill_dirs):
    self.skill_registry = SkillRegistry()
    self.skill_loader = SkillLoader()
    self.skill_executor = SkillExecutor(
        self.tool_registry,
        self.llm_client,
        self.memory,
        self.context_manager
    )
    
    # 加载 Skills
    if skill_dirs:
        skills = self.skill_loader.load_from_directories(skill_dirs)
        for skill in skills:
            self.skill_registry.register(skill)
    
    self.skill_router = SkillRouter(self.skill_registry.get_all())
```

#### Task 5.3: 修改 Agent 主循环

```python
async def run(self, user_input: str) -> str:
    # 新增: Skill 路由
    skill, cleaned_input, confidence = self.skill_router.route(user_input)
    
    if skill and confidence > 0:
        context = self._build_skill_context(user_input)
        result = await self.skill_executor.execute(skill, cleaned_input, context)
        return self._format_skill_result(result)
    
    # 原有 Agent Loop
    return await self._run_agent_loop(user_input)
```

### 6.4 验收标准

- [x] Agent 正确初始化 Skill 系统
- [x] Skill 路由集成正确
- [x] Skill 执行集成正确
- [x] 不影响原有 Agent Loop
- [x] 集成测试通过

---

## 七、Phase 6: 配置与测试

### 7.1 目标

- 添加配置支持
- 编写完整测试

### 7.2 文件清单

| 文件 | 说明 |
|------|------|
| `q_agent/config/config.py` | 配置修改 |
| `q_agent/tests/test_skills.py` | Skill 系统测试 |

### 7.3 详细任务

#### Task 6.1: 添加配置支持

```python
# config/config.py
DEFAULT_CONFIG = {
    # 现有配置...
    
    "skill_dirs": [
        "~/.q_agent/skills",
        "./skills"
    ],
    "skills": {
        "auto_load": True,
        "recursive": True
    }
}
```

#### Task 6.2: 编写单元测试

```python
# test_skills.py

def test_skill_parser():
    # 测试 YAML frontmatter 解析
    # 测试 SOP 提取
    pass

def test_skill_loader():
    # 测试目录扫描
    # 测试文件加载
    pass

def test_skill_registry():
    # 测试注册/注销
    # 测试启用/禁用
    pass

def test_skill_router():
    # 测试命令匹配
    # 测试意图匹配
    pass

def test_skill_executor():
    # 测试 SOP 执行
    # 测试工具调用
    pass

def test_agent_skill_integration():
    # 测试 Agent 集成
    pass
```

### 7.4 验收标准

- [x] 配置正确读取
- [x] 所有单元测试通过
- [x] 测试覆盖率 > 80%

---

## 八、Phase 7: 内置 Skill 示例

### 8.1 目标

- 提供内置 Skill 作为示例
- 验证 Skill 系统可用性

### 8.2 文件清单

| 文件 | 说明 |
|------|------|
| `q_agent/skills/builtin/code_review/skill.md` | 代码审查 Skill |
| `q_agent/skills/builtin/summarize/skill.md` | 文本总结 Skill |
| `examples/skill_example.py` | 使用示例 |

### 8.3 详细任务

#### Task 7.1: 创建 code_review Skill

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
---

# Code Review Skill

## 执行流程
...
```

#### Task 7.2: 创建 summarize Skill

```yaml
---
name: summarize
description: 总结文本内容
version: "1.0.0"
triggers:
  - type: command
    pattern: "^/summarize"
  - type: intent
    keywords: ["总结", "summarize", "概括"]
    confidence: 0.7
allowed-tools:
  - file_read
output:
  type: text
---

# Summarize Skill

## 执行流程
...
```

#### Task 7.3: 创建使用示例

```python
# agents/skill_example.py
"""
Skill 使用示例
"""

from q_agent.core import Agent
from q_agent.tools import FileReadTool, SearchTool
from q_agent.config import Config

def main():
    # 创建 Agent
    agent = Agent(
        llm_client=...,
        tools=[FileReadTool(), SearchTool()],
        skill_dirs=["~/.q_agent/skills", "./q_agent/skills/builtin"]
    )
    
    # 显式调用 Skill
    result = agent.run("/review src/main.py")
    print(result)
    
    # 意图匹配调用
    result = agent.run("帮我总结一下 README.md 的内容")
    print(result)

if __name__ == "__main__":
    main()
```

### 8.4 验收标准

- [x] 内置 Skill 正确加载
- [x] 内置 Skill 可正确执行
- [x] 示例代码可运行

---

## 九、开发顺序建议

```
Phase 1 (types, parser)
    │
    ▼
Phase 2 (loader, registry)
    │
    ├──▶ Phase 3 (router)
    │
    └──▶ Phase 4 (executor)
              │
              ▼
         Phase 5 (agent integration)
              │
              ▼
         Phase 6 (config, tests)
              │
              ▼
         Phase 7 (builtin skills)
```

---

## 十、风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| YAML 解析异常 | Skill 加载失败 | 增加格式校验和错误提示 |
| 意图匹配误判 | 路由错误 Skill | 设置合理阈值，支持用户确认 |
| SOP 执行超时 | 长时间无响应 | 添加超时机制 |
| 工具调用失败 | Skill 执行中断 | 完善错误处理和重试机制 |

---

## 十一、验收清单

### 功能验收

- [x] Skill 文件正确解析
- [x] 目录扫描正确加载
- [x] 显式命令路由正确
- [x] 意图匹配路由正确
- [x] SOP 执行正确
- [x] 工具调用正确
- [x] Hooks 执行正确
- [x] Agent 集成正确

### 质量验收

- [x] 单元测试覆盖率 > 80%
- [x] 无明显性能问题
- [x] 错误处理完善
- [x] 文档完整

### 兼容性验收

- [x] 不影响现有 Tool 系统
- [x] 不影响现有 Agent Loop
- [x] 配置向后兼容