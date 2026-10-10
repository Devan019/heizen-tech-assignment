from fastapi.responses import HTMLResponse

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FastAPI MCP Server & Groq Agent Gateway</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg: #090d16;
            --card-bg: rgba(21, 28, 44, 0.7);
            --card-border: rgba(255, 255, 255, 0.08);
            --card-hover: rgba(30, 41, 65, 0.85);
            --primary: #f97316;
            --primary-glow: rgba(249, 115, 22, 0.25);
            --accent-grafana: #f59e0b;
            --accent-composio: #8b5cf6;
            --accent-groq: #f43f5e;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --success: #10b981;
            --success-glow: rgba(16, 185, 129, 0.2);
            --radius-lg: 16px;
            --radius-md: 10px;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: 'Plus Jakarta Sans', sans-serif;
            background-color: var(--bg);
            background-image: 
                radial-gradient(circle at 10% 20%, rgba(249, 115, 22, 0.08) 0%, transparent 40%),
                radial-gradient(circle at 90% 80%, rgba(139, 92, 246, 0.08) 0%, transparent 40%),
                radial-gradient(circle at 50% 50%, rgba(15, 23, 42, 0.6) 0%, transparent 100%);
            color: var(--text-main);
            min-height: 100vh;
            padding: 32px 24px;
        }

        .container {
            max-width: 1280px;
            margin: 0 auto;
        }

        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 32px;
            padding-bottom: 24px;
            border-bottom: 1px solid var(--card-border);
        }

        .logo-area {
            display: flex;
            align-items: center;
            gap: 16px;
        }

        .logo-icon {
            width: 48px;
            height: 48px;
            background: linear-gradient(135deg, var(--primary), #ea580c);
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 24px;
            box-shadow: 0 0 20px var(--primary-glow);
        }

        .logo-text h1 {
            font-size: 22px;
            font-weight: 700;
            letter-spacing: -0.02em;
        }

        .logo-text p {
            color: var(--text-muted);
            font-size: 13px;
        }

        .badges {
            display: flex;
            gap: 10px;
        }

        .badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            backdrop-filter: blur(8px);
        }

        .badge.online {
            color: var(--success);
            border-color: rgba(16, 185, 129, 0.3);
            background: var(--success-glow);
        }

        .grid-3 {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(340px, 1fr));
            gap: 20px;
            margin-bottom: 32px;
        }

        .card {
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: var(--radius-lg);
            padding: 24px;
            backdrop-filter: blur(12px);
            transition: all 0.2s ease;
        }

        .card:hover {
            border-color: rgba(255, 255, 255, 0.15);
            background: var(--card-hover);
        }

        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
        }

        .card-title {
            font-size: 16px;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .card-body p {
            font-size: 13px;
            color: var(--text-muted);
            margin-bottom: 16px;
            line-height: 1.5;
        }

        .stat-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
            margin-bottom: 16px;
        }

        .stat-box {
            background: rgba(0, 0, 0, 0.25);
            padding: 12px;
            border-radius: var(--radius-md);
            border: 1px solid rgba(255, 255, 255, 0.04);
        }

        .stat-val {
            font-size: 18px;
            font-weight: 700;
            color: var(--text-main);
            font-family: 'JetBrains Mono', monospace;
        }

        .stat-lbl {
            font-size: 11px;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        .main-playground {
            display: grid;
            grid-template-columns: 1fr 1.1fr;
            gap: 24px;
            margin-bottom: 32px;
        }

        @media (max-width: 960px) {
            .main-playground {
                grid-template-columns: 1fr;
            }
        }

        .input-group {
            margin-bottom: 16px;
        }

        label {
            display: block;
            font-size: 12px;
            font-weight: 600;
            color: var(--text-muted);
            margin-bottom: 6px;
            text-transform: uppercase;
            letter-spacing: 0.04em;
        }

        input, select, textarea {
            width: 100%;
            background: rgba(0, 0, 0, 0.35);
            border: 1px solid var(--card-border);
            border-radius: var(--radius-md);
            padding: 12px 14px;
            color: var(--text-main);
            font-size: 14px;
            font-family: inherit;
            outline: none;
            transition: border-color 0.2s;
        }

        input:focus, select:focus, textarea:focus {
            border-color: var(--primary);
            box-shadow: 0 0 0 2px var(--primary-glow);
        }

        textarea {
            resize: vertical;
            min-height: 110px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 13px;
        }

        .btn {
            background: linear-gradient(135deg, var(--primary), #ea580c);
            color: white;
            border: none;
            padding: 12px 20px;
            border-radius: var(--radius-md);
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            width: 100%;
            transition: opacity 0.2s, transform 0.1s;
        }

        .btn:hover {
            opacity: 0.92;
        }

        .btn:active {
            transform: scale(0.99);
        }

        .output-box {
            background: #06090e;
            border: 1px solid var(--card-border);
            border-radius: var(--radius-md);
            padding: 16px;
            min-height: 380px;
            max-height: 520px;
            overflow-y: auto;
            font-family: 'JetBrains Mono', monospace;
            font-size: 13px;
            color: #cbd5e1;
            white-space: pre-wrap;
            line-height: 1.6;
        }

        .code-block {
            background: rgba(0, 0, 0, 0.4);
            border: 1px solid var(--card-border);
            border-radius: var(--radius-md);
            padding: 14px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 12px;
            color: #38bdf8;
            overflow-x: auto;
            margin-top: 8px;
        }

        .tabs {
            display: flex;
            gap: 8px;
            margin-bottom: 16px;
            border-bottom: 1px solid var(--card-border);
            padding-bottom: 8px;
        }

        .tab-btn {
            background: none;
            border: none;
            color: var(--text-muted);
            padding: 8px 14px;
            border-radius: 6px;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
        }

        .tab-btn.active {
            background: rgba(255, 255, 255, 0.08);
            color: var(--text-main);
        }

        .tool-badge {
            display: inline-block;
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid var(--card-border);
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 11px;
            margin: 2px;
            font-family: 'JetBrains Mono', monospace;
        }

        .link-btn {
            color: var(--primary);
            text-decoration: none;
            font-size: 13px;
            font-weight: 600;
            display: inline-flex;
            align-items: center;
            gap: 4px;
        }

        .link-btn:hover {
            text-decoration: underline;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="logo-area">
                <div class="logo-icon">⚡</div>
                <div class="logo-text">
                    <h1>FastAPI MCP Gateway & Groq Agent</h1>
                    <p>Aggregating Grafana & Composio Model Context Protocol Servers with Groq LLM</p>
                </div>
            </div>
            <div class="badges">
                <span class="badge online" id="status-badge">● System Online</span>
                <a href="/docs" class="badge" style="color:#38bdf8; text-decoration:none;">📘 Swagger API Docs</a>
            </div>
        </header>

        <div class="grid-3">
            <!-- Grafana MCP Card -->
            <div class="card" style="border-top: 3px solid var(--accent-grafana);">
                <div class="card-header">
                    <span class="card-title">📊 Grafana MCP</span>
                    <span class="badge online" id="grafana-status">Connected</span>
                </div>
                <div class="card-body">
                    <p>Observability & metrics MCP server. Manages Prometheus, Loki, Tempo, Alerts & Dashboards.</p>
                    <div class="stat-grid">
                        <div class="stat-box">
                            <div class="stat-val" id="grafana-count">79</div>
                            <div class="stat-lbl">Active Tools</div>
                        </div>
                        <div class="stat-box">
                            <div class="stat-val" style="font-size:13px; color:#f59e0b;">localhost:8000</div>
                            <div class="stat-lbl">Server URL</div>
                        </div>
                    </div>
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span style="font-size:12px; color:var(--text-muted);">Endpoint: <code>/api/grafana/run</code></span>
                        <a href="/api/grafana/tools" target="_blank" class="link-btn">View Tools →</a>
                    </div>
                </div>
            </div>

            <!-- Composio MCP Card -->
            <div class="card" style="border-top: 3px solid var(--accent-composio);">
                <div class="card-header">
                    <span class="card-title">🔗 Composio MCP</span>
                    <span class="badge online" id="composio-status">Connected</span>
                </div>
                <div class="card-body">
                    <p>Integration & action MCP server. Connects GitHub, Slack, Jira, Remote Bash & Workbench.</p>
                    <div class="stat-grid">
                        <div class="stat-box">
                            <div class="stat-val" id="composio-count">11</div>
                            <div class="stat-lbl">Active Tools</div>
                        </div>
                        <div class="stat-box">
                            <div class="stat-val" style="font-size:13px; color:#a78bfa;">connect.composio.dev</div>
                            <div class="stat-lbl">Server URL</div>
                        </div>
                    </div>
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span style="font-size:12px; color:var(--text-muted);">Endpoint: <code>/api/composio/run</code></span>
                        <a href="/api/composio/tools" target="_blank" class="link-btn">View Tools →</a>
                    </div>
                </div>
            </div>

            <!-- Groq LLM Card -->
            <div class="card" style="border-top: 3px solid var(--accent-groq);">
                <div class="card-header">
                    <span class="card-title">🧠 Groq LLM Agent</span>
                    <span class="badge" id="groq-model-badge" style="color:#f43f5e;">llama-3.3-70b-versatile</span>
                </div>
                <div class="card-body">
                    <p>High-speed autonomous function-calling agent orchestrating multi-step MCP tool calls.</p>
                    <div class="stat-grid">
                        <div class="stat-box">
                            <div class="stat-val" id="total-tools">90</div>
                            <div class="stat-lbl">Total MCP Tools</div>
                        </div>
                        <div class="stat-box">
                            <div class="stat-val" style="font-size:13px; color:#f43f5e;">Dual Server</div>
                            <div class="stat-lbl">Orchestration</div>
                        </div>
                    </div>
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span style="font-size:12px; color:var(--text-muted);">Endpoint: <code>/api/agent/chat</code></span>
                        <a href="/api/tools" target="_blank" class="link-btn">Catalog →</a>
                    </div>
                </div>
            </div>
        </div>

        <!-- Interactive Playground -->
        <div class="main-playground">
            <div class="card">
                <div class="card-header">
                    <span class="card-title">🚀 Interactive Agent & Tool Playground</span>
                </div>

                <div class="tabs">
                    <button class="tab-btn active" onclick="setMode('grafana')">Grafana Endpoint (/api/grafana/run)</button>
                    <button class="tab-btn" onclick="setMode('composio')">Composio Endpoint (/api/composio/run)</button>
                    <button class="tab-btn" onclick="setMode('agent')">Unified Agent (/api/agent/chat)</button>
                </div>

                <div class="input-group">
                    <label>Target API Endpoint</label>
                    <input type="text" id="endpoint-display" value="/api/grafana/run" readonly style="color:#f59e0b; font-weight:600;">
                </div>

                <div class="input-group">
                    <label>LLM Model</label>
                    <input type="text" id="model-input" value="llama-3.3-70b-versatile" placeholder="llama-3.3-70b-versatile or llama-3.3-70b-versatile">
                </div>

                <div class="input-group">
                    <label>Prompt / Task</label>
                    <textarea id="prompt-input" placeholder="e.g. List all datasources configured in Grafana">List all configured datasources in Grafana and show their status</textarea>
                </div>

                <div class="input-group">
                    <label>Groq API Key (Optional override if not set in .env)</label>
                    <input type="password" id="api-key-input" placeholder="gsk_... (leave empty if configured in .env)">
                </div>

                <button class="btn" id="run-btn" onclick="executeRun()">
                    <span>Execute Agent Request</span> ⚡
                </button>
            </div>

            <div class="card">
                <div class="card-header">
                    <span class="card-title">📄 Agent Response & Tool Execution Stream</span>
                    <button class="tab-btn" style="padding:4px 8px; font-size:11px;" onclick="clearOutput()">Clear</button>
                </div>
                <div class="output-box" id="output-box">// Output will appear here after execution...
// Ready to execute Groq LLM agent with MCP tools.</div>
            </div>
        </div>

        <!-- MCP Server Client Config Block -->
        <div class="card">
            <div class="card-header">
                <span class="card-title">🔌 Connect to this FastAPI Server as an MCP Server</span>
                <span class="badge" style="color:#38bdf8;">SSE Transport: /mcp</span>
            </div>
            <p style="font-size:13px; color:var(--text-muted); margin-bottom:12px;">
                You can connect Claude Desktop, Antigravity IDE, Cursor, or any MCP client directly to this server using the configuration below:
            </p>
            <div class="code-block" id="mcp-config-snippet">
{
  "mcpServers": {
    "fastapi-groq-gateway": {
      "serverUrl": "http://localhost:8080/mcp"
    }
  }
}</div>
        </div>
    </div>

    <script>
        let currentMode = 'grafana';

        function setMode(mode) {
            currentMode = mode;
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            event.target.classList.add('active');

            const ep = document.getElementById('endpoint-display');
            const prompt = document.getElementById('prompt-input');

            if (mode === 'grafana') {
                ep.value = '/api/grafana/run';
                ep.style.color = '#f59e0b';
                prompt.value = 'List all configured datasources in Grafana and show their status';
            } else if (mode === 'composio') {
                ep.value = '/api/composio/run';
                ep.style.color = '#a78bfa';
                prompt.value = 'Search for available GitHub tools in Composio';
            } else {
                ep.value = '/api/agent/chat';
                ep.style.color = '#f43f5e';
                prompt.value = 'Check Grafana datasource health and search GitHub tools on Composio';
            }
        }

        function clearOutput() {
            document.getElementById('output-box').textContent = '// Cleared';
        }

        async function loadHealth() {
            try {
                const res = await fetch('/api/health');
                const data = await res.json();
                if (data.mcp_servers.grafana.status === 'online') {
                    document.getElementById('grafana-count').textContent = data.mcp_servers.grafana.tools_count;
                }
                if (data.mcp_servers.composio.status === 'online') {
                    document.getElementById('composio-count').textContent = data.mcp_servers.composio.tools_count;
                }
                const total = (data.mcp_servers.grafana.tools_count || 0) + (data.mcp_servers.composio.tools_count || 0);
                document.getElementById('total-tools').textContent = total;
                if (data.groq.model) {
                    document.getElementById('groq-model-badge').textContent = data.groq.model;
                }
            } catch (e) {
                console.error('Health check error:', e);
            }
        }

        async function executeRun() {
            const btn = document.getElementById('run-btn');
            const out = document.getElementById('output-box');
            const ep = document.getElementById('endpoint-display').value;
            const promptVal = document.getElementById('prompt-input').value;
            const modelVal = document.getElementById('model-input').value;
            const keyVal = document.getElementById('api-key-input').value;

            btn.disabled = true;
            btn.innerHTML = 'Executing Agent Reasoning... ⏳';
            out.textContent = `[Sending request to ${ep}]...\nModel: ${modelVal}\nPrompt: ${promptVal}\n\nThinking & executing MCP tools...`;

            try {
                const headers = { 'Content-Type': 'application/json' };
                if (keyVal) {
                    headers['X-Groq-API-Key'] = keyVal;
                }

                const res = await fetch(ep, {
                    method: 'POST',
                    headers: headers,
                    body: JSON.stringify({
                        prompt: promptVal,
                        model: modelVal || undefined
                    })
                });

                const data = await res.json();
                if (!res.ok) {
                    out.textContent = `❌ Error (${res.status}):\n` + JSON.stringify(data, null, 2);
                } else {
                    let formatted = `✅ AGENT COMPLETED RUN\nModel: ${data.model_used}\nIterations: ${data.iterations}\n\n`;
                    if (data.tool_steps && data.tool_steps.length > 0) {
                        formatted += `=== EXECUTED MCP TOOLS (${data.tool_steps.length}) ===\n`;
                        data.tool_steps.forEach((s) => {
                            formatted += `[Step ${s.step}] Tool: ${s.tool_name} (${s.provider})\nArgs: ${JSON.stringify(s.arguments)}\nOutput: ${JSON.stringify(s.output, null, 2)}\n\n`;
                        });
                        formatted += `===================================\n\n`;
                    }
                    formatted += `=== FINAL AGENT ANSWER ===\n${data.response}\n\n`;
                    if (data.usage) {
                        formatted += `Tokens Used: ${JSON.stringify(data.usage)}`;
                    }
                    out.textContent = formatted;
                }
            } catch (err) {
                out.textContent = `❌ Network/Client Error: ${err.message}`;
            } finally {
                btn.disabled = false;
                btn.innerHTML = '<span>Execute Agent Request</span> ⚡';
            }
        }

        loadHealth();
    </script>
</body>
</html>
"""


def get_dashboard_html() -> HTMLResponse:
    return HTMLResponse(content=DASHBOARD_HTML)
