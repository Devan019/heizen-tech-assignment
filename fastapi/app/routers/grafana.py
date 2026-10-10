import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field
from app.mcp_client import mcp_client_manager
from app.agent import groq_agent

logger = logging.getLogger("mcp_gateway.routers.grafana")
router = APIRouter(prefix="/api/grafana", tags=["Grafana MCP"])


class Message(BaseModel):
    role: str = Field(...,
                      description="Role: 'user', 'assistant', or 'system'")
    content: str = Field(..., description="Message content")


class GrafanaRunRequest(BaseModel):
    prompt: str = Field(..., description="Task or prompt to solve using Grafana MCP tools", examples=[
                        "List all configured datasources in Grafana"])
    model: Optional[str] = Field(
        None, description="Groq model (default: llama-3.3-70b-versatile or llama-3.3-70b-versatile)")
    temperature: Optional[float] = Field(
        None, description="Sampling temperature (0.0 to 1.0)", ge=0.0, le=1.0)
    history: Optional[List[Message]] = Field(
        default=None, description="Previous conversation history")
    max_steps: Optional[int] = Field(
        default=8, description="Max autonomous tool reasoning iterations", ge=1, le=15)


class GrafanaToolCallRequest(BaseModel):
    tool_name: str = Field(..., description="Exact name of the Grafana tool to call", examples=[
                           "list_datasources", "search_dashboards"])
    arguments: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Input arguments for the tool")


class GrafanaRunResponse(BaseModel):
    success: bool
    response: str
    tool_steps: List[Dict[str, Any]]
    model_used: str
    iterations: int
    usage: Dict[str, Any]


class ToolDetail(BaseModel):
    name: str
    description: str
    provider: str
    inputSchema: Dict[str, Any]


class GrafanaToolsListResponse(BaseModel):
    success: bool
    count: int
    provider: str
    tools: List[ToolDetail]


@router.post("/run", response_model=GrafanaRunResponse, summary="Execute Groq Agent with Grafana MCP Tools")
async def run_grafana_agent(
    payload: GrafanaRunRequest,
    x_groq_api_key: Optional[str] = Header(
        None, description="Optional Groq API key override"),
):
    """
    Exposes a specialized endpoint to query Grafana using the Groq LLM agent with Grafana MCP tools.

    The agent autonomously selects and executes appropriate Grafana tools (e.g. `list_datasources`,
    `search_dashboards`, `query_prometheus`, `list_incidents`, `get_annotations`, etc.)
    and returns synthesized answers and step-by-step tool results.
    """
    try:
        history_dicts = [m.model_dump()
                         for m in payload.history] if payload.history else None
        result = await groq_agent.run(
            prompt=payload.prompt,
            history=history_dicts,
            provider_filter="grafana",
            model=payload.model,
            temperature=payload.temperature,
            max_steps=payload.max_steps or 8,
            custom_api_key=x_groq_api_key,
        )
        return GrafanaRunResponse(
            success=True,
            response=result.response,
            tool_steps=[s.to_dict() for s in result.steps],
            model_used=result.model,
            iterations=result.iterations,
            usage=result.usage,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Error during Grafana agent run")
        raise HTTPException(
            status_code=500, detail=f"Grafana agent execution failed: {str(e)}")


@router.post("/call", summary="Directly Execute a Grafana MCP Tool")
async def call_grafana_tool_direct(payload: GrafanaToolCallRequest):
    """
    Directly execute any tool on the Grafana MCP server without LLM intervention.
    """
    try:
        result = await mcp_client_manager.call_grafana_tool(payload.tool_name, payload.arguments)
        return {
            "success": True,
            "tool_name": payload.tool_name,
            "provider": "grafana",
            "result": result,
        }
    except Exception as e:
        logger.exception(f"Error calling Grafana tool {payload.tool_name}")
        raise HTTPException(
            status_code=500, detail=f"Tool call failed: {str(e)}")


@router.get("/tools", response_model=GrafanaToolsListResponse, summary="List all Grafana MCP Tools")
async def list_grafana_tools():
    """
    Returns all tools available from the connected Grafana MCP server with their input schemas.
    """
    try:
        tools = await mcp_client_manager.list_grafana_tools()
        return GrafanaToolsListResponse(
            success=True,
            count=len(tools),
            provider="grafana",
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
        raise HTTPException(
            status_code=500, detail=f"Failed to list Grafana tools: {str(e)}")
