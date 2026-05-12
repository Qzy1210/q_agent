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
        context_manager: Optional[ContextManager] = None,
        config: Optional[Config] = None
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
        
        # 配置管理
        self.config = config or Config()
        
        # 如果没有提供llm_client，从配置创建
        if not self.llm_client:
            self._init_llm_client()
    
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
        
        # 清空上下文（保留记忆）
        self.context_manager.clear_context(True)
        
        # 记录任务到记忆系统
        self.memory.save_message("user", task)
        
        # 添加系统提示到上下文
        system_prompt = self._build_system_prompt()
        self.context_manager.add_message("system", system_prompt)
        
        # 添加用户任务到上下文
        self.context_manager.add_message("user", task)
        
        print(f"✅ 任务已初始化: {task[:50]}...")
    
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
        
        # 2. 调用LLM
        response = self._call_llm(messages)
        
        # 3. 解析响应
        action = self._parse_response_to_action(response)
        
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
        3. 返回结果
        
        设计思路：
        - 错误处理：工具不存在或执行失败
        - 日志记录：记录所有工具调用
        - 结果格式化：统一结果格式
        """
        print(f"🔧 执行工具: {action.tool_name}")
        print(f"📝 参数: {action.parameters}")
        print(f"💭 理由: {action.reasoning}")
        
        # 查找工具
        tool = self._find_tool(action.tool_name)
        
        if tool is None:
            error_msg = f"工具 '{action.tool_name}' 不存在"
            print(f"❌ {error_msg}")
            return f"错误: {error_msg}"
        
        # 执行工具
        try:
            result = tool.execute(**action.parameters)
            print(f"✅ 执行结果: {result[:100]}...")
            return result
        except Exception as e:
            error_msg = f"工具执行失败: {str(e)}"
            print(f"❌ {error_msg}")
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

        system_prompt = f"""你是一个智能助手 {self.name}。

你的职责是帮助用户完成任务。你会使用工具来解决问题。

可用工具：
{tools_text}

工作流程：
1. 分析用户任务
2. 选择合适的工具
3. 执行工具并观察结果
4. 继续下一步或完成任务

输出格式要求（JSON）：
{{
    "thinking": "你的思考过程",
    "action": "工具名称 或 finish（完成任务）",
    "parameters": {{根据action不同，参数格式不同（见工具定义）}},
    "reasoning": "选择这个行动的理由"
}}

重要提示：
- action为"finish"时，parameters格式为：{{"result": "最终答案"}}
- action为工具名称时，parameters必须按照该工具的参数定义提供
- 仔细阅读工具的参数要求，确保参数格式正确
- 如果没有合适的工具，说明原因并建议其他方案
- 始终保持JSON格式输出
"""
        return system_prompt
    
    def _call_llm(self, messages: List[Dict[str, str]]) -> str:
        """
        调用LLM（大语言模型）

        参数：
            messages (List[Dict]): 消息列表
                格式：[{"role": "user/assistant/system", "content": "..."}]
        返回：
            str: LLM的响应文本（JSON格式）
        功能：
        1. 使用配置的LLM客户端调用API
        2. 处理响应和错误
        3. 记录token使用情况

        设计思路：
        - 统一的调用接口
        - 自动重试机制（可选）
        - 详细的错误处理

        学习重点：
        - 理解LLM调用的输入输出
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

            # 实际调用
            response: LLMResponse = self.llm_client.call(messages)

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
                self.memory.save_message("assistant", f"最终答案: {result}")
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
    
    def _get_final_result(self) -> str:
        """
        获取最终结果
        
        返回：
            str: 任务执行的最终结果
            
        功能：
        从记忆中提取最终结果，格式化输出
        """
        if self.state == AgentState.COMPLETED:
            # 从 ContextManager 获取最后的消息
            context = self.context_manager.get_context()
            if context:
                # 获取最后的 assistant 消息
                for msg in reversed(context):
                    if msg["role"] == "assistant":
                        return msg["content"]
            return "任务完成"
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
    for msg in agent.memory.get_recent(count=5):
        print(f"  [{msg['role']}]: {msg['content']}")
    
    print("\n" + "=" * 60)
    print("示例执行完成！")
    print("=" * 60)
