---
name: code_review
description: 审查代码质量，返回结构化报告。分析代码规范、潜在问题和改进建议。
version: "1.0.0"
author: "q_agent"
triggers:
  - type: command
    pattern: "^/review"
  - type: intent
    keywords: ["审查", "review", "代码质量", "代码分析", "检查代码", "代码问题"]
    confidence: 0.6
allowed-tools:
  - file_read
  - search
output:
  type: structured
  schema:
    score:
      type: integer
      description: 代码质量评分 (0-100)
    summary:
      type: string
      description: 代码总体评价
    issues:
      type: array
      description: 发现的问题列表
    suggestions:
      type: array
      description: 改进建议列表
metadata:
  category: development
  tags: [code, quality, review, analysis]
---

# Code Review Skill

审查代码质量，生成结构化报告。

## 执行流程

### Phase 1: 读取目标文件

1. 使用 `file_read` 工具读取用户指定的文件
2. 如果文件不存在或读取失败，返回错误信息

### Phase 2: 代码分析

从以下维度分析代码：

**代码质量指标：**
- 代码复杂度
- 命名规范
- 注释覆盖率
- 代码重复度

**安全问题检查：**
- SQL 注入风险
- XSS 风险
- 敏感信息泄露
- 不安全的函数调用

**最佳实践检查：**
- 错误处理
- 资源管理
- 代码风格一致性

### Phase 3: 生成报告

输出结构化报告，格式如下：

```json
{
  "score": 85,
  "summary": "代码质量良好，建议改进错误处理",
  "issues": [
    {
      "line": 42,
      "type": "warning",
      "message": "缺少空值检查"
    }
  ],
  "suggestions": [
    "建议添加更多单元测试",
    "考虑使用类型注解"
  ]
}
```

## 注意事项

- 对于大型文件，分段分析以避免超时
- 对于不支持的文件类型，仅做基础文本分析
- 保持客观中立的评价风格
