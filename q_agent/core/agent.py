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
        context_manager: Optional[ContextManager] = None
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
        
    def run(self, task: str) -> str:
        """
        执行主循环 - Agent的核心方法
        这是Agent Loop的入口点，实现了完整的思考-行动循环。
        参数：
            task (str): 用户交给Agent的任务描述
        返回：
            str: 任务执行的最终结果
            
        执行流程：
        1. 初始化任务状态
        2. 进入循环（最多max_iterations次）
        3. 每次循环：
           - 思考：分析当前状态
           - 决策：选择下一步行动
           - 行动：执行工具
           - 观察：记录结果
        4. 判断是否完成或失败
        5. 返回最终结果
        
        学习重点：
        - 注意循环的终止条件
        - 理解每次迭代的输入输出
        - 观察如何记录和更新状态
         ？ 如何控制工具
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
        
        # 将用户任务添加到记忆
        self.memory.add_message("user", task)
        
        # 准备初始上下文：包含用户任务和可用工具
        self.context_manager.set_task(task)
        self.context_manager.set_tools(self.tools)
    
    def _should_continue(self) -> bool:
        """
        判断是否应该继续循环
        
        返回：
            bool: True继续循环，False停止循环
            
        停止条件：
        1. 达到最大迭代次数（防止无限循环）
        2. 状态为COMPLETED或FAILED
        3. 任务已完成
        
        设计说明：
        - 多重保护机制，确保Agent不会无限循环
        - 每个条件都有明确的语义
        - 便于调试和理解Agent状态
        """
        # 检查迭代次数
        if self.iteration_count >= self.max_iterations:
            print(f"⚠️  达到最大迭代次数 {self.max_iterations}，停止执行")
            return False
            
        # 检查状态
        if self.state in [AgentState.COMPLETED, AgentState.FAILED]:
            return False
            
        return True
    
    def _think(self) -> Optional[AgentAction]:
        """
        思考阶段 - Agent的核心决策过程
        
        返回：
            AgentAction: 决定执行的行动，None表示任务完成
        功能：
        1. 构建提示词（Prompt）
        2. 调用LLM进行分析
        3. 解析LLM的响应
        4. 转换为具体的行动
        
        Prompt设计要点：
        - 包含任务描述
        - 包含历史上下文
        - 包含可用工具列表
        - 明确输出格式
        
        学习重点：
        - Prompt工程是Agent开发的核心技能
        - 注意如何将工具信息传递给LLM
        - 理解如何解析结构化输出
        """
        # 构建提示词
        prompt = self._build_thinking_prompt()
        
        # 调用LLM（这里先模拟，后续会实现真实的LLM调用）
        response = self._call_llm(prompt)
        
        # 解析响应，转换为行动
        action = self._parse_response_to_action(response)
        
        return action
    
    def _act(self, action: AgentAction) -> str:
        """
        行动阶段 - 执行具体的工具
        
        参数：
            action (AgentAction): 要执行的行动
            
        返回：
            str: 工具执行的返回结果
            
        功能：
        1. 根据工具名称查找工具
        2. 验证参数
        3. 执行工具
        4. 返回结果
        
        设计思路：
        - 分离工具查找和执行
        - 提供详细的错误信息
        - 记录执行过程，便于调试
        """
        print(f"🎯 执行工具: {action.tool_name}")
        print(f"📝 参数: {action.parameters}")
        print(f"💭 理由: {action.reasoning}")
        
        # 查找工具
        tool = self._find_tool(action.tool_name)
        
        if tool is None:
            error_msg = f"❌ 未找到工具: {action.tool_name}"
            print(error_msg)
            return error_msg
        
        # 执行工具
        try:
            result = tool.execute(**action.parameters)
            print(f"✅ 执行结果: {result}")
            return result
        except Exception as e:
            error_msg = f"❌ 工具执行失败: {str(e)}"
            print(error_msg)
            return error_msg
    
    def _observe(self, action: AgentAction, result: str):
        """
        观察阶段 - 记录执行结果，更新记忆和上下文
        
        参数：
            action (AgentAction): 执行的行动
            result (str): 执行结果
            
        功能：
        1. 记录行动和结果到记忆系统
        2. 更新上下文
        3. 判断任务是否完成
        
        设计思路：
        - 每次观察都是学习的机会
        - 记录完整的信息，便于后续分析
        - 及时更新状态，保持同步
        """
        # 记录到记忆
        self.memory.add_message("assistant", f"执行 {action.tool_name}: {action.reasoning}")
        self.memory.add_message("system", f"执行结果: {result}")
        
        # 更新上下文
        self.context_manager.add_interaction(action, result)
        
        # 检查是否完成任务
        if self._is_task_complete(result):
            self.state = AgentState.COMPLETED
            print("✅ 任务完成！")
    
    def _build_thinking_prompt(self) -> str:
        """
        构建思考阶段的提示词
        
        返回：
            str: 完整的提示词
        提示词结构：
        1. 系统提示（角色定义、能力说明）
        2. 当前任务
        3. 历史上下文
        4. 可用工具列表
        5. 输出格式要求
        
        设计要点：
        - 清晰的角色定义
        - 明确的任务描述
        - 详细的工具说明
        - 结构化的输出要求
        
        学习重点：
        - 这是Prompt工程的核心
        - 注意每个部分的作用
        - 理解如何引导LLM输出
        """
        prompt = f"""
你是一个智能助手 {self.name}，能够使用各种工具帮助用户完成任务。

当前任务: {self.current_task}

历史记录:
{self.memory.get_recent_messages()}

可用工具:
{self._format_tools_for_prompt()}

请分析当前状态，决定下一步行动。

输出格式（JSON）:
{{
    "thinking": "你的思考过程",
    "action": "工具名称",
    "parameters": {{}},
    "reasoning": "选择这个行动的理由"
}}

如果任务已完成，输出:
{{
    "thinking": "分析任务完成情况",
    "action": "finish",
    "parameters": {{"result": "最终结果"}},
    "reasoning": "为什么认为任务已完成"
}}
"""
        return prompt
    
    def _format_tools_for_prompt(self) -> str:
        """
        格式化工具列表，用于提示词
        
        返回：
            str: 格式化后的工具描述
            
        功能：
        将工具对象列表转换为LLM可理解的文本描述
        
        设计思路：
        - 每个工具都有清晰的名称、描述、参数说明
        - 提供示例，帮助LLM正确使用
        - 格式统一，便于解析
        """
        if not self.tools:
            return "当前没有可用工具"
            
        formatted = []
        for tool in self.tools:
            # 工具名称和描述
            desc = f"- {tool.name}: {tool.description}\n"
            # 参数说明
            if hasattr(tool, 'parameters') and tool.parameters:
                desc += "  参数:\n"
                for param, details in tool.parameters.items():
                    desc += f"    - {param}: {details}\n"
            formatted.append(desc)
            
        return "\n".join(formatted)
    
    def _call_llm(self, prompt: str) -> str:
        """
        调用LLM（语言模型）
        
        参数：
            prompt (str): 提示词
        返回：
            str: LLM的响应文本
        功能：
        将提示词发送给LLM，获取响应
        
        说明：
        目前是模拟实现，返回一个固定的响应。
        后续会实现真实的OpenAI API调用。
        
        学习重点：
        - 理解LLM调用的输入输出
        - 注意错误处理
        - 了解token限制
        """
        # 模拟LLM响应（实际项目中会调用OpenAI API）
        # 这里返回一个示例响应，便于测试
        return json.dumps({
            "thinking": "这是一个测试响应",
            "action": "finish",
            "parameters": {"result": "任务完成（模拟）"},
            "reasoning": "这是初始测试，返回模拟结果"
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
        - 处理各种可能的错误情况
        - 提供详细的错误信息
        - 验证必需字段
        
        学习重点：
        - 结构化输出的解析
        - 错误处理的重要性
        - 数据验证的必要性
        """
        try:
            # 解析JSON
            data = json.loads(response)
            
            # 检查是否完成任务
            if data.get("action") == "finish":
                result = data["parameters"].get("result", "任务完成")
                self.memory.add_message("assistant", f"最终答案: {result}")
                return None
            
            # 创建AgentAction对象
            action = AgentAction(
                tool_name=data.get("action"),
                parameters=data.get("parameters", {}),
                reasoning=data.get("reasoning", "")
            )
            
            return action
            
        except json.JSONDecodeError as e:
            print(f"❌ JSON解析失败: {e}")
            return None
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
        判断任务是否完成
        
        参数：
            result (str): 最新的执行结果
            
        返回：
            bool: True表示完成，False表示继续
            
        功能：
        分析执行结果，判断任务是否完成
        
        说明：
        目前使用简单规则，后续可以用LLM来判断
        """
        # 简单规则：检查是否包含完成标志
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
        self.memory.add_message("system", error_message)
    
    def _get_final_result(self) -> str:
        """
        获取最终结果
        
        返回：
            str: 任务执行的最终结果
            
        功能：
        从记忆中提取最终结果，格式化输出
        """
        if self.state == AgentState.COMPLETED:
            # 获取最后的助手消息作为结果
            recent_messages = self.memory.get_recent_messages(count=1)
            return recent_messages[0]["content"] if recent_messages else "任务完成"
        else:
            return f"任务未完成。当前状态: {self.state.value}"


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
    for msg in agent.memory.get_recent_messages(count=5):
        print(f"  [{msg['role']}]: {msg['content']}")
    
    print("\n" + "=" * 60)
    print("示例执行完成！")
    print("=" * 60)
