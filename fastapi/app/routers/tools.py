import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from app.mcp_client import mcp_client_manager

logger = logging.getLogger("mcp_gateway.routers.tools")
router = APIRouter(prefix="/api/tools", tags=["MCP Tools"])


class UniversalToolCallRequest(BaseModel):
    tool_name: str = Field(..., description="Name of the tool to execute from Grafana or Composio", examples=["list_datasources", "COMPOSIO_SEARCH_TOOLS"])
    arguments: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Input arguments for the tool")


class ToolDetail(BaseModel):
    name: str
    description: str
    provider: str
    inputSchema: Dict[str, Any]


class AllToolsResponse(BaseModel):
    success: bool
    total_count: int
    grafana_count: int
    composio_count: int
    tools: List[ToolDetail]


@router.get("", response_model=AllToolsResponse, summary="List All Discovered MCP Tools")
async def list_all_tools(
    provider: Optional[str] = Query(None, description="Filter by provider: 'grafana' or 'composio'"),
    force_refresh: bool = Query(False, description="Force refresh from upstream MCP servers"),
):
    """
    Returns all tools aggregated across both Grafana and Composio MCP servers.
    """
    try:
        if provider == "grafana":
            tools = await mcp_client_manager.list_grafana_tools(force_refresh=force_refresh)
        elif provider == "composio":
            tools = await mcp_client_manager.list_composio_tools(force_refresh=force_refresh)
        else:
            tools = await mcp_client_manager.get_all_tools(force_refresh=force_refresh)

        all_tools = await mcp_client_manager.get_all_tools()
        grafana_count = len([t for t in all_tools if t.provider == "grafana"])
        composio_count = len([t for t in all_tools if t.provider == "composio"])

        return AllToolsResponse(
            success=True,
            total_count=len(tools),
            grafana_count=grafana_count,
            composio_count=composio_count,
            tools=[
                ToolDetail(
                    name=t.name,
                    description=t.description,
                    provider=t.provider,
                    inputSchema=t.input_schema,
                )
                for t in tools
            ],
        )
    except Exception as e:
        logger.exception("Failed to fetch tools")
        raise HTTPException(status_code=500, detail=f"Failed to fetch tools: {str(e)}")


@router.post("/call", summary="Universally Call Any MCP Tool")
async def universal_tool_call(payload: UniversalToolCallRequest):
    """
    Directly execute any tool by name. The gateway automatically resolves the provider (Grafana or Composio)
    and executes the tool over the appropriate MCP transport.
    """
    try:
        result = await mcp_client_manager.call_tool(payload.tool_name, payload.arguments)
        return {
            "success": True,
            "tool_name": payload.tool_name,
            "result": result,
        }
    except Exception as e:
        logger.exception(f"Universal call failed for {payload.tool_name}")
        raise HTTPException(status_code=500, detail=f"Tool call failed: {str(e)}")


@router.post("/refresh", summary="Force Refresh MCP Tool Schemas")
async def refresh_tool_schemas():
    """
    Forces an immediate cache refresh of all tool schemas from both upstream MCP servers.
    """
    try:
        tools = await mcp_client_manager.get_all_tools(force_refresh=True)
        return {
            "success": True,
            "message": "Tool schemas refreshed successfully",
            "total_tools": len(tools),
            "grafana_tools": len([t for t in tools if t.provider == "grafana"]),
            "composio_tools": len([t for t in tools if t.provider == "composio"]),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Refresh failed: {str(e)}")
