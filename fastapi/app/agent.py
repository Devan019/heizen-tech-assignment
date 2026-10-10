import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Set
from groq import AsyncGroq
from app.config import get_settings
from app.mcp_client import MCPClientManager, ToolDefinition, mcp_client_manager

logger = logging.getLogger("mcp_gateway.agent")


class AgentStep:
    def __init__(self, step_number: int, tool_name: str, arguments: Dict[str, Any], output: Any, provider: str):
        self.step_number = step_number
        self.tool_name = tool_name
        self.arguments = arguments
        self.output = output
        self.provider = provider

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step": self.step_number,
            "tool_name": self.tool_name,
            "arguments": self.arguments,
            "output": self.output,
            "provider": self.provider,
        }


class AgentRunResult:
    def __init__(
        self,
        response: str,
        steps: List[AgentStep],
        model: str,
        provider_used: List[str],
        iterations: int,
        usage: Optional[Dict[str, Any]] = None,
    ):
        self.response = response
        self.steps = steps
        self.model = model
        self.provider_used = provider_used
        self.iterations = iterations
        self.usage = usage or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "response": self.response,
            "tool_steps": [s.to_dict() for s in self.steps],
            "model": self.model,
            "providers_used": self.provider_used,
            "iterations": self.iterations,
            "usage": self.usage,
        }


SYSTEM_PROMPT = """You are an intelligent AI agent equipped with powerful Model Context Protocol (MCP) tools.
You have access to:
1. Grafana MCP tools: Search dashboards, check datasources, query Prometheus metrics, inspect Loki logs, analyze Tempo traces, create/manage incidents and annotations, list alerts, and manage on-call shifts.
2. Composio MCP tools: Connect and manage integrations (GitHub, Slack, Jira, Bash, Workbench, etc.), search tools, and execute workflows across platforms.
3. Microsoft SQL Server Database tools (wf database):
   - create_student: Insert/Create new student result record.
   - get_students_data: List, search, and filter student records (by branch, semester, CPI, name).
   - get_student_by_id: Fetch a single student record by primary ID.
   - update_student: Update existing student result fields.
   - delete_student: Delete student record by ID.
   - get_students_performance_summary: Statistical summary across all branches.
   - query_sql_server: Execute custom read-only SQL queries.

Rules:
- When a user asks a question or gives a command that requires external information or actions, pick and execute the most appropriate MCP tool.
- Inspect the tool response carefully before answering or taking the next step.
- If a tool requires arguments, supply them accurately based on the user's request and prior tool outputs.
- Synthesize all findings into a clean, concise, and structured markdown response.
"""

# Core essential tools to always prioritize if relevant
CORE_GRAFANA_TOOLS = {
    "list_datasources",
    "check_datasources_health",
    "get_datasource",
    "search_dashboards",
    "get_dashboard_summary",
    "list_alert_groups",
    "list_incidents",
    "query_prometheus",
    "query_loki_logs",
    "get_current_oncall_users",
}

CORE_COMPOSIO_TOOLS = {
    "COMPOSIO_SEARCH_TOOLS",
    "COMPOSIO_GET_TOOL_SCHEMAS",
    "COMPOSIO_MANAGE_CONNECTIONS",
    "COMPOSIO_MULTI_EXECUTE_TOOL",
    "COMPOSIO_REMOTE_BASH_TOOL",
    "COMPOSIO_REMOTE_WORKBENCH",
}

CORE_DB_TOOLS = {
    "create_student",
    "get_students_data",
    "get_student_by_id",
    "update_student",
    "delete_student",
    "get_students_performance_summary",
    "query_sql_server",
}


class GroqAgent:
    def __init__(self, client_manager: Optional[MCPClientManager] = None):
        self.settings = get_settings()
        self.mcp_client = client_manager or mcp_client_manager

    def _get_groq_client(self, custom_api_key: Optional[str] = None) -> AsyncGroq:
        api_key = custom_api_key or self.settings.GROQ_API_KEY
        if not api_key:
            raise ValueError(
                "GROQ_API_KEY is not configured. Please set GROQ_API_KEY in your .env file or pass X-Groq-API-Key header."
            )
        
        # Clean environment if a bad GROQ_BASE_URL was set
        if "GROQ_BASE_URL" in os.environ and "openai/v1" in os.environ["GROQ_BASE_URL"]:
            del os.environ["GROQ_BASE_URL"]

        if self.settings.GROQ_BASE_URL and "openai/v1" not in self.settings.GROQ_BASE_URL:
            return AsyncGroq(api_key=api_key, base_url=self.settings.GROQ_BASE_URL)
        return AsyncGroq(api_key=api_key)

    def _select_relevant_tools(
        self,
        all_tools: List[ToolDefinition],
        prompt: str,
        history: Optional[List[Dict[str, str]]] = None,
        max_tools: int = 18,
    ) -> List[ToolDefinition]:
        """
        Intelligently filter and rank tools based on keyword relevance to avoid exceeding LLM payload token limits.
        """
        if len(all_tools) <= max_tools:
            return all_tools

        # Extract tokens from prompt and history
        text_corpus = prompt.lower()
        if history:
            for h in history:
                text_corpus += " " + h.get("content", "").lower()

        keywords = set(re.findall(r"\b[a-z0-9_-]{3,}\b", text_corpus))

        scored_tools: List[tuple[int, ToolDefinition]] = []
        for tool in all_tools:
            score = 0
            name_lower = tool.name.lower()
            desc_lower = (tool.description or "").lower()

            # Boost core tools
            if tool.name in CORE_GRAFANA_TOOLS or tool.name in CORE_COMPOSIO_TOOLS or tool.name in CORE_DB_TOOLS:
                score += 3

            for kw in keywords:
                if kw in name_lower:
                    score += 8
                elif kw in desc_lower:
                    score += 3

            scored_tools.append((score, tool))

        # Sort by relevance score descending
        scored_tools.sort(key=lambda x: x[0], reverse=True)
        selected = [t for _, t in scored_tools[:max_tools]]
        return selected

    async def run(
        self,
        prompt: str,
        history: Optional[List[Dict[str, str]]] = None,
        provider_filter: Optional[str] = None,  # "grafana", "composio", or None (both)
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_steps: int = 8,
        custom_api_key: Optional[str] = None,
    ) -> AgentRunResult:
        """
        Execute an agentic reasoning and tool-calling loop using Groq LLM.
        """
        client = self._get_groq_client(custom_api_key)
        target_model = model or self.settings.GROQ_MODEL
        temp = temperature if temperature is not None else self.settings.GROQ_TEMPERATURE

        # 1. Fetch tools based on provider filter
        if provider_filter == "grafana":
            available_tools = await self.mcp_client.list_grafana_tools()
        elif provider_filter == "composio":
            available_tools = await self.mcp_client.list_composio_tools()
        else:
            available_tools = await self.mcp_client.get_all_tools()

        # 2. Select top relevant tools to stay well within Groq payload/TPM limits
        max_tools = self.settings.MAX_TOOLS_PER_REQUEST
        relevant_tools = self._select_relevant_tools(available_tools, prompt, history, max_tools=max_tools)
        openai_tools = [t.to_openai_tool() for t in relevant_tools] if relevant_tools else None

        # 3. Build message conversation
        messages: List[Dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}]

        if history:
            for msg in history:
                messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})

        messages.append({"role": "user", "content": prompt})

        steps: List[AgentStep] = []
        providers_used: Set[str] = set()
        iterations = 0
        total_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

        # 4. Agent reasoning loop
        for step_idx in range(1, max_steps + 1):
            iterations += 1
            try:
                kwargs: Dict[str, Any] = {
                    "model": target_model,
                    "messages": messages,
                    "temperature": temp,
                    "max_tokens": self.settings.GROQ_MAX_TOKENS,
                }
                if openai_tools:
                    kwargs["tools"] = openai_tools
                    kwargs["tool_choice"] = "auto"

                response = await client.chat.completions.create(**kwargs)
            except Exception as e:
                err_str = str(e)
                logger.warning(f"Error calling model '{target_model}': {err_str}")
                # Try fallback model if default model failed
                if target_model != self.settings.GROQ_FALLBACK_MODEL and (
                    "model_not_found" in err_str or "404" in err_str or "does not exist" in err_str
                ):
                    logger.info(f"Falling back to model: {self.settings.GROQ_FALLBACK_MODEL}")
                    target_model = self.settings.GROQ_FALLBACK_MODEL
                    kwargs["model"] = target_model
                    response = await client.chat.completions.create(**kwargs)
                else:
                    raise

            # Track token usage
            if hasattr(response, "usage") and response.usage:
                total_usage["prompt_tokens"] += getattr(response.usage, "prompt_tokens", 0)
                total_usage["completion_tokens"] += getattr(response.usage, "completion_tokens", 0)
                total_usage["total_tokens"] += getattr(response.usage, "total_tokens", 0)

            choice = response.choices[0]
            message = choice.message

            # Check if LLM requested tool execution
            if message.tool_calls:
                # Add assistant's tool-call message to history
                tool_calls_dict = []
                for tc in message.tool_calls:
                    tool_calls_dict.append({
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        }
                    })

                messages.append({
                    "role": "assistant",
                    "content": message.content or "",
                    "tool_calls": tool_calls_dict,
                })

                # Execute each requested tool call
                for tc in message.tool_calls:
                    tool_name = tc.function.name
                    try:
                        arguments = json.loads(tc.function.arguments) if tc.function.arguments else {}
                    except Exception:
                        arguments = {}

                    # Route tool execution
                    tool_def = self.mcp_client._tools_cache.get(tool_name)
                    provider = tool_def.provider if tool_def else ("grafana" if provider_filter == "grafana" else "composio")
                    providers_used.add(provider)

                    logger.info(f"[Step {step_idx}] Executing tool '{tool_name}' ({provider}) with args: {arguments}")
                    result = await self.mcp_client.call_tool(tool_name, arguments)

                    steps.append(
                        AgentStep(
                            step_number=step_idx,
                            tool_name=tool_name,
                            arguments=arguments,
                            output=result,
                            provider=provider,
                        )
                    )

                    # Format tool output for next LLM turn
                    output_str = json.dumps(result) if not isinstance(result, str) else result
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": output_str,
                    })

                # Continue to next iteration so LLM can synthesize or call further tools
                continue
            else:
                # LLM provided final answer
                final_text = message.content or "No response generated."
                return AgentRunResult(
                    response=final_text,
                    steps=steps,
                    model=target_model,
                    provider_used=list(providers_used),
                    iterations=iterations,
                    usage=total_usage,
                )

        # Reached max steps
        return AgentRunResult(
            response="Max reasoning steps reached. Partial output collected.",
            steps=steps,
            model=target_model,
            provider_used=list(providers_used),
            iterations=iterations,
            usage=total_usage,
        )


# Global agent instance
groq_agent = GroqAgent()
