# 消息格式说明文档

## 消息结构

所有 WebSocket 消息都使用 JSON 格式，遵循统一的消息结构：

```json
{
  "id": "消息唯一标识",
  "type": "消息类型",
  "from": "发送者ID",
  "to": "接收者ID（可选）",
  "session_id": "会话ID",
  "timestamp": 1234567890,
  "content": {}
}
```

## 字段说明

### 必需字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | string | 消息唯一标识，用于消息追踪和去重 |
| `type` | string | 消息类型，见下方消息类型列表 |
| `from` | string | 发送者客户端ID |
| `session_id` | string | 会话ID，用于消息路由 |
| `timestamp` | number | Unix 时间戳（秒） |
| `content` | object | 消息内容，结构根据消息类型而定 |

### 可选字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `to` | string | 接收者客户端ID，用于点对点消息 |

## 消息类型

### 1. 文本消息 (text)

用于发送普通文本内容。

**消息示例：**

```json
{
  "id": "msg_20240507_001",
  "type": "text",
  "from": "app1",
  "session_id": "session1",
  "timestamp": 1715088000,
  "content": {
    "text": "你好，这是一条测试消息"
  }
}
```

**Content 字段：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `text` | string | 文本内容 |

**使用场景：**
- App 发送文本消息给 Agent
- Agent 回复文本消息给 App
- 聊天对话

### 2. 文件消息 (file)

用于发送文件内容，文件内容使用 Base64 编码。

**消息示例：**

```json
{
  "id": "msg_20240507_002",
  "type": "file",
  "from": "app1",
  "session_id": "session1",
  "timestamp": 1715088001,
  "content": {
    "name": "document.pdf",
    "type": "application/pdf",
    "size": 102400,
    "content": "base64_encoded_file_content_here"
  }
}
```

**Content 字段：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `name` | string | 文件名 |
| `type` | string | MIME 类型 |
| `size` | number | 文件大小（字节） |
| `content` | string | Base64 编码的文件内容 |

**使用场景：**
- 发送图片、文档等文件
- 文件共享

### 3. 工具调用 (tool_call)

用于调用 Agent 提供的工具。

**消息示例：**

```json
{
  "id": "msg_20240507_003",
  "type": "tool_call",
  "from": "app1",
  "session_id": "session1",
  "timestamp": 1715088002,
  "content": {
    "tool_name": "search",
    "parameters": {
      "query": "WebSocket 教程",
      "limit": 10
    }
  }
}
```

**Content 字段：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `tool_name` | string | 工具名称 |
| `parameters` | object | 工具参数，根据工具定义而定 |

**使用场景：**
- App 请求 Agent 执行特定功能
- 调用搜索、计算等工具

### 4. 工具结果 (tool_result)

Agent 返回工具执行结果。

**消息示例：**

```json
{
  "id": "msg_20240507_004",
  "type": "tool_result",
  "from": "agent1",
  "session_id": "session1",
  "timestamp": 1715088003,
  "content": {
    "tool_name": "search",
    "result": {
      "items": [
        {"title": "WebSocket 入门", "url": "https://example.com/1"},
        {"title": "WebSocket 进阶", "url": "https://example.com/2"}
      ],
      "total": 2
    },
    "error": ""
  }
}
```

**Content 字段：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `tool_name` | string | 工具名称 |
| `result` | any | 工具执行结果 |
| `error` | string | 错误信息，为空表示成功 |

**使用场景：**
- Agent 返回工具执行结果给 App

### 5. 心跳消息 (heartbeat)

用于保持连接活跃。

**消息示例：**

```json
{
  "id": "heartbeat_1715088004",
  "type": "heartbeat",
  "from": "app1",
  "session_id": "session1",
  "timestamp": 1715088004,
  "content": {
    "timestamp": 1715088004
  }
}
```

**Content 字段：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `timestamp` | number | 时间戳 |

**使用场景：**
- 客户端定期发送心跳
- 服务器响应心跳
- 检测连接是否存活

### 6. 状态消息 (status)

用于通知连接状态或其他状态信息。

**消息示例：**

```json
{
  "id": "status_1715088005",
  "type": "status",
  "from": "system",
  "session_id": "session1",
  "timestamp": 1715088005,
  "content": {
    "status": "connected",
    "message": "Welcome! Client ID: app1"
  }
}
```

**Content 字段：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `status` | string | 状态类型 |
| `message` | string | 状态描述 |

**常见状态：**
- `connected`: 连接成功
- `disconnected`: 连接断开
- `error`: 错误状态
- `busy`: 忙碌状态

**使用场景：**
- 连接建立时发送欢迎消息
- 状态变更通知
- 错误通知

### 7. 错误消息 (error)

用于通知错误信息。

**消息示例：**

```json
{
  "id": "error_1715088006",
  "type": "error",
  "from": "system",
  "session_id": "session1",
  "timestamp": 1715088006,
  "content": {
    "code": "INVALID_MESSAGE",
    "message": "消息格式错误",
    "details": "缺少必需字段: type"
  }
}
```

**Content 字段：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `code` | string | 错误代码 |
| `message` | string | 错误消息 |
| `details` | string | 详细错误信息 |

**常见错误代码：**
- `INVALID_MESSAGE`: 消息格式错误
- `UNKNOWN_TYPE`: 未知的消息类型
- `UNAUTHORIZED`: 未授权
- `RATE_LIMIT`: 频率限制

## 消息ID生成规则

消息ID格式：`YYYYMMDDHHmmss` + 8位随机字符

示例：`20240507120000abc123de`

**生成算法：**

```javascript
function generateMessageID() {
  const now = new Date();
  const timestamp = now.getFullYear().toString() +
    (now.getMonth() + 1).toString().padStart(2, '0') +
    now.getDate().toString().padStart(2, '0') +
    now.getHours().toString().padStart(2, '0') +
    now.getMinutes().toString().padStart(2, '0') +
    now.getSeconds().toString().padStart(2, '0');
  
  const random = Math.random().toString(36).substring(2, 10);
  
  return timestamp + random;
}
```

## 消息路由规则

### App → Agent

当 App 客户端发送消息时，服务器会：

1. 根据 `session_id` 查找对应的 Agent 客户端
2. 将消息转发给该 Agent
3. 保持消息原始内容不变

### Agent → App

当 Agent 客户端发送消息时，服务器会：

1. 根据 `session_id` 查找对应的所有 App 客户端
2. 将消息转发给所有 App 客户端（支持多设备）
3. 保持消息原始内容不变

### 消息流转示例

```
App Client                WebSocket Server                Agent Client
    |                            |                              |
    |--- text message --------->|                              |
    |                            |--- text message ---------->|
    |                            |                              |
    |                            |<--- text message -----------|
    |<--- text message ----------|                              |
    |                            |                              |
```

## 消息序列化

所有消息使用 JSON 格式序列化：

```javascript
// 序列化
const message = {
  id: 'msg1',
  type: 'text',
  from: 'app1',
  session_id: 'session1',
  timestamp: Date.now(),
  content: { text: 'Hello' }
};

const json = JSON.stringify(message);

// 反序列化
const received = JSON.parse(json);
```

## 消息验证

客户端发送消息前应验证：

1. **必需字段检查**
   - `id` 不为空
   - `type` 为有效类型
   - `from` 不为空
   - `session_id` 不为空
   - `timestamp` 为有效时间戳
   - `content` 不为空

2. **类型检查**
   - `type` 必须是以下之一：`text`, `file`, `tool_call`, `tool_result`, `heartbeat`, `status`, `error`

3. **内容检查**
   - 根据 `type` 验证 `content` 结构

**验证示例：**

```javascript
function validateMessage(message) {
  // 检查必需字段
  if (!message.id || !message.type || !message.from || 
      !message.session_id || !message.timestamp || !message.content) {
    return { valid: false, error: 'Missing required fields' };
  }
  
  // 检查消息类型
  const validTypes = ['text', 'file', 'tool_call', 'tool_result', 'heartbeat', 'status', 'error'];
  if (!validTypes.includes(message.type)) {
    return { valid: false, error: 'Invalid message type' };
  }
  
  // 检查内容结构
  switch (message.type) {
    case 'text':
      if (!message.content.text) {
        return { valid: false, error: 'Missing text field in content' };
      }
      break;
    // 其他类型的检查...
  }
  
  return { valid: true };
}
```

## 最佳实践

### 1. 消息ID唯一性

确保每条消息的ID唯一，可以使用：
- UUID
- 时间戳 + 随机数
- 雪花算法

### 2. 时间戳精度

使用秒级或毫秒级时间戳，保持一致性。

### 3. 消息大小控制

- 单条消息不超过 8KB
- 大文件应分块传输或使用文件服务器

### 4. 错误处理

- 总是检查消息格式
- 处理未知消息类型
- 记录错误日志

### 5. 消息顺序

WebSocket 保证消息顺序，但建议：
- 使用消息ID进行去重
- 实现消息确认机制（如需要）

## 下一步

- 查看 [WebSocket API 文档](./websocket_api.md) 了解连接细节
- 查看 [集成指南](./integration_guide.md) 了解如何集成
