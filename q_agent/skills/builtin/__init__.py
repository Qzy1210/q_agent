"""
内置 Skill 目录

包含两个示例 Skill：
- code_review: 代码审查
- summarize: 文本总结

这些 Skill 作为示例，展示 Skill 文件的标准格式。
用户可以在 ~/.q_agent/skills/ 目录下创建自己的 Skill。
"""

# 注意：Skill 是通过文件系统加载的，不需要在此文件中导入
# SkillLoader 会扫描此目录下的所有 skill.md 文件

__all__ = []