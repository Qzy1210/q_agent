"""
工具系统测试 - 测试工具的各项功能

测试内容：
1. 工具基类
2. 工具注册器
3. 基础工具

学习重点：
1. 理解工具测试的方法
2. 掌握参数验证测试
3. 学习错误处理测试
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from tools.base import Tool, ToolResult
from tools.registry import ToolRegistry
from tools.basic_tools import CalculatorTool, SearchTool


def test_tool_base():
    """测试工具基类"""
    calc = CalculatorTool()
    
    # 测试工具属性
    assert calc.name == "calculator"
    assert "计算" in calc.description
    assert "expression" in calc.parameters["properties"]
    
    print("✅ 工具基类测试通过")


def test_tool_validation():
    """测试参数验证"""
    calc = CalculatorTool()
    
    # 测试缺少必需参数
    is_valid, error = calc.validate_parameters()
    assert not is_valid
    assert "缺少必需参数" in error
    
    # 测试参数类型错误
    is_valid, error = calc.validate_parameters(expression=123)
    assert not is_valid
    assert "类型错误" in error
    
    print("✅ 参数验证测试通过")


def test_calculator_tool():
    """测试计算器工具"""
    calc = CalculatorTool()
    
    # 测试基本计算
    result = calc.execute(expression="2 + 3")
    assert result.success
    assert result.result == 5
    
    # 测试复杂表达式
    result = calc.execute(expression="2 + 3 * 4")
    assert result.success
    assert result.result == 14
    
    # 测试除零错误
    result = calc.execute(expression="1 / 0")
    assert not result.success
    assert "除零" in result.error
    
    print("✅ 计算器工具测试通过")


def test_search_tool():
    """测试搜索工具"""
    search = SearchTool()
    
    # 测试基本搜索
    text = "AI Agent是人工智能的重要概念"
    result = search.execute(text=text, keyword="Agent")
    assert result.success
    assert result.result["total_matches"] == 1
    
    # 测试无匹配
    result = search.execute(text=text, keyword="Python")
    assert result.success
    assert result.result["total_matches"] == 0
    
    print("✅ 搜索工具测试通过")


def test_tool_registry():
    """测试工具注册器"""
    registry = ToolRegistry()
    
    # 测试注册
    calc = CalculatorTool()
    registry.register(calc)
    
    stats = registry.get_tool_count()
    assert stats["total"] == 1
    assert stats["enabled"] == 1
    
    # 测试获取工具
    tool = registry.get_tool("calculator")
    assert tool is not None
    assert tool.name == "calculator"
    
    # 测试禁用/启用
    registry.disable_tool("calculator")
    assert "calculator" not in registry.enabled_tools
    
    registry.enable_tool("calculator")
    assert "calculator" in registry.enabled_tools
    
    print("✅ 工具注册器测试通过")


def test_tool_execution():
    """测试工具执行"""
    registry = ToolRegistry()
    calc = CalculatorTool()
    registry.register(calc)
    
    # 测试执行
    result = registry.execute_tool("calculator", expression="2 + 3")
    assert result.success
    assert result.result == 5
    
    # 测试执行未启用的工具
    registry.disable_tool("calculator")
    result = registry.execute_tool("calculator", expression="2 + 3")
    assert not result.success
    assert "未启用" in result.error
    
    print("✅ 工具执行测试通过")


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("工具系统测试")
    print("=" * 60)
    
    # 运行所有测试函数
    test_tool_base()
    test_tool_validation()
    test_calculator_tool()
    test_search_tool()
    test_tool_registry()
    test_tool_execution()
    
    print("=" * 60)
    print("✅ 所有测试通过！")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
