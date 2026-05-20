"""
Skill 文件解析器

解析 skill.md 文件，提取 YAML frontmatter 元信息和 Markdown SOP 执行流程。

文件格式示例：
```yaml
---
name: code_review
description: 审查代码质量
triggers:
  - type: command
    pattern: "^/review"
allowed-tools:
  - file_read
---

# Code Review Skill

## 执行流程
...
```
"""

import re
import yaml
from pathlib import Path
from typing import Optional, List, Dict, Any

from .types import (
    Skill,
    SkillMeta,
    SkillTrigger,
    SkillHook,
    SkillOutput,
    TriggerType
)


class SkillParseError(Exception):
    """Skill 解析错误"""
    pass


class SkillParser:
    """
    Skill 文件解析器

    解析格式为 YAML frontmatter + Markdown 的 skill.md 文件。

    使用方法：
        parser = SkillParser()
        skill = parser.parse_file("~/.q_agent/skills/my_skill/skill.md")
    """

    # YAML frontmatter 正则表达式
    # 匹配 --- 开头和结尾的 YAML 块，以及后面的 Markdown 内容
    FRONTMATTER_PATTERN = re.compile(
        r'^---\s*\n(.*?)\n---\s*\n(.*)$',
        re.DOTALL
    )

    def parse_file(self, file_path: str) -> Skill:
        """
        解析 skill.md 文件

        Args:
            file_path: skill.md 文件路径

        Returns:
            Skill 对象

        Raises:
            SkillParseError: 文件不存在或格式错误
        """
        path = Path(file_path).expanduser()

        if not path.exists():
            raise SkillParseError(f"Skill file not found: {file_path}")

        if not path.is_file():
            raise SkillParseError(f"Not a file: {file_path}")

        try:
            content = path.read_text(encoding='utf-8')
        except Exception as e:
            raise SkillParseError(f"Failed to read file {file_path}: {e}")

        return self.parse_content(content, str(path))

    def parse_content(self, content: str, source_path: str = "") -> Skill:
        """
        解析 Skill 内容字符串

        Args:
            content: skill.md 文件内容
            source_path: 来源文件路径（用于错误提示）

        Returns:
            Skill 对象

        Raises:
            SkillParseError: 格式错误
        """
        # 匹配 frontmatter 和正文
        match = self.FRONTMATTER_PATTERN.match(content)

        if not match:
            raise SkillParseError(
                f"Invalid skill format: missing YAML frontmatter. "
                f"File should start with '---' and contain YAML metadata."
            )

        yaml_content, sop_content = match.groups()

        # 解析 YAML frontmatter
        try:
            meta_dict = yaml.safe_load(yaml_content)
        except yaml.YAMLError as e:
            raise SkillParseError(f"Invalid YAML frontmatter: {e}")

        if not isinstance(meta_dict, dict):
            raise SkillParseError("YAML frontmatter must be a dictionary")

        # 验证必填字段
        if 'name' not in meta_dict:
            raise SkillParseError("Missing required field: name")
        if 'description' not in meta_dict:
            raise SkillParseError("Missing required field: description")

        # 解析元信息
        meta = self._parse_meta(meta_dict)

        return Skill(
            meta=meta,
            sop=sop_content.strip(),
            source_path=source_path
        )

    def _parse_meta(self, data: Dict[str, Any]) -> SkillMeta:
        """
        解析元信息

        Args:
            data: YAML 解析后的字典

        Returns:
            SkillMeta 对象
        """
        # 解析触发条件
        triggers = self._parse_triggers(data.get('triggers', []))

        # 解析事件钩子
        hooks = self._parse_hooks(data.get('hooks', {}))

        # 解析输出格式
        output = self._parse_output(data.get('output'))

        # 解析允许的工具列表
        allowed_tools = data.get('allowed-tools', [])
        if isinstance(allowed_tools, str):
            # 支持逗号分隔的字符串
            allowed_tools = [t.strip() for t in allowed_tools.split(',')]

        return SkillMeta(
            name=data['name'],
            description=data['description'],
            version=data.get('version', '1.0.0'),
            author=data.get('author', ''),
            triggers=triggers,
            allowed_tools=allowed_tools,
            output=output,
            hooks=hooks,
            metadata=data.get('metadata', {})
        )

    def _parse_triggers(self, triggers_data: List[Dict]) -> List[SkillTrigger]:
        """
        解析触发条件列表

        Args:
            triggers_data: triggers 字段的值

        Returns:
            SkillTrigger 列表
        """
        triggers = []

        for t in triggers_data:
            if not isinstance(t, dict):
                continue

            trigger_type = t.get('type', 'intent')

            try:
                trigger = SkillTrigger(
                    type=TriggerType(trigger_type),
                    pattern=t.get('pattern'),
                    keywords=t.get('keywords', []),
                    confidence=t.get('confidence', 0.8)
                )
                triggers.append(trigger)
            except ValueError:
                # 忽略无效的触发器类型
                continue

        return triggers

    def _parse_hooks(self, hooks_data: Dict) -> Dict[str, List[SkillHook]]:
        """
        解析事件钩子

        Args:
            hooks_data: hooks 字段的值

        Returns:
            事件名 -> SkillHook 列表的映射
        """
        hooks = {}

        for event, hook_list in hooks_data.items():
            if not isinstance(hook_list, list):
                continue

            parsed_hooks = []
            for h in hook_list:
                if not isinstance(h, dict):
                    continue

                hook = SkillHook(
                    type=h.get('type', 'command'),
                    command=h.get('command'),
                    callback=h.get('callback'),
                    condition=h.get('condition')
                )
                parsed_hooks.append(hook)

            if parsed_hooks:
                hooks[event] = parsed_hooks

        return hooks

    def _parse_output(self, output_data: Optional[Dict]) -> Optional[SkillOutput]:
        """
        解析输出格式定义

        Args:
            output_data: output 字段的值

        Returns:
            SkillOutput 对象或 None
        """
        if not output_data or not isinstance(output_data, dict):
            return None

        return SkillOutput(
            type=output_data.get('type', 'text'),
            schema=output_data.get('schema'),
            template=output_data.get('template')
        )

    def validate_skill(self, skill: Skill) -> List[str]:
        """
        验证 Skill 定义的有效性

        Args:
            skill: Skill 对象

        Returns:
            错误消息列表（空列表表示验证通过）
        """
        errors = []

        # 验证名称
        if not skill.meta.name:
            errors.append("Skill name cannot be empty")

        # 验证名称格式（只允许字母、数字、下划线、连字符）
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_-]*$', skill.meta.name):
            errors.append(
                f"Invalid skill name '{skill.meta.name}': "
                "must start with a letter and contain only letters, numbers, underscores, and hyphens"
            )

        # 验证触发条件
        for i, trigger in enumerate(skill.meta.triggers):
            if trigger.type == TriggerType.COMMAND and not trigger.pattern:
                errors.append(f"Trigger {i}: command type must have a pattern")

        # 验证 SOP 不为空
        if not skill.sop.strip():
            errors.append("SOP (execution flow) cannot be empty")

        return errors
