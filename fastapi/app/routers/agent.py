import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field
from app.agent import groq_agent

logger = logging.getLogger("mcp_gateway.routers.agent")
router = APIRouter(prefix="/api/agent", tags=["Agent Chat"])


class Message(BaseModel):
    role: str = Field(...,
                      description="Role: 'user', 'assistant', or 'system'")
    content: str = Field(..., description="Message content")


class AgentChatRequest(BaseModel):
    prompt: str = Field(..., description="User prompt or instruction for the multi-tool agent",
                        examples=["Check Grafana datasource health and search GitHub tools on Composio"])
    provider: Optional[str] = Field(
        None, description="Optional provider filter: 'grafana', 'composio', or None for all tools")
    model: Optional[str] = Field(
        None, description="Groq model (default: llama-3.3-70b-versatile or llama-3.3-70b-versatile)")
    temperature: Optional[float] = Field(
        None, description="Sampling temperature (0.0 to 1.0)", ge=0.0, le=1.0)
    history: Optional[List[Message]] = Field(
        default=None, description="Previous conversation history")
    max_steps: Optional[int] = Field(
        default=8, description="Max autonomous tool reasoning iterations", ge=1, le=15)


class AgentChatResponse(BaseModel):
    success: bool
    response: str
    tool_steps: List[Dict[str, Any]]
    model_used: str
    providers_used: List[str]
    iterations: int
    usage: Dict[str, Any]


@router.post("/chat", response_model=AgentChatResponse, summary="Unified Multi-Tool Groq LLM Agent Chat")
async def chat_with_agent(
    payload: AgentChatRequest,
    x_groq_api_key: Optional[str] = Header(
        None, description="Optional Groq API key override"),
):
    """
    Unified agent chat endpoint that connects Groq LLM with tools from both Grafana and Composio MCP servers.
    The agent autonomously decides which tools from either provider to execute to answer the query.
    """
    try:
        history_dicts = [m.model_dump()
                         for m in payload.history] if payload.history else None
        result = await groq_agent.run(
            prompt=payload.prompt,
            history=history_dicts,
            provider_filter=payload.provider,
            model=payload.model,
            temperature=payload.temperature,
            max_steps=payload.max_steps or 8,
            custom_api_key=x_groq_api_key,
        )
        return AgentChatResponse(
            success=True,
            response=result.response,
            tool_steps=[s.to_dict() for s in result.steps],
            model_used=result.model,
            providers_used=result.provider_used,
            iterations=result.iterations,
            usage=result.usage,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Error during agent chat run")
        raise HTTPException(
            status_code=500, detail=f"Agent chat execution failed: {str(e)}")
