import os
import json
import asyncio
from typing import Any

import httpx

INTAKE_URL = os.getenv("INTAKE_AGENT_URL", "http://127.0.0.1:8001")
DEFECT_URL = os.getenv("DEFECT_AGENT_URL", "http://127.0.0.1:8002")
DYE_URL = os.getenv("DYE_AGENT_URL", "http://127.0.0.1:8003")
EFFLUENT_URL = os.getenv("EFFLUENT_AGENT_URL", "http://127.0.0.1:8004")
ENERGY_URL = os.getenv("ENERGY_AGENT_URL", "http://127.0.0.1:8005")
MAINTENANCE_URL = os.getenv("MAINTENANCE_AGENT_URL", "http://127.0.0.1:8006")
SAFETY_URL = os.getenv("SAFETY_AGENT_URL", "http://127.0.0.1:8007")
DEMAND_URL = os.getenv("DEMAND_AGENT_URL", "http://127.0.0.1:8008")
TRACE_URL = os.getenv("TRACE_AGENT_URL", "http://127.0.0.1:8009")
SUSTAINABILITY_URL = os.getenv("SUSTAINABILITY_AGENT_URL", "http://127.0.0.1:8010")
NOTIFICATION_URL = os.getenv("NOTIFICATION_AGENT_URL", "http://127.0.0.1:8011")

GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta"

AGENT_CATALOG = """
TexMind Multi-Agent Cognitive Suite (Textile Mill Digital Twin):

Agent 00 — Master Brain Orchestrator (port 8020)
Agent 01 — Raw Material Intake (port 8001) — XGBoost Classifier
Agent 02 — Weaving Defect Detection (port 8002) — OpenCV vision
Agent 03 — Dyeing Recipe Optimization (port 8003) — Random Forest
Agent 04 — Effluent Compliance ETP (port 8004) — Isolation Forest
Agent 05 — Energy Optimization (port 8005) — XGBoost baseline
Agent 06 — Predictive Maintenance (port 8006) — Weibull RUL
Agent 07 — Worker Safety Monitor (port 8007) — YOLOv8
Agent 08 — Demand Forecasting (port 8008) — Facebook Prophet
Agent 09 — Supply Chain Traceability (port 8009) — Random Forest + SHA-256
Agent 10 — Sustainability ESG (port 8010) — Random Forest ESG Grader
Agent 11 — Notification & Tamil IVR (port 8011) — gTTS + Asterisk

Pipeline: Intake → Defect → Dyeing → Traceability → ESG (with background ETP/Energy/Safety/Maintenance)
"""


def _gemini_headers(api_key: str) -> dict:
    return {
        "x-goog-api-key": api_key,
        "Content-Type": "application/json",
    }


def _format_value(data: Any) -> str:
    if data is None:
        return "offline / no data"
    if isinstance(data, (dict, list)):
        return json.dumps(data, indent=2, default=str)
    return str(data)


async def _fetch_json(client: httpx.AsyncClient, url: str) -> Any:
    try:
        res = await client.get(url, timeout=4.0)
        if res.status_code == 200:
            return res.json()
    except Exception:
        pass
    return None


async def gather_live_context(
    latest_state: dict,
    background_snapshots: dict,
    pipeline_history: list,
) -> dict:
    async with httpx.AsyncClient() as client:
        results = await asyncio.gather(
            _fetch_json(client, f"{INTAKE_URL}/agents/intake/health"),
            _fetch_json(client, f"{DEFECT_URL}/agents/defect/health"),
            _fetch_json(client, f"{DEFECT_URL}/agents/defect/model-info"),
            _fetch_json(client, f"{DYE_URL}/agents/dye/health"),
            _fetch_json(client, f"{EFFLUENT_URL}/agents/effluent/status"),
            _fetch_json(client, f"{ENERGY_URL}/agents/energy/report"),
            _fetch_json(client, f"{MAINTENANCE_URL}/agents/maintenance/queue"),
            _fetch_json(client, f"{MAINTENANCE_URL}/agents/maintenance/machines"),
            _fetch_json(client, f"{SAFETY_URL}/agents/safety/health"),
            _fetch_json(client, f"{SAFETY_URL}/agents/safety/violations"),
            _fetch_json(client, f"{DEMAND_URL}/agents/demand/health"),
            _fetch_json(client, f"{TRACE_URL}/agents/traceability/health"),
            _fetch_json(client, f"{SUSTAINABILITY_URL}/agents/sustainability/health"),
            _fetch_json(client, f"{NOTIFICATION_URL}/agents/notification/health"),
            _fetch_json(client, f"{NOTIFICATION_URL}/agents/notification/active-alerts"),
            return_exceptions=True,
        )

    keys = [
        "intake_health", "defect_health", "defect_model", "dye_health",
        "effluent_live", "energy_live", "maintenance_queue", "maintenance_machines",
        "safety_health", "safety_violations", "demand_health", "trace_health",
        "sustainability_health", "notification_health", "notification_alerts",
    ]
    live = {k: (v if not isinstance(v, Exception) else None) for k, v in zip(keys, results)}

    return {
        "latest_batch_state": latest_state,
        "background_snapshots": background_snapshots,
        "pipeline_history": pipeline_history[:5],
        "live_agent_telemetry": live,
    }


def _build_gemini_prompt(query: str, context: dict) -> str:
    state = context.get("latest_batch_state") or {}
    live = context.get("live_agent_telemetry") or {}
    history = context.get("pipeline_history") or []
    snapshots = context.get("background_snapshots") or {}

    return f"""{AGENT_CATALOG}

=== LIVE SYSTEM DATA (fetched from real agent endpoints just now) ===

LATEST BATCH PIPELINE STATE:
{_format_value(state)}

BACKGROUND MONITOR SNAPSHOTS:
{_format_value(snapshots)}

LIVE AGENT TELEMETRY:
Agent 01 Intake Health: {_format_value(live.get('intake_health'))}
Agent 02 Defect Health: {_format_value(live.get('defect_health'))}
Agent 02 Defect Model Info: {_format_value(live.get('defect_model'))}
Agent 03 Dye Health: {_format_value(live.get('dye_health'))}
Agent 04 ETP Live Sensors: {_format_value(live.get('effluent_live'))}
Agent 05 Energy Live Report: {_format_value(live.get('energy_live'))}
Agent 06 Maintenance Queue: {_format_value(live.get('maintenance_queue'))}
Agent 06 Machine Health: {_format_value(live.get('maintenance_machines'))}
Agent 07 Safety Health: {_format_value(live.get('safety_health'))}
Agent 07 Active Violations: {_format_value(live.get('safety_violations'))}
Agent 08 Demand Health: {_format_value(live.get('demand_health'))}
Agent 09 Traceability Health: {_format_value(live.get('trace_health'))}
Agent 10 Sustainability Health: {_format_value(live.get('sustainability_health'))}
Agent 11 Notification Health: {_format_value(live.get('notification_health'))}
Agent 11 Active Alerts: {_format_value(live.get('notification_alerts'))}

RECENT PIPELINE HISTORY ({len(history)} batches):
{_format_value(history)}

=== USER QUESTION ===
{query}

=== INSTRUCTIONS ===
You are the TexMind Senior AI Copilot powered by Google Gemini.

Analyze ONLY the live agent data provided above and answer the user's question.

STRICT RULES:
1. Use ONLY values present in the live data above. Never invent, estimate, or use placeholder numbers.
2. If a value is missing or an agent shows "offline / no data", say so clearly.
3. Write in natural conversational prose with markdown formatting (headers, bold, bullet points).
4. Do NOT output JSON, code blocks of raw data, or structured API responses.
5. Explain agent processes, ML models, inputs, outputs, and pipeline connections based on real telemetry.
6. Be thorough but readable — like a senior engineer briefing the mill manager.
"""


async def _list_available_models(client: httpx.AsyncClient, api_key: str) -> list[str]:
    res = await client.get(
        f"{GEMINI_BASE}/models",
        headers=_gemini_headers(api_key),
        timeout=15.0,
    )
    if res.status_code != 200:
        raise RuntimeError(f"Could not list Gemini models: HTTP {res.status_code} — {res.text[:300]}")

    models = []
    for m in res.json().get("models", []):
        name = m.get("name", "")
        methods = m.get("supportedGenerationMethods", [])
        if "generateContent" in methods and name.startswith("models/"):
            models.append(name.replace("models/", ""))

    if not models:
        raise RuntimeError("No Gemini models available for generateContent")

    flash = [m for m in models if "flash" in m.lower()]
    return flash + [m for m in models if m not in flash]


async def call_gemini(query: str, context: dict) -> tuple[str, str]:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set in .env")

    prompt = _build_gemini_prompt(query, context)
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 2048,
        },
    }

    last_error = None
    async with httpx.AsyncClient() as client:
        models = await _list_available_models(client, api_key)

        for model in models:
            url = f"{GEMINI_BASE}/models/{model}:generateContent"
            try:
                res = await client.post(
                    url,
                    json=payload,
                    headers=_gemini_headers(api_key),
                    timeout=45.0,
                )
                if res.status_code == 200:
                    data = res.json()
                    text = data["candidates"][0]["content"]["parts"][0]["text"]
                    return text.strip(), model
                last_error = f"{model}: HTTP {res.status_code} — {res.text[:200]}"
            except Exception as exc:
                last_error = f"{model}: {exc}"

    raise RuntimeError(f"All Gemini models failed. Last error: {last_error}")


async def generate_copilot_response(
    query: str,
    latest_state: dict,
    background_snapshots: dict,
    pipeline_history: list,
) -> dict:
    context = await gather_live_context(latest_state, background_snapshots, pipeline_history)
    agents_polled = sum(1 for v in context["live_agent_telemetry"].values() if v is not None)

    response_text, model = await call_gemini(query, context)
    return {
        "query": query,
        "response": response_text,
        "source": f"Google Gemini ({model})",
        "agents_polled": agents_polled,
    }


