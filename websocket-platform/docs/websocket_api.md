# WebSocket API 文档

## 概述

WebSocket Platform 提供基于 WebSocket 的实时双向通信能力，支持 App 客户端和 Agent 客户端之间的消息转发。

## 连接端点

### App 客户端连接

**端点：** `ws://localhost:8080/ws/app`

**连接参数：**
- `client_id`: 客户端唯一标识（必填）
- `user_id`: 用户ID（必填）
- `session_id`: 会话ID（必填）

**示例：**
```javascript
const ws = new WebSocket('ws://localhost:8080/ws/app?client_id=app1&user_id=user1&session_id=session1');
```

### Agent 客户端连接

**端点：** `ws://localhost:8080/ws/agent`

**连接参数：**
- `client_id`: 客户端唯一标识（必填）
- `user_id`: 用户ID（必填）
- `session_id`: 会话ID（必填）

**示例：**
```javascript
const ws = new WebSocket('ws://localhost:8080/ws/agent?client_id=agent1&user_id=user1&session_id=session1');
```

## 连接流程

### 1. 建立连接

客户端通过 HTTP 升级请求建立 WebSocket 连接：

```
GET /ws/app?client_id=app1&user_id=user1&session_id=session1 HTTP/1.1
Host: localhost:8080
Upgrade: websocket
Connection: Upgrade
Sec-WebSocket-Key: <随机生成的Base64编码的16字节值>
Sec-WebSocket-Version: 13
```

服务器返回升级响应：

```
HTTP/1.1 101 Switching Protocols
Upgrade: websocket
Connection: Upgrade
Sec-WebSocket-Accept: <根据Sec-WebSocket-Key计算出的值>
```

### 2. 连接成功

连接建立后，服务器会发送欢迎消息：

```json
{
  "id": "welcome_msg_id",
  "type": "status",
  "from": "system",
  "session_id": "session1",
  "timestamp": 1715088000,
  "content": {
    "status": "connected",
    "message": "Welcome! Client ID: app1"
  }
}
```

### 3. 心跳机制

服务器会定期发送 Ping 消息（每54秒），客户端需要响应 Pong 消息。

如果客户端在60秒内没有响应，服务器将关闭连接。

客户端也可以主动发送心跳消息：

```json
{
  "id": "heartbeat_123",
  "type": "heartbeat",
  "from": "app1",
  "session_id": "session1",
  "timestamp": 1715088000,
  "content": {
    "timestamp": 1715088000
  }
}
```

服务器会响应心跳消息：

```json
{
  "id": "heartbeat_456",
  "type": "heartbeat",
  "from": "system",
  "session_id": "session1",
  "timestamp": 1715088001,
  "content": {
    "timestamp": 1715088000
  }
}
```

### 4. 断开连接

客户端可以主动关闭连接：

```javascript
ws.close();
```

服务器会清理相关资源并记录日志。

## 错误处理

### 连接错误

**错误码：**

- `400 Bad Request`: 参数缺失或无效
- `503 Service Unavailable`: 达到最大连接数限制

**示例错误响应：**

```json
{
  "error": "missing required parameters"
}
```

### 消息错误

如果发送的消息格式不正确，服务器会记录错误日志并忽略该消息。

**常见错误：**

1. JSON 格式错误
2. 缺少必需字段
3. 消息类型不存在

## 连接限制

### 最大连接数

默认支持最多 10,000 个并发连接（可在配置中调整）。

### 消息大小限制

单条消息最大 8,192 字节（可在配置中调整）。

### 发送队列

每个客户端的发送队列大小为 100 条消息，超出后会丢弃新消息。

## 连接状态

客户端可以通过以下方式判断连接状态：

```javascript
ws.onopen = () => {
  console.log('Connected');
};

ws.onclose = (event) => {
  console.log('Disconnected', event.code, event.reason);
};

ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};
```

## 完整连接示例

### JavaScript (浏览器)

```javascript
class WebSocketClient {
  constructor(clientId, userId, sessionId, clientType = 'app') {
    this.clientId = clientId;
    this.userId = userId;
    this.sessionId = sessionId;
    this.clientType = clientType;
    this.ws = null;
  }

  connect() {
    const url = `ws://localhost:8080/ws/${this.clientType}?client_id=${this.clientId}&user_id=${this.userId}&session_id=${this.sessionId}`;
    
    this.ws = new WebSocket(url);
    
    this.ws.onopen = () => {
      console.log('Connected to WebSocket server');
      this.startHeartbeat();
    };
    
    this.ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      console.log('Received:', message);
      this.handleMessage(message);
    };
    
    this.ws.onclose = (event) => {
      console.log('Disconnected:', event.code, event.reason);
      this.stopHeartbeat();
    };
    
    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
  }

  send(message) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    }
  }

  handleMessage(message) {
    switch (message.type) {
      case 'text':
        console.log('Text message:', message.content.text);
        break;
      case 'status':
        console.log('Status:', message.content.status);
        break;
      case 'heartbeat':
        // Ignore heartbeat responses
        break;
      default:
        console.log('Unknown message type:', message.type);
    }
  }

  startHeartbeat() {
    this.heartbeatInterval = setInterval(() => {
      this.send({
        id: `heartbeat_${Date.now()}`,
        type: 'heartbeat',
        from: this.clientId,
        session_id: this.sessionId,
        timestamp: Date.now(),
        content: { timestamp: Date.now() }
      });
    }, 30000);
  }

  stopHeartbeat() {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
    }
  }

  close() {
    this.stopHeartbeat();
    if (this.ws) {
      this.ws.close();
    }
  }
}

// 使用示例
const client = new WebSocketClient('app1', 'user1', 'session1', 'app');
client.connect();

// 发送消息
client.send({
  id: 'msg1',
  type: 'text',
  from: 'app1',
  session_id: 'session1',
  timestamp: Date.now(),
  content: { text: 'Hello from App!' }
});
```

## 下一步

- 查看 [消息格式说明](./message_format.md) 了解详细的消息结构
- 查看 [集成指南](./integration_guide.md) 了解如何集成到你的应用
