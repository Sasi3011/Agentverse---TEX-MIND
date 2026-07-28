# 00 — The Master Brain (Orchestrator Agent)
### How 10 independent agents become 1 system

This is the document that makes TexVerse AI "one agent" instead of ten disconnected services. Every agent file (01–10) can run completely standalone with its own API. This document defines the layer that sits above all of them, owns the shared state, and makes decisions about sequencing, parallelism, and failure handling.

---

## 1. What "one brain" actually means

Each of the 10 agents is a **microservice** — its own container, its own API, testable and deployable in isolation. The **orchestrator** is a separate service that:
- Holds the single shared `MillState` object for a batch/time-window.
- Decides which agents run now, which run in parallel, and which must wait for another agent's output.
- Routes data between agents (agent outputs become other agents' inputs).
- Presents ONE external API and ONE dashboard to the human user — nobody outside the system talks to agents 1–10 directly.

This is exactly the distinction judges are told to reward: not ten scripts glued together, but one coordinated system with visible, structured hand-offs.

## 2. Two categories of agents

| Category | Agents | Trigger pattern |
|---|---|---|
| **Batch-triggered (the production line)** | 1 Intake → 2 Defect → 3 Dyeing → 9 Traceability → 10 Sustainability | Runs per fabric batch, mostly sequential (each depends on the previous) |
| **Always-on background monitors** | 4 Effluent, 5 Energy, 6 Maintenance, 7 Safety | Run continuously on their own clock, publish events to shared state whenever something changes |
| **Scheduled planning** | 8 Demand | Runs on a cron schedule (e.g. weekly), informs production planning, not tied to a single batch |

The orchestrator must handle all three trigger patterns — it is not a single linear pipeline, it's a supervisor managing three different rhythms of work.

## 3. Shared State Schema (the "memory" every agent reads/writes)

```python
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class MillState(BaseModel):
    batch_id: str
    created_at: datetime

    intake_result: Optional[dict] = None          # from Agent 1
    defect_result: Optional[dict] = None          # from Agent 2
    dye_recipe: Optional[dict] = None             # from Agent 3
    effluent_status: Optional[dict] = None        # from Agent 4 (latest snapshot)
    energy_status: Optional[dict] = None          # from Agent 5 (latest snapshot)
    maintenance_queue: Optional[List[dict]] = None # from Agent 6
    safety_status: Optional[dict] = None          # from Agent 7 (latest snapshot)
    demand_forecast: Optional[dict] = None        # from Agent 8
    traceability_record: Optional[dict] = None     # from Agent 9
    sustainability_report: Optional[dict] = None   # from Agent 10

    status: str = "in_progress"   # in_progress | completed | halted
    halted_reason: Optional[str] = None
```

This object is persisted in Postgres (one row per batch, JSONB columns for the nested agent outputs) so any agent's output — and the full history of a batch's journey through the mill — can be queried later for audits.

## 4. Orchestration Graph (LangGraph)

```python
from langgraph.graph import StateGraph, END

graph = StateGraph(MillState)

graph.add_node("intake", call_intake_agent)
graph.add_node("defect", call_defect_agent)
graph.add_node("dye", call_dye_agent)
graph.add_node("traceability", call_traceability_agent)
graph.add_node("sustainability", call_sustainability_agent)

graph.set_entry_point("intake")

def route_after_intake(state: MillState):
    if state.intake_result["decision"] == "flag":
        return "halt"
    return "defect"

graph.add_conditional_edges("intake", route_after_intake, {
    "defect": "defect",
    "halt": END
})

def route_after_defect(state: MillState):
    if state.defect_result["decision"] == "reject_roll":
        return "halt"
    return "dye"

graph.add_conditional_edges("defect", route_after_defect, {
    "dye": "dye",
    "halt": END
})

graph.add_edge("dye", "traceability")

def route_before_sustainability(state: MillState):
    # sustainability report requires the always-on monitors to have current data
    if state.effluent_status and state.energy_status:
        return "sustainability"
    return "wait"

graph.add_conditional_edges("traceability", route_before_sustainability, {
    "sustainability": "sustainability",
    "wait": END   # re-triggered later once background monitors have fresh data
})

graph.add_edge("sustainability", END)

app = graph.compile()
```

**Key design decision:** the batch pipeline (1→2→3→9→10) has explicit halt conditions — a bad intake or a rejected fabric roll stops the pipeline immediately rather than wastefully running downstream agents on doomed material. This is a real production judgment, not just a happy-path demo.

## 5. Background Monitor Supervisor (Agents 4, 5, 6, 7)

These don't fit a request/response graph — they run on independent loops. Implement as async workers, each publishing to a message queue (Redis Streams or a lightweight pub/sub) that the orchestrator subscribes to:

```python
import asyncio

async def effluent_monitor_loop():
    while True:
        reading = await get_next_sensor_reading("effluent")
        result = await call_effluent_agent(reading)
        await publish_to_state_bus("effluent_status", result)
        await asyncio.sleep(POLL_INTERVAL_SECONDS)

# one loop per background agent, run as separate asyncio tasks
# or as separate lightweight worker processes for true isolation
```

The orchestrator's dashboard reads the latest published state from each monitor without needing to actively poll every agent on every request.

## 6. Inter-Agent Communication Protocol

- **Protocol:** REST over HTTP (simplest, most debuggable for a hackathon-to-pilot timeline). Each agent exposes its own FastAPI service on its own port.
- **For production scale-up later:** consider gRPC for lower latency between internal services, or a message broker (RabbitMQ/Kafka) if agent call volume grows past what synchronous REST can comfortably handle — not needed at pilot scale.
- **Service discovery:** Docker Compose service names (`http://intake-agent:8001`) for local/single-host deployment; Kubernetes DNS (`http://intake-agent.texverse.svc.cluster.local`) if deployed on Kubernetes.
- **Timeouts & retries:** every orchestrator→agent call has a timeout (default 10s) and up to 2 retries with exponential backoff before the pipeline halts and flags a system-level failure (distinct from a business-logic halt like a rejected batch).

## 7. Full System Architecture (Deployment View)

```
                         ┌────────────────────────┐
                         │   Nginx / API Gateway    │  ← single external entry point
                         └────────────┬─────────────┘
                                      │
                         ┌────────────▼─────────────┐
                         │   Orchestrator Service     │
                         │   (FastAPI + LangGraph)    │
                         └──┬───────────────────────┬─┘
           ┌────────────────┤                       ├─────────────────┐
           ▼                ▼                       ▼                 ▼
  ┌─────────────────┐┌──────────────┐      ┌──────────────────┐┌──────────────┐
  │ Batch-pipeline    ││ Background   │      │ Scheduled agent   ││ Postgres      │
  │ agents (1,2,3,9,10)││ monitors     │      │ (8 demand)        ││ (MillState +  │
  │ — REST calls      ││ (4,5,6,7)    │      │ — cron trigger    ││ agent history)│
  │                  ││ — async loops │      │                   ││               │
  └─────────────────┘└──────────────┘      └──────────────────┘└──────────────┘
           │                │                       │                 │
           └────────────────┴───────────┬───────────┴─────────────────┘
                                         ▼
                         ┌────────────────────────┐
                         │  Dashboard (Streamlit /  │
                         │  Next.js) — single UI    │
                         └────────────────────────┘
```

## 8. Deployment (Production-Level)

### Local / hackathon demo
```
docker compose up
```
One `docker-compose.yml` at the repo root defines all 11 services (10 agents + orchestrator) plus Postgres, Redis, and the dashboard.

### Production deployment
- **Container orchestration:** Kubernetes (each agent = its own Deployment + Service; orchestrator = its own Deployment with a horizontal pod autoscaler since it's the highest-traffic component).
- **CI/CD:** GitHub Actions — on push to `main`, run tests per agent (each agent's test suite runs independently since they're independent services), build and push Docker images, deploy via `kubectl apply` or a GitOps tool (ArgoCD) for a real pilot deployment.
- **Secrets management:** never commit `.env` files — use Kubernetes Secrets or a vault (HashiCorp Vault/AWS Secrets Manager) for database credentials, alert webhook URLs, and any API keys.
- **Database:** managed Postgres (RDS/Cloud SQL) for production, not the local SQLite used for early prototyping.
- **Observability stack:** Prometheus (metrics) + Grafana (dashboards) + a centralized log aggregator (Loki or ELK) — every agent should expose a `/metrics` endpoint and structured JSON logs.

## 9. Production Readiness Checklist

- [ ] Every agent has its own health check endpoint, tested by the orchestrator before routing traffic to it
- [ ] Every agent's database writes are transactional — no partial-state corruption on crash mid-write
- [ ] Orchestrator has a circuit breaker per agent (if an agent fails N times in a row, stop calling it and alert, rather than retry-storming it)
- [ ] All compliance-relevant logic (Agent 4, Agent 9) has been reviewed by a human domain expert, not just a developer
- [ ] Full audit logging on every state transition, retained per your regulatory requirements
- [ ] Role-based access control on the dashboard (plant manager, QC staff, compliance officer see different views)
- [ ] Load tested at expected real throughput (frames/sec for CV agents, readings/sec for sensor agents) before claiming "production ready"
- [ ] Rollback plan documented for every model deployment (Agents 1, 2, 3, 6, 7 all involve trained models that will need updates)
- [ ] Data backup and disaster recovery plan for the Postgres instance holding MillState and history

## 10. Scaling Path (Hackathon → Pilot → Real Deployment)

| Stage | What changes |
|---|---|
| **Hackathon demo** | Synthetic data, single Docker Compose host, SQLite acceptable, no real cameras/sensors |
| **Single-mill pilot** | Real sensor/camera integration for 1–2 agents at a time (start with Agent 4 effluent — highest impact, lowest integration complexity), Postgres, basic monitoring |
| **Full mill deployment** | All 10 agents on real data feeds, Kubernetes deployment, full observability stack, human-in-the-loop review for all automated decisions initially |
| **Multi-mill / SaaS** | Multi-tenant orchestrator (one MillState per mill site), centralized model retraining across mills' anonymized data, buyer-facing report portal |

## 11. What to Say in the Pitch About This Layer

*"Each of our 10 agents works as an independent, testable microservice — you could deploy any one of them on its own tomorrow. What makes this one system, not ten tools, is the orchestrator: it owns a shared state object, decides what runs in what order, halts the pipeline the moment a batch fails quality or safety checks, and produces one report at the end that ties every department's data together. That's the 'brain' — and it's built the same way real production systems are, not just wired together for a demo."*
