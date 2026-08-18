<div align="center">

# ✈️ TripMate AI — Multi-Agent Travel Planner

**A LangGraph-powered multi-agent travel planner with FastAPI, PostgreSQL persistence, and one-command Render deployment**

![Python 3.11](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.136-009688?logo=fastapi&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-1.2.2-6510F4)
![Groq](https://img.shields.io/badge/Groq-Qwen_27B-F55036)
![Render](https://img.shields.io/badge/Render-Docker-46E3B7)

[Quick Start](#-quick-start) | [Architecture](#-architecture) | [Repository](#-repository-structure) | [Deploy](#-render-deployment) | [Troubleshooting](#-troubleshooting)

</div>

> [!IMPORTANT]
> All four environment variables (`DATABASE_URL`, `GROQ_API_KEY`, `TAVILY_API_KEY`, `AVIATIONSTACK_API_KEY`) must be set before the app will start. The PostgreSQL schema is created automatically on first run.

## What You Get

| Service | Address | Purpose |
| --- | --- | --- |
| Web UI | `http://localhost:8000/` | Chat interface for natural-language travel queries |
| Travel API | `http://localhost:8000/api/travel` | JSON endpoint for travel planning requests |
| Health check | `http://localhost:8000/health` | Service readiness probe |
| PostgreSQL | configured via `DATABASE_URL` | LangGraph conversation state persistence |

```text
User query -> Flight Agent -> Hotel Agent -> Itinerary Agent -> Final Agent -> Formatted travel report
```

## 🚀 Quick Start

### 1. Prerequisites

Install:

- Python 3.10 or newer
- Git
- A running PostgreSQL instance (local or Render managed)
- API keys for Groq, Tavily, and AviationStack

Verify:

```bash
python --version   # must be 3.10+
git --version
```

### 2. Clone

```bash
git clone https://github.com/Hamza-Ghaffar/mlops-engineering-journey.git
cd mlops-engineering-journey
```

### 3. Create and Activate Environment

```bash
python -m venv .venv
```

Windows:

```powershell
.venv\Scripts\Activate.ps1
```

Linux / macOS:

```bash
source .venv/bin/activate
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Configure Environment Variables

Create a `.env` file inside `AI_System_Project_v1_Trip_planner/`:

```dotenv
DATABASE_URL=postgresql://user:password@localhost:5432/travel_db
GROQ_API_KEY=your_groq_api_key
AVIATIONSTACK_API_KEY=your_aviationstack_api_key
TAVILY_API_KEY=your_tavily_api_key
DEFAULT_ORIGIN_IATA=DAC
```

> [!WARNING]
> Never commit `.env`. It is excluded by `.gitignore`.

### 6. Start the Server

```bash
cd AI_System_Project_v1_Trip_planner
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

### 7. Verify

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{
  "status": "ok",
  "message": "AI Travel Planner API is running"
}
```

Open `http://localhost:8000` in your browser.

<details>
<summary><strong>Windows PowerShell alternative</strong></summary>

```powershell
Invoke-RestMethod http://localhost:8000/health
Test-NetConnection localhost -Port 8000
```

</details>

## 🏗️ Architecture

```text
                      Browser / API client

 Web UI ------------> FastAPI :8000
 REST client              |
                          |
                 LangGraph workflow
                          |
         +--------+-------+-------+--------+
         |        |               |        |
         v        v               v        v
      Flight    Hotel         Itinerary  Final
      Agent     Agent           Agent    Agent
         |        |
         v        v
    AviationStack  Tavily
      REST API   Web Search
                          |
                    PostgreSQL
                  (psycopg checkpointer)

LLM calls ---------------> Groq API (Qwen 27B)
```

### Agent Responsibilities

| Agent | Tool | Output |
| --- | --- | --- |
| Flight Agent | AviationStack API | Live flight route and schedule data |
| Hotel Agent | Tavily web search | Hotel suggestions with source URLs |
| Itinerary Agent | Groq LLM | Day-by-day structured travel plan |
| Final Agent | Groq LLM | Complete formatted travel report |

### Conversation Persistence

Each request carries a `thread_id`. LangGraph checkpoints the full agent state to PostgreSQL after every step. Sending the same `thread_id` in a follow-up request continues the conversation from where it left off. The schema is created automatically on startup via `checkpointer.setup()`.

## 📁 Repository Structure

```text
.
├── AI_System_Project_v1_Trip_planner/
│   ├── app.py                FastAPI entry point and route definitions
│   ├── backend.py            LangGraph agents, state graph, and DB setup
│   ├── static/
│   │   ├── script.js         Frontend JavaScript
│   │   └── style.css         Frontend styles
│   ├── templates/
│   │   └── index.html        Jinja2 HTML template
│   ├── tests/
│   │   └── test_tavily.py    Tavily tool unit tests
│   └── tools/
│       ├── flight_tool.py    AviationStack flight search integration
│       └── tavily_tool.py    Tavily web search wrapper
├── Dockerfile                Render-ready Docker image
├── render.yaml               Render infrastructure-as-code (web + Postgres)
└── requirements.txt          Pinned Python dependencies
```

### Files That Must Stay Outside Git

| Item | Reason |
| --- | --- |
| `.env` | Contains real API keys |
| `.venv/` | Recreated from `requirements.txt` |
| `__pycache__/` | Generated bytecode |

## ☁️ Render Deployment

The repository includes a `render.yaml` that provisions a Docker web service and a managed PostgreSQL database in one step.

### Deploy via Blueprint

1. Push the repository to GitHub.
2. Go to [render.com](https://render.com) - **New** - **Blueprint**.
3. Connect your repository. Render reads `render.yaml` automatically.
4. Set the following secrets under **Environment** in the Render dashboard:

| Variable | Where to get it |
| --- | --- |
| `GROQ_API_KEY` | [console.groq.com](https://console.groq.com) |
| `TAVILY_API_KEY` | [app.tavily.com](https://app.tavily.com) |
| `AVIATIONSTACK_API_KEY` | [aviationstack.com/dashboard](https://aviationstack.com/dashboard) |
| `DATABASE_URL` | Auto-linked from the Render Postgres instance by `render.yaml` |
| `DEFAULT_ORIGIN_IATA` | Your default departure airport IATA code, e.g. `DAC` |

5. Click **Apply** and wait for both services to turn green.
6. Open your web service URL and check `/health`.

### Local Docker Build

```bash
# from repo root
docker build -t tripmate-ai .
docker run -p 8000:8000 \
  -e DATABASE_URL=postgresql://... \
  -e GROQ_API_KEY=... \
  -e TAVILY_API_KEY=... \
  -e AVIATIONSTACK_API_KEY=... \
  tripmate-ai
```

## 🔄 Daily Operation

### Start

```bash
cd AI_System_Project_v1_Trip_planner
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

### Stop

Press `Ctrl+C`.

### Example API Request

```bash
curl -X POST http://localhost:8000/api/travel \
  -H "Content-Type: application/json" \
  -d '{"message": "Plan a 5-day trip from Dhaka to Tokyo under $2000"}'
```

Response fields:

| Field | Description |
| --- | --- |
| `thread_id` | Conversation ID - reuse in follow-up requests |
| `answer` | Final formatted travel report |
| `flight_results` | Raw flight data from AviationStack |
| `hotel_results` | Hotel suggestions from Tavily |
| `itinerary` | Day-by-day plan from the LLM |
| `llm_calls` | Total LLM invocations in this run |

To continue a conversation, pass the returned `thread_id` in the next request:

```bash
curl -X POST http://localhost:8000/api/travel \
  -H "Content-Type: application/json" \
  -d '{"message": "What visa do I need?", "thread_id": "user_abc123"}'
```

## 🩺 Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| `ValueError: DATABASE_URL is missing` | `.env` not loaded or variable not set | Create `.env` with a valid `DATABASE_URL` |
| `ValueError: GROQ_API_KEY is missing` | Groq key not set | Add `GROQ_API_KEY` to `.env` or Render env vars |
| `ModuleNotFoundError: No module named 'app'` | uvicorn run from wrong directory | Run uvicorn from inside `AI_System_Project_v1_Trip_planner/` |
| `psycopg.OperationalError` | PostgreSQL not reachable | Verify `DATABASE_URL` and that the DB server is running |
| Flight results empty | AviationStack free-plan route limit | Check your API quota at aviationstack.com/dashboard |
| `SSL CERTIFICATE_VERIFY_FAILED` | Corporate CA issue | The app sets `SSL_CERT_FILE` via `certifi` automatically on start |
| Port 8000 already in use | Another process on the same port | Stop the other process or use `--port 8001` |
| 500 error on `/api/travel` | Missing API key or DB not ready | Check server logs and confirm all env vars are set |

## 🔐 Security

- Never commit `.env`, API keys, or passwords.
- All four API keys must be injected at runtime via environment variables, never hardcoded.
- The AviationStack free tier uses HTTP. Upgrade to a paid plan for HTTPS API calls in production.
- Error messages from `/api/travel` include raw exception text. Review this before exposing the endpoint to untrusted clients.
- Local `DEFAULT_ORIGIN_IATA` is a convenience default and carries no secrets.

## ✅ Pre-Deploy Checklist

```text
[ ] Python 3.10+ confirmed
[ ] pip install -r requirements.txt completed without errors
[ ] .env created with all four required variables
[ ] DATABASE_URL points to a reachable PostgreSQL instance
[ ] /health returns {"status": "ok"}
[ ] /api/travel returns a valid travel plan for a test query
[ ] .env is listed in .gitignore and not tracked by Git
[ ] Docker image builds and the container starts without errors
[ ] Render environment variables set in the dashboard
```

## Upstream

This project is built on [LangGraph](https://github.com/langchain-ai/langgraph) (MIT), [LangChain](https://github.com/langchain-ai/langchain) (MIT), [FastAPI](https://github.com/fastapi/fastapi) (MIT), [Groq Python SDK](https://github.com/groq/groq-python) (Apache-2.0), and [Tavily Python](https://github.com/tavily-ai/tavily-python) (MIT). Review upstream licenses before redistributing modified artifacts.
