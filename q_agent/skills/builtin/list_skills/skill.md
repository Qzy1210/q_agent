---
name: list_skills
description: 列出当前 Agent 已加载的所有 Skill，包括名称、描述、触发方式和可用工具。
version: "1.0.0"
author: "q_agent"
triggers:
  - type: command
    pattern: "^/skills"
  - type: intent
    keywords: ["skill", "技能", "有哪些skill", "有什么skill", "列出skill", "查看skill", "skill列表", "所有skill", "能力列表", "有哪些能力", "有什么能力"]
    confidence: 0.5
allowed-tools: []
output:
  type: text
metadata:
  category: system
  tags: [skill, list, info, system]
---

# List Skills

列出当前 Agent 已加载的所有 Skill 信息。

## 执行流程

### Phase 1: 获取所有已注册 Skill

1. 从 SkillRegistry 中获取所有已启用的 Skill
2. 如果没有任何 Skill，返回提示信息

### Phase 2: 格式化输出

对每个 Skill 输出以下信息：

**输出格式：**

```
## 已加载的 Skill（共 N 个）

1. **skill_name** - 描述信息
   - 版本: 1.0.0
   - 触发方式: /command 或 关键词匹配
   - 可用工具: tool1, tool2

2. ...
```

### Phase 3: 补充说明

- 提示用户如何使用 Skill（显式命令或自然语言）
- 提示用户如何创建自定义 Skill

## 注意事项

- 只列出已启用的 Skill
- 信息要简洁明了，方便用户快速了解
