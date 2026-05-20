# q_agent 流式输出开发计划

> 版本: 1.0.0 | 日期: 2025-05-18 | 状态: 待开发

## 一、概述

### 1.1 目标

实现从 LLM 到 Agent 的完整流式输出链路，让用户能够实时看到生成内容，提升交互体验。

### 1.2 当前状态

- LLM 客户端返回完整的 `LLMResponse` 对象
- 底层 API（OpenAI、Anthropic、Ollama）都原生支持流式输出
- WebSocket 端已有消息推送机制
- SkillExecutor 和 Agent 都是同步返回完整结果

### 1.3 流式输出链路

```
LLM API (stream) → LLMClient (stream_call) → SkillExecutor (execute_stream) → Agent (run_stream) → WebSocket (push chunks)
```

---

## 二、开发阶段概览

| Phase | 内容 | 预计工时 | 依赖 |
|-------|------|----------|------|
| Phase 1 | LLM 客户端流式接口 | 2h | 无 |
| Phase 2 | OpenAI 流式实现 | 1h | Phase 1 |
| Phase 3 | Anthropic 流式实现 | 1h | Phase 1 |
| Phase 4 | Ollama 流式实现 | 1h | Phase 1 |
| Phase 5 | SkillExecutor 流式支持 | 1.5h | Phase 1-4 |
| Phase 6 | Agent 流式支持 | 1h | Phase 5 |
| Phase 7 | WebSocket 流式推送 | 1h | Phase 6 |
| Phase 8 | 测试与文档 | 1h | Phase 7 |

**总计**: 约 9.5 小时

---

## 三、Phase 1: LLM 客户端流式接口

### 3.1 目标

- 在 BaseLLMClient 中定义流式调用抽象方法
- 定义流式响应数据类型

### 3.2 文件清单

| 文件 | 说明 |
|------|------|
| `q_agent/core/llm_client.py` | 添加流式接口 |

### 3.3 详细设计

#### 新增数据类型

```python
from typing import Generator, AsyncGenerator

@dataclass
class StreamChunk:
    """
    流式响应块

    每次返回的内容片段
    """
    content: str              # 本次返回的内容片段
    delta: str                # 增量内容（与 content 相同）
    is_finished: bool = False # 是否结束
    finish_reason: str = ""   # 结束原因：stop, length, tool_calls
    usage: Dict[str, int] = None  # 最后一个 chunk 包含 usage
```

#### BaseLLMClient 新增方法

```python
class BaseLLMClient(ABC):

    # 现有同步方法
    @abstractmethod
    def call(self, messages, **kwargs) -> LLMResponse:
        pass

    # 新增：流式调用（同步生成器）
    @abstractmethod
    def stream_call(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> Generator[StreamChunk, None, None]:
        """
        流式调用 LLM

        参数：
            messages: 消息列表
            **kwargs: 其他参数

        返回：
            Generator[StreamChunk]: 流式响应块生成器

        使用示例：
            for chunk in client.stream_call(messages):
                print(chunk.content, end="", flush=True)
        """
        pass

    # 新增：异步流式调用
    @abstractmethod
    async def stream_call_async(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> AsyncGenerator[StreamChunk, None]:
        """
        异步流式调用 LLM

        使用示例：
            async for chunk in client.stream_call_async(messages):
                print(chunk.content, end="", flush=True)
        """
        pass
```

### 3.4 验收标准

- [ ] StreamChunk 类型定义完整
- [ ] BaseLLMClient 包含流式抽象方法
- [ ] 子类未实现时报 NotImplementedError

---

## 四、Phase 2: OpenAI 流式实现

### 4.1 目标

为 OpenAIClient 实现流式调用方法

### 4.2 实现代码

```python
class OpenAIClient(BaseLLMClient):

    def stream_call(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> Generator[StreamChunk, None, None]:
        """
        OpenAI 流式调用

        文档：https://platform.openai.com/docs/api-reference/streaming
        """
        try:
            import openai

            client = openai.OpenAI(api_key=self.api_key)

            stream = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=kwargs.get("temperature", self.temperature),
                max_tokens=kwargs.get("max_tokens", self.max_tokens),
                stream=True  # 启用流式
            )

            for chunk in stream:
                delta = chunk.choices[0].delta

                # 检查是否结束
                if chunk.choices[0].finish_reason:
                    yield StreamChunk(
                        content="",
                        delta="",
                        is_finished=True,
                        finish_reason=chunk.choices[0].finish_reason,
                        usage={
                            "prompt_tokens": chunk.usage.prompt_tokens if chunk.usage else 0,
                            "completion_tokens": chunk.usage.completion_tokens if chunk.usage else 0,
                            "total_tokens": chunk.usage.total_tokens if chunk.usage else 0
                        }
                    )
                    break

                # 返回内容块
                content = delta.content or ""
                yield StreamChunk(
                    content=content,
                    delta=content,
                    is_finished=False
                )

        except Exception as e:
            yield StreamChunk(
                content="",
                delta="",
                is_finished=True,
                finish_reason="error",
                usage={"error": str(e)}
            )

    async def stream_call_async(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> AsyncGenerator[StreamChunk, None]:
        """
        OpenAI 异步流式调用
        """
        try:
            import openai

            client = openai.AsyncOpenAI(api_key=self.api_key)

            stream = await client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=kwargs.get("temperature", self.temperature),
                max_tokens=kwargs.get("max_tokens", self.max_tokens),
                stream=True
            )

            async for chunk in stream:
                delta = chunk.choices[0].delta

                if chunk.choices[0].finish_reason:
                    yield StreamChunk(
                        content="",
                        delta="",
                        is_finished=True,
                        finish_reason=chunk.choices[0].finish_reason
                    )
                    break

                content = delta.content or ""
                yield StreamChunk(
                    content=content,
                    delta=content,
                    is_finished=False
                )

        except Exception as e:
            yield StreamChunk(
                content="",
                delta="",
                is_finished=True,
                finish_reason="error"
            )
```

### 4.3 验收标准

- [ ] 同步流式调用正常工作
- [ ] 异步流式调用正常工作
- [ ] 正确处理 finish_reason
- [ ] 错误处理完善

---

## 五、Phase 3: Anthropic 流式实现

### 5.1 目标

为 AnthropicClient 实现流式调用方法

### 5.2 实现代码

```python
class AnthropicClient(BaseLLMClient):

    def stream_call(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> Generator[StreamChunk, None, None]:
        """
        Anthropic 流式调用

        文档：https://docs.anthropic.com/claude/reference/streaming
        """
        try:
            import anthropic

            client = anthropic.Anthropic(api_key=self.api_key)

            # 提取 system 消息
            system_message = ""
            chat_messages = []
            for msg in messages:
                if msg["role"] == "system":
                    system_message = msg["content"]
                else:
                    chat_messages.append(msg)

            with client.messages.stream(
                model=self.model,
                max_tokens=kwargs.get("max_tokens", self.max_tokens),
                temperature=kwargs.get("temperature", self.temperature),
                system=system_message if system_message else None,
                messages=chat_messages
            ) as stream:
                for text in stream.text_stream:
                    yield StreamChunk(
                        content=text,
                        delta=text,
                        is_finished=False
                    )

                # 获取最终消息（包含 usage）
                final_message = stream.get_final_message()
                yield StreamChunk(
                    content="",
                    delta="",
                    is_finished=True,
                    finish_reason="stop",
                    usage={
                        "prompt_tokens": final_message.usage.input_tokens,
                        "completion_tokens": final_message.usage.output_tokens,
                        "total_tokens": final_message.usage.input_tokens + final_message.usage.output_tokens
                    }
                )

        except Exception as e:
            yield StreamChunk(
                content="",
                delta="",
                is_finished=True,
                finish_reason="error"
            )
```

### 5.3 验收标准

- [ ] 流式调用正常工作
- [ ] 正确处理 system 消息
- [ ] 最后一个 chunk 包含 usage 信息

---

## 六、Phase 4: Ollama 流式实现

### 6.1 目标

为 OllamaClient 实现流式调用方法

### 6.2 实现代码

```python
class OllamaClient(BaseLLMClient):

    def stream_call(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> Generator[StreamChunk, None, None]:
        """
        Ollama 流式调用

        文档：https://github.com/ollama/ollama/blob/main/docs/api.md
        """
        try:
            import requests

            url = f"{self.base_url}/api/chat"
            data = {
                "model": self.model,
                "messages": messages,
                "stream": True,  # 启用流式
                "options": {
                    "temperature": kwargs.get("temperature", self.temperature),
                    "num_predict": kwargs.get("max_tokens", self.max_tokens)
                }
            }

            response = requests.post(url, json=data, stream=True)

            for line in response.iter_lines():
                if line:
                    import json
                    chunk = json.loads(line)

                    content = chunk.get('message', {}).get('content', '')

                    if chunk.get('done', False):
                        yield StreamChunk(
                            content="",
                            delta="",
                            is_finished=True,
                            finish_reason="stop",
                            usage={
                                "prompt_tokens": chunk.get('prompt_eval_count', 0),
                                "completion_tokens": chunk.get('eval_count', 0),
                                "total_tokens": chunk.get('prompt_eval_count', 0) + chunk.get('eval_count', 0)
                            }
                        )
                        break

                    if content:
                        yield StreamChunk(
                            content=content,
                            delta=content,
                            is_finished=False
                        )

        except Exception as e:
            yield StreamChunk(
                content="",
                delta="",
                is_finished=True,
                finish_reason="error"
            )
```

### 6.3 验收标准

- [ ] 流式调用正常工作
- [ ] 正确解析 NDJSON 响应
- [ ] 最后一个 chunk 包含 usage 信息

---

## 七、Phase 5: SkillExecutor 流式支持

### 7.1 目标

让 SkillExecutor 支持流式执行 Skill

### 7.2 文件清单

| 文件 | 说明 |
|------|------|
| `q_agent/skills/executor.py` | 添加流式执行方法 |

### 7.3 实现代码

```python
class SkillExecutor:

    def execute_stream(
        self,
        skill: Skill,
        user_input: str,
        context: Optional[SkillContext] = None,
        on_chunk: Optional[Callable[[str], None]] = None
    ) -> Generator[StreamChunk, None, None]:
        """
        流式执行 Skill

        参数：
            skill: 要执行的 Skill
            user_input: 用户输入
            context: 执行上下文
            on_chunk: 每个 chunk 的回调函数

        返回：
            Generator[StreamChunk]: 流式响应

        使用示例：
            for chunk in executor.execute_stream(skill, user_input):
                print(chunk.content, end="", flush=True)
                if on_chunk:
                    on_chunk(chunk.content)
        """
        # 特殊处理：list_skills 不需要流式
        if skill.meta.name == "list_skills":
            result = self._handle_list_skills()
            yield StreamChunk(content=result, delta=result, is_finished=True)
            return

        # 构建提示
        system_prompt = self._build_system_prompt(skill)
        user_prompt = self._build_user_prompt(skill, user_input)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        # 流式调用 LLM
        if self.llm_client and hasattr(self.llm_client, 'stream_call'):
            for chunk in self.llm_client.stream_call(messages):
                yield chunk
                if on_chunk:
                    on_chunk(chunk.content)
        else:
            # 降级为同步调用
            response = self._call_llm(messages, [])
            yield StreamChunk(content=response, delta=response, is_finished=True)
```

### 7.4 验收标准

- [ ] 流式执行正常工作
- [ ] 回调函数正确调用
- [ ] 不支持流式时降级为同步

---

## 八、Phase 6: Agent 流式支持

### 8.1 目标

让 Agent 支持流式运行

### 8.2 文件清单

| 文件 | 说明 |
|------|------|
| `q_agent/core/agent.py` | 添加流式运行方法 |

### 8.3 实现代码

```python
class Agent:

    def run_stream(
        self,
        task: str,
        on_chunk: Optional[Callable[[str], None]] = None
    ) -> Generator[StreamChunk, None, None]:
        """
        流式运行 Agent

        参数：
            task: 用户任务
            on_chunk: 每个 chunk 的回调函数

        返回：
            Generator[StreamChunk]: 流式响应

        使用示例：
            for chunk in agent.run_stream("帮我审查代码"):
                print(chunk.content, end="", flush=True)
        """
        # 尝试路由到 Skill
        skill, cleaned_input, confidence = self.skill_router.route(task)

        if skill and confidence > 0:
            print(f"🎯 匹配到 Skill: {skill.meta.name} (置信度: {confidence:.2f})")

            context = SkillContext(
                tool_registry=self.tool_registry,
                llm_client=self.llm_client,
                memory=self.memory,
                context_manager=self.context_manager,
                user_input=task
            )

            # 流式执行 Skill
            for chunk in self.skill_executor.execute_stream(skill, cleaned_input, context):
                yield chunk
                if on_chunk:
                    on_chunk(chunk.content)

            return

        # 无匹配 Skill，走普通 Agent Loop（流式）
        for chunk in self._run_agent_loop_stream(task):
            yield chunk
            if on_chunk:
                on_chunk(chunk.content)

    def _run_agent_loop_stream(self, task: str) -> Generator[StreamChunk, None, None]:
        """
        流式 Agent Loop
        """
        # 实现流式的 think → act → observe 循环
        # ...
        pass
```

### 8.4 验收标准

- [ ] 流式运行正常工作
- [ ] Skill 路由后流式执行
- [ ] 回调函数正确调用

---

## 九、Phase 7: WebSocket 流式推送

### 9.1 目标

通过 WebSocket 实时推送流式内容到前端

### 9.2 文件清单

| 文件 | 说明 |
|------|------|
| `websocket-platform/internal/controllers/` | WebSocket 消息处理 |

### 9.3 消息格式

```json
{
  "id": "msg_001",
  "type": "stream_chunk",
  "from": "agent",
  "to": "app_client",
  "session_id": "session_001",
  "timestamp": 1234567890,
  "content": {
    "text": "本次推送的内容片段",
    "is_finished": false,
    "finish_reason": ""
  }
}
```

### 9.4 实现思路

```python
# WebSocket 消息处理器
async def handle_agent_message_stream(websocket, message):
    """处理 Agent 流式消息"""

    # 创建 Agent
    agent = Agent(...)

    # 流式运行
    for chunk in agent.run_stream(message.content.text):
        # 构建流式消息
        stream_msg = {
            "id": generate_message_id(),
            "type": "stream_chunk",
            "content": {
                "text": chunk.content,
                "is_finished": chunk.is_finished,
                "finish_reason": chunk.finish_reason
            }
        }

        # 推送到 WebSocket
        await websocket.send_json(stream_msg)
```

### 9.5 前端适配

```javascript
// WebSocket 消息处理
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);

    if (data.type === 'stream_chunk') {
        // 流式追加内容
        appendToMessage(data.content.text);

        if (data.content.is_finished) {
            // 流式结束
            finishMessage();
        }
    } else {
        // 普通消息处理
        handleMessage(data);
    }
};
```

### 9.6 验收标准

- [ ] WebSocket 正确推送流式消息
- [ ] 前端正确接收并显示
- [ ] 流式结束后正确处理

---

## 十、Phase 8: 测试与文档

### 8.1 单元测试

```python
# tests/test_stream.py

def test_openai_stream():
    """测试 OpenAI 流式调用"""
    client = OpenAIClient(config)
    full_content = ""

    for chunk in client.stream_call([{"role": "user", "content": "Hello"}]):
        full_content += chunk.content

    assert len(full_content) > 0

def test_skill_executor_stream():
    """测试 Skill 流式执行"""
    executor = SkillExecutor(...)
    full_content = ""

    for chunk in executor.execute_stream(skill, "test input"):
        full_content += chunk.content

    assert len(full_content) > 0

def test_agent_run_stream():
    """测试 Agent 流式运行"""
    agent = Agent(...)
    full_content = ""

    for chunk in agent.run_stream("帮我审查代码"):
        full_content += chunk.content

    assert len(full_content) > 0
```

### 8.2 文档更新

- [ ] 更新 `llm_client.py` 文档字符串
- [ ] 更新 `executor.py` 文档字符串
- [ ] 更新 `agent.py` 文档字符串
- [ ] 添加使用示例到 `examples/`

---

## 十一、风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 流式中断 | 用户看到不完整内容 | 添加超时和重试机制 |
| 不同厂商 API 差异 | 实现复杂度增加 | 统一 StreamChunk 格式 |
| 工具调用 + 流式 | 实现复杂 | 先实现纯文本流式，工具调用后续支持 |
| WebSocket 连接断开 | 流式中断 | 添加断点续传或重新生成机制 |

---

## 十二、验收清单

### 功能验收

- [ ] OpenAI 流式调用正常
- [ ] Anthropic 流式调用正常
- [ ] Ollama 流式调用正常
- [ ] SkillExecutor 流式执行正常
- [ ] Agent 流式运行正常
- [ ] WebSocket 流式推送正常
- [ ] 前端流式显示正常

### 性能验收

- [ ] 流式首字延迟 < 500ms
- [ ] 流式过程无明显卡顿
- [ ] 内存占用合理

### 兼容性验收

- [ ] 不影响现有同步调用
- [ ] 不支持流式时自动降级
- [ ] 向后兼容现有 API

---

## 十三、后续扩展

### 13.1 工具调用 + 流式

当前方案先实现纯文本流式输出。后续可扩展支持：

```python
# 流式工具调用
for chunk in agent.run_stream("帮我搜索并总结"):
    if chunk.type == "text":
        print(chunk.content)
    elif chunk.type == "tool_call":
        print(f"调用工具: {chunk.tool_name}")
    elif chunk.type == "tool_result":
        print(f"工具结果: {chunk.result}")
```

### 13.2 多模态流式

支持图片、音频等多模态内容的流式输出。

### 13.3 流式取消

支持用户中途取消流式输出。

---

## 十四、参考文档

- [OpenAI Streaming API](https://platform.openai.com/docs/api-reference/streaming)
- [Anthropic Streaming](https://docs.anthropic.com/claude/reference/streaming)
- [Ollama API](https://github.com/ollama/ollama/blob/main/docs/api.md)
