---
name: summarize
description: 总结文本内容，提取核心信息和关键要点。
version: "1.0.0"
author: "q_agent"
triggers:
  - type: command
    pattern: "^/summarize"
  - type: intent
    keywords: ["总结", "summarize", "概括", "摘要", "提炼", "总结一下", "帮我总结"]
    confidence: 0.7
allowed-tools:
  - file_read
output:
  type: text
metadata:
  category: productivity
  tags: [text, summary, analysis]
---

# Summarize Skill

总结文本内容，提取核心信息和关键要点。

## 执行流程

### Phase 1: 获取内容

1. 如果用户提供了文件路径，使用 `file_read` 工具读取文件内容
2. 如果用户直接提供了文本，使用该文本
3. 如果内容为空，返回提示信息

### Phase 2: 分析内容

分析文本内容：

**内容分析：**
- 识别文本类型（文章、代码、对话、文档等）
- 确定文本长度和复杂度
- 识别关键主题和概念

**信息提取：**
- 提取核心观点
- 识别关键数据
- 找出重要结论

### Phase 3: 生成摘要

根据用户需求生成摘要：

**默认摘要格式：**

```
## 概要
[一句话概括主要内容]

## 核心要点
1. [要点1]
2. [要点2]
3. [要点3]

## 关键信息
- [关键信息1]
- [关键信息2]

## 结论
[总结性陈述]
```

## 参数说明

- `content`: 要总结的文本内容（可选，如果提供文件路径则忽略）
- `file_path`: 文件路径（可选）
- `max_length`: 摘要最大长度（可选，默认不限制）
- `style`: 摘要风格（可选：brief, detailed, bullet_points）

## 注意事项

- 保持摘要的准确性和客观性
- 不遗漏重要信息
- 保留原文的关键术语和专业表达
- 根据文本类型调整摘要风格
