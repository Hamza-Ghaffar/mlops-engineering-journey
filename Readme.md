<div align="center">

# TripMate AI v3.0 — Supervisor · Guardrails · Human-in-the-Loop

**Five specialist agents. One supervisor. One guardrail. One human checkpoint.**

Built by **Hamza Ghaffar** · hamza.ghaffar@hotmail.com

![Python 3.11](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.136-009688?logo=fastapi&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-1.2.2-6510F4)
![MCP](https://img.shields.io/badge/MCP-3_Servers-1e88e5)
![Groq](https://img.shields.io/badge/Groq-Qwen_27B-F55036)
![HITL](https://img.shields.io/badge/HITL-Enabled-22C55E)

[Architecture](#-architecture) | [HITL Flow](#-human-in-the-loop-flow) | [API Reference](#-api-reference) | [Quick Start](#-quick-start) | [Deploy](#-render-deployment) | [Troubleshooting](#-troubleshooting)

</div>

> [!IMPORTANT]
> v3.0 adds four major features on top of the MCP foundation from v2.0:
> **Input Guardrail** (blocks non-travel requests), **Supervisor Agent** (picks only
> the agents needed), **Budget Agent** (assesses cost feasibility), and
> **Human-in-the-Loop** (the user reviews and approves the draft itinerary before
> the final report is generated).

---

## What You Get

| Service | Address | Purpose |
| --- | --- | --- |
| Web UI | `http://localhost:8080/` | Full chat + approval interface |
| Travel API | `http://localhost:8080/api/travel` | Start a planning run |
| Approval API | `http://localhost:8080/api/travel/approve` | Resume after human review |
| Health check | `http://localhost:8080/health` | Lists active features |
| PostgreSQL | `DATABASE_URL` env var | LangGraph conversation checkpointer |

Health response confirms active features:
```json
{
  "status": "ok",
  "message": "TripMate AI API is running",
  "features": ["supervisor_agent", "input_guardrail", "human_in_the_loop"]
}
```

---

## Architecture

### System Overview

```
 User Request
      |
      | POST /api/travel
      v
 FastAPI (app.py)
      |
      | travel_graph.invoke(state, thread_id)
      v
 +--------------------------------------------------+
 |           LangGraph StateGraph                   |
 |                                                  |
 |  START                                           |
 |    |                                             |
 |    v                                             |
 |  supervisor_agent                                |
 |    Guardrail:  is this a travel query?           |
 |    Selector:   which agents does it need?        |
 |    Extractor:  destination, budget, duration     |
 |    |                                             |
 |    +--- blocked -------> guardrail_blocked --> END
 |    |                                             |
 |    v  (conditional routing)                      |
 |  flight_agent    MCP: AviationStack              |
 |    |                                             |
 |  hotel_agent     MCP: Tavily                     |
 |    |                                             |
 |  weather_agent   MCP: OpenWeather                |
 |    |                                             |
 |  budget_agent    LLM: cost feasibility           |
 |    |                                             |
 |  itinerary_agent LLM: draft plan                 |
 |    |                                             |
 |  human_approval  <-- PAUSE (interrupt)           |
 |    |  User reviews draft via browser / API       |
 |    | POST /api/travel/approve                    |
 |    |                                             |
 |  final_agent     LLM: polished report            |
 |    |                                             |
 |   END                                            |
 +--------------------------------------------------+
      |
      | checkpointer.save(state, thread_id)
      v
 PostgreSQL (full state keyed by thread_id)
```

### Conditional Agent Routing

The supervisor selects only the agents needed for the query. Examples:

| Query type | Agents selected |
| --- | --- |
| Full trip ("Plan 7 days Japan...") | flight + hotel + weather + budget + itinerary |
| Weather only ("What is the weather in Bangkok?") | weather + itinerary |
| Budget check ("Is $500 enough for Dubai?") | budget + itinerary |
| Blocked ("How do I hack...") | guardrail_blocked only |

---

## Human-in-the-Loop Flow

### Phase 1 — Start a run

```
POST /api/travel
{ "message": "Plan a 5-day Tokyo trip from Dhaka under $1500" }

Response (requires_approval: true):
{
  "success": true,
  "thread_id": "user_abc123",
  "requires_approval": true,
  "answer": "<draft itinerary>",
  "approval_request": "Please review the draft. Approve or provide feedback.",
  "selected_agents": ["flight_agent", "hotel_agent", "weather_agent", "budget_agent", "itinerary_agent"],
  "supervisor_reasoning": "Full trip requested...",
  "flight_results": "...",
  "hotel_results": "...",
  "weather_results": "...",
  "budget_results": "..."
}
```

### Phase 2 — Human reviews the draft

The user reads the draft itinerary in the browser and either:
- **Approves** it → final report polishes and preserves the draft
- **Rejects** with feedback → final report applies the revision

### Phase 3 — Resume with approval

```
POST /api/travel/approve
{
  "thread_id": "user_abc123",
  "approved": true,
  "feedback": ""
}

# or with revision request:
{
  "thread_id": "user_abc123",
  "approved": false,
  "feedback": "Add more budget hotel options under $80/night"
}

Response:
{
  "success": true,
  "thread_id": "user_abc123",
  "requires_approval": false,
  "answer": "<final polished travel report>",
  "approved": true,
  ...
}
```

---

## Input Guardrail

The supervisor runs an LLM guardrail check before any specialist agents are started.

```
Allowed:   "Plan a trip to Tokyo"
Allowed:   "What hotels are good in Dubai?"
Allowed:   "Is $1000 enough for Bangkok for 5 days?"

Blocked:   "Write a Python script to hack a database"
Blocked:   "Help me with my homework"
Blocked:   "Tell me a joke"

Blocked response:
{
  "guardrail_allowed": false,
  "guardrail_reason": "TripMate AI can only help with travel-planning requests.",
  "answer": "TripMate AI can only help with travel-planning requests."
}
```

Guardrail is fail-open: if the LLM returns a malformed JSON response, the request is allowed through so the original travel-planning workflow is preserved.

---

## Agent Responsibilities

| Agent | Type | Tool / Model | Output |
| --- | --- | --- | --- |
| `supervisor_agent` | Orchestrator | Groq LLM | Guardrail decision, agent list, constraints |
| `flight_agent` | Specialist | MCP: AviationStack | Flight routes and airfare guidance |
| `hotel_agent` | Specialist | MCP: Tavily | Hotel suggestions with sources |
| `weather_agent` | Specialist | MCP: OpenWeather | Current weather + 5-step forecast |
| `budget_agent` | Specialist | Groq LLM | Cost categories, risks, savings tips |
| `itinerary_agent` | Specialist | Groq LLM | Draft day-by-day plan (for HITL review) |
| `human_approval` | HITL | `interrupt()` | Pauses graph, waits for POST /approve |
| `final_agent` | Specialist | Groq LLM | Polished final report incorporating feedback |
| `guardrail_blocked` | Fallback | — | Returns block reason immediately |

---

## State Object

```python
class TravelState(TypedDict, total=False):
    messages:             list[AnyMessage]   # full conversation history
    user_query:           str                # original request

    # Supervisor + guardrail
    guardrail_allowed:    bool
    guardrail_reason:     str
    selected_agents:      list[str]
    trip_constraints:     dict               # destination, origin, duration, budget ...
    supervisor_reasoning: str

    # Specialist outputs
    flight_results:       str
    hotel_results:        str
    weather_results:      str
    budget_results:       str
    itinerary:            str

    # HITL
    approval_request:     str
    approved:             bool
    human_feedback:       str
    final_response:       str

    llm_calls:            int
```

---

## MCP Servers

Three MCP servers provide live data. All wired via `langchain-mcp-adapters`.

| Server | Transport | Tools | API key env var |
| --- | --- | --- | --- |
| Tavily | HTTP/SSE (cloud) | `tavily_search` | `TAVILY_API_KEY` |
| AviationStack | stdio via `uvx` | `list_airports`, `list_airlines` | `AVIATIONSTACK_API_KEY` |
| OpenWeather | stdio via Python | `get_current_weather`, `get_forecast` | `OPENWEATHER_API_KEY` |

---

## Repository Structure

```
.
├── Tip_Planner_v2.0_with_MCP/
│   ├── app.py                        FastAPI — /api/travel + /api/travel/approve
│   ├── backend.py                    All agents, graph, HITL, routing, DB
│   ├── mcp_client.py                 MultiServerMCPClient (3 MCP servers)
│   ├── custom_weather_mcp_server.py  FastMCP stdio server for OpenWeather
│   ├── static/
│   │   ├── script.js                 HITL-aware frontend — approval panel
│   │   └── style.css                 Light theme, split hero, responsive
│   ├── templates/
│   │   └── index.html                Jinja2 template with approval UI
│   └── tests/
│       └── test_tavily.py
├── Dockerfile                        WORKDIR fix + uv for uvx
├── render.yaml                       Render Blueprint (web + Postgres)
└── requirements.txt                  All pinned deps
```

---

## Quick Start

### Prerequisites

- Python 3.10+, Git, PostgreSQL (local or Render)
- `uv` for `uvx aviationstack-mcp` — `pip install uv`
- API keys: Groq, Tavily, AviationStack, OpenWeatherMap

```bash
git clone https://github.com/Hamza-Ghaffar/mlops-engineering-journey.git
cd mlops-engineering-journey
git checkout 03_AI_LLM_Agents_MCP_HITL_GR

python -m venv .venv
# Windows:   .venv\Scripts\activate
# Linux/Mac: source .venv/bin/activate

pip install -r requirements.txt
pip install uv
```

Create `.env` in the repo root (or inside `Tip_Planner_v2.0_with_MCP/`):

```dotenv
DATABASE_URL=postgresql://user:password@localhost:5432/travel_db
GROQ_API_KEY=your_groq_api_key
AVIATIONSTACK_API_KEY=your_aviationstack_api_key
TAVILY_API_KEY=your_tavily_api_key
OPENWEATHER_API_KEY=your_openweather_api_key
```

```bash
cd Tip_Planner_v2.0_with_MCP
uvicorn app:app --host 0.0.0.0 --port 8080 --reload
```

---

## Render Deployment

1. Push to GitHub on branch `03_AI_LLM_Agents_MCP_HITL_GR`.
2. Render → **New → Blueprint** → connect repo (`render.yaml` is auto-detected).
3. Set secrets in the Render dashboard:

| Variable | Source |
| --- | --- |
| `GROQ_API_KEY` | [console.groq.com](https://console.groq.com) |
| `TAVILY_API_KEY` | [app.tavily.com](https://app.tavily.com) |
| `AVIATIONSTACK_API_KEY` | [aviationstack.com](https://aviationstack.com) |
| `OPENWEATHER_API_KEY` | [openweathermap.org/api](https://openweathermap.org/api) |
| `DATABASE_URL` | Auto-linked from Render Postgres |

---

## Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| `ValueError: DATABASE_URL is missing` | `.env` not loaded | Add `DATABASE_URL` to `.env` |
| `ValueError: GROQ_API_KEY is missing` | Key not set | Add `GROQ_API_KEY` to `.env` |
| `Error code: 413 — tokens per minute exceeded` | Groq free-tier TPM limit | Upgrade Groq plan or reduce prompt length |
| `uvx: command not found` | `uv` not installed | `pip install uv` |
| AviationStack MCP fails | `uvx` package not cached | Run `uvx aviationstack-mcp --help` once |
| Weather `FileNotFoundError` | Wrong working directory | Run uvicorn from inside `Tip_Planner_v2.0_with_MCP/` |
| `ModuleNotFoundError: No module named 'app'` | Wrong directory | `cd Tip_Planner_v2.0_with_MCP` first |
| Approval returns 400 | Rejected without feedback | Provide `feedback` text when `approved: false` |
| `psycopg.OperationalError` | PostgreSQL not reachable | Verify `DATABASE_URL` and DB status |

> **Groq TPM note:** The free tier allows 8 000 tokens per minute on `qwen/qwen3.6-27b`.
> Each run makes 5-7 LLM calls. Add a `time.sleep(10)` between rapid tests, or upgrade
> to the Groq Dev tier.

---

## Pre-Deploy Checklist

```
[ ] Python 3.10+ confirmed
[ ] pip install -r requirements.txt completed
[ ] pip install uv completed
[ ] All five environment variables set in .env
[ ] DATABASE_URL points to a reachable PostgreSQL instance
[ ] GET /health returns features list
[ ] POST /api/travel returns requires_approval: true for a travel query
[ ] POST /api/travel/approve returns final polished report
[ ] Guardrail blocks a non-travel query (guardrail_allowed: false)
[ ] .env not tracked by Git
[ ] Docker image builds without errors
```

---

## Upstream

Built on [LangGraph](https://github.com/langchain-ai/langgraph) (MIT),
[FastAPI](https://github.com/fastapi/fastapi) (MIT),
[langchain-mcp-adapters](https://github.com/langchain-ai/langchain-mcp-adapters) (MIT), and
[MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) (MIT).

---

*Built by [Hamza Ghaffar](mailto:hamza.ghaffar@hotmail.com)*
