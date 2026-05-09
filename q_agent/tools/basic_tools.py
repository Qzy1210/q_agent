"""
基础工具集 - 提供常用的工具实现

这个模块包含了一些常用的基础工具：
- FileReadTool: 文件读取工具
- CalculatorTool: 计算器工具
- SearchTool: 搜索工具

学习重点：
1. 学习如何实现具体的工具
2. 掌握错误处理方法
3. 理解参数验证的重要性
"""

import os
import re
from typing import Dict, Any
from .base import Tool, ToolResult


class FileReadTool(Tool):
    """
    文件读取工具
    
    功能：读取文件内容
    用途：Agent需要读取文件时使用
    
    学习要点：
    - 文件操作的安全处理
    - 编码处理
    - 错误处理
    """
    
    @property
    def name(self) -> str:
        return "file_read"
    
    @property
    def description(self) -> str:
        return """读取文件内容。
        
用途：
- 读取文本文件
- 查看配置文件
- 获取文件内容

注意：
- 只支持文本文件
- 文件大小限制为1MB
- 需要文件读取权限
"""
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "文件路径（绝对路径或相对路径）"
                },
                "encoding": {
                    "type": "string",
                    "default": "utf-8",
                    "description": "文件编码，默认utf-8"
                },
                "lines": {
                    "type": "integer",
                    "description": "读取的行数（可选，默认读取全部）"
                }
            },
            "required": ["file_path"]
        }
    
    def execute(self, **kwargs) -> ToolResult:
        """执行文件读取"""
        # 验证参数
        is_valid, error = self.validate_parameters(**kwargs)
        if not is_valid:
            return ToolResult(success=False, result=None, error=error)
        
        file_path = kwargs.get("file_path")
        encoding = kwargs.get("encoding", "utf-8")
        lines = kwargs.get("lines")
        
        try:
            # 检查文件是否存在
            if not os.path.exists(file_path):
                return ToolResult(
                    success=False,
                    result=None,
                    error=f"文件不存在: {file_path}"
                )
            
            # 检查是否是文件
            if not os.path.isfile(file_path):
                return ToolResult(
                    success=False,
                    result=None,
                    error=f"路径不是文件: {file_path}"
                )
            
            # 检查文件大小（限制1MB）
            file_size = os.path.getsize(file_path)
            if file_size > 1024 * 1024:
                return ToolResult(
                    success=False,
                    result=None,
                    error=f"文件过大（{file_size / 1024:.1f}KB），最大支持1MB"
                )
            
            # 读取文件
            with open(file_path, 'r', encoding=encoding) as f:
                if lines:
                    content = ''.join(f.readline() for _ in range(lines))
                else:
                    content = f.read()
            
            return ToolResult(
                success=True,
                result=content,
                metadata={
                    "file_path": file_path,
                    "file_size": file_size,
                    "encoding": encoding
                }
            )
            
        except PermissionError:
            return ToolResult(
                success=False,
                result=None,
                error=f"没有权限读取文件: {file_path}"
            )
        except UnicodeDecodeError:
            return ToolResult(
                success=False,
                result=None,
                error=f"文件编码错误，尝试使用其他编码: {encoding}"
            )
        except Exception as e:
            return ToolResult(
                success=False,
                result=None,
                error=f"读取文件时出错: {str(e)}"
            )


class CalculatorTool(Tool):
    """
    计算器工具
    
    功能：执行数学运算
    用途：Agent需要进行数学计算时使用
    
    学习要点：
    - 数学表达式解析
    - 安全性考虑（避免代码注入）
    - 错误处理
    """
    
    @property
    def name(self) -> str:
        return "calculator"
    
    @property
    def description(self) -> str:
        return """执行数学计算。
        
用途：
- 基本运算：加减乘除
- 科学计算：幂运算、开方
- 表达式计算

支持的操作：
- 基本运算: +, -, *, /
- 幂运算: **, ^
- 数学函数: sqrt, abs, log

示例：
- "2 + 3 * 4" = 14
- "sqrt(16)" = 4
- "2 ** 10" = 1024
"""
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "数学表达式"
                }
            },
            "required": ["expression"]
        }
    
    def execute(self, **kwargs) -> ToolResult:
        """执行数学计算"""
        # 验证参数
        is_valid, error = self.validate_parameters(**kwargs)
        if not is_valid:
            return ToolResult(success=False, result=None, error=error)
        
        expression = kwargs.get("expression")
        
        try:
            # 安全检查：只允许数字、运算符和特定函数
            allowed_chars = r'[\d+\-*/.() \w]'
            if not all(re.match(allowed_chars, c) for c in expression):
                return ToolResult(
                    success=False,
                    result=None,
                    error="表达式包含非法字符"
                )
            
            # 替换一些常用函数
            safe_dict = {
                'sqrt': lambda x: x ** 0.5,
                'abs': abs,
                'pow': pow,
                'log': lambda x: x if x > 0 else None,
            }
            
            # 执行计算
            result = eval(expression, {"__builtins__": {}}, safe_dict)
            
            return ToolResult(
                success=True,
                result=result,
                metadata={
                    "expression": expression,
                    "result_type": type(result).__name__
                }
            )
            
        except ZeroDivisionError:
            return ToolResult(
                success=False,
                result=None,
                error="除零错误"
            )
        except SyntaxError:
            return ToolResult(
                success=False,
                result=None,
                error="表达式语法错误"
            )
        except Exception as e:
            return ToolResult(
                success=False,
                result=None,
                error=f"计算错误: {str(e)}"
            )


class SearchTool(Tool):
    """
    搜索工具
    
    功能：在文本中搜索关键词
    用途：Agent需要查找信息时使用
    
    学习要点：
    - 文本搜索算法
    - 正则表达式
    - 结果排序
    """
    
    @property
    def name(self) -> str:
        return "search"
    
    @property
    def description(self) -> str:
        return """在文本中搜索关键词。
        
用途：
- 查找关键词
- 正则表达式搜索
- 匹配计数

功能：
- 搜索关键词出现的位置
- 统计关键词出现次数
- 返回匹配的上下文
"""
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "要搜索的文本"
                },
                "keyword": {
                    "type": "string",
                    "description": "搜索关键词"
                },
                "context_length": {
                    "type": "integer",
                    "default": 50,
                    "description": "返回的上下文长度"
                }
            },
            "required": ["text", "keyword"]
        }
    
    def execute(self, **kwargs) -> ToolResult:
        """执行搜索"""
        # 验证参数
        is_valid, error = self.validate_parameters(**kwargs)
        if not is_valid:
            return ToolResult(success=False, result=None, error=error)
        
        text = kwargs.get("text")
        keyword = kwargs.get("keyword")
        context_length = kwargs.get("context_length", 50)
        
        try:
            # 查找所有匹配
            matches = []
            pattern = re.compile(re.escape(keyword), re.IGNORECASE)
            
            for match in pattern.finditer(text):
                start = max(0, match.start() - context_length)
                end = min(len(text), match.end() + context_length)
                
                context = text[start:end]
                if start > 0:
                    context = "..." + context
                if end < len(text):
                    context = context + "..."
                
                matches.append({
                    "position": match.start(),
                    "matched_text": match.group(),
                    "context": context
                })
            
            # 返回结果
            result = {
                "total_matches": len(matches),
                "matches": matches
            }
            
            return ToolResult(
                success=True,
                result=result,
                metadata={
                    "keyword": keyword,
                    "text_length": len(text)
                }
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                result=None,
                error=f"搜索错误: {str(e)}"
            )


# 使用示例
if __name__ == "__main__":
    """
    基础工具使用示例
    
    演示如何使用各个工具
    """
    import json
    
    print("=" * 60)
    print("基础工具使用示例")
    print("=" * 60)
    
    # 测试计算器工具
    print("\n1. 计算器工具测试：")
    calc = CalculatorTool()
    result = calc.execute(expression="2 + 3 * 4")
    print(f"   2 + 3 * 4 = {result.result}")
    
    result = calc.execute(expression="sqrt(16)")
    print(f"   sqrt(16) = {result.result}")
    
    # 测试搜索工具
    print("\n2. 搜索工具测试：")
    search = SearchTool()
    text = "AI Agent是人工智能领域的重要概念，Agent Loop是Agent的核心机制"
    result = search.execute(text=text, keyword="Agent")
    print(f"   搜索 'Agent': 找到 {result.result['total_matches']} 个匹配")
    
    print("\n" + "=" * 60)
    print("示例执行完成！")
    print("=" * 60)
