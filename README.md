# Q-Agent 学习项目

AI Agent 学习框架，通过从零手搓深入理解核心概念。

## 子项目

### q_agent (Python)

从零手搓 AI Agent 框架，深入理解核心概念：
- **Agent Loop**: 思考-决策-行动循环
- **Memory**: 长期记忆存储和检索
- **Context**: 短期上下文管理
- **Tool**: 工具调用机制
- **Skill**: 声明式能力定义（YAML + Markdown）
- **MCP**: Anthropic Model Context Protocol 支持

[查看详情](./q_agent/README.md)

### websocket-platform (Go)

WebSocket 通信平台，实现 App 与 Agent 的实时消息转发：
- 三层架构：App层 ↔ 平台层 ↔ Agent层
- Provider 模式框架
- 会话持久化
- 消息路由

[查看详情](./websocket-platform/README.md)

## 快速开始

### Python Agent

```bash
# 安装依赖
pip install sqlalchemy pymysql openai pyyaml

# 配置环境变量
export Q_AGENT_LLM_API_KEY='your-api-key'

# 运行示例
python examples/simple_agent.py

# 运行测试
python -m pytest q_agent/tests/
```

### WebSocket Platform

```bash
cd websocket-platform

# 安装依赖
make deps

# 运行服务
make run
```

服务将在 `http://localhost:8080` 启动

## 文档

| 文档 | 说明 |
|------|------|
| [CLAUDE.md](./CLAUDE.md) | Claude Code 工作指引 |
| [task_plan.md](./task_plan.md) | 项目规划和架构 |
| [progress.md](./progress.md) | 开发进度和学习心得 |
| [docs/CHANGELOG.md](./docs/CHANGELOG.md) | 更新日志 |
| [deploy/DEPLOY.md](./deploy/DEPLOY.md) | 部署指南 |

## 项目状态

| Phase | 内容 | 状态 |
|-------|------|------|
| Phase 1 | Agent核心 | ✅ 完成 |
| Phase 2 | WebSocket平台 | ✅ 完成 |
| Phase 3 | Android客户端 | ✅ 完成 |
| Phase 4 | Agent客户端集成 | ✅ 完成 |
| Phase 5 | Skill + MCP | ✅ 完成 |

## 学习价值

1. **深入理解 Agent Loop**: 思考-决策-行动循环的实现
2. **掌握 Memory 系统**: 长期记忆的管理和存储
3. **学习上下文管理**: Token 限制和上下文优化
4. **工具系统设计**: 工具的设计模式和注册机制
5. **WebSocket 通信**: 实时通信和消息转发机制
6. **Provider 模式**: 依赖注入和生命周期管理
7. **声明式设计**: YAML + Markdown 定义 Agent 能力
8. **协议标准化**: MCP 协议和适配器模式

## License

MIT
