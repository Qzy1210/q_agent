"""
Memory系统测试 - 测试记忆系统的各项功能

测试内容：
1. 消息保存
2. 记忆检索
3. 记忆导出/导入
4. 边界情况处理

学习重点：
1. 理解单元测试的重要性
2. 掌握pytest的使用方法
3. 学习测试驱动开发（TDD）

API变更说明（重构后）：
- Memory() 不再接受 max_short_term 参数
- add_message() → save_message()
- search_memory() → search()
- export_memory() → export_to_file(filepath)
- import_memory() → import_from_file(filepath)
- short_term_memory 已移除，统一使用 long_term_memory
- get_important_messages() 已移除
"""

import sys
import os
import tempfile
import json

# 添加项目根目录到路径（确保 q_agent 包可被导入）
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from q_agent.core.memory import Memory, Message


def test_memory_init():
    """测试Memory初始化"""
    memory = Memory()

    # 检查初始状态
    assert len(memory.long_term_memory) == 0
    assert memory.stats["total_messages"] == 0

    print("✅ Memory初始化测试通过")


def test_memory_init_with_storage_file():
    """测试带存储文件的Memory初始化"""
    # 创建临时文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump({
            "long_term": [
                {"role": "user", "content": "历史消息", "timestamp": "2024-01-01T00:00:00", "metadata": {}}
            ],
            "stats": {"total_messages": 1, "user_messages": 1, "assistant_messages": 0, "system_messages": 0}
        }, f)
        temp_path = f.name

    try:
        memory = Memory(storage_file=temp_path)

        # 检查是否加载了历史数据
        assert len(memory.long_term_memory) == 1
        assert memory.stats["total_messages"] == 1

        print("✅ 带存储文件的Memory初始化测试通过")
    finally:
        os.unlink(temp_path)


def test_save_message():
    """测试保存消息"""
    memory = Memory()

    # 保存消息
    memory.save_message("user", "测试消息")

    # 检查消息数量
    assert len(memory.long_term_memory) == 1
    assert memory.stats["total_messages"] == 1

    # 检查消息内容
    msg = memory.long_term_memory[0]
    assert msg.role == "user"
    assert msg.content == "测试消息"

    print("✅ 保存消息测试通过")


def test_save_multiple_messages():
    """测试保存多条消息"""
    memory = Memory()

    # 保存多条消息
    memory.save_message("user", "消息1")
    memory.save_message("assistant", "消息2")
    memory.save_message("user", "消息3")

    # 检查消息数量
    assert len(memory.long_term_memory) == 3
    assert memory.stats["total_messages"] == 3
    assert memory.stats["user_messages"] == 2
    assert memory.stats["assistant_messages"] == 1

    print("✅ 保存多条消息测试通过")


def test_search():
    """测试记忆搜索"""
    memory = Memory()

    # 保存测试消息
    memory.save_message("user", "我想学习AI Agent")
    memory.save_message("assistant", "好的，我来帮你学习AI")
    memory.save_message("user", "什么是Agent Loop？")

    # 搜索关键词
    results = memory.search("Agent")

    # 检查搜索结果（应该找到2条包含Agent的消息，大小写不敏感）
    assert len(results) == 2

    print("✅ 记忆搜索测试通过")


def test_search_case_insensitive():
    """测试搜索大小写不敏感"""
    memory = Memory()

    memory.save_message("user", "Hello World")
    memory.save_message("assistant", "hello world")

    # 搜索应该大小写不敏感
    results = memory.search("hello")
    assert len(results) == 2

    results = memory.search("WORLD")
    assert len(results) == 2

    print("✅ 搜索大小写不敏感测试通过")


def test_get_recent():
    """测试获取最近消息"""
    memory = Memory()

    # 保存多条消息
    for i in range(10):
        memory.save_message("user", f"消息{i}")

    # 获取最近5条
    recent = memory.get_recent(5)
    assert len(recent) == 5
    assert recent[-1]["content"] == "消息9"

    # 获取最近20条（超过总数）
    recent = memory.get_recent(20)
    assert len(recent) == 10

    print("✅ 获取最近消息测试通过")


def test_get_all():
    """测试获取所有消息"""
    memory = Memory()

    memory.save_message("user", "消息1")
    memory.save_message("assistant", "消息2")

    all_msgs = memory.get_all()
    assert len(all_msgs) == 2

    print("✅ 获取所有消息测试通过")


def test_clear():
    """测试清空记忆"""
    memory = Memory()

    memory.save_message("user", "消息1")
    memory.save_message("assistant", "消息2")

    assert len(memory.long_term_memory) == 2

    memory.clear()

    assert len(memory.long_term_memory) == 0
    assert memory.stats["total_messages"] == 0

    print("✅ 清空记忆测试通过")


def test_export_import():
    """测试记忆导出/导入"""
    memory1 = Memory()

    # 保存一些消息
    memory1.save_message("user", "测试导出")
    memory1.save_message("assistant", "好的")

    # 导出到临时文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_path = f.name

    try:
        memory1.export_to_file(temp_path)

        # 创建新的Memory实例并导入
        memory2 = Memory()
        memory2.import_from_file(temp_path)

        # 检查导入后的状态
        assert len(memory2.long_term_memory) == 2
        assert memory2.stats["total_messages"] == 2

        print("✅ 记忆导出/导入测试通过")
    finally:
        os.unlink(temp_path)


def test_message_to_dict():
    """测试Message转换为字典"""
    msg = Message("user", "测试内容", {"key": "value"})

    msg_dict = msg.to_dict()

    assert msg_dict["role"] == "user"
    assert msg_dict["content"] == "测试内容"
    assert msg_dict["metadata"] == {"key": "value"}
    assert "timestamp" in msg_dict

    print("✅ Message转字典测试通过")


def test_message_with_metadata():
    """测试带元数据的消息"""
    memory = Memory()

    metadata = {"important": True, "source": "test"}
    memory.save_message("user", "重要消息", metadata=metadata)

    msg = memory.long_term_memory[0]
    assert msg.metadata["important"] == True
    assert msg.metadata["source"] == "test"

    print("✅ 带元数据消息测试通过")


def test_get_summary():
    """测试获取记忆摘要"""
    memory = Memory()

    memory.save_message("user", "消息1")
    memory.save_message("assistant", "消息2")

    summary = memory.get_summary()

    assert "长期记忆: 2 条" in summary
    assert "总消息数: 2" in summary

    print("✅ 获取记忆摘要测试通过")


def test_search_no_results():
    """测试搜索无结果"""
    memory = Memory()

    memory.save_message("user", "Hello World")

    results = memory.search("xyz")
    assert len(results) == 0

    print("✅ 搜索无结果测试通过")


def test_empty_memory_operations():
    """测试空记忆的操作"""
    memory = Memory()

    # 空记忆的搜索
    results = memory.search("anything")
    assert len(results) == 0

    # 空记忆的获取最近
    recent = memory.get_recent(10)
    assert len(recent) == 0

    # 空记忆的获取所有
    all_msgs = memory.get_all()
    assert len(all_msgs) == 0

    print("✅ 空记忆操作测试通过")


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("Memory系统测试（重构后API）")
    print("=" * 60)

    # 运行所有测试函数
    test_memory_init()
    test_memory_init_with_storage_file()
    test_save_message()
    test_save_multiple_messages()
    test_search()
    test_search_case_insensitive()
    test_get_recent()
    test_get_all()
    test_clear()
    test_export_import()
    test_message_to_dict()
    test_message_with_metadata()
    test_get_summary()
    test_search_no_results()
    test_empty_memory_operations()

    print("=" * 60)
    print("✅ 所有测试通过！")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
