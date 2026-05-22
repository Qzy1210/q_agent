"""
Agent核心类 - 实现Agent Loop循环

这是整个项目的核心模块，实现了Agent的思考-决策-行动循环。
Agent Loop是AI Agent最核心的概念，理解这个循环是理解Agent的关键。

学习重点：
1. Agent Loop的工作原理
2. 如何与LLM进行交互
3. 如何调用工具
4. 如何管理记忆和上下文
"""

import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

# 导入其他核心模块
from .memory import Memory
from .context import ContextManager
from .llm_client import LLMClientFactory, LLMResponse
from ..config import Config

# 导入 Skill 系统
from ..skills import (
    Skill,
    SkillLoader,
    SkillRegistry,
    SkillRouter,
    SkillExecutor,
    SkillContext,
    SkillResult
)

# 导入 MCP 系统
from ..mcp import (
    MCPClient,
    MCPToolRegistry
)


class AgentState(Enum):
    """
    Agent状态枚举

    定义Agent在执行过程中可能处于的状态
    这有助于我们理解Agent的执行流程
    """
    IDLE = "idle"              # 空闲状态，等待新任务
    THINKING = "thinking"      # 思考状态，正在分析任务
    ACTING = "acting"          # 行动状态，正在执行工具
    COMPLETED = "completed"    # 完成状态，任务已完成
    FAILED = "failed"          # 失败状态，任务执行失败


@dataclass
class ToolCall:
    """
    工具调用记录

    记录一次工具调用的完整信息
    """
    tool_name: str              # 工具名称
    parameters: Dict[str, Any]  # 调用参数
    result: str                 # 执行结果
    reasoning: str = ""         # 调用理由
    success: bool = True        # 是否成功


@dataclass
class AgentResult:
    """
    Agent 执行结果

    包含完整的执行信息，便于调试和展示
    """
    result: str                         # 最终结果
    success: bool = True                # 是否成功
    source: str = "agent_loop"          # 来源: "skill", "agent_loop", "mcp"
    skill_name: str = ""                # 如果来自 Skill
    tools_called: List[ToolCall] = None # 调用的工具列表
    iterations: int = 0                 # 迭代次数
    error: str = ""                     # 错误信息

    def __post_init__(self):
        if self.tools_called is None:
            self.tools_called = []

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "result": self.result,
            "success": self.success,
            "source": self.source,
            "skill_name": self.skill_name,
            "tools_called": [
                {
                    "tool_name": tc.tool_name,
                    "parameters": tc.parameters,
                    "result": tc.result[:500] + "..." if len(tc.result) > 500 else tc.result,
                    "reasoning": tc.reasoning,
                    "success": tc.success
                }
                for tc in self.tools_called
            ],
            "iterations": self.iterations,
            "error": self.error
        }

    def __str__(self) -> str:
        """字符串表示，直接返回结果"""
        return self.result


@dataclass
class AgentAction:
    """
    Agent行动数据类
    
    记录Agent决定执行的动作
    包含工具名称和参数
    """
    tool_name: str              # 要调用的工具名称
    parameters: Dict[str, Any]  # 调用工具所需的参数
    reasoning: str              # Agent选择这个行动的理由（重要：帮助理解Agent的决策过程）


class Agent:
    """
    Agent主类 - 实现智能体的核心逻辑
    
    这是整个项目最重要的类，实现了Agent Loop循环。
    
    工作流程：
    1. 接收用户任务
    2. 思考：分析当前状态，决定下一步行动
    3. 行动：执行选择的工具
    4. 观察：查看执行结果
    5. 循环：重复2-4直到任务完成
    
    设计思路：
    - 分离关注点：记忆、上下文、工具调用各自独立
    - 可扩展：容易添加新工具和新能力
    - 可观察：每一步都有详细日志，方便理解
    """
    
    def __init__(
        self,
        name: str = "Q-Agent",
        max_iterations: int = 10,
        llm_client: Optional[Any] = None,
        tools: Optional[List[Any]] = None,
        memory: Optional[Memory] = None,
        context_manager: Optional[ContextManager] = None,
        config: Optional[Config] = None,
        skill_dirs: Optional[List[str]] = None
    ):
        """
        初始化Agent

        参数说明：
            name (str): Agent的名字，用于日志和显示
            max_iterations (int): 最大迭代次数，防止无限循环
            llm_client: LLM客户端，用于调用语言模型
            tools (List): 可用工具列表
            memory (Memory): 记忆系统实例
            context_manager (ContextManager): 上下文管理器实例
            config (Config): 配置管理器实例
            skill_dirs (List[str]): Skill 目录列表，用于加载用户自定义 Skill

        设计说明：
            - 使用依赖注入模式，便于测试和扩展
            - 提供默认值，简化使用
            - 所有组件都是可选的，可以后续设置
        """
        # 基本信息
        self.name = name
        self.max_iterations = max_iterations

        # 核心组件
        self.llm_client = llm_client
        self.tools = tools or []
        self.memory = memory or Memory()
        self.context_manager = context_manager or ContextManager()

        # 状态管理
        self.state = AgentState.IDLE
        self.current_task = None
        self.iteration_count = 0
        self._tools_called: List[ToolCall] = []  # 执行轨迹：记录调用的工具
        self._last_action: Optional[AgentAction] = None  # 上一次的 action，用于检测重复调用

        # 配置管理
        self.config = config or Config(config_file="../config.json")

        # 如果没有提供llm_client，从配置创建
        if not self.llm_client:
            self._init_llm_client()

        # 初始化 Skill 系统
        self._init_skill_system(skill_dirs)
    
    def _init_llm_client(self):
        """
        从配置初始化LLM客户端

        功能：
        1. 从配置中读取LLM配置
        2. 使用工厂模式创建客户端
        3. 处理初始化错误
        """
        try:
            llm_config = {
                "provider": self.config.get("llm.provider", "openai"),
                "api_key": self.config.get("llm.api_key", ""),
                "model": self.config.get("llm.model", "gpt-3.5-turbo"),
                "temperature": self.config.get("llm.temperature", 0.7),
                "max_tokens": self.config.get("llm.max_tokens", 2000),
                # Ollama专用配置
                "base_url": self.config.get("llm.base_url", "http://localhost:11434")
            }

            # 验证API Key（Ollama除外）
            if llm_config["provider"] != "ollama" and not llm_config["api_key"]:
                print("⚠️ 未配置LLM API Key，使用模拟模式")
                self.llm_client = None
                return

            # 创建客户端
            self.llm_client = LLMClientFactory.create(llm_config)
            print(f"✅ LLM客户端初始化成功: {llm_config['provider']} - {llm_config['model']}")

        except Exception as e:
            print(f"⚠️ LLM客户端初始化失败: {str(e)}")
            self.llm_client = None

    def _init_skill_system(self, skill_dirs: Optional[List[str]] = None):
        """
        初始化 Skill 系统

        参数：
            skill_dirs (List[str]): Skill 目录列表

        功能：
        1. 创建 Skill 注册器、加载器、路由器、执行器
        2. 从配置中获取 skill_dirs（如果未显式提供）
        3. 加载所有 Skill
        4. 初始化路由器
        """
        self.skill_registry = SkillRegistry()
        self.skill_loader = SkillLoader()

        # 获取 skill_dirs：优先使用参数，其次从配置读取
        if skill_dirs is None:
            config_dirs = self.config.get("skill_dirs", [])
            if isinstance(config_dirs, str):
                config_dirs = [config_dirs]
            skill_dirs = config_dirs

        # 加载 Skills
        if skill_dirs:
            skills = self.skill_loader.load_from_directories(skill_dirs)
            for skill in skills:
                self.skill_registry.register(skill)

            if skills:
                print(f"✅ 已加载 {len(skills)} 个 Skill")
            else:
                print("ℹ️ 未找到任何 Skill 文件")

        # 创建执行器（在加载 Skills 之后，传入 skill_registry 以支持 list_skills）
        self.skill_executor = SkillExecutor(
            tool_registry=self.tools,
            llm_client=self.llm_client,
            memory=self.memory,
            context_manager=self.context_manager,
            skill_registry=self.skill_registry
        )

        # 初始化路由器
        self.skill_router = SkillRouter(self.skill_registry.get_all())

        # 初始化 MCP 系统（默认为 None，可通过 connect_mcp 连接）
        self.mcp_client: Optional[MCPClient] = None
        self.mcp_tool_registry: Optional[MCPToolRegistry] = None

    async def connect_mcp_stdio(
        self,
        server_name: str,
        command: str,
        args: Optional[List[str]] = None,
        env: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        连接 MCP 服务器（stdio 方式）

        参数：
            server_name: 服务器名称
            command: 启动命令
            args: 命令参数
            env: 环境变量

        返回：
            bool: 是否成功连接
        """
        if not self.mcp_client:
            self.mcp_client = MCPClient()

        success = await self.mcp_client.connect_stdio(
            server_name, command, args, env
        )

        if success:
            # 自动注册 MCP 工具
            self._register_mcp_tools()

        return success

    async def connect_mcp_http(
        self,
        server_name: str,
        base_url: str,
        headers: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        连接 MCP 服务器（HTTP 方式）

        参数：
            server_name: 服务器名称
            base_url: MCP 服务器 URL
            headers: HTTP 请求头

        返回：
            bool: 是否成功连接
        """
        if not self.mcp_client:
            self.mcp_client = MCPClient()

        success = await self.mcp_client.connect_http(
            server_name, base_url, headers
        )

        if success:
            # 自动注册 MCP 工具
            self._register_mcp_tools()

        return success

    def _register_mcp_tools(self):
        """
        注册 MCP 工具到工具列表
        """
        if not self.mcp_client:
            return

        if not self.mcp_tool_registry:
            self.mcp_tool_registry = MCPToolRegistry(self.mcp_client)

        # 注册所有 MCP 工具
        # 注意：这里使用简单的列表方式，而非 ToolRegistry
        all_tools = self.mcp_client.get_all_tools()
        for server_name, tools in all_tools.items():
            for tool_def in tools:
                from ..mcp import MCPToolAdapter
                adapter = MCPToolAdapter(
                    self.mcp_client,
                    server_name,
                    tool_def
                )
                self.tools.append(adapter)

        total_tools = sum(len(t) for t in all_tools.values())
        if total_tools > 0:
            print(f"✅ 已注册 {total_tools} 个 MCP 工具")

    def list_mcp_servers(self) -> List[str]:
        """
        列出已连接的 MCP 服务器

        返回：
            List[str]: 服务器名称列表
        """
        if not self.mcp_client:
            return []
        return self.mcp_client.list_servers()

    def list_mcp_tools(self) -> Dict[str, List]:
        """
        列出所有 MCP 工具

        返回：
            Dict[str, List]: {server_name: [tools]}
        """
        if not self.mcp_client:
            return {}
        return self.mcp_client.get_all_tools()

    async def disconnect_mcp(self, server_name: Optional[str] = None):
        """
        断开 MCP 连接

        参数：
            server_name: 服务器名称（可选，不提供则断开所有）
        """
        if not self.mcp_client:
            return

        if server_name:
            await self.mcp_client.disconnect(server_name)
        else:
            await self.mcp_client.disconnect_all()
            self.mcp_client = None
            self.mcp_tool_registry = None
        
    def run(self, task: str) -> AgentResult:
        """
        执行主循环 - Agent的核心方法
        这是Agent Loop的入口点，实现了完整的思考-行动循环。

        参数：
            task (str): 用户交给Agent的任务描述

        返回：
            AgentResult: 包含执行结果、调用工具、来源等完整信息

        执行流程：
        1. 尝试路由到 Skill（如果匹配）
        2. 如果匹配 Skill，执行 Skill SOP
        3. 如果无匹配 Skill，进入普通 Agent Loop
        4. 判断是否完成或失败
        5. 返回 AgentResult

        学习重点：
        - 注意循环的终止条件
        - 理解每次迭代的输入输出
        - 观察如何记录和更新状态
        """
        # 重置执行轨迹
        self._tools_called = []
        self.iteration_count = 0

        # 仅处理显式命令调用（/ 开头），普通意图交给 LLM 自主决策
        if task.startswith('/'):
            skill, cleaned_input, confidence = self.skill_router.route(task)
            if skill and confidence == 1.0:  # 仅命令匹配才走快速通道
                print(f"🎯 匹配到 Skill: {skill.meta.name} (置信度: {confidence:.2f})")

                # 构建 Skill 执行上下文
                context = SkillContext(
                    tool_registry=self.tools,
                    llm_client=self.llm_client,
                    memory=self.memory,
                    context_manager=self.context_manager,
                    user_input=cleaned_input
                )

                # 执行 Skill
                result = self.skill_executor.execute(skill, context)

                if result.success:
                    # 将 Skill 执行轨迹中的工具调用转为 ToolCall
                    for trace_item in result.execution_trace:
                        if trace_item.get("step") == "tool_call":
                            self._tools_called.append(ToolCall(
                                tool_name=trace_item.get("tool", ""),
                                parameters={},
                                result=str(trace_item.get("success", "")),
                                success=trace_item.get("success", False)
                            ))

                    return AgentResult(
                        result=self._format_skill_result(result),
                        success=True,
                        source="skill",
                        skill_name=skill.meta.name,
                        tools_called=self._tools_called
                    )
                else:
                    return AgentResult(
                        result=f"Skill 执行失败: {result.error}",
                        success=False,
                        source="skill",
                        skill_name=skill.meta.name,
                        error=result.error or ""
                    )

        # 无匹配 Skill 或非显式命令，走普通 Agent Loop
        return self._run_agent_loop(task)

    def _run_agent_loop(self, task: str) -> AgentResult:
        """
        执行普通 Agent Loop

        参数：
            task (str): 用户任务

        返回：
            AgentResult: 执行结果
        """
        # 初始化任务
        self._initialize_task(task)

        # 主循环：Agent Loop的核心
        while self._should_continue():
            # 记录迭代次数
            self.iteration_count += 1

            try:
                # 步骤1：思考 - 分析当前状态，决定下一步
                self.state = AgentState.THINKING
                action = self._think()

                # 如果没有行动，说明任务完成或无法继续
                if action is None:
                    # LLM 返回了 action="finish"，任务完成
                    self.state = AgentState.COMPLETED
                    break

                # 步骤2：行动 - 执行选择的工具
                self.state = AgentState.ACTING
                result = self._act(action)

                # 步骤3：观察 - 记录结果，更新记忆
                self._observe(action, result)

            except Exception as e:
                # 错误处理：记录错误，设置失败状态
                self._handle_error(e)
                break
        
        # 返回最终结果
        return self._get_final_result()
    
    def _initialize_task(self, task: str):
        """
        初始化任务
        
        参数：
            task (str): 用户任务描述
        功能：
        1. 记录当前任务
        2. 重置状态
        3. 将任务添加到记忆中
        4. 准备初始上下文
        
        设计思路：
        - 每个新任务都是全新的开始
        - 保留历史记忆，但重置当前状态
        - 立即记录任务，防止丢失
        """
        self.current_task = task
        self.state = AgentState.IDLE
        self.iteration_count = 0
        self._last_action = None  # 重置上一次 action

        # 清空上下文（包括优先级消息，确保新任务从头开始）
        # 注意：memory（长期记忆）保留，但 context（当前上下文）完全清空
        self.context_manager.clear_context(keep_priority=False)

        # 记录任务到记忆系统（长期存储）
        self.memory.save_message("user", task)

        # 添加系统提示到上下文
        system_prompt = self._build_system_prompt()
        self.context_manager.add_message("system", system_prompt)

        # 🔧 Bug修复: 从长期记忆恢复最近的对话历史到上下文
        # 之前的问题：clear_context() 清空后不恢复历史，导致 LLM 完全"忘记"之前的对话
        # 现在：从 Memory 中取最近的消息（排除当前任务），恢复到上下文窗口
        self._restore_context_from_memory(exclude_task=task)

        # 添加用户任务到上下文
        self.context_manager.add_message("user", task)

        print(f"✅ 任务已初始化: {task[:50]}...")
    
    def _restore_context_from_memory(self, exclude_task: str = "", max_messages: int = 10):
        """
        🔧 从长期记忆恢复最近的对话历史到上下文窗口
        
        参数：
            exclude_task (str): 要排除的消息内容（当前新任务，避免重复）
            max_messages (int): 最多恢复的消息数量
            
        功能：
        - 从 Memory 中取最近的对话历史
        - 排除当前新任务（避免重复添加）
        - 将历史消息恢复到 ContextManager 的上下文窗口中
        - 这样 LLM 在 _think() 时能看到之前的对话
        
        修复的 Bug：
        之前 clear_context() 后不恢复历史，导致每次 run() 时 LLM 都"失忆"
        用户说"叫我大大大哥"后，再问"我叫什么"时 LLM 完全不知道
        """
        recent = self.memory.get_recent(count=max_messages + 1)  # +1 因为包含当前新任务
        
        restored_count = 0
        for msg in recent:
            content = msg.get("content", "")
            role = msg.get("role", "")
            
            # 跳过当前新任务（避免重复）
            if exclude_task and content == exclude_task and role == "user":
                continue
            
            # 跳过系统提示（后面会重新添加）
            if role == "system" and "你是" in content:
                continue
            
            # 恢复到上下文
            self.context_manager.add_message(role, content)
            restored_count += 1
        
        if restored_count > 0:
            print(f"🔄 已从记忆恢复 {restored_count} 条历史消息到上下文")
        else:
            print("ℹ️ 无历史消息需要恢复（首次对话）")
    
    def _should_continue(self) -> bool:
        """
        判断是否继续循环
        
        返回：
            bool: True继续，False停止
            
        判断条件：
        1. 状态不是COMPLETED或FAILED
        2. 迭代次数未超过限制
        3. 没有发生错误
        
        设计思路：
        - 防止无限循环
        - 提供多种终止条件
        - 清晰的状态管理
        """
        # 检查状态
        if self.state in [AgentState.COMPLETED, AgentState.FAILED]:
            return False
        
        # 检查迭代次数
        if self.iteration_count >= self.max_iterations:
            print(f"⚠️ 达到最大迭代次数: {self.max_iterations}")
            self.state = AgentState.COMPLETED
            return False
        
        return True
    
    def _think(self) -> Optional[AgentAction]:
        """
        思考步骤 - Agent决策的核心
        
        返回：
            AgentAction: 决定执行的动作，None表示任务完成
            
        功能：
        1. 准备上下文（从记忆中加载相关信息）
        2. 调用LLM进行推理
        3. 解析LLM响应
        4. 返回决策结果
        
        设计思路：
        - 上下文管理：只传递相关信息，避免信息过载
        - 结构化输出：要求LLM返回JSON格式，便于解析
        - 错误处理：处理LLM调用失败的情况
        
        学习重点：
        - Prompt工程：如何设计有效的Prompt
        - 上下文窗口管理
        - 结构化输出的处理
        """
        print(f"\n🤔 思考中... (迭代 {self.iteration_count})")

        # 1. 准备上下文
        messages = self.context_manager.get_context()

        # 调试：打印当前上下文
        print(f"[DEBUG] 当前上下文消息数: {len(messages)}")
        for i, msg in enumerate(messages):
            content_preview = msg.get('content', '')[:100] + "..." if len(msg.get('content', '')) > 100 else msg.get('content', '')
            print(f"  [{i}] {msg.get('role')}: {content_preview}")

        # 2. 调用LLM
        response = self._call_llm(messages)

        # 3. 解析响应
        action = self._parse_response_to_action(response)

        # 4. 检测重复调用（防止无限循环）
        if action and self._last_action:
            if (action.tool_name == self._last_action.tool_name and
                action.parameters == self._last_action.parameters):
                print(f"⚠️ 检测到重复调用: {action.tool_name}({action.parameters})")
                print(f"⚠️ 强制结束任务，避免无限循环")
                return None  # 强制结束

        # 记录本次 action
        self._last_action = action

        return action
    
    def _act(self, action: AgentAction) -> str:
        """
        行动步骤 - 执行工具

        参数：
            action (AgentAction): 要执行的行动

        返回：
            str: 执行结果

        功能：
        1. 查找对应的工具
        2. 执行工具
        3. 记录工具调用轨迹
        4. 返回结果

        设计思路：
        - 错误处理：工具不存在或执行失败
        - 日志记录：记录所有工具调用
        - 结果格式化：统一结果格式
        """
        # 检查是否是 use_skill 动作（渐进式 Skill 调用）
        if action.tool_name == 'use_skill':
            skill_name = action.parameters.get('skill_name')
            skill_input = action.parameters.get('skill_input', '')

            print(f"🎯 LLM 选择使用 Skill: {skill_name}")

            # 查找 Skill
            skill = self.skill_registry.get(skill_name)
            if not skill:
                available = ', '.join(self.skill_registry.get_skill_names())
                return f"❌ 找不到名为 '{skill_name}' 的 Skill。可用 Skill: {available}"

            print(f"📖 正在加载完整 SOP: {skill.meta.name}")

            # 构建 Skill 执行上下文
            context = SkillContext(
                tool_registry=self.tools,
                llm_client=self.llm_client,
                memory=self.memory,
                context_manager=self.context_manager,
                user_input=skill_input
            )

            # 执行 Skill
            result = self.skill_executor.execute(skill, context)

            # 记录执行
            self._tools_called.append(ToolCall(
                tool_name=f"skill:{skill_name}",
                parameters=action.parameters,
                result=str(result.result) if result.success else result.error or "",
                reasoning=action.reasoning,
                success=result.success
            ))

            return self._format_skill_result(result)

        print(f"🔧 执行工具: {action.tool_name}")
        print(f"📝 参数: {action.parameters}")
        print(f"💭 理由: {action.reasoning}")

        # 查找工具
        tool = self._find_tool(action.tool_name)

        if tool is None:
            error_msg = f"工具 '{action.tool_name}' 不存在"
            print(f"❌ {error_msg}")
            # 记录失败的工具调用
            self._tools_called.append(ToolCall(
                tool_name=action.tool_name,
                parameters=action.parameters,
                result=error_msg,
                reasoning=action.reasoning,
                success=False
            ))
            return f"错误: {error_msg}"

        # 执行工具
        try:
            tool_result = tool.execute(**action.parameters)

            # ToolResult 是一个 dataclass 对象，需要正确处理
            if tool_result.success:
                # 成功：返回结果内容
                result_str = str(tool_result.result) if tool_result.result is not None else "执行成功"
                print(f"✅ 执行结果: {result_str[:100]}...")
                # 记录成功的工具调用
                self._tools_called.append(ToolCall(
                    tool_name=action.tool_name,
                    parameters=action.parameters,
                    result=result_str,
                    reasoning=action.reasoning,
                    success=True
                ))
                return result_str
            else:
                # 失败：返回错误信息
                error_msg = tool_result.error or "工具执行失败"
                print(f"❌ {error_msg}")
                # 记录失败的工具调用
                self._tools_called.append(ToolCall(
                    tool_name=action.tool_name,
                    parameters=action.parameters,
                    result=error_msg,
                    reasoning=action.reasoning,
                    success=False
                ))
                return f"工具执行失败: {error_msg}"
        except Exception as e:
            error_msg = f"工具执行失败: {str(e)}"
            print(f"❌ {error_msg}")
            # 记录异常的工具调用
            self._tools_called.append(ToolCall(
                tool_name=action.tool_name,
                parameters=action.parameters,
                result=error_msg,
                reasoning=action.reasoning,
                success=False
            ))
            return error_msg
    
    def _observe(self, action: AgentAction, result: str):
        """
        观察步骤 - 记录和分析结果

        参数：
            action (AgentAction): 执行的行动
            result (str): 执行结果

        功能：
        1. 将结果添加到记忆
        2. 更新上下文
        3. 不在此处判断任务完成（由LLM在下一轮think中决定）

        设计思路：
        - 记录所有执行历史
        - 维护对话上下文
        - 任务完成由LLM决定，而非工具执行结果的关键词匹配

        学习重点：
        - 记忆管理策略
        - 上下文窗口优化
        - Agent Loop的正确实现：工具执行成功 ≠ 任务完成

        重要说明：
        任务是否完成应该由LLM在下一轮_think()中决定（返回action="finish"），
        而不是根据工具执行结果的关键词来判断。例如：
        """
        # 记录到记忆系统
        self.memory.save_message(
            "assistant",
            f"执行 {action.tool_name}: {result}"
        )

        # 添加到上下文（供下一轮LLM调用使用）
        self.context_manager.add_message(
            "assistant",
            f"我执行了 {action.tool_name}，结果是: {result}"
        )

        # 注意：不在工具执行后判断任务完成
        # 任务完成由LLM决定，在_parse_response_to_action中处理action="finish"
    
    def _build_skill_index_text(self) -> str:
        """
        构建轻量 Skill 索引（渐进式披露 - 仅 name + description）

        返回:
            str: 格式化的 Skill 索引文本
        """
        skills = self.skill_registry.get_all(enabled_only=True)
        if not skills:
            return ''

        lines = ['---', '', '# 可用高级能力（Skill）', '']
        lines.append('除基础工具外，你还可以调用以下预定义的高级能力。')
        lines.append('当用户请求匹配某个 Skill 的描述时，使用 action="use_skill" 来调用。')
        lines.append('**注意：一次只能调用一个工具或一个 Skill。**')
        lines.append('')

        for skill in skills:
            desc = skill.meta.description or '暂无描述'
            lines.append(f'- **{skill.meta.name}**: {desc}')

        lines.extend([
            '',
            '**调用方式**：',
            '在 JSON 中使用 action="use_skill"，parameters 格式如下：',
            '{"skill_name": "Skill名称", "skill_input": "用户原始输入或具体需求"}',
            '',
            '**关键规则**：',
            '- 仅当用户请求明确匹配某个 Skill 的功能时才使用 use_skill',
            '- skill_name 必须是上述列表中的名称（精确匹配）',
            '- skill_input 应包含用户的具体需求，帮助 Skill 执行器理解任务',
        ])

        return '\n'.join(lines)

    def _build_system_prompt(self) -> str:
        """
        构建系统提示

        返回：
            str: 系统提示文本

        功能：
        1. 定义Agent的角色和能力
        2. 提供工具列表和使用说明（包括参数定义）
        3. 规定输出格式

        设计思路：
        - 明确Agent的边界
        - 提供清晰的操作指南（工具参数要明确）
        - 要求结构化输出

        学习重点：
        - Prompt工程的最佳实践
        - 如何定义Agent能力边界
        - 结构化输出的设计
        """
        # 构建工具列表（包含参数定义）
        tool_descriptions = []
        for tool in self.tools:
            # 构建工具描述，包含名称、描述和参数定义
            tool_info = f"- {tool.name}: {tool.description}"

            # 添加参数定义
            params = tool.parameters
            if params and "properties" in params:
                required_params = params.get("required", [])
                param_list = []

                for param_name, param_info in params["properties"].items():
                    param_type = param_info.get("type", "any")
                    param_desc = param_info.get("description", "")
                    is_required = param_name in required_params
                    required_mark = "（必需）" if is_required else "（可选）"
                    default_val = param_info.get("default")
                    default_info = f"，默认值: {default_val}" if default_val is not None else ""

                    param_list.append(
                        f"    - {param_name} ({param_type}){required_mark}: {param_desc}{default_info}"
                    )

                if param_list:
                    tool_info += "\n  参数:\n" + "\n".join(param_list)

            tool_descriptions.append(tool_info)

        tools_text = "\n\n".join(tool_descriptions) if tool_descriptions else "暂无可用工具"

        # ====== 角色定义 ======
        system_prompt = f"""# 角色

你是 {self.name}，一个智能 AI 助手。你的目标是通过调用可用工具来帮助用户完成任务。

---

# 核心原则

1. **直接高效**：用最少的步骤完成任务，避免冗余操作
2. **结果导向**：当工具返回的结果已完整回答问题时，立即返回 finish，不再调用额外工具
3. **安全可靠**：严格按照工具参数定义调用，不传入未定义的参数
4. **诚实透明**：在 thinking 中展示你的推理过程，让用户了解决策依据

---

# 工作流程

```
收到任务 → 分析需求 → 选择工具 → 执行工具 → 观察结果 → 判断是否完成
                                                    ↓ 否
                                              继续选择工具
                                                    ↓ 是
                                             返回 action="finish"
```

**关键判断标准**：
- ✅ 工具结果已直接回答了用户问题 → **立即 finish**
- ✅ 已获得用户所需的全部信息 → **立即 finish**
- ❌ 还在收集信息、还在处理中间步骤 → **继续调用工具**

---

# 可用工具

{tools_text}

**工具调用规则**：
- 只使用上述列表中存在的工具
- 参数必须符合工具定义中的类型和要求
- 必需参数（必需）必须提供，可选参数可按需提供
- 一次只能调用一个工具

---

# 输出格式（严格 JSON）

每次回复必须输出且仅输出以下 JSON 格式，不要输出任何 JSON 之外的内容：

```json
{{
    "thinking": "你的思考过程：分析当前状态、为什么选择下一步",
    "action": "工具名称 或 finish",
    "parameters": {{}},
    "reasoning": "选择这个行动的简要理由"
}}
```

**action 取值规则**：
- `"action": "工具名称"`：需要调用工具时使用，parameters 按该工具的参数定义填写
- `"action": "finish"`：任务完成时使用，parameters 必须为 `{{"result": "最终答案"}}`

---

# JSON 格式规范

1. **必须是有效的 JSON**，不要输出 markdown 代码块或其他包裹格式
2. **字符串转义**：换行用 `\\n`，双引号用 `\\"`，反斜杠用 `\\\\`，制表符用 `\\t`
3. **禁止无效转义**：不要在字符串中使用 `\\以`、`\\*`、`\\@` 等无效转义序列
4. **finish 格式**：action 为 finish 时，parameters 必须是 `{{"result": "最终答案文本"}}`

---

# 示例

**示例 1：数学计算**
```
用户：15*16等于多少
你调用：calculator(expression="15*16") → 返回 240
你返回：{{"thinking": "计算已完成，结果为240", "action": "finish", "parameters": {{"result": "15*16=240"}}, "reasoning": "计算器已给出准确结果"}}
```

**示例 2：文件读取**
```
用户：读取 config.json 的内容
你调用：file_read(file_path="config.json") → 返回文件内容
你返回：{{"thinking": "文件内容已获取", "action": "finish", "parameters": {{"result": "文件内容如下：..." }}, "reasoning": "文件读取成功，内容已完整返回"}}
```

**示例 3：多步骤任务**
```
用户：读取文件并统计行数
第一轮：{{"thinking": "需要先读取文件内容", "action": "file_read", "parameters": {{"file_path": "data.txt"}}, "reasoning": "获取文件内容后才能统计行数"}}
观察结果：文件内容有100行
第二轮：{{"thinking": "已获取文件内容，可以统计行数", "action": "finish", "parameters": {{"result": "文件共有100行"}}, "reasoning": "已从文件内容中统计出行数"}}
```

---

请严格遵循以上规则，确保每次输出都是有效的 JSON。
"""
        # 注入 Skill 索引（渐进式披露 - 只展示名称和描述，SOP 按需加载）
        skill_index = self._build_skill_index_text()
        if skill_index:
            system_prompt += '\n\n' + skill_index

        return system_prompt
    
    def _call_llm(self, messages: List[Dict[str, str]], use_structured_output: bool = True) -> str:
        """
        调用LLM（大语言模型）

        参数：
            messages (List[Dict]): 消息列表
                格式：[{"role": "user/assistant/system", "content": "..."}]
            use_structured_output (bool): 是否使用结构化输出（强制返回有效JSON）
        返回：
            str: LLM的响应文本（JSON格式）
        功能：
        1. 使用配置的LLM客户端调用API
        2. 支持结构化输出，保证返回有效JSON
        3. 处理响应和错误
        4. 记录token使用情况

        设计思路：
        - 统一的调用接口
        - 结构化输出优先，避免JSON解析问题
        - 自动重试机制（可选）
        - 详细的错误处理

        学习重点：
        - 理解LLM调用的输入输出
        - 结构化输出的重要性
        - 注意错误处理
        - 了解token限制
        """
        # 如果没有LLM客户端，根据环境决定行为
        if not self.llm_client:
            # 学习/开发环境：允许使用模拟模式
            if self.config.get("debug", False) or self.config.get("allow_mock", False):
                print("⚠️ LLM客户端未初始化，使用模拟模式（仅限开发/学习环境）")
                return self._mock_llm_response()
            # 生产环境：抛出异常
            raise RuntimeError("LLM客户端未初始化，无法执行任务。请检查配置文件中的 llm.api_key")

        try:
            # 调用LLM
            print(f"🤖 调用LLM: {len(messages)} 条消息")

            # 记录请求（调试用）
            if self.config.get("debug", False):
                print("📤 请求消息：")
                for msg in messages:
                    print(f"  [{msg['role']}]: {msg['content'][:100]}...")

            # 准备调用参数
            call_kwargs = {}

            # 结构化输出：根据 LLM 提供商选择合适的方式
            if use_structured_output:
                provider = getattr(self.llm_client, '__class__', None).__name__ if self.llm_client else ""

                if provider == "OpenAIClient":
                    # OpenAI: 使用 json_object 模式（简单可靠）
                    call_kwargs["response_format"] = {"type": "json_object"}
                    print("📐 使用结构化输出: json_object 模式")

                elif provider == "AnthropicClient":
                    # Anthropic: 通过 system 提示强制 JSON 输出
                    # (Anthropic 的 tool calling 更适合复杂场景)
                    print("📐 使用结构化输出: 提示词约束模式")

                elif provider == "OllamaClient":
                    # Ollama: 通过提示词约束
                    print("📐 使用结构化输出: 提示词约束模式")

            # 实际调用
            response: LLMResponse = self.llm_client.call(messages, **call_kwargs)

            # 检查响应是否包含错误
            if response.content.startswith("Error:"):
                error_msg = f"LLM调用失败: {response.content}"
                print(f"❌ {error_msg}")
                # 生产环境：抛出异常；开发环境：使用mock降级
                if self.config.get("debug", False) or self.config.get("allow_mock", False):
                    print("⚠️ 降级使用模拟响应")
                    return self._mock_llm_response()
                raise RuntimeError(error_msg)

            # 记录token使用
            if response.usage:
                print(f"📊 Token使用: {response.usage}")
                # 保存到记忆中（可选）
                self.memory.save_message(
                    "system",
                    f"Token使用: {response.usage['total_tokens']} "
                    f"(prompt: {response.usage['prompt_tokens']}, "
                    f"completion: {response.usage['completion_tokens']})"
                )

            # 检查响应内容是否为空
            if not response.content or not response.content.strip():
                print("⚠️ LLM返回空响应")
                if self.config.get("debug", False) or self.config.get("allow_mock", False):
                    print("⚠️ 降级使用模拟响应")
                    return self._mock_llm_response()
                raise RuntimeError("LLM返回空响应，请检查模型配置或API连接")

            # 返回响应内容
            return response.content

        except RuntimeError:
            # 重新抛出RuntimeError（我们自己的错误）
            raise
        except Exception as e:
            error_msg = f"LLM调用异常: {str(e)}"
            print(f"❌ {error_msg}")
            # 生产环境：抛出异常；开发环境：使用mock降级
            if self.config.get("debug", False) or self.config.get("allow_mock", False):
                print("⚠️ 降级使用模拟响应")
                return self._mock_llm_response()
            raise RuntimeError(error_msg) from e
    
    def _mock_llm_response(self) -> str:
        """
        模拟LLM响应

        返回：
            str: 模拟的JSON格式响应

        用途：
        - 仅限开发/学习环境使用
        - 需要设置 debug=true 或 allow_mock=true 才会启用
        - 生产环境应该抛出异常而非返回mock

        安全警告：
        - mock响应返回 action="finish"，会直接终止任务
        - 在生产环境使用会导致任务静默失败，返回虚假结果
        - 请确保生产环境关闭 debug 和 allow_mock 配置
        """
        return json.dumps({
            "thinking": "这是一个模拟响应（仅限开发环境）",
            "action": "finish",
            "parameters": {"result": "任务完成（模拟模式 - 非实际执行结果）"},
            "reasoning": "LLM客户端未初始化或调用失败，使用模拟响应"
        })
    
    def _parse_response_to_action(self, response: str) -> Optional[AgentAction]:
        """
        解析LLM响应，转换为Agent行动

        参数：
            response (str): LLM的响应文本

        返回：
            AgentAction: 解析后的行动对象，None表示任务完成

        功能：
        1. 解析JSON格式的响应
        2. 提取工具名称、参数、理由
        3. 创建AgentAction对象

        设计思路：
        - 使用通用的 JSON 解析工具（支持自动修复）
        - 处理各种可能的错误情况
        - 提供详细的错误信息
        - 验证必需字段

        学习重点：
        - 结构化输出的解析
        - 错误处理的重要性
        - 数据验证的必要性
        """
        from .llm_client import safe_json_loads

        print(f"[DEBUG] 原始响应长度: {len(response)}, 类型: {type(response)}")
        print(f"[DEBUG] LLM原始响应: {response[:500]}")

        # 使用通用 JSON 解析工具（自动修复 + 提取）
        data, error = safe_json_loads(response)

        if error:
            print(f"❌ JSON解析失败: {error}")
            print(f"[DEBUG] 响应前500字符: {response[:500]}")
            return None

        try:
            print(f"[DEBUG] 解析成功, action={data.get('action')}")
            print(f"[DEBUG] 完整解析数据: {data}")
            # 检查是否完成任务
            if data.get("action") == "finish":
                result = data.get("parameters", {}).get("result", "任务完成")
                print(f"[DEBUG~~~~~~~~~~~~~~~] <UNK>: {result}")
                # 同时保存到 memory（长期存储）和 context（当前上下文）
                self.memory.save_message("assistant", f"最终答案: {result}")
                self.context_manager.add_message("assistant", result)
                return None

            # 创建AgentAction对象
            action = AgentAction(
                tool_name=data.get("action"),
                parameters=data.get("parameters", {}),
                reasoning=data.get("reasoning", "")
            )

            return action

        except Exception as e:
            print(f"❌ 响应解析失败: {e}")
            return None

    def _find_tool(self, tool_name: str) -> Optional[Any]:
        """
        查找工具

        参数：
            tool_name (str): 工具名称

        返回：
            Tool对象，如果未找到返回None

        功能：
        根据名称在工具列表中查找对应的工具
        """
        for tool in self.tools:
            if tool.name == tool_name:
                return tool
        return None
    
    def _is_task_complete(self, result: str) -> bool:
        """
        [已废弃] 判断任务是否完成

        参数：
            result (str): 最新的执行结果

        返回：
            bool: True表示完成，False表示继续

        废弃原因：
        工具执行成功 ≠ 任务完成。例如：
        - 任务："读取文件并总结"
        - 执行read_file后结果包含"成功"，但任务并未完成
        - 正确做法：由LLM决定何时返回action="finish"

        保留此方法仅供参考，未来可考虑：
        1. 用LLM来判断任务是否完成（额外调用成本）
        2. 完全依赖LLM返回的action="finish"
        """
        # 简单规则：检查是否包含完成标志（已废弃使用）
        completion_keywords = ["完成", "成功", "finished", "completed", "done"]
        result_lower = result.lower()

        return any(keyword in result_lower for keyword in completion_keywords)
    
    def _handle_error(self, error: Exception):
        """
        错误处理
        
        参数：
            error (Exception): 捕获的异常
            
        功能：
        1. 记录错误信息
        2. 更新状态为FAILED
        3. 记录到记忆系统
        
        设计思路：
        - 详细的错误记录，便于调试
        - 不中断程序，优雅降级
        - 提供有用的错误信息
        """
        error_message = f"执行出错: {str(error)}"
        print(f"❌ {error_message}")
        
        self.state = AgentState.FAILED
        self.memory.save_message("system", error_message)
    
    def _get_final_result(self) -> AgentResult:
        """
        获取最终结果

        返回：
            AgentResult: 包含完整执行信息的结果对象

        功能：
        从记忆中提取最终结果，构建 AgentResult
        """
        if self.state == AgentState.COMPLETED:
            # 从 ContextManager 获取最后的消息
            context = self.context_manager.get_context()
            result_text = "任务完成"
            if context:
                # 获取最后的 assistant 消息
                for msg in reversed(context):
                    if msg["role"] == "assistant":
                        result_text = msg["content"]
                        break

            return AgentResult(
                result=result_text,
                success=True,
                source="agent_loop",
                tools_called=self._tools_called,
                iterations=self.iteration_count
            )
        else:
            return AgentResult(
                result=f"任务未完成。当前状态: {self.state.value}",
                success=False,
                source="agent_loop",
                tools_called=self._tools_called,
                iterations=self.iteration_count,
                error=f"Agent 状态: {self.state.value}"
            )

    def _format_skill_result(self, result: SkillResult) -> str:
        """
        格式化 Skill 执行结果

        参数：
            result: Skill 执行结果

        返回：
            str: 格式化后的结果文本
        """
        if not result.success:
            return f"Skill 执行失败: {result.error}"

        # 根据输出格式处理
        if result.output_format == "structured" and isinstance(result.result, dict):
            import json
            return json.dumps(result.result, ensure_ascii=False, indent=2)

        # 默认返回文本
        if result.result is not None:
            return str(result.result)

        return "Skill 执行完成"

    def get_skill_context(self) -> SkillContext:
        """
        构建 Skill 执行上下文

        返回：
            SkillContext: 包含所有能力的上下文
        """
        return SkillContext(
            tool_registry=self.tools,
            llm_client=self.llm_client,
            memory=self.memory,
            context_manager=self.context_manager
        )

    def list_skills(self) -> List[Dict]:
        """
        列出所有已加载的 Skill

        返回：
            List[Dict]: Skill 信息列表
        """
        return self.skill_registry.list_skills()

    def reload_skills(self, skill_dirs: Optional[List[str]] = None) -> int:
        """
        重新加载 Skills

        参数：
            skill_dirs: Skill 目录列表（可选，默认使用初始化时的目录）

        返回：
            int: 加载的 Skill 数量
        """
        if skill_dirs is None:
            config_dirs = self.config.get("skill_dirs", [])
            if isinstance(config_dirs, str):
                config_dirs = [config_dirs]
            skill_dirs = config_dirs

        # 清空并重新加载
        self.skill_registry.clear()
        self.skill_loader.clear_loaded()

        if skill_dirs:
            skills = self.skill_loader.load_from_directories(skill_dirs)
            for skill in skills:
                self.skill_registry.register(skill)

            # 更新路由器
            self.skill_router.update_skills(self.skill_registry.get_all())

            return len(skills)

        return 0


# 使用示例（详细注释）
if __name__ == "__main__":
    """
    使用示例 - 演示如何创建和使用Agent
    
    这个示例展示了Agent的基本使用方法。
    在实际项目中，我们会添加真实的工具和LLM客户端。
    """
    
    print("=" * 60)
    print("Q-Agent 使用示例")
    print("=" * 60)
    
    # 步骤1: 创建Agent实例
    print("\n📝 步骤1: 创建Agent实例")
    agent = Agent(
        name="学习助手",
        max_iterations=5
    )
    print(f"✅ Agent '{agent.name}' 创建成功")
    
    # 步骤2: 执行任务（使用模拟的LLM响应）
    print("\n📝 步骤2: 执行任务")
    task = "帮我创建一个test.txt文件"
    print(f"任务: {task}")
    
    result = agent.run(task)
    print(f"\n🎯 最终结果: {result}")
    
    # 步骤3: 查看记忆
    print("\n📝 步骤3: 查看记忆")
    print("最近的消息:")
    for msg in agent.memory.get_recent(count=5):
        print(f"  [{msg['role']}]: {msg['content']}")
    
    print("\n" + "=" * 60)
    print("示例执行完成！")
    print("=" * 60)
