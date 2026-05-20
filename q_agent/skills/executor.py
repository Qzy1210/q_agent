"""
Skill 执行器

执行 Skill 的 SOP（标准化操作流程），包括：
1. 构建系统提示（包含 SOP 和可用工具）
2. 调用 LLM 执行 SOP
3. 处理工具调用
4. 执行 Hooks
5. 返回 SkillResult

使用方法：
    executor = SkillExecutor(tool_registry, llm_client, memory, context_manager)
    result = await executor.execute(skill, user_input, context)
"""

import subprocess
import os
from typing import Dict, List, Any, Optional

from .types import Skill, SkillResult, SkillContext, SkillHook


class SkillExecutor:
    """
    Skill 执行器

    负责执行 Skill 的 SOP，协调 LLM 和工具调用。
    """

    def __init__(
        self,
        tool_registry: Any = None,
        llm_client: Any = None,
        memory: Any = None,
        context_manager: Any = None,
        skill_registry: Any = None
    ):
        """
        初始化执行器

        Args:
            tool_registry: 工具注册器（ToolRegistry 实例或 tools 列表）
            llm_client: LLM 客户端
            memory: 记忆系统
            context_manager: 上下文管理器
            skill_registry: Skill 注册器（用于 list_skills 等系统 Skill）
        """
        self.tool_registry = tool_registry
        self.llm_client = llm_client
        self.memory = memory
        self.context_manager = context_manager
        self.skill_registry = skill_registry

    def execute(
        self,
        skill: Skill,
        user_input: str,
        context: Optional[SkillContext] = None
    ) -> SkillResult:
        """
        执行 Skill

        Args:
            skill: 要执行的 Skill
            user_input: 用户输入
            context: 执行上下文（可选）

        Returns:
            SkillResult: 执行结果
        """
        trace = []

        try:
            # 特殊处理：list_skills Skill 直接返回结果
            if skill.meta.name == "list_skills":
                result = self._handle_list_skills()
                trace.append({"step": "list_skills", "status": "completed"})
                return SkillResult(
                    success=True,
                    result=result,
                    execution_trace=trace,
                    output_format="text"
                )

            # 1. 执行 PreExecute hooks
            self._run_hooks(skill, "PreExecute", {"user_input": user_input})
            trace.append({"step": "pre_execute_hooks", "status": "completed"})

            # 2. 构建系统提示
            system_prompt = self._build_system_prompt(skill)
            trace.append({"step": "build_system_prompt", "status": "completed"})

            # 3. 构建用户提示
            user_prompt = self._build_user_prompt(skill, user_input)

            # 4. 准备消息
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]

            # 5. 获取可用工具
            tools = self._get_allowed_tools(skill)
            trace.append({
                "step": "prepare_tools",
                "tools": [t.get("name") for t in tools] if tools else []
            })

            # 6. 调用 LLM
            llm_response = self._call_llm(messages, tools)
            trace.append({
                "step": "llm_call",
                "response_length": len(llm_response) if llm_response else 0
            })

            # 7. 处理响应（可能包含工具调用）
            result = self._process_response(llm_response, skill, trace)

            # 8. 执行 PostExecute hooks
            self._run_hooks(skill, "PostExecute", {"result": result})
            trace.append({"step": "post_execute_hooks", "status": "completed"})

            return SkillResult(
                success=True,
                result=result,
                execution_trace=trace,
                output_format=skill.meta.output.type if skill.meta.output else "text"
            )

        except Exception as e:
            # 执行 OnError hooks
            self._run_hooks(skill, "OnError", {"error": str(e)})
            trace.append({"step": "error", "error": str(e)})

            return SkillResult(
                success=False,
                result=None,
                error=str(e),
                execution_trace=trace
            )

    def _build_system_prompt(self, skill: Skill) -> str:
        """
        构建系统提示

        包含：
        - Skill 名称和描述
        - SOP 执行流程
        - 可用工具列表
        - 输出格式要求

        Args:
            skill: Skill 对象

        Returns:
            系统提示文本
        """
        # 构建工具列表
        tools_text = ""
        if skill.meta.allowed_tools:
            tools_text = "\n可用工具：\n"
            for tool_name in skill.meta.allowed_tools:
                tool_info = self._get_tool_info(tool_name)
                if tool_info:
                    tools_text += f"- {tool_name}: {tool_info.get('description', '')}\n"

        # 构建输出格式要求
        output_text = ""
        if skill.meta.output:
            if skill.meta.output.type == "structured" and skill.meta.output.schema:
                import json
                schema_str = json.dumps(skill.meta.output.schema, ensure_ascii=False, indent=2)
                output_text = f"\n输出格式要求（JSON Schema）：\n```json\n{schema_str}\n```\n"
            elif skill.meta.output.type == "text":
                output_text = "\n输出格式：纯文本\n"

        system_prompt = f"""你正在执行 Skill: {skill.meta.name}

{skill.meta.description}

## 执行流程 (SOP)

{skill.sop}
{tools_text}{output_text}

请严格按照 SOP 执行流程完成任务。如果 SOP 中包含工具调用，请按照工具参数要求正确调用。
"""

        return system_prompt

    def _build_user_prompt(self, skill: Skill, user_input: str) -> str:
        """
        构建用户提示

        Args:
            skill: Skill 对象
            user_input: 用户输入

        Returns:
            用户提示文本
        """
        return f"""用户请求：{user_input}

请按照 SOP 执行流程完成任务。"""

    def _get_allowed_tools(self, skill: Skill) -> List[Dict]:
        """
        获取 Skill 允许使用的工具定义

        Args:
            skill: Skill 对象

        Returns:
            工具定义列表
        """
        tools = []

        if not skill.meta.allowed_tools:
            return tools

        for tool_name in skill.meta.allowed_tools:
            tool_info = self._get_tool_info(tool_name)
            if tool_info:
                # 构建 OpenAI 格式的工具定义
                tools.append({
                    "type": "function",
                    "function": {
                        "name": tool_info.get("name", tool_name),
                        "description": tool_info.get("description", ""),
                        "parameters": tool_info.get("parameters", {})
                    }
                })

        return tools

    def _get_tool_info(self, tool_name: str) -> Optional[Dict]:
        """
        获取工具信息

        支持两种 tool_registry 格式：
        1. ToolRegistry 实例（有 get 方法）
        2. tools 列表

        Args:
            tool_name: 工具名称

        Returns:
            工具信息字典
        """
        if not self.tool_registry:
            return None

        # 尝试作为 ToolRegistry 使用
        if hasattr(self.tool_registry, 'get'):
            tool = self.tool_registry.get(tool_name)
            if tool:
                return {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters
                }

        # 尝试作为列表使用
        if hasattr(self.tool_registry, '__iter__'):
            for tool in self.tool_registry:
                if hasattr(tool, 'name') and tool.name == tool_name:
                    return {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.parameters
                    }

        return None

    def _call_llm(
        self,
        messages: List[Dict],
        tools: List[Dict] = None
    ) -> str:
        """
        调用 LLM

        Args:
            messages: 消息列表
            tools: 工具定义列表

        Returns:
            LLM 响应文本
        """
        if not self.llm_client:
            return self._mock_llm_response()

        try:
            # 检查是否支持 tools 参数
            if tools and hasattr(self.llm_client, 'call'):
                # 尝试传递 tools 参数
                response = self.llm_client.call(messages, tools=tools)
            else:
                response = self.llm_client.call(messages)

            # 处理 LLMResponse 对象
            if hasattr(response, 'content'):
                return response.content

            return str(response)

        except Exception as e:
            print(f"[SkillExecutor] LLM 调用失败: {e}")
            return self._mock_llm_response()

    def _mock_llm_response(self) -> str:
        """
        模拟 LLM 响应（开发/测试用）

        Returns:
            模拟的响应文本
        """
        import json
        return json.dumps({
            "thinking": "这是一个模拟响应（仅限开发环境）",
            "result": "任务完成（模拟模式 - 非实际执行结果）",
            "tool_calls": []
        })

    def _process_response(
        self,
        response: str,
        skill: Skill,
        trace: List[Dict]
    ) -> Any:
        """
        处理 LLM 响应

        可能包含：
        - 直接文本结果
        - 工具调用请求

        Args:
            response: LLM 响应
            skill: Skill 对象
            trace: 执行轨迹

        Returns:
            处理后的结果
        """
        import json

        # 尝试解析 JSON
        try:
            data = json.loads(response)
        except json.JSONDecodeError:
            # 非 JSON，直接返回文本
            trace.append({"step": "parse_response", "type": "text"})
            return response

        trace.append({"step": "parse_response", "type": "json"})

        # 检查是否有工具调用
        tool_calls = data.get("tool_calls", [])
        if tool_calls:
            trace.append({"step": "tool_calls", "count": len(tool_calls)})

            results = []
            for call in tool_calls:
                tool_name = call.get("name") or call.get("tool_name")
                tool_args = call.get("arguments") or call.get("args", {})

                # 执行工具调用
                tool_result = self._execute_tool(skill, tool_name, tool_args)
                results.append({
                    "tool": tool_name,
                    "result": tool_result
                })
                trace.append({
                    "step": "tool_call",
                    "tool": tool_name,
                    "success": tool_result.get("success", False)
                })

            # 如果只有一个工具调用，返回其结果
            if len(results) == 1:
                return results[0]["result"]

            return {"tool_results": results}

        # 检查是否有直接结果
        if "result" in data:
            return data["result"]

        # 返回解析后的数据
        return data

    def _execute_tool(
        self,
        skill: Skill,
        tool_name: str,
        arguments: Dict
    ) -> Dict:
        """
        执行工具调用

        Args:
            skill: Skill 对象
            tool_name: 工具名称
            arguments: 工具参数

        Returns:
            执行结果
        """
        # 检查工具是否在允许列表中
        if tool_name not in skill.meta.allowed_tools:
            return {
                "success": False,
                "error": f"工具 '{tool_name}' 不在 Skill 允许的工具列表中"
            }

        # 查找工具
        tool = self._find_tool(tool_name)
        if not tool:
            return {
                "success": False,
                "error": f"工具 '{tool_name}' 不存在"
            }

        try:
            # 执行 PreToolUse hooks
            self._run_hooks(skill, "PreToolUse", {
                "tool_name": tool_name,
                "arguments": arguments
            })

            # 执行工具
            result = tool.execute(**arguments)

            # 执行 PostToolUse hooks
            self._run_hooks(skill, "PostToolUse", {
                "tool_name": tool_name,
                "result": result
            })

            # 处理 ToolResult 对象
            if hasattr(result, 'to_dict'):
                return result.to_dict()

            return {"success": True, "result": result}

        except Exception as e:
            return {
                "success": False,
                "error": f"工具执行失败: {str(e)}"
            }

    def _find_tool(self, tool_name: str) -> Optional[Any]:
        """
        查找工具

        Args:
            tool_name: 工具名称

        Returns:
            工具对象或 None
        """
        if not self.tool_registry:
            return None

        # 尝试作为 ToolRegistry 使用
        if hasattr(self.tool_registry, 'get'):
            return self.tool_registry.get(tool_name)

        # 尝试作为列表使用
        if hasattr(self.tool_registry, '__iter__'):
            for tool in self.tool_registry:
                if hasattr(tool, 'name') and tool.name == tool_name:
                    return tool

        return None

    def _run_hooks(
        self,
        skill: Skill,
        event: str,
        context: Dict = None
    ) -> None:
        """
        执行 Hooks

        Args:
            skill: Skill 对象
            event: 事件名称
            context: 执行上下文
        """
        hooks = skill.meta.hooks.get(event, [])
        context = context or {}

        for hook in hooks:
            try:
                self._run_single_hook(hook, context)
            except Exception as e:
                print(f"[SkillExecutor] Hook 执行失败: {e}")

    def _run_single_hook(self, hook: SkillHook, context: Dict) -> None:
        """
        执行单个 Hook

        Args:
            hook: Hook 定义
            context: 执行上下文
        """
        if hook.type == "command":
            # 执行 shell 命令
            command = hook.command or ""

            # 替换变量
            for key, value in context.items():
                placeholder = f"${key.upper()}"
                if placeholder in command:
                    command = command.replace(placeholder, str(value))

            # 特殊变量替换
            if "$ERROR" in command and "error" in context:
                command = command.replace("$ERROR", str(context["error"]))

            # 执行命令
            subprocess.run(command, shell=True, capture_output=True)

        elif hook.type == "callback":
            # TODO: 支持 Python 回调
            pass

    def _handle_list_skills(self) -> str:
        """
        处理 list_skills Skill

        返回所有已加载的 Skill 信息

        Returns:
            格式化的 Skill 列表文本
        """
        if not self.skill_registry:
            return "❌ SkillRegistry 未初始化，无法列出 Skills"

        skills_info = self.skill_registry.list_skills(enabled_only=True)

        if not skills_info:
            return "ℹ️ 当前没有加载任何 Skill"

        lines = [f"## 已加载的 Skill（共 {len(skills_info)} 个）\n"]

        for i, info in enumerate(skills_info, 1):
            name = info.get('name', 'unknown')
            description = info.get('description', '无描述')
            version = info.get('version', '1.0.0')
            triggers = info.get('triggers', [])
            tools = info.get('tools', [])

            lines.append(f"{i}. **{name}** - {description}")
            lines.append(f"   - 版本: {version}")

            # 触发方式
            trigger_parts = []
            for t in triggers:
                if t.get('type') == 'command' and t.get('pattern'):
                    # 提取命令，如 "^/review" -> "/review"
                    pattern = t['pattern']
                    if pattern.startswith('^'):
                        pattern = pattern[1:]
                    trigger_parts.append(f"命令 `{pattern}`")
                elif t.get('type') == 'intent' and t.get('keywords'):
                    keywords = t['keywords'][:3]  # 只显示前3个关键词
                    trigger_parts.append(f"关键词: {', '.join(keywords)}")

            if trigger_parts:
                lines.append(f"   - 触发方式: {' 或 '.join(trigger_parts)}")

            # 可用工具
            if tools:
                lines.append(f"   - 可用工具: {', '.join(tools)}")

            lines.append("")

        # 使用说明
        lines.append("### 使用方式")
        lines.append("- **显式命令**: 直接输入命令，如 `/review main.py`")
        lines.append("- **自然语言**: 描述你的意图，如 \"帮我审查代码质量\"")
        lines.append("")
        lines.append("### 创建自定义 Skill")
        lines.append("在 `~/.q_agent/skills/` 目录下创建 `skill.md` 文件即可")

        return "\n".join(lines)
