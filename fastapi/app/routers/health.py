import logging
from fastapi import APIRouter
from app.config import get_settings
from app.mcp_client import mcp_client_manager

logger = logging.getLogger("mcp_gateway.routers.health")
router = APIRouter(prefix="/api/health", tags=["Health & Status"])


@router.get("", summary="System & Upstream Health Check")
async def health_check():
    """
    Check connectivity to upstream MCP servers (Grafana & Composio) and Groq LLM configuration.
    """
    settings = get_settings()
    mcp_health = await mcp_client_manager.check_health()

    groq_configured = bool(settings.GROQ_API_KEY)

    return {
        "status": "healthy" if (mcp_health["grafana"]["status"] == "online" or mcp_health["composio"]["status"] == "online") else "degraded",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "groq": {
            "configured": groq_configured,
            "model": settings.GROQ_MODEL,
            "fallback_model": settings.GROQ_FALLBACK_MODEL,
        },
        "mcp_servers": mcp_health,
    }
