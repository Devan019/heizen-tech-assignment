import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from app.config import get_settings
from app.mcp_client import mcp_client_manager
from app.mcp_server import gateway_mcp_server
from app.routers import grafana, composio, agent, tools, health, students
from app.ui import get_dashboard_html

# Setup structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("mcp_gateway")

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup & shutdown events."""
    logger.info("⚡ Starting FastAPI MCP Gateway & Groq Agent...")
    logger.info(
        f"Target Groq Model: {settings.GROQ_MODEL} (Fallback: {settings.GROQ_FALLBACK_MODEL})")
    logger.info(f"Grafana MCP Endpoint: {settings.GRAFANA_MCP_URL}")
    logger.info(f"Composio MCP Endpoint: {settings.COMPOSIO_MCP_URL}")
    logger.info(f"SQL Server Database: {settings.SQL_SERVER_HOST} / {settings.SQL_SERVER_DATABASE}")

    # Asynchronously pre-fetch tool schemas from upstream MCP servers in the background
    asyncio.create_task(mcp_client_manager.get_all_tools(force_refresh=True))

    yield

    logger.info("🛑 Shutting down FastAPI MCP Gateway...")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
# FastAPI MCP Gateway & Groq Agent

This unified server acts as:
1. **An MCP Aggregator**: Dynamically discovers and proxies tools from **Grafana**, **Composio**, and native **SQL Server database (wf)**.
2. **A Groq LLM Agent**: Equips Groq LLM models (`openai/gpt-oss-20b`, etc.) with full autonomous tool-calling loops.
3. **An MCP Server Endpoint**: Exposes standard SSE transport at `/mcp` for Claude Desktop, Antigravity IDE, Cursor, etc.
4. **Specialized FastAPI Endpoints**:
   - `GET /api/db/students`: Direct SQL Server query for student exam data.
   - `GET /api/db/students/stats/summary`: Aggregate analytics across engineering branches.
   - `POST /api/db/query`: Custom read-only SQL query runner.
   - `POST /api/grafana/run` & `POST /api/grafana/call`: Dedicated Grafana agent and direct tool caller.
   - `POST /api/composio/run` & `POST /api/composio/call`: Dedicated Composio agent and direct tool caller.
   - `POST /api/agent/chat`: Unified multi-tool agent (Grafana + Composio + SQL Server DB).
   - `GET /api/tools`: Catalog of all discovered tools.
   - `GET /api/health`: Health & status check.
    """,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware for Next.js frontend or external integrations
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(grafana.router)
app.include_router(composio.router)
app.include_router(agent.router)
app.include_router(tools.router)
app.include_router(health.router)
app.include_router(students.router)

# Mount our own MCP Server SSE transport at /mcp
try:
    app.mount("/mcp", gateway_mcp_server.sse_app())
    logger.info("Mounted MCP Server SSE application at /mcp")
except Exception as e:
    logger.warning(f"Could not mount MCP SSE app: {e}")


@app.get("/", summary="Dashboard UI & Interactive Playground", include_in_schema=False)
async def root_dashboard():
    """Interactive Web UI Dashboard & Testing Playground."""
    return get_dashboard_html()


def start():
    """Entry point for uv run or poetry."""
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )


if __name__ == "__main__":
    start()
