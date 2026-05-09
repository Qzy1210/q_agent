"""
工具基类 - 定义工具的标准接口

工具是Agent执行具体操作的能力单元，每个工具都需要：
1. 明确的名称和描述
2. 清晰的参数定义（JSON Schema）
3. 执行方法
4. 错误处理

学习重点：
1. 理解工具的设计模式
2. 掌握参数验证方法
3. 学习错误处理机制
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass
from abc import ABC, abstractmethod
import json


@dataclass
class ToolResult:
    """
    工具执行结果
    
    统一的工具返回格式，包含：
    - success: 是否成功
    - result: 执行结果
    - error: 错误信息（如果失败）
    - metadata: 额外元数据
    
    设计思路：
    - 统一返回格式，便于Agent处理
    - 包含成功/失败状态
    - 支持元数据扩展
    """
    success: bool
    result: Any
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典格式
        
        返回：
            dict: 包含所有结果的字典
        """
        return {
            "success": self.success,
            "result": self.result,
            "error": self.error,
            "metadata": self.metadata
        }
    
    def __repr__(self) -> str:
        """
        字符串表示
        
        返回：
            str: 结果的简短描述
        """
        status = "✅ 成功" if self.success else "❌ 失败"
        return f"ToolResult({status}, result={str(self.result)[:50]}...)"


class Tool(ABC):
    """
    工具基类 - 所有工具必须继承此类
    
    工具的设计原则：
    1. 单一职责：每个工具只做一件事
    2. 清晰描述：名称和描述要明确
    3. 参数验证：使用JSON Schema定义参数
    4. 错误处理：捕获异常并返回友好的错误信息
    
    必须实现的方法：
    - name: 工具名称
    - description: 工具描述
    - parameters: 参数定义（JSON Schema）
    - execute: 执行方法
    
    学习要点：
    - 抽象基类的使用
    - JSON Schema的定义
    - 参数验证的实现
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """
        工具名称（必须唯一）
        
        返回：
            str: 工具名称
            
        命名规范：
        - 使用小写字母和下划线
        - 简洁明了，如：file_read, calculator
        """
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """
        工具描述
        
        返回：
            str: 工具的详细描述
            
        描述要求：
        - 说明工具的功能
        - 说明适用场景
        - 说明注意事项
        """
        pass
    
    @property
    @abstractmethod
    def parameters(self) -> Dict[str, Any]:
        """
        参数定义（JSON Schema格式）
        
        返回：
            dict: JSON Schema格式的参数定义
            
        JSON Schema示例：
        {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "文件路径"
                },
                "encoding": {
                    "type": "string",
                    "default": "utf-8",
                    "description": "文件编码"
                }
            },
            "required": ["file_path"]
        }
        """
        pass
    
    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        """
        执行工具
        
        参数：
            **kwargs: 工具参数
            
        返回：
            ToolResult: 执行结果
            
        实现要求：
        1. 参数验证
        2. 异常捕获
        3. 返回标准格式
        """
        pass
    
    def validate_parameters(self, **kwargs) -> tuple[bool, Optional[str]]:
        """
        验证参数
        
        参数：
            **kwargs: 待验证的参数
            
        返回：
            tuple: (是否验证通过, 错误信息)
            
        验证逻辑：
        1. 检查必需参数是否存在
        2. 检查参数类型是否正确
        3. 检查参数值是否合法
        """
        # 获取参数定义
        schema = self.parameters
        required = schema.get("required", [])
        properties = schema.get("properties", {})
        
        # 检查必需参数
        for param_name in required:
            if param_name not in kwargs:
                return False, f"缺少必需参数: {param_name}"
        
        # 检查参数类型（简化版本）
        for param_name, param_value in kwargs.items():
            if param_name in properties:
                expected_type = properties[param_name].get("type")
                if expected_type:
                    type_mapping = {
                        "string": str,
                        "integer": int,
                        "number": (int, float),
                        "boolean": bool,
                        "array": list,
                        "object": dict
                    }
                    expected_python_type = type_mapping.get(expected_type)
                    if expected_python_type and not isinstance(param_value, expected_python_type):
                        return False, f"参数 {param_name} 类型错误，期望 {expected_type}，实际 {type(param_value).__name__}"
        
        return True, None
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典格式（用于Prompt构建）
        
        返回：
            dict: 包含工具信息的字典
        """
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters
        }
    
    def __repr__(self) -> str:
        """
        字符串表示
        
        返回：
            str: 工具的简短描述
        """
        return f"Tool(name={self.name}, description={self.description[:30]}...)"


# 使用示例
if __name__ == "__main__":
    """
    工具基类使用示例
    
    演示如何创建自定义工具
    """
    
    class SimpleEchoTool(Tool):
        """简单的回显工具示例"""
        
        @property
        def name(self) -> str:
            return "echo"
        
        @property
        def description(self) -> str:
            return "回显输入的文本"
        
        @property
        def parameters(self) -> Dict[str, Any]:
            return {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "要回显的文本"
                    }
                },
                "required": ["text"]
            }
        
        def execute(self, **kwargs) -> ToolResult:
            # 验证参数
            is_valid, error = self.validate_parameters(**kwargs)
            if not is_valid:
                return ToolResult(success=False, result=None, error=error)
            
            # 执行操作
            text = kwargs.get("text")
            return ToolResult(success=True, result=f"Echo: {text}")
    
    print("=" * 60)
    print("工具基类使用示例")
    print("=" * 60)
    
    # 创建工具实例
    echo_tool = SimpleEchoTool()
    
    # 查看工具信息
    print(f"\n工具名称: {echo_tool.name}")
    print(f"工具描述: {echo_tool.description}")
    print(f"参数定义: {json.dumps(echo_tool.parameters, indent=2, ensure_ascii=False)}")
    
    # 测试执行
    result = echo_tool.execute(text="Hello, Agent!")
    print(f"\n执行结果: {result}")
    
    # 测试参数验证
    print("\n测试参数验证：")
    invalid_result = echo_tool.execute()  # 缺少必需参数
    print(f"  缺少参数: {invalid_result}")
    
    print("\n" + "=" * 60)
    print("示例执行完成！")
    print("=" * 60)
