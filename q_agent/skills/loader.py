"""
Skill 加载器

扫描指定目录，加载所有 skill.md 文件。

支持：
- 单目录加载
- 多目录加载
- 递归扫描子目录
- 避免重复加载

使用方法：
    loader = SkillLoader()

    # 从单个目录加载
    skills = loader.load_from_directory("~/.q_agent/skills")

    # 从多个目录加载
    skills = loader.load_from_directories([
        "~/.q_agent/skills",
        "./skills"
    ])
"""

import os
from pathlib import Path
from typing import List, Set, Optional

from .types import Skill
from .parser import SkillParser, SkillParseError


class SkillLoader:
    """
    Skill 加载器

    扫描目录结构，查找并解析所有 skill.md 文件。
    """

    def __init__(self):
        """初始化加载器"""
        self.parser = SkillParser()
        self._loaded_paths: Set[str] = set()  # 已加载的文件路径，避免重复

    def load_from_file(self, file_path: str) -> Optional[Skill]:
        """
        从单个文件加载 Skill

        Args:
            file_path: skill.md 文件路径

        Returns:
            Skill 对象，加载失败返回 None
        """
        # 展开路径（处理 ~ 等）
        expanded_path = str(Path(file_path).expanduser().resolve())

        # 检查是否已加载
        if expanded_path in self._loaded_paths:
            return None

        try:
            skill = self.parser.parse_file(expanded_path)
            self._loaded_paths.add(expanded_path)
            return skill
        except SkillParseError as e:
            print(f"[SkillLoader] Failed to load {file_path}: {e}")
            return None
        except Exception as e:
            print(f"[SkillLoader] Unexpected error loading {file_path}: {e}")
            return None

    def load_from_directory(
        self,
        directory: str,
        recursive: bool = True
    ) -> List[Skill]:
        """
        从目录加载所有 Skill

        扫描目录中的 skill.md 文件（默认递归扫描子目录）。

        目录结构示例：
            skills/
            ├── code_review/
            │   └── skill.md
            ├── summarize/
            │   └── skill.md
            └── nested/
                └── advanced/
                    └── skill.md

        Args:
            directory: 目录路径
            recursive: 是否递归扫描子目录，默认 True

        Returns:
            加载的 Skill 列表
        """
        dir_path = Path(directory).expanduser().resolve()

        if not dir_path.exists():
            print(f"[SkillLoader] Directory not found: {directory}")
            return []

        if not dir_path.is_dir():
            print(f"[SkillLoader] Not a directory: {directory}")
            return []

        # 查找所有 skill.md 文件
        pattern = "**/skill.md" if recursive else "*/skill.md"
        skill_files = list(dir_path.glob(pattern))

        skills = []
        for skill_file in skill_files:
            skill = self.load_from_file(str(skill_file))
            if skill:
                skills.append(skill)
                print(f"[SkillLoader] Loaded skill: {skill.meta.name} from {skill_file}")

        return skills

    def load_from_directories(
        self,
        directories: List[str],
        recursive: bool = True
    ) -> List[Skill]:
        """
        从多个目录加载 Skill

        Args:
            directories: 目录路径列表
            recursive: 是否递归扫描子目录

        Returns:
            加载的 Skill 列表
        """
        all_skills = []

        for directory in directories:
            skills = self.load_from_directory(directory, recursive)
            all_skills.extend(skills)

        return all_skills

    def scan_directory(
        self,
        directory: str,
        recursive: bool = True
    ) -> List[str]:
        """
        扫描目录，返回所有 skill.md 文件路径

        不加载，只返回路径列表。

        Args:
            directory: 目录路径
            recursive: 是否递归扫描

        Returns:
            skill.md 文件路径列表
        """
        dir_path = Path(directory).expanduser().resolve()

        if not dir_path.exists() or not dir_path.is_dir():
            return []

        pattern = "**/skill.md" if recursive else "*/skill.md"
        return [str(f) for f in dir_path.glob(pattern)]

    def get_loaded_paths(self) -> Set[str]:
        """
        获取已加载的文件路径

        Returns:
            已加载路径集合
        """
        return self._loaded_paths.copy()

    def is_loaded(self, file_path: str) -> bool:
        """
        检查文件是否已加载

        Args:
            file_path: 文件路径

        Returns:
            是否已加载
        """
        expanded_path = str(Path(file_path).expanduser().resolve())
        return expanded_path in self._loaded_paths

    def clear_loaded(self) -> None:
        """清空已加载记录"""
        self._loaded_paths.clear()

    def reload(
        self,
        file_path: str
    ) -> Optional[Skill]:
        """
        重新加载 Skill

        强制重新加载指定文件，即使之前已加载。

        Args:
            file_path: skill.md 文件路径

        Returns:
            Skill 对象
        """
        expanded_path = str(Path(file_path).expanduser().resolve())

        # 从已加载集合中移除
        self._loaded_paths.discard(expanded_path)

        # 重新加载
        return self.load_from_file(file_path)

    def load_from_config(self, config: dict) -> List[Skill]:
        """
        从配置加载 Skill

        配置格式：
            {
                "skill_dirs": ["~/.q_agent/skills", "./skills"],
                "skills": {
                    "auto_load": true,
                    "recursive": true
                }
            }

        Args:
            config: 配置字典

        Returns:
            加载的 Skill 列表
        """
        skill_dirs = config.get("skill_dirs", [])
        if isinstance(skill_dirs, str):
            skill_dirs = [skill_dirs]

        skills_config = config.get("skills", {})
        recursive = skills_config.get("recursive", True)
        auto_load = skills_config.get("auto_load", True)

        if not auto_load:
            return []

        return self.load_from_directories(skill_dirs, recursive)
