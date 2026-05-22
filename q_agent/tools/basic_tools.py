"""
基础工具集 - 提供常用的工具实现

这个模块包含了一些常用的基础工具：
- FileReadTool: 文件读取工具
- FileWriteTool: 文件写入工具
- FileEditTool: 文件精确编辑工具
- FileListTool: 目录列表工具
- CalculatorTool: 计算器工具
- SearchTool: 搜索工具
- ShellTool: Shell 命令执行工具
- WebFetchTool: 网页抓取工具
- WebSearchTool: 网络搜索工具
- UrlFetchTool: URL 资源下载工具
- DateTimeTool: 日期时间工具
- ImageAnalyzeTool: 图片分析工具
- MemorySaveTool: 记忆存储工具

学习重点：
1. 学习如何实现具体的工具
2. 掌握错误处理方法
3. 理解参数验证的重要性
"""

import os
import re
import json
import subprocess
import datetime
from pathlib import Path
from typing import Dict, Any, Optional

try:
    import requests
except ImportError:
    requests = None

try:
    from PIL import Image
    import PIL
except ImportError:
    Image = None
    PIL = None

# 处理相对导入和直接运行两种情况
try:
    from .base import Tool, ToolResult
except ImportError:
    # 直接运行时使用绝对导入
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from tools.base import Tool, ToolResult


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
                    "description": "要读取的文件路径"
                }
            },
            "required": ["file_path"]
        }
    
    def execute(self, **kwargs) -> ToolResult:
        """
        执行文件读取操作
        
        参数：
            file_path: 文件路径
            
        返回：
            ToolResult: 包含文件内容或错误信息
        """
        file_path = kwargs.get("file_path")
        
        if not file_path:
            return ToolResult(
                success=False,
                result=None,
                error="缺少参数: file_path"
            )
        
        try:
            # 检查文件大小（1MB限制）
            file_size = os.path.getsize(file_path)
            if file_size > 1024 * 1024:
                return ToolResult(
                    success=False,
                    result=None,
                    error=f"文件过大({file_size}字节)，超过1MB限制"
                )
            
            # 读取文件
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return ToolResult(
                success=True,
                result=content,
                metadata={
                    "file_path": file_path,
                    "file_size": file_size
                }
            )
            
        except FileNotFoundError:
            return ToolResult(
                success=False,
                result=None,
                error=f"文件不存在: {file_path}"
            )
        except PermissionError:
            return ToolResult(
                success=False,
                result=None,
                error=f"没有读取权限: {file_path}"
            )
        except Exception as e:
            return ToolResult(
                success=False,
                result=None,
                error=f"读取文件时发生错误: {str(e)}"
            )


class FileWriteTool(Tool):
    """
    文件写入工具
    
    功能：创建或写入文件内容
    用途：Agent需要创建或修改文件时使用
    
    学习要点：
    - 文件写入模式（覆盖/追加）
    - 自动创建父目录
    - 文件大小限制
    """
    
    @property
    def name(self) -> str:
        return "file_write"
    
    @property
    def description(self) -> str:
        return """创建或写入文件内容。

用途：
- 创建新文件
- 写入文本内容
- 追加内容到文件

注意：
- 自动创建不存在的父目录
- 文件大小限制为5MB
- 支持覆盖(w)和追加(a)两种模式
"""
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "要写入的文件路径"
                },
                "content": {
                    "type": "string",
                    "description": "要写入的内容"
                },
                "mode": {
                    "type": "string",
                    "description": "写入模式：w=覆盖，a=追加",
                    "enum": ["w", "a"],
                    "default": "w"
                }
            },
            "required": ["file_path", "content"]
        }
    
    def execute(self, **kwargs) -> ToolResult:
        file_path = kwargs.get("file_path")
        content = kwargs.get("content")
        mode = kwargs.get("mode", "w")
        
        if not file_path or content is None:
            return ToolResult(
                success=False,
                result=None,
                error="缺少参数: file_path 和 content 是必需的"
            )
        
        # 检查内容大小（5MB限制）
        content_bytes = content.encode('utf-8')
        if len(content_bytes) > 5 * 1024 * 1024:
            return ToolResult(
                success=False,
                result=None,
                error=f"内容过大({len(content_bytes)}字节)，超过5MB限制"
            )
        
        try:
            # 自动创建父目录
            parent_dir = os.path.dirname(file_path)
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)
            
            # 写入文件
            write_mode = 'a' if mode == 'a' else 'w'
            with open(file_path, write_mode, encoding='utf-8') as f:
                f.write(content)
            
            file_size = os.path.getsize(file_path)
            
            return ToolResult(
                success=True,
                result=f"成功写入 {len(content_bytes)} 字节到 {file_path}",
                metadata={
                    "file_path": file_path,
                    "bytes_written": len(content_bytes),
                    "file_size": file_size,
                    "mode": mode
                }
            )
            
        except PermissionError:
            return ToolResult(
                success=False,
                result=None,
                error=f"没有写入权限: {file_path}"
            )
        except Exception as e:
            return ToolResult(
                success=False,
                result=None,
                error=f"写入文件时发生错误: {str(e)}"
            )


class FileEditTool(Tool):
    """
    文件精确编辑工具
    
    功能：在文件中查找并替换文本
    用途：修改已有文件中的特定内容
    
    学习要点：
    - 精确字符串匹配
    - 多次匹配处理
    - 安全编辑
    """
    
    @property
    def name(self) -> str:
        return "file_edit"
    
    @property
    def description(self) -> str:
        return """在文件中精确查找并替换文本。

用途：
- 修改文件中的特定内容
- 替换代码片段
- 更新配置值

注意：
- 精确匹配（非正则表达式）
- 如果查找内容出现多次或不存在，将返回错误
- 建议先使用 file_read 确认内容
"""
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "要编辑的文件路径"
                },
                "old_string": {
                    "type": "string",
                    "description": "要查找的原始文本（精确匹配）"
                },
                "new_string": {
                    "type": "string",
                    "description": "要替换成的新文本"
                }
            },
            "required": ["file_path", "old_string", "new_string"]
        }
    
    def execute(self, **kwargs) -> ToolResult:
        file_path = kwargs.get("file_path")
        old_string = kwargs.get("old_string")
        new_string = kwargs.get("new_string")
        
        if not file_path or old_string is None or new_string is None:
            return ToolResult(
                success=False,
                result=None,
                error="缺少参数: file_path, old_string, new_string 都是必需的"
            )
        
        try:
            # 读取文件
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 检查匹配次数
            count = content.count(old_string)
            
            if count == 0:
                return ToolResult(
                    success=False,
                    result=None,
                    error=f"未找到匹配内容: '{old_string[:50]}...'（如果太长请截断）在 {file_path} 中不存在"
                )
            
            if count > 1:
                return ToolResult(
                    success=False,
                    result=None,
                    error=f"找到 {count} 处匹配，请提供更精确的 old_string（需要唯一匹配）"
                )
            
            # 执行替换
            new_content = content.replace(old_string, new_string, 1)
            
            # 写回文件
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            return ToolResult(
                success=True,
                result=f"成功替换 1 处内容",
                metadata={
                    "file_path": file_path,
                    "replacements": 1
                }
            )
            
        except FileNotFoundError:
            return ToolResult(
                success=False,
                result=None,
                error=f"文件不存在: {file_path}"
            )
        except Exception as e:
            return ToolResult(
                success=False,
                result=None,
                error=f"编辑文件时发生错误: {str(e)}"
            )


class FileListTool(Tool):
    """
    目录列表工具
    
    功能：列出目录中的文件和子目录
    用途：浏览文件系统结构
    
    学习要点：
    - 目录遍历
    - 递归列表
    - 隐藏文件处理
    """
    
    @property
    def name(self) -> str:
        return "file_list"
    
    @property
    def description(self) -> str:
        return """列出目录中的文件和子目录。

用途：
- 查看目录内容
- 浏览文件结构
- 查找文件位置

注意：
- 默认不显示隐藏文件
- 递归深度限制为3层
"""
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "directory": {
                    "type": "string",
                    "description": "要列出的目录路径",
                    "default": "."
                },
                "show_hidden": {
                    "type": "boolean",
                    "description": "是否显示隐藏文件（以.开头的文件）",
                    "default": False
                },
                "recursive": {
                    "type": "boolean",
                    "description": "是否递归列出子目录内容",
                    "default": False
                }
            },
            "required": []
        }
    
    def execute(self, **kwargs) -> ToolResult:
        directory = kwargs.get("directory", ".")
        show_hidden = kwargs.get("show_hidden", False)
        recursive = kwargs.get("recursive", False)
        
        try:
            directory = os.path.expanduser(directory)
            
            if not os.path.isdir(directory):
                return ToolResult(
                    success=False,
                    result=None,
                    error=f"目录不存在: {directory}"
                )
            
            items = []
            
            if recursive:
                # 递归遍历，限制深度为3
                for root, dirs, files in os.walk(directory):
                    # 计算当前深度
                    depth = root.replace(directory, '').count(os.sep)
                    if depth >= 3:
                        dirs.clear()
                        continue
                    
                    # 过滤隐藏文件
                    if not show_hidden:
                        dirs[:] = [d for d in dirs if not d.startswith('.')]
                        files = [f for f in files if not f.startswith('.')]
                    
                    for name in files:
                        full_path = os.path.join(root, name)
                        rel_path = os.path.relpath(full_path, directory)
                        size = os.path.getsize(full_path)
                        items.append({
                            "type": "file",
                            "path": rel_path,
                            "size": size
                        })
                    
                    for name in dirs:
                        full_path = os.path.join(root, name)
                        rel_path = os.path.relpath(full_path, directory)
                        items.append({
                            "type": "directory",
                            "path": rel_path
                        })
            else:
                # 仅列出当前目录
                for name in os.listdir(directory):
                    if not show_hidden and name.startswith('.'):
                        continue
                    
                    full_path = os.path.join(directory, name)
                    if os.path.isfile(full_path):
                        size = os.path.getsize(full_path)
                        items.append({
                            "type": "file",
                            "path": name,
                            "size": size
                        })
                    else:
                        items.append({
                            "type": "directory",
                            "path": name
                        })
            
            # 格式化输出
            lines = [f"目录: {directory}", ""]
            for item in sorted(items, key=lambda x: (x["type"], x["path"])):
                if item["type"] == "directory":
                    lines.append(f"  📁 {item['path']}/")
                else:
                    size_str = self._format_size(item.get("size", 0))
                    lines.append(f"  📄 {item['path']} ({size_str})")
            
            lines.append(f"\n共 {len(items)} 项")
            
            return ToolResult(
                success=True,
                result="\n".join(lines),
                metadata={
                    "directory": directory,
                    "count": len(items)
                }
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                result=None,
                error=f"列出目录时发生错误: {str(e)}"
            )
    
    def _format_size(self, size_bytes: int) -> str:
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f}{unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f}TB"


class CalculatorTool(Tool):
    """
    计算器工具
    
    功能：执行数学表达式计算
    用途：需要进行数学运算时使用
    
    学习要点：
    - 安全地执行数学表达式
    - 使用 ast 模块防止代码注入
    - 支持常用数学函数
    """
    
    @property
    def name(self) -> str:
        return "calculator"
    
    @property
    def description(self) -> str:
        return """执行数学表达式计算。

用途：
- 基本四则运算 (+, -, *, /)
- 幂运算 (**)
- 数学函数 (sqrt, sin, cos, tan, log, exp 等)
- 括号和优先级

注意：
- 仅支持数学表达式
- 不支持变量赋值
- 使用安全评估，防止代码注入
"""
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "要计算的数学表达式，如 '2 + 3 * 4', 'sqrt(16)', 'sin(3.14)'等"
                }
            },
            "required": ["expression"]
        }
    
    def execute(self, **kwargs) -> ToolResult:
        """
        执行数学表达式计算
        
        参数：
            expression: 数学表达式字符串
            
        返回：
            ToolResult: 计算结果或错误信息
        """
        expression = kwargs.get("expression")
        
        if not expression:
            return ToolResult(
                success=False,
                result=None,
                error="缺少参数: expression"
            )
        
        try:
            import ast
            import math
            
            # 定义安全的命名空间
            safe_dict = {
                'abs': abs, 'round': round,
                'min': min, 'max': max, 'sum': sum,
                'sqrt': math.sqrt, 'pow': math.pow,
                'sin': math.sin, 'cos': math.cos, 'tan': math.tan,
                'asin': math.asin, 'acos': math.acos, 'atan': math.atan,
                'log': math.log, 'log10': math.log10, 'log2': math.log2,
                'exp': math.exp, 'ceil': math.ceil, 'floor': math.floor,
                'pi': math.pi, 'e': math.e, 'tau': math.tau,
                'inf': math.inf, 'nan': math.nan
            }
            
            # 使用 ast 模块安全地解析表达式
            node = ast.parse(expression, mode='eval')
            
            # 检查表达式安全性
            self._check_safe_node(node.body)
            
            # 编译并执行
            code = compile(node, '<expression>', 'eval')
            result = eval(code, {"__builtins__": {}}, safe_dict)
            
            return ToolResult(
                success=True,
                result=result,
                metadata={
                    "expression": expression
                }
            )
            
        except SyntaxError as e:
            return ToolResult(
                success=False,
                result=None,
                error=f"表达式语法错误: {str(e)}"
            )
        except Exception as e:
            return ToolResult(
                success=False,
                result=None,
                error=f"计算错误: {str(e)}"
            )
    
    def _check_safe_node(self, node):
        """检查 AST 节点是否安全"""
        import ast
        safe_nodes = (
            ast.Expression, ast.BinOp, ast.UnaryOp, ast.operator,
            ast.unaryop, ast.cmpop, ast.Num, ast.Constant,
            ast.Call, ast.Name, ast.Load, ast.Attribute,
            ast.Compare, ast.BoolOp, ast.BoolOp
        )
        
        if not isinstance(node, safe_nodes):
            raise ValueError(f"不支持的操作: {type(node).__name__}")
        
        # 递归检查子节点
        for child in ast.walk(node):
            if not isinstance(child, safe_nodes):
                raise ValueError(f"不支持的节点类型: {type(child).__name__}")
        
        # 检查不允许的名称
        if isinstance(node, ast.Name):
            # 只允许数学常量
            allowed_names = {'pi', 'e', 'tau', 'inf', 'nan'}
            if node.id not in allowed_names:
                raise ValueError(f"不允许的变量名: {node.id}")


class SearchTool(Tool):
    """
    搜索工具
    
    功能：在文本中搜索关键词
    用途：查找文本中的特定内容
    
    学习要点：
    - 正则表达式搜索
    - 多行文本处理
    - 搜索结果格式化
    """
    
    @property
    def name(self) -> str:
        return "search"
    
    @property
    def description(self) -> str:
        return """在文本中搜索关键词。

用途：
- 在长文本中查找关键词
- 统计关键词出现次数
- 获取关键词所在的上下文

注意：
- 支持正则表达式
- 返回匹配位置和上下文
"""
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "要搜索的文本内容"
                },
                "keyword": {
                    "type": "string",
                    "description": "要搜索的关键词（支持正则表达式）"
                }
            },
            "required": ["text", "keyword"]
        }
    
    def execute(self, **kwargs) -> ToolResult:
        """
        在文本中搜索关键词
        
        参数：
            text: 要搜索的文本
            keyword: 关键词（支持正则）
            
        返回：
            ToolResult: 搜索结果
        """
        text = kwargs.get("text")
        keyword = kwargs.get("keyword")
        
        if not text or not keyword:
            return ToolResult(
                success=False,
                result=None,
                error="缺少参数: text 和 keyword 都是必需的"
            )
        
        try:
            # 搜索所有匹配项
            matches = list(re.finditer(keyword, text, re.MULTILINE))
            
            # 提取每个匹配的上下文
            results = []
            for match in matches:
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 50)
                context = text[start:end]
                
                results.append({
                    "position": match.start(),
                    "matched": match.group(),
                    "context": context
                })
            
            # 返回结果
            result = {
                "total_matches": len(matches),
                "matches": results
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


class ShellTool(Tool):
    """
    Shell 命令执行工具
    
    功能：执行系统 shell 命令
    用途：需要执行系统命令时使用
    
    学习要点：
    - subprocess 模块使用
    - 超时控制
    - stdout 和 stderr 捕获
    """
    
    @property
    def name(self) -> str:
        return "shell"
    
    @property
    def description(self) -> str:
        return """执行 shell 命令。

用途：
- 执行系统命令（ls, cat, mkdir 等）
- 运行脚本
- 获取系统信息

注意：
- 命令执行有超时限制（默认30秒，最大120秒）
- 可以指定工作目录
- 同时捕获 stdout 和 stderr
"""
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "要执行的 shell 命令"
                },
                "timeout": {
                    "type": "integer",
                    "description": "超时时间（秒），默认30，最大120",
                    "default": 30
                },
                "workdir": {
                    "type": "string",
                    "description": "工作目录（可选）"
                }
            },
            "required": ["command"]
        }
    
    def execute(self, **kwargs) -> ToolResult:
        command = kwargs.get("command")
        timeout = kwargs.get("timeout", 30)
        workdir = kwargs.get("workdir")
        
        if not command:
            return ToolResult(
                success=False,
                result=None,
                error="缺少参数: command"
            )
        
        # 限制超时时间
        timeout = min(timeout, 120)
        
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=workdir
            )
            
            output = result.stdout
            if result.stderr:
                output += "\n[stderr]\n" + result.stderr
            
            success = result.returncode == 0
            
            return ToolResult(
                success=success,
                result=output.strip() if output else "(无输出)",
                metadata={
                    "command": command,
                    "return_code": result.returncode,
                    "timeout": timeout
                }
            )
            
        except subprocess.TimeoutExpired:
            return ToolResult(
                success=False,
                result=None,
                error=f"命令执行超时（{timeout}秒）"
            )
        except Exception as e:
            return ToolResult(
                success=False,
                result=None,
                error=f"执行命令时发生错误: {str(e)}"
            )


class WebFetchTool(Tool):
    """
    网页抓取工具
    
    功能：抓取网页内容
    用途：获取网页文本内容
    
    学习要点：
    - HTTP 请求处理
    - 编码处理
    - 超时控制
    """
    
    @property
    def name(self) -> str:
        return "web_fetch"
    
    @property
    def description(self) -> str:
        return """抓取网页内容。

用途：
- 获取网页文本内容
- 读取在线文档
- 提取网页信息

注意：
- 默认限制返回长度为10000字符
- 超时15秒
- 需要网络连接
"""
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "要抓取的网页 URL"
                },
                "max_chars": {
                    "type": "integer",
                    "description": "最大返回字符数",
                    "default": 10000
                }
            },
            "required": ["url"]
        }
    
    def execute(self, **kwargs) -> ToolResult:
        url = kwargs.get("url")
        max_chars = kwargs.get("max_chars", 10000)
        
        if not url:
            return ToolResult(
                success=False,
                result=None,
                error="缺少参数: url"
            )
        
        if requests is None:
            return ToolResult(
                success=False,
                result=None,
                error="requests 库未安装，请运行: pip install requests"
            )
        
        try:
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            
            # 尝试使用正确的编码
            if response.encoding is None or response.encoding.lower() == 'iso-8859-1':
                response.encoding = 'utf-8'
            
            content = response.text
            
            # 截断到最大长度
            if len(content) > max_chars:
                content = content[:max_chars] + f"\n...（已截断，总长度超过{max_chars}字符）"
            
            return ToolResult(
                success=True,
                result=content,
                metadata={
                    "url": url,
                    "status_code": response.status_code,
                    "content_length": len(response.text)
                }
            )
            
        except requests.exceptions.Timeout:
            return ToolResult(
                success=False,
                result=None,
                error=f"请求超时（15秒）: {url}"
            )
        except requests.exceptions.RequestException as e:
            return ToolResult(
                success=False,
                result=None,
                error=f"请求失败: {str(e)}"
            )
        except Exception as e:
            return ToolResult(
                success=False,
                result=None,
                error=f"抓取网页时发生错误: {str(e)}"
            )


class WebSearchTool(Tool):
    """
    网络搜索工具
    
    功能：使用搜索引擎搜索信息
    用途：查找实时信息、新闻、技术文档等
    
    学习要点：
    - 搜索引擎 API 使用
    - 结果解析和格式化
    """
    
    @property
    def name(self) -> str:
        return "web_search"
    
    @property
    def description(self) -> str:
        return """使用搜索引擎搜索信息。

用途：
- 查找实时信息
- 搜索新闻
- 查找技术文档和资料

注意：
- 默认返回5条结果
- 最多可返回10条
- 需要网络连接
"""
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索关键词"
                },
                "count": {
                    "type": "integer",
                    "description": "返回结果数量（1-10）",
                    "default": 5
                }
            },
            "required": ["query"]
        }
    
    def execute(self, **kwargs) -> ToolResult:
        query = kwargs.get("query")
        count = min(kwargs.get("count", 5), 10)
        
        if not query:
            return ToolResult(
                success=False,
                result=None,
                error="缺少参数: query"
            )
        
        if requests is None:
            return ToolResult(
                success=False,
                result=None,
                error="requests 库未安装，请运行: pip install requests"
            )
        
        try:
            # 使用 DuckDuckGo HTML 搜索
            search_url = "https://html.duckduckgo.com/html/"
            response = requests.post(
                search_url,
                data={"q": query},
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=10
            )
            response.raise_for_status()
            
            # 简单的 HTML 解析
            from html.parser import HTMLParser
            
            class DuckParser(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self.results = []
                    self.current = {}
                    self.in_result = False
                    self.in_title = False
                    self.in_snippet = False
                    self.collect_text = ""
                
                def handle_starttag(self, tag, attrs):
                    attrs_dict = dict(attrs)
                    if tag == "a" and "class" in attrs_dict and "result__snippet" in attrs_dict.get("class", ""):
                        self.in_snippet = True
                        self.collect_text = ""
                    elif tag == "a" and "class" in attrs_dict and "result__title" in attrs_dict.get("class", ""):
                        self.in_title = True
                        self.current["url"] = attrs_dict.get("href", "")
                        self.collect_text = ""
                
                def handle_endtag(self, tag):
                    if tag == "a":
                        if self.in_title:
                            self.current["title"] = self.collect_text.strip()
                            self.in_title = False
                        elif self.in_snippet:
                            self.current["snippet"] = self.collect_text.strip()
                            self.in_snippet = False
                            if "title" in self.current:
                                self.results.append(self.current)
                                self.current = {}
                
                def handle_data(self, data):
                    if self.in_title or self.in_snippet:
                        self.collect_text += data
            
            parser = DuckParser()
            parser.feed(response.text)
            
            results = parser.results[:count]
            
            if not results:
                return ToolResult(
                    success=True,
                    result="未找到搜索结果",
                    metadata={"query": query, "count": 0}
                )
            
            # 格式化输出
            lines = [f"搜索结果: {query}", ""]
            for i, r in enumerate(results, 1):
                lines.append(f"{i}. {r.get('title', '无标题')}")
                lines.append(f"   URL: {r.get('url', '')}")
                lines.append(f"   {r.get('snippet', '')}")
                lines.append("")
            
            return ToolResult(
                success=True,
                result="\n".join(lines),
                metadata={
                    "query": query,
                    "count": len(results)
                }
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                result=None,
                error=f"搜索失败: {str(e)}"
            )


class UrlFetchTool(Tool):
    """
    URL 资源下载工具
    
    功能：从 URL 下载文件到本地
    用途：下载文件、图片等资源
    
    学习要点：
    - 文件下载
    - 流式写入
    - 文件大小限制
    """
    
    @property
    def name(self) -> str:
        return "url_fetch"
    
    @property
    def description(self) -> str:
        return """从 URL 下载文件到本地。

用途：
- 下载文件
- 下载图片
- 下载其他网络资源

注意：
- 文件大小限制50MB
- 未指定保存路径时使用 URL 中的文件名
- 超时30秒
"""
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "要下载的资源的 URL"
                },
                "save_path": {
                    "type": "string",
                    "description": "保存路径（可选，默认使用 URL 中的文件名）"
                },
                "timeout": {
                    "type": "integer",
                    "description": "超时时间（秒）",
                    "default": 30
                }
            },
            "required": ["url"]
        }
    
    def execute(self, **kwargs) -> ToolResult:
        url = kwargs.get("url")
        save_path = kwargs.get("save_path")
        timeout = kwargs.get("timeout", 30)
        
        if not url:
            return ToolResult(
                success=False,
                result=None,
                error="缺少参数: url"
            )
        
        if requests is None:
            return ToolResult(
                success=False,
                result=None,
                error="requests 库未安装，请运行: pip install requests"
            )
        
        try:
            response = requests.get(url, timeout=timeout, stream=True)
            response.raise_for_status()
            
            # 确定保存路径
            if not save_path:
                # 从 URL 提取文件名
                from urllib.parse import urlparse
                parsed = urlparse(url)
                filename = os.path.basename(parsed.path)
                if not filename:
                    filename = "downloaded_file"
                save_path = os.path.join(".", filename)
            
            # 创建父目录
            parent = os.path.dirname(save_path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            
            # 流式下载，限制50MB
            max_size = 50 * 1024 * 1024
            downloaded = 0
            
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if downloaded > max_size:
                            f.close()
                            os.remove(save_path)
                            return ToolResult(
                                success=False,
                                result=None,
                                error=f"文件过大（超过50MB），已删除部分下载的文件"
                            )
            
            size_str = self._format_size(downloaded)
            
            return ToolResult(
                success=True,
                result=f"成功下载文件到: {save_path} ({size_str})",
                metadata={
                    "url": url,
                    "save_path": save_path,
                    "bytes_downloaded": downloaded
                }
            )
            
        except requests.exceptions.Timeout:
            return ToolResult(
                success=False,
                result=None,
                error=f"下载超时（{timeout}秒）"
            )
        except Exception as e:
            return ToolResult(
                success=False,
                result=None,
                error=f"下载失败: {str(e)}"
            )
    
    def _format_size(self, size_bytes: int) -> str:
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f}{unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f}TB"


class DateTimeTool(Tool):
    """
    日期时间工具
    
    功能：获取当前日期时间
    用途：需要知道当前时间时使用
    
    学习要点：
    - datetime 模块使用
    - 时区处理
    - 格式化输出
    """
    
    @property
    def name(self) -> str:
        return "date_time"
    
    @property
    def description(self) -> str:
        return """获取当前日期时间。

用途：
- 获取当前时间
- 格式化日期输出
- 支持不同时区

注意：
- 默认时区为 Asia/Shanghai
- 支持自定义格式
"""
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "format": {
                    "type": "string",
                    "description": "时间格式化字符串",
                    "default": "%Y-%m-%d %H:%M:%S"
                },
                "timezone": {
                    "type": "string",
                    "description": "时区名称（如 Asia/Shanghai, UTC, America/New_York）",
                    "default": "Asia/Shanghai"
                }
            },
            "required": []
        }
    
    def execute(self, **kwargs) -> ToolResult:
        time_format = kwargs.get("format", "%Y-%m-%d %H:%M:%S")
        timezone_str = kwargs.get("timezone", "Asia/Shanghai")
        
        try:
            # 尝试使用 zoneinfo（Python 3.9+）
            try:
                from zoneinfo import ZoneInfo
                tz = ZoneInfo(timezone_str)
            except (ImportError, ZoneInfoNotFoundError):
                # fallback: 尝试 dateutil
                try:
                    from dateutil import tz
                    tz = tz.gettz(timezone_str)
                    if tz is None:
                        raise ValueError(f"未知时区: {timezone_str}")
                except ImportError:
                    # 最终 fallback: 使用 UTC
                    tz = datetime.timezone.utc
            
            now = datetime.datetime.now(tz)
            formatted = now.strftime(time_format)
            
            return ToolResult(
                success=True,
                result=formatted,
                metadata={
                    "timezone": timezone_str,
                    "format": time_format,
                    "iso_format": now.isoformat()
                }
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                result=None,
                error=f"获取时间失败: {str(e)}"
            )


class ImageAnalyzeTool(Tool):
    """
    图片分析工具（基础版）
    
    功能：获取图片基本信息
    用途：分析图片尺寸、格式、大小等
    
    学习要点：
    - PIL/Pillow 使用
    - 图片元数据读取
    - Fallback 处理
    """
    
    @property
    def name(self) -> str:
        return "image_analyze"
    
    @property
    def description(self) -> str:
        return """获取图片基本信息。

用途：
- 查看图片尺寸
- 查看图片格式
- 查看文件大小

注意：
- 需要安装 Pillow 库：pip install Pillow
- 如果 Pillow 不可用，返回基本文件信息
"""
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "image_path": {
                    "type": "string",
                    "description": "图片文件路径"
                }
            },
            "required": ["image_path"]
        }
    
    def execute(self, **kwargs) -> ToolResult:
        image_path = kwargs.get("image_path")
        
        if not image_path:
            return ToolResult(
                success=False,
                result=None,
                error="缺少参数: image_path"
            )
        
        try:
            image_path = os.path.expanduser(image_path)
            
            if not os.path.exists(image_path):
                return ToolResult(
                    success=False,
                    result=None,
                    error=f"文件不存在: {image_path}"
                )
            
            file_size = os.path.getsize(image_path)
            size_str = self._format_size(file_size)
            
            # 尝试使用 PIL
            if Image is not None:
                try:
                    with Image.open(image_path) as img:
                        info = {
                            "path": image_path,
                            "format": img.format or "未知",
                            "mode": img.mode,
                            "width": img.width,
                            "height": img.height,
                            "size": f"{img.width}x{img.height}",
                            "file_size": size_str
                        }
                        
                        result_text = (
                            f"图片信息:\n"
                            f"  路径: {image_path}\n"
                            f"  格式: {img.format or '未知'}\n"
                            f"  模式: {img.mode}\n"
                            f"  尺寸: {img.width}x{img.height}\n"
                            f"  文件大小: {size_str}"
                        )
                        
                        return ToolResult(
                            success=True,
                            result=result_text,
                            metadata=info
                        )
                except Exception as pil_error:
                    # PIL 打开失败，降级到文件信息
                    pass
            
            # Fallback: 返回基本文件信息
            result_text = (
                f"文件信息 (PIL 不可用):\n"
                f"  路径: {image_path}\n"
                f"  大小: {size_str}\n"
                f"  提示: 安装 Pillow 可获取图片详细信息\n"
                f"  pip install Pillow"
            )
            
            return ToolResult(
                success=True,
                result=result_text,
                metadata={
                    "path": image_path,
                    "file_size": file_size,
                    "note": "PIL not available"
                }
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                result=None,
                error=f"分析图片失败: {str(e)}"
            )
    
    def _format_size(self, size_bytes: int) -> str:
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f}{unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f}TB"


class MemorySaveTool(Tool):
    """
    记忆存储工具
    
    功能：保存关键信息到持久化记忆
    用途：需要记住重要信息时使用
    
    学习要点：
    - JSON 文件持久化
    - 读写锁处理
    - 记忆管理
    """
    
    @property
    def name(self) -> str:
        return "memory_save"
    
    @property
    def description(self) -> str:
        return """保存关键信息到持久化记忆。

用途：
- 记住用户偏好
- 存储重要事实
- 跨会话记忆

注意：
- 记忆保存在 ~/.q_agent/memory.json
- 支持追加和覆盖
- 相同的 key 会被覆盖
"""
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "key": {
                    "type": "string",
                    "description": "记忆的键（唯一标识符）"
                },
                "value": {
                    "type": "string",
                    "description": "记忆的值"
                }
            },
            "required": ["key", "value"]
        }
    
    def execute(self, **kwargs) -> ToolResult:
        key = kwargs.get("key")
        value = kwargs.get("value")
        
        if not key or value is None:
            return ToolResult(
                success=False,
                result=None,
                error="缺少参数: key 和 value 都是必需的"
            )
        
        try:
            # 确定记忆文件路径
            memory_dir = os.path.expanduser("~/.q_agent")
            os.makedirs(memory_dir, exist_ok=True)
            memory_file = os.path.join(memory_dir, "memory.json")
            
            # 读取现有记忆
            memories = {}
            if os.path.exists(memory_file):
                with open(memory_file, 'r', encoding='utf-8') as f:
                    memories = json.load(f)
            
            # 保存新记忆
            is_new = key not in memories
            memories[key] = value
            
            # 写回文件
            with open(memory_file, 'w', encoding='utf-8') as f:
                json.dump(memories, f, ensure_ascii=False, indent=2)
            
            action = "新增" if is_new else "更新"
            
            return ToolResult(
                success=True,
                result=f"成功{action}记忆: {key} = {value[:50]}{'...' if len(value) > 50 else ''}",
                metadata={
                    "key": key,
                    "action": "new" if is_new else "update",
                    "total_memories": len(memories)
                }
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                result=None,
                error=f"保存记忆失败: {str(e)}"
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
    
    # 测试文件写入工具
    print("\n3. 文件写入工具测试：")
    writer = FileWriteTool()
    result = writer.execute(file_path="/tmp/test_write.txt", content="Hello, World!")
    print(f"   {result.result}")
    
    # 测试文件读取工具
    print("\n4. 文件读取工具测试：")
    reader = FileReadTool()
    result = reader.execute(file_path="/tmp/test_write.txt")
    print(f"   读取内容: {result.result}")
    
    # 测试 Shell 工具
    print("\n5. Shell 工具测试：")
    shell = ShellTool()
    result = shell.execute(command="echo 'Hello from shell' && ls -la /tmp/test_write.txt")
    print(f"   {result.result}")
    
    # 测试日期时间工具
    print("\n6. 日期时间工具测试：")
    dt = DateTimeTool()
    result = dt.execute()
    print(f"   当前时间: {result.result}")
    
    # 测试记忆存储工具
    print("\n7. 记忆存储工具测试：")
    mem = MemorySaveTool()
    result = mem.execute(key="test_key", value="测试记忆值")
    print(f"   {result.result}")
    
    # 测试目录列表工具
    print("\n8. 目录列表工具测试：")
    fl = FileListTool()
    result = fl.execute(directory="/tmp", show_hidden=False)
    print(f"   {result.result[:200]}...")
    
    print("\n" + "=" * 60)
    print("示例执行完成！")
    print("=" * 60)
