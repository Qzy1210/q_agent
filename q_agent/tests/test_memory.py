"""
Memory系统测试 - 测试记忆系统的各项功能

测试内容：
1. 消息添加
2. 记忆检索
3. 记忆导出/导入
4. 边界情况处理

学习重点：
1. 理解单元测试的重要性
2. 掌握pytest的使用方法
3. 学习测试驱动开发（TDD）
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.memory import Memory, Message


def test_memory_init():
    """测试Memory初始化"""
    memory = Memory(max_short_term=10)
    
    # 检查初始状态
    assert len(memory.short_term_memory) == 0
    assert len(memory.long_term_memory) == 0
    assert memory.max_short_term == 10
    
    print("✅ Memory初始化测试通过")


def test_add_message():
    """测试添加消息"""
    memory = Memory(max_short_term=5)
    
    # 添加消息
    memory.add_message("user", "测试消息")
    
    # 检查消息数量
    assert len(memory.short_term_memory) == 1
    assert memory.stats["total_messages"] == 1
    
    # 检查消息内容
    msg = memory.short_term_memory[0]
    assert msg.role == "user"
    assert msg.content == "测试消息"
    
    print("✅ 添加消息测试通过")


def test_memory_overflow():
    """测试记忆溢出（超过最大数量）"""
    memory = Memory(max_short_term=3)
    
    # 添加超过限制的消息
    memory.add_message("user", "消息1")
    memory.add_message("user", "消息2")
    memory.add_message("user", "消息3")
    memory.add_message("user", "消息4")  # 应该移除消息1
    
    # 检查消息数量
    assert len(memory.short_term_memory) == 3
    
    # 检查最旧的消息已被移除
    assert memory.short_term_memory[0].content == "消息2"
    
    print("✅ 记忆溢出测试通过")


def test_search_memory():
    """测试记忆搜索"""
    memory = Memory(max_short_term=10)
    
    # 添加测试消息
    memory.add_message("user", "我想学习AI Agent")
    memory.add_message("assistant", "好的，我来帮你学习AI")
    memory.add_message("user", "什么是Agent Loop？")
    
    # 搜索关键词
    results = memory.search_memory("Agent")
    
    # 检查搜索结果
    assert len(results) == 2  # 应该找到2条包含Agent的消息
    
    print("✅ 记忆搜索测试通过")


def test_export_import():
    """测试记忆导出/导入"""
    memory1 = Memory(max_short_term=10)
    
    # 添加一些消息
    memory1.add_message("user", "测试导出")
    memory1.add_message("assistant", "好的")
    
    # 导出记忆
    exported = memory1.export_memory()
    
    # 创建新的Memory实例并导入
    memory2 = Memory(max_short_term=10)
    memory2.import_memory(exported)
    
    # 检查导入后的状态
    assert len(memory2.short_term_memory) == 2
    assert memory2.stats["total_messages"] == 2
    
    print("✅ 记忆导出/导入测试通过")


def test_important_messages():
    """测试重要消息标记"""
    memory = Memory(max_short_term=10)
    
    # 添加普通消息和重要消息
    memory.add_message("user", "普通消息", metadata={"important": False})
    memory.add_message("user", "重要消息", metadata={"important": True})
    
    # 搜索重要消息
    important = memory.get_important_messages()
    
    # 检查重要消息数量
    assert len(important) == 1
    assert important[0].content == "重要消息"
    
    print("✅ 重要消息测试通过")


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("Memory系统测试")
    print("=" * 60)
    
    # 运行所有测试函数
    test_memory_init()
    test_add_message()
    test_memory_overflow()
    test_search_memory()
    test_export_import()
    test_important_messages()
    
    print("=" * 60)
    print("✅ 所有测试通过！")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
