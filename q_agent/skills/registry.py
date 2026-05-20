"""
Skill 注册器

管理 Skill 的注册、启用、禁用、查询等操作。

使用方法：
    registry = SkillRegistry()

    # 注册 Skill
    registry.register(skill)

    # 获取 Skill
    skill = registry.get("code_review")

    # 列出所有 Skill
    skills = registry.get_all()

    # 启用/禁用
    registry.disable("code_review")
    registry.enable("code_review")
"""

from typing import Dict, List, Optional
from .types import Skill


class SkillRegistry:
    """
    Skill 注册器

    负责：
    - Skill 的注册和注销
    - Skill 的启用和禁用
    - Skill 的查询和列举
    """

    def __init__(self):
        """初始化注册器"""
        self._skills: Dict[str, Skill] = {}
        self._enabled: Dict[str, bool] = {}

    def register(self, skill: Skill, enable: bool = True) -> None:
        """
        注册 Skill

        Args:
            skill: Skill 对象
            enable: 是否启用，默认 True

        Raises:
            ValueError: skill 参数无效
        """
        if not skill or not skill.meta.name:
            raise ValueError("Invalid skill: name is required")

        name = skill.meta.name

        if name in self._skills:
            # 已存在同名 Skill，发出警告但允许覆盖
            import warnings
            warnings.warn(
                f"Skill '{name}' already registered, overwriting",
                UserWarning
            )

        self._skills[name] = skill
        self._enabled[name] = enable

    def unregister(self, name: str) -> bool:
        """
        注销 Skill

        Args:
            name: Skill 名称

        Returns:
            是否注销成功
        """
        if name in self._skills:
            del self._skills[name]
            del self._enabled[name]
            return True
        return False

    def get(self, name: str) -> Optional[Skill]:
        """
        获取 Skill

        Args:
            name: Skill 名称

        Returns:
            Skill 对象，不存在返回 None
        """
        return self._skills.get(name)

    def get_all(self, enabled_only: bool = True) -> List[Skill]:
        """
        获取所有 Skill

        Args:
            enabled_only: 是否只返回启用的 Skill

        Returns:
            Skill 列表
        """
        if enabled_only:
            return [
                skill for name, skill in self._skills.items()
                if self._enabled.get(name, True)
            ]
        return list(self._skills.values())

    def enable(self, name: str) -> bool:
        """
        启用 Skill

        Args:
            name: Skill 名称

        Returns:
            是否操作成功
        """
        if name in self._enabled:
            self._enabled[name] = True
            return True
        return False

    def disable(self, name: str) -> bool:
        """
        禁用 Skill

        Args:
            name: Skill 名称

        Returns:
            是否操作成功
        """
        if name in self._enabled:
            self._enabled[name] = False
            return True
        return False

    def is_enabled(self, name: str) -> bool:
        """
        检查 Skill 是否启用

        Args:
            name: Skill 名称

        Returns:
            是否启用
        """
        return self._enabled.get(name, False)

    def exists(self, name: str) -> bool:
        """
        检查 Skill 是否存在

        Args:
            name: Skill 名称

        Returns:
            是否存在
        """
        return name in self._skills

    def count(self, enabled_only: bool = False) -> int:
        """
        统计 Skill 数量

        Args:
            enabled_only: 是否只统计启用的

        Returns:
            数量
        """
        if enabled_only:
            return sum(1 for name in self._skills if self._enabled.get(name, True))
        return len(self._skills)

    def list_skills(self, enabled_only: bool = True) -> List[Dict]:
        """
        列出所有 Skill 的简要信息

        Args:
            enabled_only: 是否只列出启用的

        Returns:
            Skill 信息列表，每项包含 name, description, enabled, version
        """
        skills_info = []

        for name, skill in self._skills.items():
            if enabled_only and not self._enabled.get(name, True):
                continue

            skills_info.append({
                'name': name,
                'description': skill.meta.description,
                'version': skill.meta.version,
                'enabled': self._enabled.get(name, True),
                'triggers': [
                    {
                        'type': t.type.value,
                        'pattern': t.pattern,
                        'keywords': t.keywords
                    }
                    for t in skill.meta.triggers
                ],
                'tools': skill.meta.allowed_tools
            })

        return skills_info

    def clear(self) -> None:
        """清空所有注册的 Skill"""
        self._skills.clear()
        self._enabled.clear()

    def __len__(self) -> int:
        """返回注册的 Skill 数量"""
        return len(self._skills)

    def __contains__(self, name: str) -> bool:
        """检查 Skill 是否存在"""
        return name in self._skills

    def __iter__(self):
        """迭代所有 Skill"""
        return iter(self._skills.values())
