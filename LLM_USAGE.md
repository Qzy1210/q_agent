# LLM 客户端使用指南

## 概述

本项目实现了一个通用的 LLM 客户端，支持多个大模型厂商，可以通过配置文件轻松切换不同的模型提供商。

## 支持的厂商

| 厂商 | Provider 名称 | 支持的模型 | 官方文档 |
|------|--------------|-----------|---------|
| OpenAI | `openai` / `gpt` | gpt-3.5-turbo, gpt-4, gpt-4-turbo | [文档](https://platform.openai.com/docs) |
| Anthropic | `anthropic` / `claude` | claude-3-opus, claude-3-sonnet, claude-3-haiku | [文档](https://docs.anthropic.com) |
| 通义千问 | `qwen` / `dashscope` | qwen-turbo, qwen-plus, qwen-max | [文档](https://help.aliyun.com/document_detail/610485.html) |
| 智谱AI | `zhipu` / `chatglm` | glm-4, glm-3-turbo | [文档](https://open.bigmodel.cn/dev/api) |
| Ollama | `ollama` | llama2, mistral, qwen, etc. | [文档](https://github.com/ollama/ollama) |

## 配置方法

### 方式1：使用配置文件（推荐）

创建 `config.json` 文件（可以复制 `config.example.json`）：

```json
{
  "llm": {
    "provider": "openai",
    "model": "gpt-3.5-turbo",
    "api_key": "sk-your-api-key-here",
    "temperature": 0.7,
    "max_tokens": 2000
  }
}
```

然后在代码中：

```python
from q_agent.config import Config
from q_agent.core import Agent

# 加载配置
config = Config(config_file="config.json")

# 创建 Agent（会自动从配置初始化 LLM 客户端）
agent = Agent(config=config)

# 执行任务
result = agent.run("你的任务")
```

### 方式2：使用环境变量

设置环境变量：

```bash
# OpenAI
export Q_AGENT_LLM_PROVIDER=openai
export Q_AGENT_LLM_API_KEY=sk-your-api-key-here
export Q_AGENT_LLM_MODEL=gpt-3.5-turbo

# 或通义千问
export Q_AGENT_LLM_PROVIDER=qwen
export Q_AGENT_LLM_API_KEY=your-dashscope-api-key
export Q_AGENT_LLM_MODEL=qwen-turbo
```

### 方式3：直接创建客户端

```python
from q_agent.core.llm_client import LLMClientFactory

# 配置
config = {
    "provider": "openai",
    "api_key": "sk-your-api-key-here",
    "model": "gpt-3.5-turbo",
    "temperature": 0.7,
    "max_tokens": 2000
}

# 创建客户端
client = LLMClientFactory.create(config)

# 调用
messages = [
    {"role": "user", "content": "你好"}
]
response = client.call(messages)
print(response.content)
```

## 各厂商配置示例

### OpenAI

```json
{
  "llm": {
    "provider": "openai",
    "api_key": "sk-xxxxxxxxxxxxx",
    "model": "gpt-3.5-turbo",
    "temperature": 0.7,
    "max_tokens": 2000
  }
}
```

安装依赖：
```bash
pip install openai
```

### 通义千问（阿里云）

```json
{
  "llm": {
    "provider": "qwen",
    "api_key": "sk-xxxxxxxxxxxxx",
    "model": "qwen-turbo",
    "temperature": 0.8,
    "max_tokens": 2000
  }
}
```

安装依赖：
```bash
pip install dashscope
```

### 智谱AI

```json
{
  "llm": {
    "provider": "zhipu",
    "api_key": "xxxxxxxxxxxxx.xxxxxxxxxxxxx",
    "model": "glm-4",
    "temperature": 0.7,
    "max_tokens": 2000
  }
}
```

安装依赖：
```bash
pip install zhipuai
```

### Ollama（本地模型）

```json
{
  "llm": {
    "provider": "ollama",
    "model": "llama2",
    "base_url": "http://localhost:11434",
    "temperature": 0.7,
    "max_tokens": 2000
  }
}
```

**注意：** Ollama 不需要 API Key，但需要先安装并启动 Ollama 服务：

```bash
# 安装 Ollama
curl -fsSL https://ollama.com/install.sh | sh

# 启动服务
ollama serve

# 拉取模型
ollama pull llama2
```

安装 Python 依赖：
```bash
pip install requests
```

## 使用示例

### 基础使用

```python
from q_agent.core import Agent

# 创建 Agent（自动从配置文件加载）
agent = Agent()

# 执行任务
result = agent.run("帮我写一个 Python 函数计算斐波那契数列")
print(result)
```

### 切换不同模型

```python
from q_agent.core.llm_client import LLMClientFactory
from q_agent.core import Agent

# 使用 GPT-4
gpt4_config = {
    "provider": "openai",
    "api_key": "sk-xxx",
    "model": "gpt-4"
}
agent1 = Agent(llm_client=LLMClientFactory.create(gpt4_config))

# 使用通义千问
qwen_config = {
    "provider": "qwen",
    "api_key": "your-key",
    "model": "qwen-max"
}
agent2 = Agent(llm_client=LLMClientFactory.create(qwen_config))

# 使用本地 Ollama
ollama_config = {
    "provider": "ollama",
    "model": "llama2"
}
agent3 = Agent(llm_client=LLMClientFactory.create(ollama_config))
```

### 直接调用 LLM

```python
from q_agent.core.llm_client import LLMClientFactory

client = LLMClientFactory.create({
    "provider": "openai",
    "api_key": "sk-xxx",
    "model": "gpt-3.5-turbo"
})

messages = [
    {"role": "system", "content": "你是一个有帮助的助手。"},
    {"role": "user", "content": "什么是机器学习？"}
]

response = client.call(messages)
print(response.content)
print(f"Token使用: {response.usage}")
```

## 高级功能

### 调试模式

在配置中启用调试模式，查看详细的请求信息：

```json
{
  "debug": true,
  "llm": {
    ...
  }
}
```

### 错误处理

客户端会自动处理错误，返回包含错误信息的响应：

```python
response = client.call(messages)
if response.content.startswith("Error:"):
    print(f"调用失败: {response.content}")
else:
    print(response.content)
```

### Token 使用统计

每次调用后，可以从响应中获取 token 使用情况：

```python
response = client.call(messages)
print(f"Prompt tokens: {response.usage['prompt_tokens']}")
print(f"Completion tokens: {response.usage['completion_tokens']}")
print(f"Total tokens: {response.usage['total_tokens']}")
```

## 注意事项

1. **API Key 安全**：不要在代码中硬编码 API Key，建议使用配置文件或环境变量
2. **费用控制**：注意 token 使用量，避免产生高额费用
3. **模型选择**：根据任务需求选择合适的模型
4. **错误处理**：生产环境中要妥善处理 API 调用失败的情况
5. **依赖安装**：根据使用的厂商安装对应的 Python 包

## 扩展新的厂商

如需添加新的 LLM 厂商：

1. 在 `llm_client.py` 中创建新的客户端类，继承 `BaseLLMClient`
2. 实现 `call` 方法
3. 在 `LLMClientFactory.PROVIDERS` 中注册

示例：

```python
class NewProviderClient(BaseLLMClient):
    def call(self, messages: List[Dict[str, str]], **kwargs) -> LLMResponse:
        # 实现具体的调用逻辑
        pass

# 在工厂中注册
LLMClientFactory.PROVIDERS["new_provider"] = NewProviderClient
```

## 更多示例

查看 `examples/llm_usage_example.py` 获取更多使用示例。
