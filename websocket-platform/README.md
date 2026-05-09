# WebSocket Platform

基于 Gin 框架的 WebSocket 通信平台，实现类似飞书与 OpenClaw 的消息转发架构。

## 项目简介

WebSocket Platform 是一个轻量级的实时通信平台，采用三层架构设计：

- **App 层**：聊天客户端（Web/Mobile）
- **平台层**：WebSocket 服务器（消息中转）
- **Agent 层**：本地 Agent 服务

## 核心特性

✅ **Provider 模式**：遵循 gin_fram 框架规范，所有服务组件实现 Provider 接口
✅ **WebSocket 通信**：基于 gorilla/websocket 实现高性能 WebSocket 服务
✅ **连接管理**：支持多客户端连接、会话管理、用户映射
✅ **消息路由**：自动在 App 和 Agent 之间转发消息
✅ **配置管理**：支持 YAML 配置文件、环境变量、多环境配置
✅ **日志系统**：基于 Zap 的结构化日志

## 快速开始

### 1. 安装依赖

```bash
make deps
# 或
go mod download
go mod tidy
```

### 2. 配置数据库

创建 MySQL 数据库：

```sql
CREATE DATABASE websocket_platform CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

修改配置文件 `conf/includes/mysql/dev.yml`。

### 3. 运行服务

```bash
make run
# 或
go run cmd/server/main.go
```

服务将在 `http://localhost:8080` 启动。

### 4. 测试连接

**App 客户端连接：**

```javascript
const ws = new WebSocket('ws://localhost:8080/ws/app?client_id=app1&user_id=user1&session_id=session1');

ws.onopen = () => {
  console.log('Connected to WebSocket server');
  // 发送消息
  ws.send(JSON.stringify({
    id: 'msg1',
    type: 'text',
    from: 'app1',
    session_id: 'session1',
    timestamp: Date.now(),
    content: { text: 'Hello from App!' }
  }));
};

ws.onmessage = (event) => {
  console.log('Received:', JSON.parse(event.data));
};
```

**Agent 客户端连接：**

```javascript
const ws = new WebSocket('ws://localhost:8080/ws/agent?client_id=agent1&user_id=user1&session_id=session1');

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  console.log('Received from App:', message);
  
  // 处理消息并返回结果
  if (message.type === 'text') {
    ws.send(JSON.stringify({
      id: 'msg2',
      type: 'text',
      from: 'agent1',
      session_id: 'session1',
      timestamp: Date.now(),
      content: { text: 'Processed by Agent: ' + message.content.text }
    }));
  }
};
```

## 项目结构

```
websocket-platform/
├── cmd/
│   └── server/
│       └── main.go              # HTTP 服务入口
├── conf/
│   ├── dev.yml                  # 主配置
│   └── includes/                # 子配置
│       ├── logger/dev.yml       # 日志配置
│       ├── mysql/dev.yml        # 数据库配置
│       └── websocket/dev.yml    # WebSocket 配置
├── framework/                   # 框架核心
│   ├── app.go                   # 应用容器
│   ├── bootstrap/               # Provider 实现
│   │   ├── provider_config.go
│   │   ├── provider_logger.go
│   │   ├── provider_mysql.go
│   │   └── provider_websocket.go
│   ├── config/                  # 配置管理
│   ├── drivers/                 # 数据库驱动
│   ├── http/                    # HTTP 服务器
│   ├── log/                     # 日志系统
│   ├── provider/                # Provider 接口
│   └── websocket/               # WebSocket 核心
│       ├── connection.go        # 连接管理
│       ├── errors.go            # 错误定义
│       ├── message.go           # 消息协议
│       ├── router.go            # 消息路由
│       └── server.go            # WebSocket 服务器
├── internal/                    # 业务逻辑
│   ├── controller/              # 控制器
│   ├── logic/                   # 业务逻辑
│   ├── middleware/              # 中间件
│   ├── model/                   # 数据模型
│   └── router/                  # 路由注册
├── pkg/                         # 公共工具
├── go.mod                       # 依赖管理
└── Makefile                     # 构建脚本
```

## 架构设计

### Provider 模式

所有服务组件都实现 Provider 接口：

```go
type Provider interface {
    Name() string      // Provider 名称
    Init() error       // 初始化资源
    Boot() error       // 启动服务
    Close() error      // 清理资源
}
```

**生命周期：**

1. App 创建
2. Provider 注册（按顺序）
3. Provider Init（所有 Provider）
4. Provider Boot（所有 Provider）
5. 应用运行
6. 收到关闭信号
7. Provider Close（反向顺序）
8. 应用退出

### WebSocket 消息协议

**消息格式：**

```json
{
  "id": "msg1",
  "type": "text",
  "from": "client_id",
  "to": "target_client_id",
  "session_id": "session1",
  "timestamp": 1234567890,
  "content": {
    "text": "Hello!"
  }
}
```

**消息类型：**

- `text`：文本消息
- `file`：文件消息
- `tool_call`：工具调用
- `tool_result`：工具结果
- `heartbeat`：心跳消息
- `status`：状态消息

### 消息路由

```
App → WebSocket Server → Agent
App ← WebSocket Server ← Agent
```

1. App 发送消息到 WebSocket 服务器
2. 服务器根据 session_id 找到对应的 Agent
3. 服务器将消息转发给 Agent
4. Agent 处理消息并返回结果
5. 服务器将结果转发回 App

## 配置说明

### 应用配置（conf/dev.yml）

```yaml
app:
  name: websocket-platform
  env: dev
  port: 8080
  mode: debug
```

### WebSocket 配置（conf/includes/websocket/dev.yml）

```yaml
websocket:
  read_buffer_size: 1024
  write_buffer_size: 1024
  ping_period: 54s
  pong_wait: 60s
  max_message_size: 8192
  max_connections: 10000
  connection_timeout: 30s
  message_queue_size: 1000
  heartbeat_interval: 30s
```

## 开发指南

### 添加新的消息类型

1. 在 `framework/websocket/message.go` 中定义新的消息类型
2. 在 `framework/websocket/router.go` 中注册新的处理器
3. 实现处理逻辑

### 添加新的 Provider

1. 实现 Provider 接口
2. 在 `framework/bootstrap/` 创建文件
3. 在 `cmd/server/main.go` 中注册

### 添加新的路由

1. 在 `internal/controller/` 创建控制器
2. 在 `internal/router/router.go` 注册路由

## 常用命令

```bash
# 构建
make build

# 运行
make run

# 测试
make test

# 清理
make clean

# 格式化代码
make fmt

# 代码检查
make lint
```

## 技术栈

- **语言**：Go 1.21+
- **Web 框架**：Gin
- **WebSocket**：gorilla/websocket
- **配置管理**：Viper
- **日志**：Zap
- **数据库**：GORM + MySQL

## 注意事项

1. **Provider 顺序很重要**：按依赖关系注册
2. **配置必须验证**：启动时验证必需字段
3. **错误必须处理**：所有错误向上传递
4. **Context 必须支持**：长时间操作支持取消
5. **日志必须记录**：关键操作记录日志

## 后续计划

- [ ] 完善消息路由逻辑
- [ ] 添加会话持久化
- [ ] 实现消息队列
- [ ] 添加认证授权
- [ ] 实现消息加密
- [ ] 添加监控指标
- [ ] 编写单元测试
- [ ] 添加 API 文档

## 许可证

MIT License
