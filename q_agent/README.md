# Q-Agent: 手搓智能体学习项目

## 项目简介
这是一个从零开始实现的智能体（Agent）项目，旨在深入理解AI Agent的核心概念：
- **Agent Loop**: 思考-决策-行动循环
- **Memory系统**: 短期和长期记忆管理
- **Context管理**: 上下文窗口优化
- **Prompt工程**: 设计高效的提示词
- **工具调用**: 让Agent具备实际操作能力

## 项目结构

```
q_agent/
├── core/               # 核心模块
│   ├── agent.py       # Agent主类，实现核心循环
│   ├── memory.py      # 记忆系统（短期/长期）
│   └── context.py     # 上下文管理
├── tools/             # 工具模块
│   ├── base.py        # 工具基类
│   ├── registry.py    # 工具注册中心
│   └── builtin/       # 内置工具集合
├── config/            # 配置模块
│   ├── settings.py    # 配置管理
│   └── database.py    # MySQL数据库连接
├── utils/             # 工具函数
│   ├── logger.py      # 日志系统
│   └── helpers.py     # 辅助函数
├── docs/              # 文档目录
│   ├── architecture.md # 架构设计文档
│   ├── agent_loop.md  # Agent Loop详解
│   └── tools.md       # 工具开发指南
└── tests/             # 测试用例
    ├── test_agent.py
    └── test_tools.py
```

## 技术栈

| 组件 | 技术选择 | 版本要求 | 说明 |
|------|---------|---------|------|
| 编程语言 | Python | 3.10+ | 类型提示、异步支持 |
| LLM API | OpenAI | - | 可替换为其他LLM |
| 数据库 | MySQL | 8.0+ | 生产级关系数据库 |
| ORM | SQLAlchemy | 2.0+ | Python ORM框架 |
| API框架 | FastAPI | 0.100+ | 现代、异步、自动文档 |

## 快速开始

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 配置数据库
创建MySQL数据库：
```sql
CREATE DATABASE q_agent CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

修改配置文件 `config/settings.py` 中的数据库连接信息。

### 3. 运行示例
```python
from q_agent.core.agent import Agent

# 创建Agent实例
agent = Agent()

# 执行任务
result = agent.run("帮我创建一个名为test.txt的文件")

# result 是 AgentResult 对象
print(result.result)           # 最终结果文本
print(result.success)          # 是否成功
print(result.source)           # 来源: "skill" 或 "agent_loop"
print(result.tools_called)     # 调用的工具列表

# 也可以直接打印（等同于 result.result）
print(result)
```

## 学习路线

### Phase 1: Agent核心（当前阶段）
- [x] 1.1 设计Agent基础架构
- [ ] 1.2 实现核心组件（Memory、Context、工具集）
- [ ] 1.3 测试与验证

### Phase 2: API接口层
- [ ] 2.1 设计RESTful API
- [ ] 2.2 实现会话管理
- [ ] 2.3 API文档与测试

### Phase 3: 用户界面
- [ ] 3.1 选择技术栈
- [ ] 3.2 实现基础功能
- [ ] 3.3 优化用户体验

## 核心概念

### Agent Loop（智能体循环）
Agent的核心是一个循环过程：
```
观察环境 → 思考分析 → 决策行动 → 观察结果 → 继续循环
```

详见：[docs/agent_loop.md](docs/agent_loop.md)

### Memory系统
分为两层：
- **短期记忆**: 当前会话的上下文信息
- **长期记忆**: 持久化的知识和经验

### 工具系统
Agent通过工具与世界交互：
- 文件操作（读写、搜索）
- 代码辅助（搜索、重构）
- 数据处理（格式转换、分析）

### Skill 体系
Agent 支持可插拔的 Skill 能力单元：
- **list_skills** (`/skills`) - 列出所有已加载的 Skill
- **code_review** (`/review`) - 审查代码质量
- **summarize** (`/summarize`) - 总结文本内容

### 执行结果
Agent 返回 `AgentResult` 结构化对象：
- `result` - 最终结果文本
- `source` - 执行来源（skill / agent_loop / mcp）
- `tools_called` - 工具调用轨迹
- `to_dict()` - 转为字典用于 JSON 序列化

## 开发规范

### 代码注释
- **每个类**都要有详细的功能说明
- **每个方法**都要有参数、返回值、用途说明
- **重要逻辑**都要有实现思路注释
- **复杂算法**要有逐步解释

### 文档要求
- 每个模块都有独立的README
- 关键概念都有专门的文档
- 示例代码要完整可运行

## 参考资源

### 论文
- [ReAct: Synergizing Reasoning and Acting in Language Models](https://arxiv.org/abs/2210.03629)
- [Toolformer: Language Models Can Teach Themselves to Use Tools](https://arxiv.org/abs/2302.04023)

### 开源项目
- [LangChain](https://github.com/langchain-ai/langchain)
- [AutoGPT](https://github.com/Significant-Gravitas/AutoGPT)
- [BabyAGI](https://github.com/yoheinakajima/babyagi)

### 博客
- [LLM Powered Autonomous Agents - Lilian Weng](https://lilianweng.github.io/posts/2023-06-23-agent/)

## 贡献指南
这是一个学习项目，欢迎提交Issue和PR！

## 许可证
MIT License
