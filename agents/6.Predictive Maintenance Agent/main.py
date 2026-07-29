from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any
from datetime import datetime
import os

try:
    from feature_extraction import SignalFeatureExtractor
    from health_model import MaintenancePredictor
except ImportError:
    try:
        from .feature_extraction import SignalFeatureExtractor
        from .health_model import MaintenancePredictor
    except ImportError:
        from feature_extraction import SignalFeatureExtractor
        from health_model import MaintenancePredictor

app = FastAPI(title="Agent 6 - Predictive Maintenance Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

extractor = SignalFeatureExtractor(window_size=30)
predictor = MaintenancePredictor()

# Monitored state
machines_state = {
    "LOOM-01": {"vibration_rms": 0.28, "temperature_c": 52.0, "operating_hours": 3200, "health_score": 0.88, "rul_days": 26.4, "priority": "healthy", "action": "Normal operation", "last_update": datetime.utcnow().isoformat()},
    "LOOM-02": {"vibration_rms": 0.85, "temperature_c": 74.5, "operating_hours": 6400, "health_score": 0.38, "rul_days": 2.8, "priority": "critical", "action": "Immediate bearing inspection & bearing replacement scheduled within 24h", "last_update": datetime.utcnow().isoformat()},
    "SPIN-01": {"vibration_rms": 0.32, "temperature_c": 55.0, "operating_hours": 2100, "health_score": 0.82, "rul_days": 24.6, "priority": "healthy", "action": "Normal operation", "last_update": datetime.utcnow().isoformat()},
    "SPIN-02": {"vibration_rms": 0.58, "temperature_c": 66.2, "operating_hours": 4900, "health_score": 0.59, "rul_days": 6.5, "priority": "warning", "action": "Schedule alignment and lubrication check during next shift change", "last_update": datetime.utcnow().isoformat()},
    "CARD-01": {"vibration_rms": 0.22, "temperature_c": 49.0, "operating_hours": 1500, "health_score": 0.94, "rul_days": 28.2, "priority": "healthy", "action": "Normal operation", "last_update": datetime.utcnow().isoformat()},
}

class SensorIngestRequest(BaseModel):
    machine_id: str
    vibration_rms: float
    temperature_c: float
    operating_hours: float = 3000.0
    timestamp: str = None

@app.get("/agents/maintenance/health")
async def health_check():
    return {
        "status": "online",
        "agent": "Agent 06 - Predictive Maintenance Agent",
        "timestamp": datetime.utcnow().isoformat(),
        "monitored_machines": len(machines_state),
        "model_status": "loaded" if predictor.model_bundle else "heuristic_fallback"
    }

@app.post("/agents/maintenance/ingest")
async def ingest_sensor_telemetry(data: SensorIngestRequest):
    feat = extractor.extract_features(
        data.machine_id, 
        data.vibration_rms, 
        data.temperature_c, 
        data.operating_hours
    )
    
    pred = predictor.predict(
        vibration_rms=feat["vibration_rms"],
        vibration_kurtosis=feat["vibration_kurtosis"],
        temperature_c=feat["temperature_c"],
        operating_hours=feat["operating_hours"]
    )
    
    ts = data.timestamp or datetime.utcnow().isoformat()
    
    machines_state[data.machine_id] = {
        "vibration_rms": data.vibration_rms,
        "vibration_kurtosis": feat["vibration_kurtosis"],
        "temperature_c": data.temperature_c,
        "operating_hours": data.operating_hours,
        "health_score": pred["health_score"],
        "rul_days": pred["estimated_remaining_useful_life_days"],
        "priority": pred["priority"],
        "action": pred["recommended_action"],
        "last_update": ts
    }
    
    return {
        "machine_id": data.machine_id,
        "health_score": pred["health_score"],
        "estimated_remaining_useful_life_days": pred["estimated_remaining_useful_life_days"],
        "priority": pred["priority"],
        "recommended_action": pred["recommended_action"],
        "features": feat,
        "timestamp": ts
    }

@app.get("/agents/maintenance/queue")
async def get_maintenance_queue():
    queue = []
    for m_id, state in machines_state.items():
        if state["priority"] in ["critical", "warning"]:
            queue.append({
                "machine_id": m_id,
                "priority": state["priority"],
                "health_score": state["health_score"],
                "estimated_remaining_useful_life_days": state["rul_days"],
                "recommended_action": state["action"],
                "last_update": state["last_update"]
            })
            
    # Sort queue by health score ascending (most critical first)
    queue.sort(key=lambda x: x["health_score"])
    return {
        "queue_length": len(queue),
        "maintenance_queue": queue,
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/agents/maintenance/machines")
async def get_all_machines():
    return {
        "machines": machines_state,
        "timestamp": datetime.utcnow().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8006, reload=True)
