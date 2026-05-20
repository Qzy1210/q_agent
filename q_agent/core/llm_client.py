"""
通用LLM客户端 - 支持多厂商大模型调用

这个模块实现了统一的LLM调用接口，支持：
- OpenAI (GPT-3.5, GPT-4)
- Anthropic (Claude)
- 国产大模型 (通义千问、文心一言、智谱AI等)
- 本地模型 (Ollama)

学习重点：
1. 理解不同LLM API的统一封装
2. 掌握配置驱动的厂商切换
3. 学习错误处理和重试机制
"""

import json
import re
import time
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod
from dataclasses import dataclass


def repair_json(json_str: str) -> str:
    """
    修复 LLM 生成的损坏 JSON

    常见问题：
    1. 无效转义序列（如 \\以、\\*、\\@）
    2. 未终止的字符串
    3. 多余的逗号
    4. 缺少引号

    参数:
        json_str: 可能损坏的 JSON 字符串

    返回:
        修复后的 JSON 字符串
    """
    if not json_str:
        return json_str

    result = json_str

    # 1. 修复无效转义序列
    # 有效转义: " \ / b f n r t u(XXXX)
    result = re.sub(r'\\([^"\\/bfnrtu])', r'\\\\\1', result)

    # 2. 修复未转义的换行符（字符串中的裸换行）
    # 这个比较复杂，需要在字符串值内部替换
    # 简单做法：在 "..." 内部，将裸换行替换为 \n

    # 3. 移除尾部多余的逗号（如 ,] 或 ,}）
    result = re.sub(r',\s*([}\]])', r'\1', result)

    return result


def safe_json_loads(json_str: str, max_retries: int = 2) -> tuple[Optional[Dict], Optional[str]]:
    """
    安全的 JSON 解析，带自动修复

    参数:
        json_str: JSON 字符串
        max_retries: 最大修复重试次数

    返回:
        (解析后的字典, 错误信息)
        成功时错误信息为 None
    """
    # 第一次尝试：直接解析
    try:
        return json.loads(json_str), None
    except json.JSONDecodeError as e:
        pass

    # 尝试提取 JSON（处理 LLM 输出带有额外文本的情况）
    extracted = extract_json(json_str)
    if extracted and extracted != json_str:
        try:
            return json.loads(extracted), None
        except json.JSONDecodeError:
            pass

    # 尝试修复后解析
    for attempt in range(max_retries):
        try:
            fixed = repair_json(json_str if attempt == 0 else extracted)
            return json.loads(fixed), None
        except json.JSONDecodeError:
            continue

    return None, f"JSON 解析失败，尝试修复 {max_retries} 次后仍无效"


def extract_json(text: str) -> Optional[str]:
    """
    从文本中提取 JSON

    支持格式：
    1. Markdown 代码块: ```json\\n{...}\\n```
    2. 裸 JSON 对象: {...}
    3. 裸 JSON 数组: [...]
    """
    # 尝试提取代码块
    code_block = re.search(r'```(?:json)?\s*\n?([\s\S]*?)\n?```', text)
    if code_block:
        return code_block.group(1).strip()

    # 尝试提取 JSON 对象
    first_brace = text.find('{')
    last_brace = text.rfind('}')
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        return text[first_brace:last_brace + 1]

    # 尝试提取 JSON 数组
    first_bracket = text.find('[')
    last_bracket = text.rfind(']')
    if first_bracket != -1 and last_bracket != -1 and last_bracket > first_bracket:
        return text[first_bracket:last_bracket + 1]

    return text


@dataclass
class LLMResponse:
    """
    LLM响应数据类
    
    统一不同厂商的响应格式
    
    属性：
        content (str): 响应内容
        usage (Dict): token使用情况
        model (str): 使用的模型
        provider (str): 提供商
    """
    content: str
    usage: Dict[str, int]
    model: str
    provider: str
    raw_response: Any = None  # 原始响应，用于调试


class BaseLLMClient(ABC):
    """
    LLM客户端基类
    
    定义统一的接口，所有厂商客户端都需要实现这些方法
    
    设计思路：
    - 使用抽象基类定义接口
    - 子类实现具体厂商的调用逻辑
    - 统一的错误处理和重试机制
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化客户端
        
        参数：
            config (Dict): 配置字典，包含api_key、model等
        """
        self.config = config
        self.api_key = config.get("api_key", "")
        self.model = config.get("model", "")
        self.temperature = config.get("temperature", 0.7)
        self.max_tokens = config.get("max_tokens", 2000)
        
        # 验证配置
        if not self.api_key:
            raise ValueError(f"{self.__class__.__name__}: API key is required")
    
    @abstractmethod
    def call(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> LLMResponse:
        """
        调用LLM
        
        参数：
            messages (List): 消息列表，格式为 [{"role": "user", "content": "..."}]
            **kwargs: 其他参数
            
        返回：
            LLMResponse: 统一格式的响应
        """
        pass
    
    def _build_error_response(self, error_msg: str) -> LLMResponse:
        """
        构建错误响应
        
        参数：
            error_msg (str): 错误信息
            
        返回：
            LLMResponse: 包含错误信息的响应
        """
        return LLMResponse(
            content=f"Error: {error_msg}",
            usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            model=self.model,
            provider=self.__class__.__name__
        )


class OpenAIClient(BaseLLMClient):
    """
    OpenAI客户端
    支持 GPT-3.5、GPT-4 等模型
    文档：https://platform.openai.com/docs/api-reference
    """

    def call(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> LLMResponse:
        """
        调用OpenAI API

        参数：
            messages: 消息列表
            **kwargs: 其他参数（如temperature、max_tokens等）

        支持的结构化输出参数：
            response_format: {"type": "json_object"} 或 {"type": "json_schema", "json_schema": {...}}

        返回：
            LLMResponse: 统一格式响应
        """
        try:
            import openai

            # 创建客户端
            client = openai.OpenAI(api_key=self.api_key)

            # 构建请求参数
            request_params = {
                "model": self.model,
                "messages": messages,
                "temperature": kwargs.get("temperature", self.temperature),
                "max_tokens": kwargs.get("max_tokens", self.max_tokens),
            }

            # 支持结构化输出 (response_format)
            if "response_format" in kwargs:
                request_params["response_format"] = kwargs["response_format"]

            # 支持其他参数
            for k in ["tools", "tool_choice", "seed"]:
                if k in kwargs:
                    request_params[k] = kwargs[k]

            # 调用API
            response = client.chat.completions.create(**request_params)

            # 构建响应
            return LLMResponse(
                content=response.choices[0].message.content,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                },
                model=self.model,
                provider="openai",
                raw_response=response
            )

        except ImportError:
            return self._build_error_response("openai package not installed. Run: pip install openai")
        except Exception as e:
            return self._build_error_response(str(e))


class AnthropicClient(BaseLLMClient):
    """
    Anthropic客户端
    
    支持 Claude 系列模型
    
    文档：https://docs.anthropic.com/claude/reference
    """
    
    def call(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> LLMResponse:
        """
        调用Anthropic API
        
        参数：
            messages: 消息列表
            **kwargs: 其他参数
            
        返回：
            LLMResponse: 统一格式响应
        """
        try:
            import anthropic
            
            # 创建客户端
            client = anthropic.Anthropic(api_key=self.api_key)
            
            # 转换消息格式（Anthropic格式略有不同）
            # 提取system消息
            system_message = ""
            chat_messages = []
            for msg in messages:
                if msg["role"] == "system":
                    system_message = msg["content"]
                else:
                    chat_messages.append(msg)
            
            # 调用API
            response = client.messages.create(
                model=self.model,
                max_tokens=kwargs.get("max_tokens", self.max_tokens),
                temperature=kwargs.get("temperature", self.temperature),
                system=system_message if system_message else None,
                messages=chat_messages
            )
            
            # 构建响应
            return LLMResponse(
                content=response.content[0].text,
                usage={
                    "prompt_tokens": response.usage.input_tokens,
                    "completion_tokens": response.usage.output_tokens,
                    "total_tokens": response.usage.input_tokens + response.usage.output_tokens
                },
                model=self.model,
                provider="anthropic",
                raw_response=response
            )
            
        except ImportError:
            return self._build_error_response("anthropic package not installed. Run: pip install anthropic")
        except Exception as e:
            return self._build_error_response(str(e))


class QwenClient(BaseLLMClient):
    """
    通义千问客户端 (阿里云)
    
    支持 qwen-turbo、qwen-plus、qwen-max 等模型
    
    文档：https://help.aliyun.com/document_detail/610485.html
    """
    
    def call(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> LLMResponse:
        """
        调用通义千问 API
        
        参数：
            messages: 消息列表
            **kwargs: 其他参数
        返回：
            LLMResponse: 统一格式响应
        """
        try:
            import dashscope
            from dashscope import Generation
            
            # 设置API Key
            dashscope.api_key = self.api_key
            
            # 调用API
            response = Generation.call(
                model=self.model,
                messages=messages,
                temperature=kwargs.get("temperature", self.temperature),
                max_tokens=kwargs.get("max_tokens", self.max_tokens),
                result_format='message'
            )
            
            # 构建响应
            if response.status_code == 200:
                return LLMResponse(
                    content=response.output.choices[0]['message']['content'],
                    usage={
                        "prompt_tokens": response.usage.input_tokens,
                        "completion_tokens": response.usage.output_tokens,
                        "total_tokens": response.usage.total_tokens
                    },
                    model=self.model,
                    provider="qwen",
                    raw_response=response
                )
            else:
                return self._build_error_response(f"API call failed: {response.code} - {response.message}")
                
        except ImportError:
            return self._build_error_response("dashscope package not installed. Run: pip install dashscope")
        except Exception as e:
            return self._build_error_response(str(e))


class ZhipuClient(BaseLLMClient):
    """
    智谱AI客户端
    
    支持 glm-4、glm-3-turbo 等模型
    
    文档：https://open.bigmodel.cn/dev/api
    """
    
    def call(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> LLMResponse:
        """
        调用智谱AI API
        
        参数：
            messages: 消息列表
            **kwargs: 其他参数
            
        返回：
            LLMResponse: 统一格式响应
        """
        try:
            from zhipuai import ZhipuAI
            
            # 创建客户端
            client = ZhipuAI(api_key=self.api_key)
            
            # 调用API
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=kwargs.get("temperature", self.temperature),
                max_tokens=kwargs.get("max_tokens", self.max_tokens)
            )
            
            # 构建响应
            return LLMResponse(
                content=response.choices[0].message.content,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                },
                model=self.model,
                provider="zhipu",
                raw_response=response
            )
            
        except ImportError:
            return self._build_error_response("zhipuai package not installed. Run: pip install zhipuai")
        except Exception as e:
            return self._build_error_response(str(e))


class OllamaClient(BaseLLMClient):
    """
    Ollama本地模型客户端
    
    支持 llama2、mistral、qwen 等本地模型
    
    文档：https://github.com/ollama/ollama/blob/main/docs/api.md
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        # Ollama默认不需要API key，使用本地服务
        self.base_url = config.get("base_url", "http://localhost:11434")
    
    def call(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> LLMResponse:
        """
        调用Ollama API
        
        参数：
            messages: 消息列表
            **kwargs: 其他参数
            
        返回：
            LLMResponse: 统一格式响应
        """
        try:
            import requests
            
            # 构建请求
            url = f"{self.base_url}/api/chat"
            data = {
                "model": self.model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": kwargs.get("temperature", self.temperature),
                    "num_predict": kwargs.get("max_tokens", self.max_tokens)
                }
            }
            
            # 调用API
            response = requests.post(url, json=data)
            response.raise_for_status()
            
            result = response.json()
            
            # 构建响应
            return LLMResponse(
                content=result['message']['content'],
                usage={
                    "prompt_tokens": result.get('prompt_eval_count', 0),
                    "completion_tokens": result.get('eval_count', 0),
                    "total_tokens": result.get('prompt_eval_count', 0) + result.get('eval_count', 0)
                },
                model=self.model,
                provider="ollama",
                raw_response=result
            )
            
        except ImportError:
            return self._build_error_response("requests package not installed. Run: pip install requests")
        except Exception as e:
            return self._build_error_response(str(e))




class CustomClient(BaseLLMClient):
    """
    自定义大模型客户端
    
    支持用户自定义 API 端点、请求格式和响应解析
    适用于自定义部署的大模型或未内置的厂商
    
    配置示例：
        config = {
            "provider": "custom",
            "api_key": "your-api-key",
            "model": "your-model-name",
            "base_url": "http://your-api-endpoint",
            "request_format": "openai",  # 可选：openai, anthropic 或 custom
            "response_parser": None,  # 可选：自定义响应解析函数
            "headers": {},  # 可选：额外的请求头
            "temperature": 0.7,
            "max_tokens": 2000
        }
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化自定义客户端
        
        参数：
            config (Dict): 配置字典
        """
        # 对于自定义模型，api_key 可以为空（某些本地部署不需要）
        self.config = config
        self.api_key = config.get("api_key", "")
        self.model = config.get("model", "")
        self.temperature = config.get("temperature", 0.7)
        self.max_tokens = config.get("max_tokens", 2000)
        
        # 自定义配置
        self.base_url = config.get("base_url", "")
        self.request_format = config.get("request_format", "openai")
        self.response_parser = config.get("response_parser", None)
        self.headers = config.get("headers", {})
        
        # 验证必要配置
        if not self.base_url:
            raise ValueError("CustomClient: base_url is required")
        if not self.model:
            raise ValueError("CustomClient: model is required")
    
    def call(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> LLMResponse:
        """
        调用自定义大模型 API
        
        参数：
            messages: 消息列表
            **kwargs: 其他参数
            
        返回：
            LLMResponse: 统一格式响应
        """
        try:
            import requests
            
            # 构建请求头
            headers = {
                "Content-Type": "application/json",
                **self.headers
            }
            
            # 如果有 API key，添加到请求头
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            
            # 构建请求体
            if self.request_format == "openai":
                # OpenAI 兼容格式
                data = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": kwargs.get("temperature", self.temperature),
                    "max_tokens": kwargs.get("max_tokens", self.max_tokens)
                }
            elif self.request_format == "anthropic":
                # Anthropic 格式
                system_message = ""
                chat_messages = []
                for msg in messages:
                    if msg["role"] == "system":
                        system_message = msg["content"]
                    else:
                        chat_messages.append(msg)
                
                data = {
                    "model": self.model,
                    "messages": chat_messages,
                    "max_tokens": kwargs.get("max_tokens", self.max_tokens),
                    "temperature": kwargs.get("temperature", self.temperature)
                }
                if system_message:
                    data["system"] = system_message
            else:
                # 自定义格式：直接使用 messages
                data = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": kwargs.get("temperature", self.temperature),
                    "max_tokens": kwargs.get("max_tokens", self.max_tokens),
                    **kwargs
                }
            
            # 调用 API
            response = requests.post(
                self.base_url,
                headers=headers,
                json=data
            )

            # 打印调试信息
            print(f"📡 API响应状态码: {response.status_code}")
            if self.config.get("debug", False):
                print(f"📡 API响应头: {dict(response.headers)}")
                print(f"📡 API响应内容(前500字符): {response.text[:500]}")

            # 检查HTTP状态码
            if response.status_code != 200:
                error_msg = f"API返回错误状态码: {response.status_code}, 响应: {response.text[:500]}"
                return self._build_error_response(error_msg)

            # 检查响应内容是否为空
            if not response.text or not response.text.strip():
                return self._build_error_response("API返回空响应，请检查 base_url 是否正确")

            # 解析JSON响应
            try:
                result = response.json()
            except json.JSONDecodeError as e:
                return self._build_error_response(f"API响应不是有效的JSON格式: {str(e)}, 响应内容: {response.text[:500]}")
            
            # 解析响应
            if self.response_parser:
                # 使用自定义解析器
                parsed = self.response_parser(result)
                return LLMResponse(
                    content=parsed.get("content", ""),
                    usage=parsed.get("usage", {
                        "prompt_tokens": 0,
                        "completion_tokens": 0,
                        "total_tokens": 0
                    }),
                    model=self.model,
                    provider="custom",
                    raw_response=result
                )
            else:
                # 默认解析：尝试 OpenAI 格式
                try:
                    content = result["choices"][0]["message"]["content"]
                    usage = {
                        "prompt_tokens": result.get("usage", {}).get("prompt_tokens", 0),
                        "completion_tokens": result.get("usage", {}).get("completion_tokens", 0),
                        "total_tokens": result.get("usage", {}).get("total_tokens", 0)
                    }
                except (KeyError, IndexError):
                    # 如果不是 OpenAI 格式，尝试直接获取 content
                    content = result.get("content", result.get("text", str(result)))
                    usage = {
                        "prompt_tokens": 0,
                        "completion_tokens": 0,
                        "total_tokens": 0
                    }
                
                return LLMResponse(
                    content=content,
                    usage=usage,
                    model=self.model,
                    provider="custom",
                    raw_response=result
                )
            
        except ImportError:
            return self._build_error_response("requests package not installed. Run: pip install requests")
        except Exception as e:
            return self._build_error_response(str(e))


class LLMClientFactory:
    """
    LLM客户端工厂
    根据配置创建对应的客户端实例
    使用示例：
        config = {
            "provider": "openai",
            "api_key": "sk-xxx",
            "model": "gpt-3.5-turbo"
        }
        client = LLMClientFactory.create(config)
        response = client.call([{"role": "user", "content": "Hello"}])
    """
    # 支持的提供商映射
    PROVIDERS = {
        "openai": OpenAIClient,
        "anthropic": AnthropicClient,
        "qwen": QwenClient,
        "zhipu": ZhipuClient,
        "ollama": OllamaClient,
        "custom": CustomClient,
        # 别名支持
        "gpt": OpenAIClient,
        "claude": AnthropicClient,
        "dashscope": QwenClient,
        "chatglm": ZhipuClient,
    }
    @classmethod
    def create(cls, config: Dict[str, Any]) -> BaseLLMClient:
        """
        创建LLM客户端
        参数：
            config (Dict): 配置字典，必须包含provider字段
        返回：
            BaseLLMClient: 对应的客户端实例
        示例：
            config = {
                "provider": "openai",
                "api_key": "sk-xxx",
                "model": "gpt-3.5-turbo",
                "temperature": 0.7,
                "max_tokens": 2000
            }
            client = LLMClientFactory.create(config)
        """
        provider = config.get("provider", "openai").lower()
        if provider not in cls.PROVIDERS:
            raise ValueError(
                f"Unsupported provider: {provider}. "
                f"Supported providers: {list(cls.PROVIDERS.keys())}"
            )
        client_class = cls.PROVIDERS[provider]
        return client_class(config)
    @classmethod
    def list_providers(cls) -> List[str]:
        """
        列出所有支持的提供商
        返回：
            List[str]: 提供商列表
        """
        return list(set(cls.PROVIDERS.values()))
# 使用示例
if __name__ == "__main__":
    """
    LLM客户端使用示例
    演示如何使用统一的接口调用不同厂商的LLM
    """
    print("=" * 60)
    print("LLM客户端使用示例")
    print("=" * 60)
    # 列出支持的提供商
    print("\n支持的提供商：")
    for provider in LLMClientFactory.list_providers():
        print(f"  - {provider}")
    # 示例配置（实际使用时需要填写真实的API Key）
    config = {
        "provider": "openai",
        "api_key": "sk-your-api-key-here",  # 替换为真实的API Key
        "model": "gpt-3.5-turbo",
        "temperature": 0.7,
        "max_tokens": 100
    }
    print("\n注意：使用前请先在配置中设置真实的API Key")
    print(f"当前配置：provider={config['provider']}, model={config['model']}")
    print("\n" + "=" * 60)
    print("示例执行完成！")
    print("=" * 60)
