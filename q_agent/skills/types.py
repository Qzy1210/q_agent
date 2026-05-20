"""
Skill 类型定义

定义 Skill 体系中的所有核心数据类型：
- TriggerType: 触发器类型枚举
- SkillTrigger: 触发条件
- SkillHook: 事件钩子
- SkillOutput: 输出格式定义
- SkillMeta: Skill 元信息（从 YAML frontmatter 解析）
- Skill: 完整的 Skill 定义
- SkillResult: Skill 执行结果
- SkillContext: Skill 执行上下文
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum


class TriggerType(Enum):
    """触发器类型"""
    COMMAND = "command"      # 显式命令调用，如 /review
    INTENT = "intent"        # 意图匹配，通过关键词识别


@dataclass
class SkillTrigger:
    """
    Skill 触发条件

    command 类型：通过正则表达式匹配命令前缀，如 "^/review"
    intent 类型：通过关键词列表匹配用户意图，并设置置信度阈值
    """
    type: TriggerType
    pattern: Optional[str] = None          # command 类型：正则表达式
    keywords: Optional[List[str]] = None   # intent 类型：关键词列表
    confidence: float = 0.8                # intent 类型：匹配置信度阈值 (0.0-1.0)


@dataclass
class SkillHook:
    """
    Skill 事件钩子

    支持的事件：
    - PreExecute: Skill 执行前
    - PostExecute: Skill 执行后
    - OnError: 发生错误时
    - PreToolUse: 工具调用前
    - PostToolUse: 工具调用后
    """
    type: str                               # command | callback
    command: Optional[str] = None           # command 类型：shell 命令
    callback: Optional[str] = None          # callback 类型：Python 函数路径
    condition: Optional[str] = None         # 执行条件（可选）


@dataclass
class SkillOutput:
    """
    Skill 输出格式定义

    type:
    - text: 纯文本输出
    - structured: 结构化输出（配合 schema 定义）
    - file: 文件输出（配合 template 定义）
    """
    type: str                               # text | structured | file
    schema: Optional[Dict] = None           # structured 类型时的 JSON Schema
    template: Optional[str] = None          # file 类型时的模板路径


@dataclass
class SkillMeta:
    """
    Skill 元信息

    从 skill.md 文件的 YAML frontmatter 部分解析而来。
    包含 Skill 的所有声明式配置：名称、描述、触发条件、
    可用工具、输出格式、事件钩子等。
    """
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
    """
    完整的 Skill 定义

    由元信息 (meta) 和 SOP 执行流程 (sop) 组成。
    meta 来自 YAML frontmatter，sop 来自 Markdown 正文。
    """
    meta: SkillMeta                        # 元信息
    sop: str                               # SOP 执行流程 (Markdown 格式)
    source_path: str = ""                  # 文件来源路径


@dataclass
class SkillResult:
    """
    Skill 执行结果

    包含执行是否成功、结果内容、错误信息、执行轨迹等。
    execution_trace 记录了 Skill 执行过程中的每一步，
    便于调试和审计。
    """
    success: bool
    result: Any = None
    error: Optional[str] = None
    execution_trace: List[Dict] = field(default_factory=list)
    output_format: str = "text"            # text | structured | file


@dataclass
class SkillContext:
    """
    Skill 执行上下文

    提供 Skill 执行所需的全部能力：
    - tool_registry: 工具注册器，用于调用工具
    - llm_client: LLM 客户端，用于调用大语言模型
    - memory: 记忆系统，用于存储和检索信息
    - context_manager: 上下文管理器，用于管理对话上下文
    - user_input: 用户原始输入
    - variables: 执行过程中的变量存储
    """
    tool_registry: Any = None              # ToolRegistry 实例
    llm_client: Any = None                 # BaseLLMClient 实例
    memory: Any = None                     # Memory 实例
    context_manager: Any = None            # ContextManager 实例
    user_input: str = ""
    variables: Dict[str, Any] = field(default_factory=dict)
