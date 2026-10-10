# FastAPI MCP Gateway & Groq Agent (`llama-3.3-70b-versatile`)

A unified, production-ready FastAPI backend that connects to upstream MCP servers (**Grafana** and **Composio**), aggregates all 90+ MCP tools, equips **Groq LLM** (`llama-3.3-70b-versatile` or `llama-3.3-70b-versatile`) with an autonomous tool-calling loop, and exposes specialized endpoints as well as its own Model Context Protocol (MCP) server.

---

## 🌟 Architecture Overview

```
                                  ┌────────────────────────┐
                                  │   Groq LLM Engine      │
                                  │ (llama-3.3-70b-versatile)   │
                                  └──────────▲─────────────┘
                                             │ Tool Calling Loop
                                             │
┌──────────────────────────────┐  ┌──────────▼─────────────┐  ┌──────────────────────────────────┐
│ Upstream MCP: Grafana        │◄─┤  FastAPI MCP Gateway   ├─►│ Upstream MCP: Composio           │
│ http://localhost:8000/mcp    │  │  (Port 8080)           │  │ https://connect.composio.dev/mcp │
│ (79 Observability Tools)     │  │                        │  │ (11 Integration Tools)           │
└──────────────────────────────┘  └──────────▲─────────────┘  └──────────────────────────────────┘
                                             │
                       ┌─────────────────────┴─────────────────────┐
                       │                                           │
         ┌─────────────▼─────────────┐               ┌─────────────▼─────────────┐
         │ Specialized REST API      │               │ Own MCP Server Transport  │
         │ - /api/grafana/run        │               │ - SSE Transport at /mcp   │
         │ - /api/composio/run       │               │ - Accessible by IDEs &    │
         │ - /api/agent/chat         │               │   External MCP Clients    │
         │ - /api/tools/call         │               └───────────────────────────┘
         └───────────────────────────┘
```

---

## 🚀 Quick Start

### 1. Configure Environment (`.env`)
Create/edit `.env` in the `fastapi/` folder:

```ini
# Server Settings
HOST=0.0.0.0
PORT=8080
DEBUG=True

# Groq LLM Settings (Get key at: https://console.groq.com/keys)
GROQ_API_KEY=gsk_your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile
GROQ_FALLBACK_MODEL=llama-3.3-70b-versatile

# Upstream MCP Server 1: Grafana
GRAFANA_MCP_URL=http://localhost:8000/mcp
GRAFANA_AUTH_TOKEN=c825acaf3b7b9921d198b704c5cdce4767cd4edf19ac72cbf72c87948249633a

# Upstream MCP Server 2: Composio
COMPOSIO_MCP_URL=https://connect.composio.dev/mcp
COMPOSIO_API_KEY=ck_JD6-Z3lzXNfA49i2NdE3
```

### 2. Start the Server
```bash
uv run python main.py
```
*Or using uvicorn:*
```bash
uv run uvicorn main:app --host 0.0.0.0 --port 8080 --reload
```

### 3. Open the Interactive Dashboard & API Docs
- **Interactive UI Dashboard**: [http://localhost:8080/](http://localhost:8080/)
- **Interactive Swagger Docs**: [http://localhost:8080/docs](http://localhost:8080/docs)
- **ReDoc API Reference**: [http://localhost:8080/redoc](http://localhost:8080/redoc)

---

## 📡 API Endpoints

### 1. SQL Server Database Endpoints (`/api/db`)

Connects to Microsoft SQL Server (`DEVAN` -> `wf` database -> `StudentsResult` table).

#### `GET /api/db/students`
Retrieves student examination records with filtering and pagination.
```bash
# Query students in Computer Engineering (CE)
curl http://localhost:8080/api/db/students?branch=CE&min_cpi=8.5&limit=10
```

#### `GET /api/db/students/stats/summary`
Calculates overall and branch-wise performance statistics.
```bash
curl http://localhost:8080/api/db/students/stats/summary
```

#### `POST /api/db/query`
Executes a read-only SELECT SQL statement.
```bash
curl -X POST http://localhost:8080/api/db/query \
  -H "Content-Type: application/json" \
  -d '{"query": "SELECT TOP 5 student_name, branch, cpi FROM StudentsResult ORDER BY cpi DESC"}'
```

---

### 2. Grafana Endpoints (`/api/grafana`)

#### `POST /api/grafana/run`
Runs the Groq LLM agent with access to Grafana MCP tools.

**Request:**
```bash
curl -X POST http://localhost:8080/api/grafana/run \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "List all configured datasources in Grafana and check if they are healthy",
    "model": "llama-3.3-70b-versatile"
  }'
```

**Response:**
```json
{
  "success": true,
  "response": "Here are the configured datasources in your Grafana instance:\n1. **PostgreSQL** (UID: `dg0t47ezkwqv4f`, Default: True)\n2. **MSSQL** (UID: `fg0t7704az280f`)\n3. **MySQL** (UID: `fg0t75iqdlkhsf`)",
  "tool_steps": [
    {
      "step": 1,
      "tool_name": "list_datasources",
      "arguments": {},
      "provider": "grafana",
      "output": { "datasources": [...], "total": 3 }
    }
  ],
  "model_used": "llama-3.3-70b-versatile",
  "iterations": 1,
  "usage": { "total_tokens": 420 }
}
```

#### `POST /api/grafana/call`
Directly calls any Grafana tool without the LLM.
```bash
curl -X POST http://localhost:8080/api/grafana/call \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "list_datasources",
    "arguments": {}
  }'
```

#### `GET /api/grafana/tools`
Lists all 79 Grafana MCP tools with JSON schemas.

---

### 2. Composio Endpoints (`/api/composio`)

#### `POST /api/composio/run`
Runs the Groq LLM agent with access to Composio MCP tools.

**Request:**
```bash
curl -X POST http://localhost:8080/api/composio/run \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Search available GitHub integration tools on Composio",
    "model": "llama-3.3-70b-versatile"
  }'
```

#### `POST /api/composio/call`
Directly calls any Composio tool without the LLM.
```bash
curl -X POST http://localhost:8080/api/composio/call \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "COMPOSIO_SEARCH_TOOLS",
    "arguments": { "query": "github" }
  }'
```

#### `GET /api/composio/tools`
Lists all Composio MCP tools with JSON schemas.

---

### 3. Unified Agent & Tools Endpoints

#### `POST /api/agent/chat`
Dual-provider agent that can reason and execute across **both** Grafana and Composio tools in one conversation.
```bash
curl -X POST http://localhost:8080/api/agent/chat \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Check the health of my Grafana datasources and search if there are GitHub action tools on Composio to trigger an alert issue",
    "model": "llama-3.3-70b-versatile"
  }'
```

#### `GET /api/tools`
Returns the complete catalog of all 90+ tools across both MCP servers.

#### `POST /api/tools/call`
Universal executor that auto-detects whether the tool belongs to Grafana or Composio.
```bash
curl -X POST http://localhost:8080/api/tools/call \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "list_datasources",
    "arguments": {}
  }'
```

#### `GET /api/health`
Real-time health check for upstream Grafana, Composio, and Groq LLM.

---

## 🔌 Connecting as an MCP Server (e.g. IDE / Claude Desktop)

To use this FastAPI instance as an MCP server in Claude Desktop or Antigravity IDE, add the following to your MCP configuration (`mcp_config.json`):

```json
{
  "mcpServers": {
    "fastapi-groq-gateway": {
      "serverUrl": "http://localhost:8080/mcp"
    }
  }
}
```

---

## 📁 Project Structure

```
c:\mcp-op\fastapi\
├── app/
│   ├── __init__.py
│   ├── config.py             # Pydantic settings & env management
│   ├── mcp_client.py         # Upstream MCP client manager (Grafana & Composio)
│   ├── mcp_server.py         # Own MCPServer instance exposing tools over SSE
│   ├── agent.py              # Autonomous Groq LLM reasoning & tool-calling loop
│   ├── ui.py                 # Interactive Web UI dashboard & playground
│   └── routers/
│       ├── __init__.py
│       ├── grafana.py        # /api/grafana/run, /api/grafana/call, /api/grafana/tools
│       ├── composio.py       # /api/composio/run, /api/composio/call, /api/composio/tools
│       ├── agent.py          # /api/agent/chat
│       ├── tools.py          # /api/tools, /api/tools/call, /api/tools/refresh
│       └── health.py         # /api/health
├── .env                      # Local environment configuration
├── .env.example              # Template for environment settings
├── main.py                   # FastAPI application entrypoint
├── pyproject.toml            # Dependencies and metadata
└── README.md                 # Full documentation
```
