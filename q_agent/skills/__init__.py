"""
q_agent Skill 系统

提供可插拔、可组合、可独立执行的任务能力单元。

核心组件：
- SkillParser: 解析 skill.md 文件
- SkillLoader: 扫描目录加载 Skill
- SkillRegistry: 管理 Skill 注册和启用/禁用
- SkillRouter: 路由用户输入到 Skill
- SkillExecutor: 执行 Skill SOP

使用示例：
    from q_agent.skills import SkillLoader, SkillRegistry, SkillRouter

    # 加载 Skills
    loader = SkillLoader()
    skills = loader.load_from_directory("~/.q_agent/skills")

    # 注册到注册器
    registry = SkillRegistry()
    for skill in skills:
        registry.register(skill)

    # 路由用户输入
    router = SkillRouter(registry.get_all())
    skill, cleaned_input, confidence = router.route("审查代码质量")
"""

from .types import (
    # 枚举
    TriggerType,

    # 数据类
    SkillTrigger,
    SkillHook,
    SkillOutput,
    SkillMeta,
    Skill,
    SkillResult,
    SkillContext,
)

from .parser import (
    SkillParser,
    SkillParseError,
)

from .loader import (
    SkillLoader,
)

from .registry import (
    SkillRegistry,
)

from .router import (
    SkillRouter,
)

from .executor import (
    SkillExecutor,
)


__all__ = [
    # 类型
    'TriggerType',
    'SkillTrigger',
    'SkillHook',
    'SkillOutput',
    'SkillMeta',
    'Skill',
    'SkillResult',
    'SkillContext',

    # 解析器
    'SkillParser',
    'SkillParseError',

    # 加载器
    'SkillLoader',

    # 注册器
    'SkillRegistry',

    # 路由器
    'SkillRouter',

    # 执行器
    'SkillExecutor',
]
