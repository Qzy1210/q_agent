# 学习发现与笔记

## Agent核心概念理解

### 1. Agent Loop（智能体循环）
**核心思想**: 思考 → 决策 → 行动 → 观察结果 → 再思考
```
while not task_complete:
    thought = think(context, memory)
    action = decide(thought, available_tools)
    result = execute(action)
    memory.update(result)
    context.update(result)
```

**关键点**:
- 不是简单的if-else，而是基于LLM的动态决策
- 需要明确的停止条件
- 错误处理和重试机制

### 2. Memory系统
**两种类型**:
- **短期记忆**: 当前会话的上下文（最近N轮对话）
- **长期记忆**: 持久化的知识/经验（向量数据库或结构化存储）

**学习要点**:
- 先实现简单版本：基于列表的短期记忆
- 后续可增强：添加向量检索、知识图谱等

### 3. Context管理
**核心挑战**: 上下文窗口有限，需要智能管理
**策略**:
- 滑动窗口：保留最近N条消息
- 重要性排序：保留关键信息
- 压缩/摘要：对长文本进行总结

### 4. Prompt工程
**Agent Prompt组成**:
```
System Prompt: 角色定义 + 能力说明 + 工具描述
User Input: 用户请求
Context: 历史对话 + 当前状态
Available Tools: 工具列表和使用说明
```

**设计原则**:
- 清晰的角色定义
- 明确的能力边界
- 详细的工具说明
- 示例对话（Few-shot）

### 5. 工具加载机制
**设计模式**:
```python
class Tool:
    name: str
    description: str
    parameters: dict  # JSON Schema
    
    def execute(self, **kwargs) -> Result:
        pass

class ToolRegistry:
    def register(self, tool: Tool)
    def get_tool(self, name: str) -> Tool
    def list_tools(self) -> List[Tool]
```

**关键考虑**:
- 工具权限控制
- 参数验证
- 错误处理
- 结果格式化

## 技术选型发现

### Python vs 其他语言
**Python优势**:
- LLM生态最成熟（LangChain、LlamaIndex等参考）
- 异步支持好（asyncio）
- 丰富的工具库

### API框架选择
**FastAPI优势**:
- 原生异步支持
- 自动生成文档
- 类型提示友好
- 性能优秀

### 存储选择
**SQLite vs PostgreSQL**:
- 学习阶段：SQLite足够
- 生产环境：PostgreSQL（并发、扩展性）

## 踩坑记录

### 待记录...
（在实际开发过程中持续更新）

## 参考资源

### 论文
- ReAct: Synergizing Reasoning and Acting in Language Models
- Toolformer: Language Models Can Teach Themselves to Use Tools

### 开源项目
- LangChain: 复杂但功能全，适合参考架构
- AutoGPT: 早期Agent实现，简单易懂
- BabyAGPT: 最小化Agent实现，适合学习

### 博客/教程
- Lilian Weng的博客: "LLM Powered Autonomous Agents"
- OpenAI Cookbook: 最佳实践
