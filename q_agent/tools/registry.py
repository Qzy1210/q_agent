"""
工具注册器 - 管理所有可用工具

工具注册器负责：
1. 注册和管理工具
2. 查找和获取工具
3. 列出所有可用工具
4. 工具权限控制

学习重点：
1. 理解注册器模式
2. 掌握工具管理机制
3. 学习权限控制方法
"""

from typing import Dict, List, Optional, Any
from .base import Tool, ToolResult


class ToolRegistry:
    """
    工具注册器
    
    管理所有可用工具，提供统一的工具管理接口。
    
    属性说明：
        tools (Dict[str, Tool]): 工具字典，key为工具名称
        enabled_tools (set): 启用的工具集合
        permissions (Dict): 工具权限配置
    
    设计思路：
    - 使用字典存储工具，便于快速查找
    - 支持工具的启用/禁用
    - 支持权限控制
    - 提供工具列表查询
    
    学习要点：
    - 注册器模式的实现
    - 字典管理技巧
    - 权限控制设计
    """
    
    def __init__(self):
        """
        初始化工具注册器
        """
        self.tools: Dict[str, Tool] = {}
        self.enabled_tools: set = set()
        self.permissions: Dict[str, List[str]] = {}
        
        print("✅ 工具注册器初始化完成")
    
    def register(self, tool: Tool, enable: bool = True) -> bool:
        """
        注册工具
        
        参数：
            tool (Tool): 要注册的工具实例
            enable (bool): 是否立即启用
            
        返回：
            bool: 是否注册成功
            
        注册流程：
        1. 检查工具名称是否已存在
        2. 添加到工具字典
        3. 根据参数决定是否启用
        """
        if tool.name in self.tools:
            print(f"⚠️ 工具 {tool.name} 已存在，将覆盖")
        
        # 注册工具
        self.tools[tool.name] = tool
        
        # 默认启用
        if enable:
            self.enabled_tools.add(tool.name)
        
        print(f"✅ 工具 {tool.name} 注册成功")
        return True
    
    def unregister(self, tool_name: str) -> bool:
        """
        注销工具
        
        参数：
            tool_name (str): 工具名称
            
        返回：
            bool: 是否注销成功
        """
        if tool_name not in self.tools:
            print(f"⚠️ 工具 {tool_name} 不存在")
            return False
        
        # 移除工具
        del self.tools[tool_name]
        self.enabled_tools.discard(tool_name)
        
        print(f"✅ 工具 {tool_name} 注销成功")
        return True
    
    def get_tool(self, tool_name: str) -> Optional[Tool]:
        """
        获取工具
        
        参数：
            tool_name (str): 工具名称
            
        返回：
            Tool: 工具实例，如果不存在返回None
            
        用途：
        - Agent调用工具时获取工具实例
        """
        tool = self.tools.get(tool_name)
        if not tool:
            print(f"⚠️ 工具 {tool_name} 不存在")
        return tool
    
    def list_tools(self, enabled_only: bool = True) -> List[Dict[str, Any]]:
        """
        列出所有工具
        
        参数：
            enabled_only (bool): 是否只列出启用的工具
            
        返回：
            List[Dict]: 工具信息列表
            
        用途：
        - 构建Prompt时列出可用工具
        - 查看所有注册的工具
        """
        tools_list = []
        
        for name, tool in self.tools.items():
            # 如果只列出启用的工具，跳过禁用的
            if enabled_only and name not in self.enabled_tools:
                continue
            
            tool_info = tool.to_dict()
            tool_info["enabled"] = name in self.enabled_tools
            tools_list.append(tool_info)
        
        
        return tools_list
    
    def enable_tool(self, tool_name: str) -> bool:
        """
        启用工具
        
        参数：
            tool_name (str): 工具名称
            
        返回：
            bool: 是否成功
        """
        if tool_name not in self.tools:
            print(f"⚠️ 工具 {tool_name} 不存在")
            return False
        
        self.enabled_tools.add(tool_name)
        print(f"✅ 工具 {tool_name} 已启用")
        return True
    
    def disable_tool(self, tool_name: str) -> bool:
        """
        禁用工具
        
        参数：
            tool_name (str): 工具名称
            
        返回：
            bool: 是否成功
        """
        if tool_name not in self.tools:
            print(f"⚠️ 工具 {tool_name} 不存在")
            return False
        
        self.enabled_tools.discard(tool_name)
        print(f"✅ 工具 {tool_name} 已禁用")
        return True
    
    def execute_tool(self, tool_name: str, **kwargs) -> ToolResult:
        """
        执行工具
        
        参数：
            tool_name (str): 工具名称
            **kwargs: 工具参数
            
        返回：
            ToolResult: 执行结果
            
        执行流程：
        1. 检查工具是否存在
        2. 检查工具是否启用
        3. 检查权限
        4. 执行工具
        """
        # 检查工具是否存在
        tool = self.get_tool(tool_name)
        if not tool:
            return ToolResult(
                success=False,
                result=None,
                error=f"工具 {tool_name} 不存在"
            )
        
        # 检查工具是否启用
        if tool_name not in self.enabled_tools:
            return ToolResult(
                success=False,
                result=None,
                error=f"工具 {tool_name} 未启用"
            )
        
        # 执行工具
        try:
            result = tool.execute(**kwargs)
            return result
        except Exception as e:
            return ToolResult(
                success=False,
                result=None,
                error=f"工具执行出错: {str(e)}"
            )
    
    def get_tool_count(self) -> Dict[str, int]:
        """
        获取工具统计信息
        
        返回：
            dict: 包含工具数量的统计信息
        """
        return {
            "total": len(self.tools),
            "enabled": len(self.enabled_tools),
            "disabled": len(self.tools) - len(self.enabled_tools)
        }
    
    def __repr__(self) -> str:
        """
        字符串表示
        
        返回：
            str: 注册器的简短描述
        """
        stats = self.get_tool_count()
        return f"ToolRegistry(总数={stats['total']}, 启用={stats['enabled']}, 禁用={stats['disabled']})"


# 使用示例
if __name__ == "__main__":
    """
    工具注册器使用示例
    
    演示如何使用工具注册器管理工具
    """
    from .base import Tool
    
    # 创建一个简单的测试工具
    class TestTool(Tool):
        @property
        def name(self) -> str:
            return "test"
        
        @property
        def description(self) -> str:
            return "测试工具"
        
        @property
        def parameters(self) -> dict:
            return {"type": "object", "properties": {}}
        
        def execute(self, **kwargs):
            from .base import ToolResult
            return ToolResult(success=True, result="测试成功")
    
    print("=" * 60)
    print("工具注册器使用示例")
    print("=" * 60)
    
    # 创建注册器
    registry = ToolRegistry()
    
    # 注册工具
    test_tool = TestTool()
    registry.register(test_tool)
    
    # 列出工具
    print("\n已注册的工具：")
    for tool_info in registry.list_tools():
        print(f"  - {tool_info['name']}: {tool_info['description']}")
    
    # 执行工具
    result = registry.execute_tool("test")
    print(f"\n执行结果: {result}")
    
    # 禁用工具
    registry.disable_tool("test")
    result = registry.execute_tool("test")
    print(f"\n禁用后执行: {result}")
    
    print("\n" + "=" * 60)
    print("示例执行完成！")
    print("=" * 60)
