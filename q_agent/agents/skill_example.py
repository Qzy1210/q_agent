"""
Skill 系统使用示例

演示如何使用 q_agent 的 Skill 系统：
1. 创建 Agent 并加载 Skills
2. 通过显式命令调用 Skill
3. 通过意图匹配调用 Skill
4. 查看已加载的 Skills
"""

import sys
import os

# 添加项目根目录到 Python 路径 (从 q_agent/q_agent/agents/ 上升到 q_agent/)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from q_agent.core import Agent
from q_agent.tools import FileReadTool
from q_agent.config import Config


def example_basic_usage():
    """
    示例 1: 基本使用

    创建 Agent 并加载内置 Skills
    """
    print("=" * 60)
    print("示例 1: 基本使用")
    print("=" * 60)

    # 创建配置
    config = Config()
    config.set("skill_dirs", [
        "~/.q_agent/skills",                    # 用户自定义 Skill
        "../q_agent/skills/builtin"              # 内置 Skill
    ])

    # 创建 Agent（会自动加载 Skills）
    agent = Agent(
        name="Skill Demo Agent",
        tools=[FileReadTool()],
        config=config
    )

    # 列出已加载的 Skills
    print("\n已加载的 Skills:")
    skills = agent.list_skills()
    for skill_info in skills:
        print(f"  - {skill_info['name']}: {skill_info['description']}")
        print(f"    触发方式: {[t['type'] for t in skill_info['triggers']]}")

    print()


def example_explicit_call():
    """
    示例 2: 显式命令调用

    使用 /skill_name 格式显式调用 Skill
    """
    print("=" * 60)
    print("示例 2: 显式命令调用")
    print("=" * 60)

    agent = Agent(
        name="Skill Demo Agent",
        tools=[FileReadTool()],
        skill_dirs=["../q_agent/skills/builtin"]
    )

    # 显式调用 code_review Skill
    print("\n调用: /review main.py")
    result = agent.run("/review main.py")
    print(f"结果: {result[:200]}...")

    print()


def example_intent_matching():
    """
    示例 3: 意图匹配调用

    通过自然语言描述，Agent 自动匹配 Skill
    """
    print("=" * 60)
    print("示例 3: 意图匹配调用")
    print("=" * 60)

    agent = Agent(
        name="Skill Demo Agent",
        tools=[FileReadTool()],
        skill_dirs=["../q_agent/skills/builtin"]
    )

    # 意图匹配调用 summarize Skill
    print("\n调用: 帮我总结一下 README.md 的内容")
    result = agent.run("帮我总结一下 README.md 的内容")
    print(f"结果: {result[:200]}...")

    print()


def example_custom_skill():
    """
    示例 4: 创建自定义 Skill

    展示如何在 ~/.q_agent/skills/ 目录下创建自定义 Skill
    """
    print("=" * 60)
    print("示例 4: 创建自定义 Skill")
    print("=" * 60)

    skill_content = '''---
name: hello
description: 打印问候语
version: "1.0.0"
triggers:
  - type: command
    pattern: "^/hello"
  - type: intent
    keywords: ["你好", "hello", "问候"]
    confidence: 0.8
allowed-tools: []
output:
  type: text
---

# Hello Skill

## 执行流程

1. 获取用户提供的名字（如果有）
2. 返回问候语

## 输出

返回格式: "Hello, {name}!"
'''

    print("\n自定义 Skill 文件内容:")
    print("-" * 40)
    print(skill_content)
    print("-" * 40)

    print("\n保存路径: ~/.q_agent/skills/hello/skill.md")
    print("\n创建步骤:")
    print("1. mkdir -p ~/.q_agent/skills/hello")
    print("2. 将上述内容保存到 ~/.q_agent/skills/hello/skill.md")
    print("3. 重启 Agent，Skill 会自动加载")

    print()


def example_skill_with_tools():
    """
    示例 5: Skill 调用工具

    展示 Skill 如何使用 allowed-tools 中的工具
    """
    print("=" * 60)
    print("示例 5: Skill 调用工具")
    print("=" * 60)

    agent = Agent(
        name="Skill Demo Agent",
        tools=[FileReadTool()],
        skill_dirs=["../q_agent/skills/builtin"]
    )

    # code_review Skill 会调用 file_read 工具
    print("\n调用: 审查一下 q_agent/skills/types.py 的代码质量")
    result = agent.run("审查一下 q_agent/skills/types.py 的代码质量")
    print(f"结果: {result[:300]}...")

    print()


def main():
    """运行所有示例"""
    print("\n" + "=" * 60)
    print("q_agent Skill 系统使用示例")
    print("=" * 60 + "\n")

    # 运行示例
    example_basic_usage()
    example_explicit_call()
    example_intent_matching()
    example_custom_skill()
    example_skill_with_tools()

    print("=" * 60)
    print("所有示例执行完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
