"""
MCP 传输层 - 支持多种传输方式

MCP 协议支持多种传输方式：
1. stdio: 标准输入输出（本地进程）
2. HTTP: HTTP/SSE 传输（远程服务）

学习重点：
1. 理解传输层的抽象设计
2. stdio 传输的实现细节
3. HTTP 传输的实现细节
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import json
import subprocess
import asyncio
import requests
import os

from .types import MCPRequest, MCPResponse


class MCPTransport(ABC):
    """
    MCP 传输层抽象基类

    所有传输方式都需要实现：
    - send: 发送请求并等待响应
    - close: 关闭连接
    """

    @abstractmethod
    async def send(self, request: MCPRequest) -> MCPResponse:
        """
        发送请求并等待响应

        参数：
            request: MCP 请求对象

        返回：
            MCPResponse: MCP 响应对象
        """
        pass

    @abstractmethod
    async def close(self):
        """
        关闭连接

        释放资源，终止连接
        """
        pass


class StdioTransport(MCPTransport):
    """
    Stdio 传输

    通过标准输入输出与 MCP 服务器通信。
    适用于本地 MCP 服务器（如 Python/Node.js 脚本）。

    工作原理：
    1. 启动 MCP 服务器作为子进程
    2. 通过 stdin 发送 JSON 请求
    3. 从 stdout 读取 JSON 响应

    学习要点：
    - subprocess.Popen 的使用
    - 进程间通信
    - 异步处理
    """

    def __init__(
        self,
        command: str,
        args: Optional[list] = None,
        env: Optional[dict] = None
    ):
        """
        初始化 Stdio 传输

        参数：
            command: 启动命令（如 "python", "npx", "node"）
            args: 命令参数列表
            env: 环境变量字典

        示例：
            transport = StdioTransport(
                command="npx",
                args=["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
            )
        """
        self.command = command
        self.args = args or []
        self.env = env or {}
        self.process: Optional[subprocess.Popen] = None
        self._request_id = 0
        self._connected = False

    async def connect(self) -> bool:
        """
        启动 MCP 服务器进程

        返回：
            bool: 是否成功启动
        """
        try:
            # 合并环境变量
            full_env = {**dict(os.environ), **self.env}

            # 启动进程
            self.process = subprocess.Popen(
                [self.command] + self.args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=full_env,
                bufsize=0  # 无缓冲，立即刷新
            )

            self._connected = True
            print(f"✅ MCP 服务器进程已启动: {self.command} {' '.join(self.args)}")
            return True

        except Exception as e:
            print(f"❌ 启动 MCP 服务器失败: {e}")
            self._connected = False
            return False

    async def send(self, request: MCPRequest) -> MCPResponse:
        """
        发送请求到 MCP 服务器

        参数：
            request: MCP 请求对象

        返回：
            MCPResponse: MCP 响应对象
        """
        if not self._connected or not self.process:
            raise RuntimeError("MCP 服务器未连接，请先调用 connect()")

        # 分配请求 ID
        self._request_id += 1
        request.id = self._request_id

        try:
            # 发送请求（JSON 格式，带换行符）
            request_json = request.to_json() + "\n"
            self.process.stdin.write(request_json.encode('utf-8'))
            self.process.stdin.flush()

            # 读取响应（一行 JSON）
            response_line = self.process.stdout.readline()
            if not response_line:
                # 检查进程是否存活
                if self.process.poll() is not None:
                    stderr = self.process.stderr.read().decode('utf-8')
                    raise RuntimeError(f"MCP 服务器已退出: {stderr}")
                raise RuntimeError("MCP 服务器无响应")

            # 解析响应
            response_str = response_line.decode('utf-8').strip()
            return MCPResponse.from_json(response_str)

        except Exception as e:
            # 返回错误响应
            return MCPResponse(
                id=request.id,
                error={
                    "code": -1,
                    "message": str(e)
                }
            )

    async def close(self):
        """
        关闭连接，终止 MCP 服务器进程
        """
        if self.process:
            try:
                # 发送关闭信号
                self.process.terminate()

                # 等待进程退出（最多 5 秒）
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    # 强制终止
                    self.process.kill()
                    self.process.wait()

                print("✅ MCP 服务器进程已关闭")

            except Exception as e:
                print(f"⚠️ 关闭进程时出错: {e}")

            finally:
                self.process = None
                self._connected = False

    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self._connected and self.process is not None and self.process.poll() is None

    def get_stderr(self) -> str:
        """获取 stderr 输出（用于调试）"""
        if self.process and self.process.stderr:
            return self.process.stderr.read().decode('utf-8')
        return ""


class HTTPTransport(MCPTransport):
    """
    HTTP 传输

    通过 HTTP 与 MCP 服务器通信。
    适用于远程 MCP 服务器。

    工作原理：
    1. POST 请求发送 JSON 数据
    2. 接收 JSON 响应

    学习要点：
    - requests 库的使用
    - HTTP 错误处理
    - 超时控制
    """

    def __init__(
        self,
        base_url: str,
        headers: Optional[dict] = None,
        timeout: int = 30
    ):
        """
        初始化 HTTP 传输

        参数：
            base_url: MCP 服务器 URL（如 "http://localhost:3000"）
            headers: HTTP 请求头（如认证信息）
            timeout: 请求超时时间（秒）

        示例：
            transport = HTTPTransport(
                base_url="http://localhost:3000",
                headers={"Authorization": "Bearer xxx"}
            )
        """
        self.base_url = base_url.rstrip("/")
        self.headers = headers or {"Content-Type": "application/json"}
        self.timeout = timeout
        self._request_id = 0
        self._connected = False

    async def connect(self) -> bool:
        """
        测试连接（可选）

        发送 ping 请求验证服务器可用
        """
        try:
            # 发送 ping 测试连接
            response = requests.post(
                f"{self.base_url}/mcp",
                json={
                    "jsonrpc": "2.0",
                    "method": "ping",
                    "id": 0
                },
                headers=self.headers,
                timeout=self.timeout
            )
            response.raise_for_status()

            self._connected = True
            print(f"✅ HTTP MCP 服务器连接成功: {self.base_url}")
            return True

        except Exception as e:
            print(f"❌ HTTP MCP 服务器连接失败: {e}")
            self._connected = False
            return False

    async def send(self, request: MCPRequest) -> MCPResponse:
        """
        发送 HTTP 请求

        参数：
            request: MCP 请求对象

        返回：
            MCPResponse: MCP 响应对象
        """
        self._request_id += 1
        request.id = self._request_id

        try:
            # 发送 POST 请求
            response = requests.post(
                f"{self.base_url}/mcp",
                json=request.to_dict(),
                headers=self.headers,
                timeout=self.timeout
            )
            response.raise_for_status()

            # 解析响应
            return MCPResponse.from_dict(response.json())

        except requests.exceptions.Timeout:
            return MCPResponse(
                id=request.id,
                error={"code": -1, "message": "请求超时"}
            )
        except requests.exceptions.ConnectionError:
            return MCPResponse(
                id=request.id,
                error={"code": -1, "message": "连接失败"}
            )
        except Exception as e:
            return MCPResponse(
                id=request.id,
                error={"code": -1, "message": str(e)}
            )

    async def close(self):
        """
        关闭连接（HTTP 无需关闭）
        """
        self._connected = False
        print("✅ HTTP MCP 连接已断开")

    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self._connected


# 使用示例
if __name__ == "__main__":
    """传输层使用示例"""

    print("=" * 60)
    print("MCP 传输层示例")
    print("=" * 60)

    # Stdio 传输示例
    print("\n📝 Stdio 传输示例:")
    transport = StdioTransport(
        command="echo",
        args=["test"]  # 仅用于演示，实际应使用 MCP 服务器
    )
    print(f"命令: {transport.command} {' '.join(transport.args)}")

    # HTTP 传输示例
    print("\n📝 HTTP 传输示例:")
    http_transport = HTTPTransport(
        base_url="http://localhost:3000",
        headers={"Authorization": "Bearer token"}
    )
    print(f"URL: {http_transport.base_url}")
    print(f"Headers: {http_transport.headers}")

    print("\n" + "=" * 60)
    print("示例执行完成！")
    print("=" * 60)