# 使用示例和集成指南

## 快速开始

### 1. 环境准备

确保已安装：
- Go 1.21+
- MySQL 5.7+

### 2. 启动服务器

```bash
cd websocket-platform
make deps  # 安装依赖
make run   # 启动服务器
```

服务器将在 `http://localhost:8080` 启动。

## JavaScript 客户端集成

### 基础示例

```javascript
// 连接 WebSocket
const ws = new WebSocket('ws://localhost:8080/ws/app?client_id=app1&user_id=user1&session_id=session1');

ws.onopen = () => {
  console.log('已连接到服务器');
};

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  console.log('收到消息:', message);
};

// 发送消息
function sendMessage(text) {
  const message = {
    id: 'msg_' + Date.now(),
    type: 'text',
    from: 'app1',
    session_id: 'session1',
    timestamp: Math.floor(Date.now() / 1000),
    content: { text: text }
  };
  
  ws.send(JSON.stringify(message));
}
```

### 高级客户端（支持重连）

```javascript
class AdvancedWebSocketClient {
  constructor(options) {
    this.url = options.url;
    this.clientId = options.clientId;
    this.userId = options.userId;
    this.sessionId = options.sessionId;
    this.reconnectInterval = options.reconnectInterval || 5000;
    this.maxReconnectAttempts = options.maxReconnectAttempts || 5;
    
    this.ws = null;
    this.reconnectAttempts = 0;
    this.shouldReconnect = true;
    this.messageQueue = [];
  }
  
  connect() {
    const url = `${this.url}/ws/app?client_id=${this.clientId}&user_id=${this.userId}&session_id=${this.sessionId}`;
    
    this.ws = new WebSocket(url);
    
    this.ws.onopen = () => {
      console.log('已连接');
      this.reconnectAttempts = 0;
      this.flushMessageQueue();
    };
    
    this.ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      this.handleMessage(message);
    };
    
    this.ws.onclose = () => {
      if (this.shouldReconnect && this.reconnectAttempts < this.maxReconnectAttempts) {
        this.reconnectAttempts++;
        setTimeout(() => this.connect(), this.reconnectInterval);
      }
    };
  }
  
  send(message) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    } else {
      this.messageQueue.push(message);
    }
  }
  
  flushMessageQueue() {
    while (this.messageQueue.length > 0) {
      const message = this.messageQueue.shift();
      this.send(message);
    }
  }
  
  handleMessage(message) {
    console.log('收到消息:', message);
  }
  
  close() {
    this.shouldReconnect = false;
    if (this.ws) {
      this.ws.close();
    }
  }
}

// 使用示例
const client = new AdvancedWebSocketClient({
  url: 'ws://localhost:8080',
  clientId: 'app1',
  userId: 'user1',
  sessionId: 'session1'
});

client.connect();
```

## Python 客户端集成

```python
import asyncio
import json
import time
from websockets import connect

class WebSocketClient:
    def __init__(self, url, client_id, user_id, session_id):
        self.url = url
        self.client_id = client_id
        self.user_id = user_id
        self.session_id = session_id
        self.ws = None
    
    async def connect(self):
        ws_url = f"{self.url}/ws/app?client_id={self.client_id}&user_id={self.user_id}&session_id={self.session_id}"
        self.ws = await connect(ws_url)
        print("已连接到服务器")
    
    async def send(self, message):
        if self.ws:
            await self.ws.send(json.dumps(message))
    
    async def receive(self):
        if self.ws:
            message = await self.ws.recv()
            return json.loads(message)
        return None
    
    async def close(self):
        if self.ws:
            await self.ws.close()

async def main():
    client = WebSocketClient(
        url='ws://localhost:8080',
        client_id='python1',
        user_id='user1',
        session_id='session1'
    )
    
    await client.connect()
    
    # 发送消息
    message = {
        'id': f'msg_{int(time.time())}',
        'type': 'text',
        'from': 'python1',
        'session_id': 'session1',
        'timestamp': int(time.time()),
        'content': {'text': 'Hello from Python!'}
    }
    await client.send(message)
    
    # 接收消息
    while True:
        try:
            received = await client.receive()
            print(f"收到消息: {received}")
        except KeyboardInterrupt:
            break
    
    await client.close()

if __name__ == '__main__':
    asyncio.run(main())
```

## Agent 集成示例

### Python Agent

```python
import asyncio
import json
import time
from websockets import connect

class Agent:
    def __init__(self, agent_id, user_id, session_id):
        self.agent_id = agent_id
        self.user_id = user_id
        self.session_id = session_id
        self.ws = None
    
    async def connect(self):
        url = f"ws://localhost:8080/ws/agent?client_id={self.agent_id}&user_id={self.user_id}&session_id={self.session_id}"
        self.ws = await connect(url)
        print(f"Agent {self.agent_id} 已连接")
    
    async def process_message(self, message):
        """处理来自 App 的消息"""
        if message['type'] == 'text':
            # 处理文本消息
            text = message['content']['text']
            response_text = f"Agent 回复: {text}"
            
            # 发送回复
            response = {
                'id': f'msg_{int(time.time())}',
                'type': 'text',
                'from': self.agent_id,
                'session_id': self.session_id,
                'timestamp': int(time.time()),
                'content': {'text': response_text}
            }
            await self.ws.send(json.dumps(response))
    
    async def run(self):
        """运行 Agent"""
        await self.connect()
        
        while True:
            try:
                data = await self.ws.recv()
                message = json.loads(data)
                print(f"收到消息: {message}")
                
                await self.process_message(message)
            except Exception as e:
                print(f"错误: {e}")
                break

async def main():
    agent = Agent(
        agent_id='agent1',
        user_id='user1',
        session_id='session1'
    )
    
    await agent.run()

if __name__ == '__main__':
    asyncio.run(main())
```

## 测试工具

### 使用 wscat 测试

```bash
# 安装 wscat
npm install -g wscat

# 连接测试
wscat -c "ws://localhost:8080/ws/app?client_id=test1&user_id=user1&session_id=session1"

# 发送消息
> {"id":"msg1","type":"text","from":"test1","session_id":"session1","timestamp":1715088000,"content":{"text":"Hello"}}
```

## 最佳实践

### 1. 错误处理

```javascript
ws.onerror = (error) => {
  console.error('WebSocket 错误:', error);
};

ws.onclose = (event) => {
  if (event.code !== 1000) {
    console.error('异常断开:', event.code, event.reason);
  }
};
```

### 2. 消息验证

```javascript
function validateMessage(message) {
  if (!message.id || !message.type || !message.from || 
      !message.session_id || !message.timestamp || !message.content) {
    return false;
  }
  
  const validTypes = ['text', 'file', 'tool_call', 'tool_result', 'heartbeat', 'status'];
  return validTypes.includes(message.type);
}
```

### 3. 心跳机制

```javascript
// 定期发送心跳
setInterval(() => {
  if (ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({
      id: 'heartbeat_' + Date.now(),
      type: 'heartbeat',
      from: clientId,
      session_id: sessionId,
      timestamp: Math.floor(Date.now() / 1000),
      content: { timestamp: Date.now() }
    }));
  }
}, 30000);
```

## 下一步

- 查看 [WebSocket API 文档](./websocket_api.md) 了解连接细节
- 查看 [消息格式说明](./message_format.md) 了解消息结构
