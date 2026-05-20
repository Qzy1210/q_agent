"""
Skill 路由器

根据用户输入匹配对应的 Skill，支持两种路由方式：
1. 显式命令：通过正则表达式匹配命令前缀（如 /review）
2. 意图匹配：通过关键词匹配用户意图

路由优先级：显式命令 > 意图匹配

使用方法：
    router = SkillRouter(skills)

    # 路由用户输入
    skill, cleaned_input, confidence = router.route("/review src/main.py")
    # skill = CodeReviewSkill, cleaned_input = "src/main.py", confidence = 1.0

    skill, cleaned_input, confidence = router.route("帮我审查代码质量")
    # skill = CodeReviewSkill, cleaned_input = "帮我审查代码质量", confidence = 0.6
"""

import re
from typing import List, Optional, Tuple

from .types import Skill, SkillTrigger, TriggerType


class SkillRouter:
    """
    Skill 路由器

    根据用户输入匹配 Skill，支持显式命令和意图匹配两种方式。
    """

    def __init__(self, skills: Optional[List[Skill]] = None):
        """
        初始化路由器

        Args:
            skills: 初始 Skill 列表
        """
        self._skills: List[Skill] = list(skills) if skills else []

    def route(self, user_input: str) -> Tuple[Optional[Skill], str, float]:
        """
        路由用户输入到 Skill

        优先级：显式命令 > 意图匹配

        Args:
            user_input: 用户输入字符串

        Returns:
            (matched_skill, cleaned_input, confidence)
            - matched_skill: 匹配的 Skill，无匹配时为 None
            - cleaned_input: 清理后的输入（命令模式会移除前缀）
            - confidence: 匹配置信度 (0.0-1.0)，命令匹配为 1.0
        """
        if not user_input or not user_input.strip():
            return (None, user_input, 0.0)

        # 1. 优先检查显式命令匹配
        for skill in self._skills:
            for trigger in skill.meta.triggers:
                if trigger.type == TriggerType.COMMAND:
                    matched, cleaned = self._match_command(user_input, trigger)
                    if matched:
                        return (skill, cleaned, 1.0)

        # 2. 意图匹配
        best_skill = None
        best_confidence = 0.0

        for skill in self._skills:
            for trigger in skill.meta.triggers:
                if trigger.type == TriggerType.INTENT:
                    confidence = self._match_intent(user_input, trigger)
                    if confidence > best_confidence and confidence >= trigger.confidence:
                        best_skill = skill
                        best_confidence = confidence

        if best_skill:
            return (best_skill, user_input, best_confidence)

        # 3. 无匹配
        return (None, user_input, 0.0)

    def _match_command(
        self,
        user_input: str,
        trigger: SkillTrigger
    ) -> Tuple[bool, str]:
        """
        匹配显式命令

        Args:
            user_input: 用户输入
            trigger: 触发条件

        Returns:
            (是否匹配, 清理后的输入)
        """
        if not trigger.pattern:
            return (False, user_input)

        try:
            match = re.match(trigger.pattern, user_input)
            if match:
                # 移除匹配的命令前缀，保留剩余部分作为参数
                cleaned = user_input[match.end():].strip()
                return (True, cleaned)
        except re.error:
            # 无效正则表达式
            pass

        return (False, user_input)

    def _match_intent(
        self,
        user_input: str,
        trigger: SkillTrigger
    ) -> float:
        """
        计算意图匹配置信度

        置信度 = 匹配的关键词数 / 总关键词数

        Args:
            user_input: 用户输入
            trigger: 触发条件

        Returns:
            置信度 (0.0-1.0)
        """
        if not trigger.keywords:
            return 0.0

        input_lower = user_input.lower()
        matches = sum(
            1 for keyword in trigger.keywords
            if keyword.lower() in input_lower
        )

        return matches / len(trigger.keywords)

    def add_skill(self, skill: Skill) -> None:
        """
        添加 Skill 到路由器

        Args:
            skill: Skill 对象
        """
        if skill not in self._skills:
            self._skills.append(skill)

    def remove_skill(self, name: str) -> bool:
        """
        从路由器移除 Skill

        Args:
            name: Skill 名称

        Returns:
            是否移除成功
        """
        for i, skill in enumerate(self._skills):
            if skill.meta.name == name:
                self._skills.pop(i)
                return True
        return False

    def update_skills(self, skills: List[Skill]) -> None:
        """
        更新路由器的 Skill 列表

        Args:
            skills: 新的 Skill 列表
        """
        self._skills = list(skills)

    def get_skill_names(self) -> List[str]:
        """
        获取所有可路由的 Skill 名称

        Returns:
            Skill 名称列表
        """
        return [skill.meta.name for skill in self._skills]

    def __len__(self) -> int:
        """返回可路由的 Skill 数量"""
        return len(self._skills)
