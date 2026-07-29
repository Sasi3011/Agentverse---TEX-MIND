import os
import asyncio
import httpx
from datetime import datetime
from shared_state import MillState

# Service URL configurations (Docker services can use hostnames, local runs fallback to localhost ports)
INTAKE_URL = os.getenv("INTAKE_AGENT_URL", "http://localhost:8001")
DEFECT_URL = os.getenv("DEFECT_AGENT_URL", "http://localhost:8002")
DYE_URL = os.getenv("DYE_AGENT_URL", "http://localhost:8003")
EFFLUENT_URL = os.getenv("EFFLUENT_AGENT_URL", "http://localhost:8004")
ENERGY_URL = os.getenv("ENERGY_AGENT_URL", "http://localhost:8005")
MAINTENANCE_URL = os.getenv("MAINTENANCE_AGENT_URL", "http://localhost:8006")
SAFETY_URL = os.getenv("SAFETY_AGENT_URL", "http://localhost:8007")
DEMAND_URL = os.getenv("DEMAND_AGENT_URL", "http://localhost:8008")
TRACE_URL = os.getenv("TRACE_AGENT_URL", "http://localhost:8009")
SUSTAINABILITY_URL = os.getenv("SUSTAINABILITY_AGENT_URL", "http://localhost:8010")

# Always-on snapshot state
background_snapshots = {
    "effluent_status": None,
    "energy_status": None,
    "maintenance_queue": None,
    "safety_status": None,
    "demand_forecast": None
}

async def run_batch_pipeline(batch_id: str, supplier_id: str, fiber_count: int, strength: float, moisture: float, target_shade: str, fabric_type: str) -> MillState:
    state = MillState(batch_id=batch_id, created_at=datetime.utcnow())
    async with httpx.AsyncClient() as client:
        # Step 1: Intake Agent
        try:
            res = await client.post(f"{INTAKE_URL}/agents/intake/evaluate", json={
                "batch_id": batch_id,
                "supplier_id": supplier_id,
                "fiber_count": fiber_count,
                "tensile_strength_g_tex": strength,
                "moisture_pct": moisture
            }, timeout=5.0)
            if res.status_code == 200:
                state.intake_result = res.json()
                if state.intake_result.get("decision") == "flag":
                    state.status = "halted"
                    state.halted_reason = f"Intake flagged quality issues: {', '.join(state.intake_result.get('flags', []))}"
                    return state
            else:
                state.status = "halted"
                state.halted_reason = f"Intake Agent returned error: {res.status_code}"
                return state
        except Exception as e:
            state.status = "halted"
            state.halted_reason = f"Failed to reach Intake Agent: {e}"
            return state

        # Step 2: Weaving Defect Detection Agent (Generate dummy image in memory)
        try:
            # 1x1 Transparent GIF bytes
            dummy_image = b'GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
            files = {"file": ("dummy.gif", dummy_image, "image/gif")}
            data = {"batch_id": batch_id, "roll_position_m": 12.5}
            res = await client.post(f"{DEFECT_URL}/agents/defect/inspect", data=data, files=files, timeout=5.0)
            if res.status_code == 200:
                state.defect_result = res.json()
                if state.defect_result.get("decision") == "reject roll":
                    state.status = "halted"
                    state.halted_reason = "Defect detection rejected the fabric roll."
                    return state
            else:
                state.status = "halted"
                state.halted_reason = f"Defect Agent returned error: {res.status_code}"
                return state
        except Exception as e:
            state.status = "halted"
            state.halted_reason = f"Failed to reach Defect Agent: {e}"
            return state

        # Step 3: Dyeing Recipe Optimization Agent
        try:
            res = await client.post(f"{DYE_URL}/agents/dye/recommend", json={
                "batch_id": batch_id,
                "target_shade_code": target_shade,
                "fabric_type": fabric_type
            }, timeout=5.0)
            if res.status_code == 200:
                state.dye_recipe = res.json()
            else:
                state.status = "halted"
                state.halted_reason = f"Dyeing Agent returned error: {res.status_code}"
                return state
        except Exception as e:
            state.status = "halted"
            state.halted_reason = f"Failed to reach Dyeing Agent: {e}"
            return state

        # Inject Background Snapshots
        state.effluent_status = background_snapshots["effluent_status"]
        state.energy_status = background_snapshots["energy_status"]
        state.maintenance_queue = background_snapshots["maintenance_queue"]
        state.safety_status = background_snapshots["safety_status"]

        # Step 4: Supply Chain Traceability Agent
        try:
            res = await client.post(f"{TRACE_URL}/agents/traceability/submit-log", json={
                "batch_id": batch_id,
                "total_distance_km": 120.0,
                "transit_hours": 6.5,
                "raw_cotton_kg": 1050.0,
                "finished_fabric_kg": 900.0,
                "custody_log": [
                    {"stage": "farm", "entity": "Kongu Organic Cotton Farmers Co-op", "cert_ref": "GOTS-TN-101", "timestamp": "2026-06-01"},
                    {"stage": "ginning", "entity": "Coimbatore Modern Ginning Works", "cert_ref": "GOTS-TN-201", "timestamp": "2026-06-05"},
                    {"stage": "spinning", "entity": "Lakshmi Mills Co-op Ltd", "cert_ref": "OEKO-TN-301", "timestamp": "2026-06-10"},
                    {"stage": "weaving", "entity": "Tiruppur Knitwear & Weaving Park", "cert_ref": "OEKO-TN-401", "timestamp": "2026-06-15"},
                    {"stage": "dyeing", "entity": "ZLD Dyeing Park", "cert_ref": "GOTS-TN-501", "timestamp": "2026-06-20"}
                ]
            }, timeout=5.0)
            if res.status_code == 200:
                state.traceability_record = res.json()
            else:
                state.status = "halted"
                state.halted_reason = f"Traceability Agent returned error: {res.status_code}"
                return state
        except Exception as e:
            state.status = "halted"
            state.halted_reason = f"Failed to reach Traceability Agent: {e}"
            return state

        # Step 5: Sustainability & Carbon Reporting Agent
        effluent_data = state.effluent_status or {"status": "compliant"}
        energy_data = state.energy_status or {"power_kwh": 3820.0}

        try:
            res = await client.post(f"{SUSTAINABILITY_URL}/agents/sustainability/generate-report", json={
                "batch_id": batch_id,
                "period": datetime.utcnow().strftime("%Y-%m"),
                "buyer_template": "H&M Export Standard",
                "energy_used_kwh": float(energy_data.get("power_kwh", 3820.0)) if isinstance(energy_data, dict) else 3820.0,
                "water_compliance": "compliant" if (isinstance(effluent_data, dict) and effluent_data.get("status") == "compliant") else "non-compliant",
                "traceability_status": state.traceability_record.get("traceability_status", "verified_sustainable") if state.traceability_record else "verified_sustainable",
                "traceability_score": float(state.traceability_record.get("traceability_score", 100.0)) if state.traceability_record else 100.0
            }, timeout=5.0)
            if res.status_code == 200:
                state.sustainability_report = res.json()
                state.status = "completed"
            else:
                state.status = "halted"
                state.halted_reason = f"Sustainability Agent returned error: {res.status_code}"
        except Exception as e:
            state.status = "halted"
            state.halted_reason = f"Failed to reach Sustainability Agent: {e}"

        return state

async def poll_background_agents():
    """Periodically queries always-on agents to populate shared memory snapshots."""
    while True:
        async with httpx.AsyncClient() as client:
            # Poll Effluent (Agent 4)
            try:
                res = await client.get(f"{EFFLUENT_URL}/agents/effluent/status", timeout=2.0)
                if res.status_code == 200:
                    background_snapshots["effluent_status"] = res.json()
            except Exception:
                pass

            # Poll Energy (Agent 5)
            try:
                res = await client.get(f"{ENERGY_URL}/agents/energy/report", timeout=2.0)
                if res.status_code == 200:
                    reports = res.json()
                    background_snapshots["energy_status"] = reports[0] if reports else {"power_kwh": 295.0, "status": "normal"}
            except Exception:
                pass

            # Poll Maintenance Queue (Agent 6)
            try:
                res = await client.get(f"{MAINTENANCE_URL}/agents/maintenance/queue", timeout=2.0)
                if res.status_code == 200:
                    background_snapshots["maintenance_queue"] = res.json().get("maintenance_queue", [])
            except Exception:
                pass

            # Poll Worker Safety (Agent 7)
            # Since Safety might only have ingest/telemetry, we mock/set its active state
            background_snapshots["safety_status"] = {"status": "all_clear", "ppe_compliance_rate": 1.0}

            # Poll Demand Forecast (Agent 8) - Runs on a slightly longer trigger
            try:
                res = await client.get(f"{DEMAND_URL}/agents/demand/forecast", timeout=2.0)
                if res.status_code == 200:
                    background_snapshots["demand_forecast"] = res.json()
            except Exception:
                pass

        await asyncio.sleep(5)
