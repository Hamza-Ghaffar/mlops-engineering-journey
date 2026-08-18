<div align="center">

# ✈️ TripMate AI v2.0 — Multi-Agent Travel Planner with MCP

**Five LangGraph agents. Three live MCP servers. One natural-language trip request.**

Built by **Hamza Ghaffar** · hamza.ghaffar@hotmail.com

![Python 3.11](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.136-009688?logo=fastapi&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-1.2.2-6510F4)
![MCP](https://img.shields.io/badge/MCP-3_Servers-1e88e5)
![Groq](https://img.shields.io/badge/Groq-Qwen_27B-F55036)
![Render](https://img.shields.io/badge/Render-Docker-46E3B7)

[MCP Architecture](#-how-mcp-tool-calling-works) | [Agent Flow](#-langgraph-agent-pipeline) | [Quick Start](#-quick-start) | [Deploy](#-render-deployment) | [Troubleshooting](#-troubleshooting)

</div>

> [!IMPORTANT]
> v2.0 replaces direct API calls with **MCP (Model Context Protocol)** servers.
> Tavily, AviationStack, and a custom OpenWeather server are each wired as separate
> MCP transports. LangGraph orchestrates five agents that call these tools, then use
> Groq LLM to reason over the results.

---

## What You Get

| Service | Address | Purpose |
| --- | --- | --- |
| Web UI | `http://localhost:8000/` | Natural-language travel query interface |
| Travel API | `http://localhost:8000/api/travel` | JSON — plan, flights, hotels, weather |
| Health check | `http://localhost:8000/health` | Service readiness probe |
| PostgreSQL | `DATABASE_URL` env var | LangGraph conversation-state checkpointer |

---

## How MCP Tool Calling Works

### What is MCP?

**Model Context Protocol (MCP)** is an open standard for connecting LLM agent frameworks to external tools through a uniform interface — whether the tool runs locally (stdio) or in the cloud (HTTP/SSE). In this project, `langchain-mcp-adapters` wraps each MCP server into a standard LangChain tool object. Agents call `tool.ainvoke(args)` — no per-API SDK needed.

### Three MCP Servers

```
MultiServerMCPClient  (mcp_client.py)
┌─────────────────────────────────────────────────────────┐
│                                                         │
│  "tavily"           "aviationstack"   "weather"         │
│  transport:         transport:        transport:         │
│  streamable_http    stdio             stdio              │
│                                                         │
│  url: cloud         command: uvx      command:           │
│  mcp.tavily.com     args:             sys.executable    │
│                     [aviationstack    args:              │
│                      -mcp]            [custom_weather    │
│                                        _mcp_server.py]  │
│                                                         │
│  Tools:             Tools:            Tools:             │
│  tavily_search      list_airports     get_current_       │
│                     list_airlines     weather            │
│                                       get_forecast      │
└─────────────────────────────────────────────────────────┘
```

### The Code That Wires It (mcp_client.py)

```python
# 1. Declare all MCP server configs in one dict
client = MultiServerMCPClient({
    "tavily": {
        "transport": "streamable_http",
        "url": f"https://mcp.tavily.com/mcp/?tavilyApiKey={TAVILY_API_KEY}"
    },
    "aviationstack": {
        "transport": "stdio",
        "command": "uvx",
        "args": ["aviationstack-mcp"],
        "env": AVIATION_ENV        # injects AVIATION_STACK_API_KEY
    },
    "weather": {
        "transport": "stdio",
        "command": sys.executable, # same Python that runs app.py
        "args": [str(WEATHER_SERVER_PATH)],
        "env": WEATHER_ENV         # injects OPENWEATHER_API_KEY
    }
})

# 2. Load tools from a specific server (lazy, on first call)
tools = await client.get_tools(server_name="tavily")
search_tool = tools_by_name["tavily_search"]

# 3. Call the MCP tool — identical to any LangChain tool
result = await search_tool.ainvoke({"query": query})
```

### Custom Weather MCP Server (custom_weather_mcp_server.py)

This file is an MCP server built with `FastMCP`, exposing two tools over stdio:

```python
mcp = FastMCP("Weather MCP Server")

@mcp.tool()
def get_current_weather(city: str): ...  # calls OpenWeatherMap REST API

@mcp.tool()
def get_forecast(city: str): ...         # returns 5-step forecast
```

`MultiServerMCPClient` spawns this file as a subprocess and communicates via stdin/stdout using the MCP wire protocol.

---

## LangGraph Agent Pipeline

### Request Lifecycle

```
User: "Plan a 7-day Japan trip from Dhaka under $2000"
       |
       |  POST /api/travel
       v
 FastAPI  (app.py)
 run_travel_agent(user_input)
       |
       |  travel_graph.invoke(state, config={thread_id})
       v
 LangGraph StateGraph  (backend.py)
 +-----------------------------------------------------+
 |                                                     |
 |  START                                              |
 |    |                                                |
 |    v                                                |
 |  flight_agent                                       |
 |    MCP: list_airports  (AviationStack)              |
 |    MCP: list_airlines  (AviationStack)              |
 |    LLM: summarise route and pricing options         |
 |    |                                                |
 |    v                                                |
 |  hotel_agent                                        |
 |    MCP: tavily_search  (Tavily)                     |
 |    |                                                |
 |    v                                                |
 |  weather_agent                                      |
 |    MCP: get_current_weather  (custom FastMCP)       |
 |    MCP: get_forecast         (custom FastMCP)       |
 |    |                                                |
 |    v                                                |
 |  itinerary_agent                                    |
 |    LLM: combine all data into a day-by-day plan     |
 |    |                                                |
 |    v                                                |
 |  final_agent                                        |
 |    LLM: format the complete travel report           |
 |    |                                                |
 |    v                                                |
 |   END                                               |
 +---------------------|---------------------------------+
                        |  checkpointer.save(state, thread_id)
                        v
                  PostgreSQL
                  (state keyed by thread_id)
                        |
                        v
            Formatted travel report returned to API
```

### Shared State Object

```python
class TravelState(TypedDict):
    messages:        list[AnyMessage]  # full conversation history
    user_query:      str               # original user request
    flight_results:  str               # written by flight_agent
    hotel_results:   str               # written by hotel_agent
    weather_results: str               # written by weather_agent
    itinerary:       str               # written by itinerary_agent
    llm_calls:       int               # running LLM invocation counter
```

### How Each Agent Calls an MCP Tool

```
Agent function (backend.py)
        |
        |  asyncio.run( tavily_mcp_search(query) )
        v
mcp_client.py
        |
        |  await tool.ainvoke({"query": query})
        |  (standard LangChain tool interface)
        |
        |  MCP wire protocol  (stdio or HTTP/SSE)
        v
MCP Server (cloud or local subprocess)
        |
        |  Returns structured JSON result
        v
Agent feeds result into LLM prompt
        |
        |  llm.invoke([SystemMessage(...), HumanMessage(prompt)])
        v
LLM output written back into TravelState
```

### MCP Transport Reference

| Server | Transport | Lifecycle | Exposed Tools |
| --- | --- | --- | --- |
| Tavily | HTTP/SSE (cloud) | Persistent connection | `tavily_search` |
| AviationStack | stdio via `uvx` | Child process per session | `list_airports`, `list_airlines` |
| Weather | stdio via Python | Child process per session | `get_current_weather`, `get_forecast` |

---

## Repository Structure

```
.
├── Tip_Planner_v2.0_with_MCP/
│   ├── app.py                        FastAPI entry point
│   ├── backend.py                    LangGraph agents, state, graph, DB setup
│   ├── mcp_client.py                 MultiServerMCPClient — wires all 3 MCP servers
│   ├── custom_weather_mcp_server.py  FastMCP server exposing OpenWeather tools
│   ├── static/
│   │   ├── script.js                 Frontend JavaScript
│   │   └── style.css                 Frontend styles (light theme)
│   ├── templates/
│   │   └── index.html                Jinja2 HTML template
│   └── tests/
├── Dockerfile                        Render-ready Docker image (WORKDIR + uvx)
├── render.yaml                       Render infrastructure-as-code
└── requirements.txt                  Pinned deps including langchain-mcp-adapters + mcp
```

### Key Dependencies

| Package | Role |
| --- | --- |
| `langchain-mcp-adapters` | Wraps MCP servers as LangChain-compatible tool objects |
| `mcp` | FastMCP server framework for `custom_weather_mcp_server.py` |
| `langgraph` | State machine orchestrating the five agents |
| `langchain-groq` | Groq LLM client (Qwen 27B) |
| `psycopg[binary]` | PostgreSQL driver for LangGraph checkpointer |
| `nest_asyncio` | Permits `asyncio.run()` inside FastAPI async handlers |
| `uv` / `uvx` | Runs `aviationstack-mcp` as a local subprocess |

---

## Quick Start

```bash
git clone https://github.com/Hamza-Ghaffar/mlops-engineering-journey.git
cd mlops-engineering-journey
git checkout 02_AI_LLM_Agents_MCP

python -m venv .venv
# Windows:   .venv\Scripts\activate
# Linux/Mac: source .venv/bin/activate

pip install -r requirements.txt
pip install uv           # provides uvx for AviationStack MCP
```

Create `.env` inside `Tip_Planner_v2.0_with_MCP/`:

```dotenv
DATABASE_URL=postgresql://user:password@localhost:5432/travel_db
GROQ_API_KEY=your_groq_api_key
AVIATIONSTACK_API_KEY=your_aviationstack_api_key
TAVILY_API_KEY=your_tavily_api_key
OPENWEATHER_API_KEY=your_openweather_api_key
```

```bash
cd Tip_Planner_v2.0_with_MCP
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

---

## Render Deployment

1. Push to GitHub.
2. Render → **New → Blueprint** → connect repo (reads `render.yaml`).
3. Set secrets in the Render dashboard:

| Variable | Source |
| --- | --- |
| `GROQ_API_KEY` | [console.groq.com](https://console.groq.com) |
| `TAVILY_API_KEY` | [app.tavily.com](https://app.tavily.com) |
| `AVIATIONSTACK_API_KEY` | [aviationstack.com](https://aviationstack.com) |
| `OPENWEATHER_API_KEY` | [openweathermap.org/api](https://openweathermap.org/api) |
| `DATABASE_URL` | Auto-linked from Render Postgres |

```bash
# Local Docker test
docker build -t tripmate-ai .
docker run -p 8000:8000 \
  -e DATABASE_URL=postgresql://... \
  -e GROQ_API_KEY=... \
  -e TAVILY_API_KEY=... \
  -e AVIATIONSTACK_API_KEY=... \
  -e OPENWEATHER_API_KEY=... \
  tripmate-ai
```

---

## Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| `ValueError: DATABASE_URL is missing` | `.env` not loaded | Create `.env` with all five variables |
| `ValueError: GROQ_API_KEY is missing` | Key not set | Add to `.env` or Render env vars |
| `uvx: command not found` | `uv` not installed | `pip install uv` |
| AviationStack MCP fails | `uvx` package not cached | Run `uvx aviationstack-mcp --help` once |
| Weather MCP `FileNotFoundError` | Wrong working directory | Run uvicorn from inside `Tip_Planner_v2.0_with_MCP/` |
| `psycopg.OperationalError` | PostgreSQL unreachable | Verify `DATABASE_URL` |
| `ModuleNotFoundError: No module named 'app'` | Wrong directory | `cd Tip_Planner_v2.0_with_MCP` first |

---

## Pre-Deploy Checklist

```
[ ] Python 3.10+ confirmed
[ ] pip install -r requirements.txt completed
[ ] pip install uv completed
[ ] All five environment variables set
[ ] /health returns {"status": "ok"}
[ ] /api/travel returns a travel plan for a test query
[ ] .env not tracked by Git
[ ] Docker image builds and starts without errors
```

---

## Upstream

Built on [LangGraph](https://github.com/langchain-ai/langgraph) (MIT),
[FastAPI](https://github.com/fastapi/fastapi) (MIT),
[langchain-mcp-adapters](https://github.com/langchain-ai/langchain-mcp-adapters) (MIT), and
[MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) (MIT).

---

*Built by [Hamza Ghaffar](mailto:hamza.ghaffar@hotmail.com)*
