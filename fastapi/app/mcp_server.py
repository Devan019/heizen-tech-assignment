import logging
from typing import Any, Dict, Optional
from mcp.server.mcpserver import MCPServer
from app.config import get_settings
from app.mcp_client import mcp_client_manager
from app.agent import groq_agent
from app.db import (
    create_student_record,
    fetch_students_data,
    fetch_student_by_id,
    update_student_record,
    delete_student_record,
    fetch_students_summary_stats,
    run_custom_sql_query,
)

logger = logging.getLogger("mcp_gateway.server")

settings = get_settings()

# Initialize our own MCP Server
gateway_mcp_server = MCPServer(
    name="FastAPI-Groq-MCP-Gateway",
    version=settings.APP_VERSION,
    instructions="Gateway MCP server aggregating Grafana, Composio, and SQL Server wf database tools with Groq LLM reasoning agent.",
)


@gateway_mcp_server.tool()
async def run_groq_agent(prompt: str, provider: Optional[str] = None, model: Optional[str] = None) -> str:
    """Run an autonomous Groq LLM agent with access to Grafana, Composio, and Database MCP tools.
    
    Args:
        prompt: The task or query to solve using available MCP tools.
        provider: Optional filter to restrict tools to 'grafana', 'composio', or 'db'.
        model: Optional model name override.
    """
    try:
        result = await groq_agent.run(prompt=prompt, provider_filter=provider, model=model)
        steps_summary = f"\n\n[Executed {len(result.steps)} tool steps using model {result.model}]"
        return result.response + steps_summary
    except Exception as e:
        return f"Agent error: {str(e)}"


@gateway_mcp_server.tool()
async def execute_grafana_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Directly execute a Grafana MCP tool (e.g. list_datasources, search_dashboards, query_prometheus).
    
    Args:
        tool_name: The name of the Grafana tool to call.
        arguments: The arguments dictionary for the tool.
    """
    return await mcp_client_manager.call_grafana_tool(tool_name, arguments)


@gateway_mcp_server.tool()
async def execute_composio_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Directly execute a Composio MCP tool (e.g. COMPOSIO_SEARCH_TOOLS, COMPOSIO_MANAGE_CONNECTIONS).
    
    Args:
        tool_name: The name of the Composio tool to call.
        arguments: The arguments dictionary for the tool.
    """
    return await mcp_client_manager.call_composio_tool(tool_name, arguments)


# ==============================================================================
# 4 CRUD MCP TOOLS FOR STUDENTS (wf database -> StudentsResult table)
# ==============================================================================


@gateway_mcp_server.tool()
async def create_student(
    student_name: str,
    branch: str,
    semester: int,
    spi: float,
    cpi: float,
    exam_year: int,
    custom_id: Optional[int] = None,
) -> Dict[str, Any]:
    """[1/4 CREATE] Insert a new student record into Microsoft SQL Server (wf database -> StudentsResult table).
    
    Args:
        student_name: Full name of the student.
        branch: Engineering branch (e.g. 'CE', 'IT', 'EC', 'ME').
        semester: Current semester (1 to 8).
        spi: Semester Performance Index (0.0 to 10.0).
        cpi: Cumulative Performance Index (0.0 to 10.0).
        exam_year: Year of examination (e.g. 2024).
        custom_id: Optional custom ID. If omitted, auto-generates MAX(id) + 1.
    """
    return create_student_record(
        student_name=student_name,
        branch=branch,
        semester=semester,
        spi=spi,
        cpi=cpi,
        exam_year=exam_year,
        custom_id=custom_id,
    )


@gateway_mcp_server.tool()
async def get_students_data(
    limit: int = 50,
    offset: int = 0,
    branch: Optional[str] = None,
    semester: Optional[int] = None,
    search: Optional[str] = None,
    min_cpi: Optional[float] = None,
) -> Dict[str, Any]:
    """[2/4 READ] Query and filter student examination results from Microsoft SQL Server (wf database -> StudentsResult table).
    
    Args:
        limit: Max number of records to return (default 50).
        offset: Pagination offset (default 0).
        branch: Filter by engineering branch (e.g. 'CE', 'IT', 'EC', 'ME').
        semester: Filter by semester number (1 to 8).
        search: Search query for student name or branch.
        min_cpi: Filter for students with CPI greater than or equal to this value (e.g. 8.5).
    """
    return fetch_students_data(
        limit=limit,
        offset=offset,
        branch=branch,
        semester=semester,
        search=search,
        min_cpi=min_cpi,
    )


@gateway_mcp_server.tool()
async def get_student_by_id(student_id: int) -> Dict[str, Any]:
    """[2/4 READ] Fetch a single student record by their primary ID from the wf database.
    
    Args:
        student_id: Primary integer ID of the student.
    """
    student = fetch_student_by_id(student_id)
    if not student:
        return {"success": False, "error": f"Student with ID {student_id} not found"}
    return {"success": True, "student": student}


@gateway_mcp_server.tool()
async def update_student(
    student_id: int,
    student_name: Optional[str] = None,
    branch: Optional[str] = None,
    semester: Optional[int] = None,
    spi: Optional[float] = None,
    cpi: Optional[float] = None,
    exam_year: Optional[int] = None,
) -> Dict[str, Any]:
    """[3/4 UPDATE] Update an existing student record in Microsoft SQL Server (wf database -> StudentsResult table).
    
    Args:
        student_id: Primary integer ID of the student to update.
        student_name: Updated student name.
        branch: Updated branch (e.g. 'CE', 'IT', 'EC', 'ME').
        semester: Updated semester (1 to 8).
        spi: Updated SPI score (0.0 to 10.0).
        cpi: Updated CPI score (0.0 to 10.0).
        exam_year: Updated exam year (e.g. 2024).
    """
    return update_student_record(
        student_id=student_id,
        student_name=student_name,
        branch=branch,
        semester=semester,
        spi=spi,
        cpi=cpi,
        exam_year=exam_year,
    )


@gateway_mcp_server.tool()
async def delete_student(student_id: int) -> Dict[str, Any]:
    """[4/4 DELETE] Delete a student record from Microsoft SQL Server (wf database -> StudentsResult table).
    
    Args:
        student_id: Primary integer ID of the student to delete.
    """
    return delete_student_record(student_id)


@gateway_mcp_server.tool()
async def get_students_performance_summary() -> Dict[str, Any]:
    """Get statistical aggregate performance summary of all students by branch from the wf database."""
    return fetch_students_summary_stats()


@gateway_mcp_server.tool()
async def query_sql_server(sql_query: str) -> Dict[str, Any]:
    """Execute a read-only SELECT SQL query directly against the Microsoft SQL Server wf database.
    
    Args:
        sql_query: The SELECT SQL statement to execute.
    """
    return run_custom_sql_query(sql_query)


@gateway_mcp_server.tool()
async def list_available_mcp_tools(provider: Optional[str] = None) -> Dict[str, Any]:
    """List all available tools from Grafana, Composio, and Database MCP servers.
    
    Args:
        provider: Optional filter for 'grafana', 'composio', or 'db'.
    """
    if provider == "grafana":
        tools = await mcp_client_manager.list_grafana_tools()
    elif provider == "composio":
        tools = await mcp_client_manager.list_composio_tools()
    else:
        tools = await mcp_client_manager.get_all_tools()
    
    return {
        "count": len(tools),
        "tools": [{"name": t.name, "description": t.description, "provider": t.provider} for t in tools],
    }
