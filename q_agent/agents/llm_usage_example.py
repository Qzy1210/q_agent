"""
LLM客户端使用示例

演示如何使用统一的接口调用不同厂商的大模型
"""

import sys
import os

# 添加项目根目录到路径 (从 q_agent/q_agent/agents/ 上升到 q_agent/)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from q_agent.core.llm_client import LLMClientFactory
from q_agent.config import Config


def example_openai():
    """OpenAI使用示例"""
    print("\n" + "="*60)
    print("OpenAI使用示例")
    print("="*60)
    
    # 方式1：直接使用客户端
    config = {
        "provider": "openai",
        "api_key": "sk-your-api-key-here",  # 替换为真实的API Key
        "model": "gpt-3.5-turbo",
        "temperature": 0.7,
        "max_tokens": 100
    }
    
    client = LLMClientFactory.create(config)
    
    # 调用LLM
    messages = [
        {"role": "system", "content": "你是一个有帮助的助手。"},
        {"role": "user", "content": "你好，请介绍一下你自己。"}
    ]
    
    # 注意：这里会因为API Key无效而返回错误
    response = client.call(messages)
    print(f"\n响应: {response.content}")
    print(f"Token使用: {response.usage}")


def example_qwen():
    """通义千问使用示例"""
    print("\n" + "="*60)
    print("通义千问使用示例")
    print("="*60)
    
    config = {
        "provider": "qwen",
        "api_key": "your-dashscope-api-key",  # 替换为真实的API Key
        "model": "qwen-turbo",
        "temperature": 0.8,
        "max_tokens": 100
    }
    
    client = LLMClientFactory.create(config)
    
    messages = [
        {"role": "user", "content": "什么是人工智能？"}
    ]
    
    response = client.call(messages)
    print(f"\n响应: {response.content}")


def example_ollama():
    """Ollama本地模型使用示例"""
    print("\n" + "="*60)
    print("Ollama本地模型使用示例")
    print("="*60)
    
    config = {
        "provider": "ollama",
        "model": "llama2",  # 或 "mistral", "qwen" 等
        "base_url": "http://localhost:11434",  # Ollama默认地址
        "temperature": 0.7,
        "max_tokens": 100
    }
    
    # 注意：Ollama不需要API Key
    client = LLMClientFactory.create(config)
    
    messages = [
        {"role": "user", "content": "Hello!"}
    ]
    
    # 注意：需要先启动Ollama服务
    response = client.call(messages)
    print(f"\n响应: {response.content}")


def example_with_config_file():
    """使用配置文件的示例"""
    print("\n" + "="*60)
    print("使用配置文件示例")
    print("="*60)
    
    # 加载配置
    config = Config(config_file="config.json")
    
    # 获取LLM配置
    llm_config = {
        "provider": config.get("llm.provider"),
        "api_key": config.get("llm.api_key"),
        "model": config.get("llm.model"),
        "temperature": config.get("llm.temperature"),
        "max_tokens": config.get("llm.max_tokens")
    }
    
    print(f"LLM配置: provider={llm_config['provider']}, model={llm_config['model']}")
    
    # 创建客户端
    if llm_config["api_key"]:
        client = LLMClientFactory.create(llm_config)
        print("✅ 客户端创建成功")
    else:
        print("⚠️ 未配置API Key")


def example_with_agent():
    """在Agent中使用LLM客户端"""
    print("\n" + "="*60)
    print("在Agent中使用LLM客户端示例")
    print("="*60)
    
    from q_agent.core import Agent
    
    # 方式1：使用配置文件
    # config = Config(config_file="config.json")
    # agent = Agent(config=config)
    
    # 方式2：直接传入LLM客户端
    llm_config = {
        "provider": "openai",
        "api_key": "sk-your-api-key-here",
        "model": "gpt-3.5-turbo"
    }
    
    client = LLMClientFactory.create(llm_config)
    agent = Agent(llm_client=client)
    
    # 执行任务
    task = "帮我分析一下Python和JavaScript的区别"
    print(f"\n任务: {task}")
    result = agent.run(task)
    print(f"\n结果: {result}")


def main():
    """主函数"""
    print("="*60)
    print("LLM客户端使用示例")
    print("="*60)
    
    print("\n支持的厂商:")
    for provider in LLMClientFactory.list_providers():
        print(f"  - {provider}")
    
    # 运行示例
    print("\n注意：以下示例需要真实的API Key才能正常工作")
    print("请替换示例中的 'your-api-key-here' 为真实的API Key")
    
    # 取消注释以运行具体示例
    # example_openai()
    # example_qwen()
    # example_ollama()
    # example_with_config_file()
    # example_with_agent()
    
    print("\n" + "="*60)
    print("示例执行完成！")
    print("="*60)


if __name__ == "__main__":
    main()
