"""
简单Agent示例 - 演示如何使用Agent系统

这个示例展示了：
1. 如何创建Agent
2. 如何配置Memory和Context
3. 如何注册和使用工具
4. 如何运行Agent

学习重点：
1. Agent的完整使用流程
2. 各组件的配置方法
3. 工具的使用方式
"""

import sys
import os

# 添加项目根目录到路径 (从 q_agent/q_agent/agents/ 上升到 q_agent/)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from q_agent.core import Agent, Memory
from q_agent.core import ContextManager
from q_agent.tools import (
    ToolRegistry,
    CalculatorTool,
    FileReadTool,
    FileWriteTool,
    FileEditTool,
    FileListTool,
    SearchTool,
    ShellTool,
    WebFetchTool,
    WebSearchTool,
    UrlFetchTool,
    DateTimeTool,
    ImageAnalyzeTool,
    MemorySaveTool,
)


def create_simple_agent():
    """
    创建一个简单的Agent
    
    返回：
        Agent: 配置好的Agent实例
    
    步骤：
    1. 创建Memory系统
    2. 创建Context管理器
    3. 创建工具注册器并注册工具
    4. 创建Agent并注入依赖
    """
    print("创建Agent...")
    
    # 创建Memory系统
    memory = Memory(max_short_term=20)
    print("✅ Memory系统创建完成")
    
    # 创建Context管理器
    context_manager = ContextManager(max_tokens=4000)
    print("✅ Context管理器创建完成")
    
    # 创建工具注册器
    tool_registry = ToolRegistry()
    
    # 注册所有工具
    tool_registry.register(CalculatorTool())
    tool_registry.register(FileReadTool())
    tool_registry.register(FileWriteTool())
    tool_registry.register(FileEditTool())
    tool_registry.register(FileListTool())
    tool_registry.register(SearchTool())
    tool_registry.register(ShellTool())
    tool_registry.register(WebFetchTool())
    tool_registry.register(WebSearchTool())
    tool_registry.register(UrlFetchTool())
    tool_registry.register(DateTimeTool())
    tool_registry.register(ImageAnalyzeTool())
    tool_registry.register(MemorySaveTool())
    print(f"✅ 工具注册完成: {tool_registry.get_tool_count()} 个工具")
    
    # 创建Agent
    agent = Agent(
        memory=memory,
        context_manager=context_manager,
        tools=tool_registry.get_tools()  # 使用get_tools()返回Tool对象列表
    )
    print("✅ Agent创建完成")
    
    return agent


def test_calculator_task():
    """
    测试计算器任务
    
    演示Agent如何使用计算器工具
    """
    print("\n" + "=" * 60)
    print("测试计算器任务")
    print("=" * 60)
    
    # 创建Agent
    agent = create_simple_agent()
    
    # 执行计算任务
    task = "请计算 123 + 456 的结果"
    print(f"\n任务: {task}")
    
    try:
        result = agent.run(task)
        print(f"\n结果: {result}")
    except Exception as e:
        print(f"\n错误: {str(e)}")
        print("注意: 需要配置LLM API Key才能运行")


def test_search_task():
    """
    测试搜索任务
    
    演示Agent如何使用搜索工具
    """
    print("\n" + "=" * 60)
    print("测试搜索任务")
    print("=" * 60)
    
    # 创建Agent
    agent = create_simple_agent()
    
    # 执行搜索任务
    task = "请在文本'AI Agent是人工智能的重要概念，Agent Loop是核心机制'中搜索'Agent'"
    print(f"\n任务: {task}")
    
    try:
        result = agent.run(task)
        print(f"\n结果: {result}")
    except Exception as e:
        print(f"\n错误: {str(e)}")
        print("注意: 需要配置LLM API Key才能运行")


def show_agent_stats():
    """
    显示Agent统计信息
    
    展示Agent内部状态
    """
    print("\n" + "=" * 60)
    print("Agent统计信息")
    print("=" * 60)
    
    # 创建Agent
    agent = create_simple_agent()
    
    # 添加一些测试消息
    agent.memory.add_message("user", "测试消息1")
    agent.memory.add_message("assistant", "收到测试消息1")
    agent.memory.add_message("user", "测试消息2")
    
    # 显示统计信息
    print("\nMemory统计:")
    memory_stats = agent.memory.get_stats()
    for key, value in memory_stats.items():
        print(f"  {key}: {value}")
    
    print("\nContext统计:")
    context_stats = agent.context_manager.get_stats()
    for key, value in context_stats.items():
        print(f"  {key}: {value}")


def main():
    """
    主函数 - 运行所有示例
    """
    print("=" * 60)
    print("简单Agent示例")
    print("=" * 60)
    
    # 显示统计信息
    show_agent_stats()
    
    # 测试计算器任务
    test_calculator_task()
    
    # 测试搜索任务
    test_search_task()
    
    print("\n" + "=" * 60)
    print("示例执行完成！")
    print("=" * 60)
    print("\n提示:")
    print("1. 要运行完整的Agent，需要配置LLM API Key")
    print("2. 在环境变量中设置: export Q_AGENT_LLM_API_KEY='your-api-key'")
    print("3. 或在配置文件中设置 llm.api_key")


if __name__ == "__main__":
    main()
