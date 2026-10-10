import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional
import httpx2
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from app.config import get_settings
from app.db import (
    create_student_record,
    fetch_students_data,
    fetch_student_by_id,
    update_student_record,
    delete_student_record,
    fetch_students_summary_stats,
    run_custom_sql_query,
)

logger = logging.getLogger("mcp_gateway.client")


class ToolDefinition:
    def __init__(
        self,
        name: str,
        description: str,
        input_schema: Dict[str, Any],
        provider: str,
    ):
        self.name = name
        self.description = description
        self.input_schema = input_schema
        self.provider = provider  # "grafana", "composio", or "database"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
            "provider": self.provider,
        }

    def to_openai_tool(self) -> Dict[str, Any]:
        """Convert to clean, optimized OpenAI / Groq tool calling format."""
        desc = (self.description or f"{self.provider} tool: {self.name}").strip()
        if len(desc) > 350:
            desc = desc[:347] + "..."

        params = self.input_schema if isinstance(self.input_schema, dict) else {"type": "object", "properties": {}}
        cleaned_params = {
            "type": params.get("type", "object"),
            "properties": params.get("properties", {}),
        }
        if "required" in params and params["required"]:
            cleaned_params["required"] = params["required"]

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": desc,
                "parameters": cleaned_params,
            },
        }


class MCPClientManager:
    def __init__(self):
        self.settings = get_settings()
        self._tools_cache: Dict[str, ToolDefinition] = {}
        self._grafana_tools: Dict[str, ToolDefinition] = {}
        self._composio_tools: Dict[str, ToolDefinition] = {}
        self._db_tools: Dict[str, ToolDefinition] = {}
        self._last_refresh: float = 0.0
        self._cache_ttl: float = 300.0  # 5 minutes
        self._init_db_tools()

    def _init_db_tools(self):
        """Register native Microsoft SQL Server database tools (4 CRUD + stats + sql)."""
        db_tools = [
            ToolDefinition(
                name="create_student",
                description="[1/4 CREATE] Insert a new student record into Microsoft SQL Server wf database (StudentsResult table).",
                input_schema={
                    "type": "object",
                    "required": ["student_name", "branch", "semester", "spi", "cpi", "exam_year"],
                    "properties": {
                        "student_name": {"type": "string", "description": "Full name of the student"},
                        "branch": {"type": "string", "description": "Branch code (e.g. 'CE', 'IT', 'EC', 'ME')"},
                        "semester": {"type": "integer", "description": "Semester number (1 to 8)"},
                        "spi": {"type": "number", "description": "Semester Performance Index (0.0 to 10.0)"},
                        "cpi": {"type": "number", "description": "Cumulative Performance Index (0.0 to 10.0)"},
                        "exam_year": {"type": "integer", "description": "Examination year (e.g. 2024)"},
                        "custom_id": {"type": "integer", "description": "Optional custom ID. Auto-increments if omitted."},
                    },
                },
                provider="database",
            ),
            ToolDefinition(
                name="get_students_data",
                description="[2/4 READ] Query and filter student exam results from Microsoft SQL Server wf database (StudentsResult table).",
                input_schema={
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer", "description": "Number of records to fetch (default 50)"},
                        "offset": {"type": "integer", "description": "Pagination offset (default 0)"},
                        "branch": {"type": "string", "description": "Branch filter (e.g. 'CE', 'IT', 'EC', 'ME')"},
                        "semester": {"type": "integer", "description": "Semester number (1 to 8)"},
                        "search": {"type": "string", "description": "Search by student name or branch"},
                        "min_cpi": {"type": "number", "description": "Filter by minimum CPI score (e.g. 8.5)"},
                    },
                },
                provider="database",
            ),
            ToolDefinition(
                name="get_student_by_id",
                description="[2/4 READ] Fetch a single student record by their primary ID from the wf database.",
                input_schema={
                    "type": "object",
                    "required": ["student_id"],
                    "properties": {
                        "student_id": {"type": "integer", "description": "Primary integer ID of the student"},
                    },
                },
                provider="database",
            ),
            ToolDefinition(
                name="update_student",
                description="[3/4 UPDATE] Update an existing student record in Microsoft SQL Server wf database (StudentsResult table).",
                input_schema={
                    "type": "object",
                    "required": ["student_id"],
                    "properties": {
                        "student_id": {"type": "integer", "description": "Primary integer ID of the student to update"},
                        "student_name": {"type": "string", "description": "Updated student name"},
                        "branch": {"type": "string", "description": "Updated branch (e.g. 'CE', 'IT', 'EC', 'ME')"},
                        "semester": {"type": "integer", "description": "Updated semester (1 to 8)"},
                        "spi": {"type": "number", "description": "Updated SPI score (0.0 to 10.0)"},
                        "cpi": {"type": "number", "description": "Updated CPI score (0.0 to 10.0)"},
                        "exam_year": {"type": "integer", "description": "Updated exam year (e.g. 2024)"},
                    },
                },
                provider="database",
            ),
            ToolDefinition(
                name="delete_student",
                description="[4/4 DELETE] Delete a student record from Microsoft SQL Server wf database (StudentsResult table) by ID.",
                input_schema={
                    "type": "object",
                    "required": ["student_id"],
                    "properties": {
                        "student_id": {"type": "integer", "description": "Primary integer ID of the student to delete"},
                    },
                },
                provider="database",
            ),
            ToolDefinition(
                name="get_students_performance_summary",
                description="Get statistical summary of student performance across all branches (average CPI, average SPI, top scores) from wf database.",
                input_schema={"type": "object", "properties": {}},
                provider="database",
            ),
            ToolDefinition(
                name="query_sql_server",
                description="Execute a custom read-only SELECT SQL query against the Microsoft SQL Server wf database.",
                input_schema={
                    "type": "object",
                    "required": ["sql_query"],
                    "properties": {
                        "sql_query": {"type": "string", "description": "SELECT SQL statement to execute"},
                    },
                },
                provider="database",
            ),
        ]
        for t in db_tools:
            self._db_tools[t.name] = t
            self._tools_cache[t.name] = t

    def _get_grafana_headers(self) -> Dict[str, str]:
        headers = {
            "Accept": "application/json, text/event-stream",
        }
        if self.settings.GRAFANA_AUTH_TOKEN:
            headers["Authorization"] = f"Bearer {self.settings.GRAFANA_AUTH_TOKEN}"
        return headers

    def _get_composio_headers(self) -> Dict[str, str]:
        headers = {
            "Accept": "application/json, text/event-stream",
        }
        if self.settings.COMPOSIO_API_KEY:
            headers["x-consumer-api-key"] = self.settings.COMPOSIO_API_KEY
        return headers

    async def list_db_tools(self) -> List[ToolDefinition]:
        """Return all native database MCP tools."""
        return list(self._db_tools.values())

    async def list_grafana_tools(self, force_refresh: bool = False) -> List[ToolDefinition]:
        """Fetch and return all tools from the Grafana MCP server."""
        if not force_refresh and self._grafana_tools and (time.time() - self._last_refresh < self._cache_ttl):
            return list(self._grafana_tools.values())

        url = self.settings.GRAFANA_MCP_URL
        headers = self._get_grafana_headers()
        tools_list: List[ToolDefinition] = []

        try:
            async with httpx2.AsyncClient(headers=headers, timeout=10.0) as http_client:
                async with streamable_http_client(url, http_client=http_client) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        result = await session.list_tools()
                        for t in result.tools:
                            tool_def = ToolDefinition(
                                name=t.name,
                                description=t.description or "",
                                input_schema=t.inputSchema if hasattr(t, "inputSchema") and t.inputSchema else {"type": "object", "properties": {}},
                                provider="grafana",
                            )
                            tools_list.append(tool_def)
                            self._grafana_tools[t.name] = tool_def
                            self._tools_cache[t.name] = tool_def
            logger.info(f"Loaded {len(tools_list)} tools from Grafana MCP ({url})")
        except Exception as e:
            logger.error(f"Failed to list tools from Grafana MCP ({url}): {e}")
            if not self._grafana_tools:
                raise RuntimeError(f"Grafana MCP server connection failed: {e}") from e

        return list(self._grafana_tools.values())

    async def list_composio_tools(self, force_refresh: bool = False) -> List[ToolDefinition]:
        """Fetch and return all tools from the Composio MCP server."""
        if not force_refresh and self._composio_tools and (time.time() - self._last_refresh < self._cache_ttl):
            return list(self._composio_tools.values())

        url = self.settings.COMPOSIO_MCP_URL
        headers = self._get_composio_headers()
        tools_list: List[ToolDefinition] = []

        try:
            async with httpx2.AsyncClient(headers=headers, timeout=15.0) as http_client:
                async with streamable_http_client(url, http_client=http_client) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        result = await session.list_tools()
                        for t in result.tools:
                            tool_def = ToolDefinition(
                                name=t.name,
                                description=t.description or "",
                                input_schema=t.inputSchema if hasattr(t, "inputSchema") and t.inputSchema else {"type": "object", "properties": {}},
                                provider="composio",
                            )
                            tools_list.append(tool_def)
                            self._composio_tools[t.name] = tool_def
                            self._tools_cache[t.name] = tool_def
            logger.info(f"Loaded {len(tools_list)} tools from Composio MCP ({url})")
        except Exception as e:
            logger.error(f"Failed to list tools from Composio MCP ({url}): {e}")
            if not self._composio_tools:
                raise RuntimeError(f"Composio MCP server connection failed: {e}") from e

        return list(self._composio_tools.values())

    async def get_all_tools(self, force_refresh: bool = False) -> List[ToolDefinition]:
        """Fetch all tools from Grafana, Composio, and SQL Server."""
        self._init_db_tools()
        if force_refresh or not self._tools_cache or (time.time() - self._last_refresh >= self._cache_ttl):
            results = await asyncio.gather(
                self.list_grafana_tools(force_refresh=True),
                self.list_composio_tools(force_refresh=True),
                return_exceptions=True,
            )
            for res in results:
                if isinstance(res, Exception):
                    logger.warning(f"Error refreshing MCP tools: {res}")
            self._last_refresh = time.time()

        return list(self._tools_cache.values())

    async def call_db_tool(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Any:
        """Call a native SQL Server database tool (4 CRUD operations + stats + custom SQL)."""
        arguments = arguments or {}
        try:
            if name == "create_student":
                return create_student_record(
                    student_name=arguments["student_name"],
                    branch=arguments["branch"],
                    semester=int(arguments["semester"]),
                    spi=float(arguments["spi"]),
                    cpi=float(arguments["cpi"]),
                    exam_year=int(arguments["exam_year"]),
                    custom_id=arguments.get("custom_id"),
                )
            elif name in ["get_students_data", "get_students", "list_students"]:
                return fetch_students_data(
                    limit=arguments.get("limit", 50),
                    offset=arguments.get("offset", 0),
                    branch=arguments.get("branch"),
                    semester=arguments.get("semester"),
                    search=arguments.get("search"),
                    min_cpi=arguments.get("min_cpi"),
                )
            elif name == "get_student_by_id":
                student_id = int(arguments["student_id"])
                res = fetch_student_by_id(student_id)
                if not res:
                    return {"success": False, "error": f"Student with ID {student_id} not found"}
                return {"success": True, "student": res}
            elif name == "update_student":
                return update_student_record(
                    student_id=int(arguments["student_id"]),
                    student_name=arguments.get("student_name"),
                    branch=arguments.get("branch"),
                    semester=int(arguments["semester"]) if arguments.get("semester") is not None else None,
                    spi=float(arguments["spi"]) if arguments.get("spi") is not None else None,
                    cpi=float(arguments["cpi"]) if arguments.get("cpi") is not None else None,
                    exam_year=int(arguments["exam_year"]) if arguments.get("exam_year") is not None else None,
                )
            elif name == "delete_student":
                return delete_student_record(student_id=int(arguments["student_id"]))
            elif name == "get_students_performance_summary":
                return fetch_students_summary_stats()
            elif name == "query_sql_server":
                return run_custom_sql_query(arguments.get("sql_query", ""))
            else:
                return {"error": f"Unknown database tool '{name}'", "success": False}
        except Exception as e:
            logger.error(f"Error executing database tool '{name}': {e}")
            return {"error": str(e), "tool": name, "provider": "database", "success": False}

    async def call_grafana_tool(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Any:
        """Call a specific tool on the Grafana MCP server."""
        url = self.settings.GRAFANA_MCP_URL
        headers = self._get_grafana_headers()
        arguments = arguments or {}

        try:
            async with httpx2.AsyncClient(headers=headers, timeout=30.0) as http_client:
                async with streamable_http_client(url, http_client=http_client) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        result = await session.call_tool(name, arguments)
                        return self._format_call_result(result)
        except Exception as e:
            logger.error(f"Error calling Grafana tool '{name}': {e}")
            return {"error": str(e), "tool": name, "provider": "grafana", "success": False}

    async def call_composio_tool(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Any:
        """Call a specific tool on the Composio MCP server."""
        url = self.settings.COMPOSIO_MCP_URL
        headers = self._get_composio_headers()
        arguments = arguments or {}

        try:
            async with httpx2.AsyncClient(headers=headers, timeout=45.0) as http_client:
                async with streamable_http_client(url, http_client=http_client) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        result = await session.call_tool(name, arguments)
                        return self._format_call_result(result)
        except Exception as e:
            logger.error(f"Error calling Composio tool '{name}': {e}")
            return {"error": str(e), "tool": name, "provider": "composio", "success": False}

    async def call_tool(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Any:
        """Route tool call automatically based on tool provider."""
        if not self._tools_cache:
            await self.get_all_tools()

        tool_def = self._tools_cache.get(name)
        if tool_def:
            if tool_def.provider == "database":
                return await self.call_db_tool(name, arguments)
            elif tool_def.provider == "grafana":
                return await self.call_grafana_tool(name, arguments)
            elif tool_def.provider == "composio":
                return await self.call_composio_tool(name, arguments)

        if name in self._db_tools or "student" in name.lower() or "sql" in name.lower():
            return await self.call_db_tool(name, arguments)
        elif name.startswith("COMPOSIO_") or name.startswith("github_"):
            return await self.call_composio_tool(name, arguments)
        else:
            return await self.call_grafana_tool(name, arguments)

    def _format_call_result(self, result: Any) -> Any:
        """Helper to extract formatted JSON/string from MCP tool call result."""
        if hasattr(result, "content") and result.content:
            contents = []
            for item in result.content:
                if hasattr(item, "text"):
                    text_val = item.text
                    try:
                        parsed = json.loads(text_val)
                        contents.append(parsed)
                    except Exception:
                        contents.append(text_val)
                else:
                    contents.append(str(item))
            if len(contents) == 1:
                return contents[0]
            return contents
        return result

    async def check_health(self) -> Dict[str, Any]:
        """Test connections to MCP servers & SQL Server and return status."""
        health = {
            "grafana": {"status": "unknown", "url": self.settings.GRAFANA_MCP_URL, "tools_count": 0, "error": None},
            "composio": {"status": "unknown", "url": self.settings.COMPOSIO_MCP_URL, "tools_count": 0, "error": None},
            "sql_server": {"status": "unknown", "database": self.settings.SQL_SERVER_DATABASE, "table": "StudentsResult", "error": None},
        }

        # Check Grafana
        t0 = time.time()
        try:
            grafana_tools = await self.list_grafana_tools(force_refresh=True)
            health["grafana"]["status"] = "online"
            health["grafana"]["tools_count"] = len(grafana_tools)
            health["grafana"]["latency_ms"] = round((time.time() - t0) * 1000, 2)
        except Exception as e:
            health["grafana"]["status"] = "offline"
            health["grafana"]["error"] = str(e)

        # Check Composio
        t0 = time.time()
        try:
            composio_tools = await self.list_composio_tools(force_refresh=True)
            health["composio"]["status"] = "online"
            health["composio"]["tools_count"] = len(composio_tools)
            health["composio"]["latency_ms"] = round((time.time() - t0) * 1000, 2)
        except Exception as e:
            health["composio"]["status"] = "offline"
            health["composio"]["error"] = str(e)

        # Check SQL Server
        t0 = time.time()
        try:
            res = fetch_students_data(limit=1)
            health["sql_server"]["status"] = "online"
            health["sql_server"]["records_count"] = res["total"]
            health["sql_server"]["latency_ms"] = round((time.time() - t0) * 1000, 2)
        except Exception as e:
            health["sql_server"]["status"] = "offline"
            health["sql_server"]["error"] = str(e)

        return health


# Global singleton instance
mcp_client_manager = MCPClientManager()
