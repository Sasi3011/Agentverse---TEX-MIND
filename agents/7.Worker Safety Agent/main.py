from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any
from datetime import datetime
import os

try:
    from safety_model import SafetyPredictor
except ImportError:
    try:
        from .safety_model import SafetyPredictor
    except ImportError:
        from safety_model import SafetyPredictor

app = FastAPI(title="Agent 07 - Worker Safety Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

predictor = SafetyPredictor()

# Monitored live zones state
zones_state = {
    "DYE-FLOOR-A": {
        "zone_name": "Dyeing Process Floor Alpha", "camera_id": "CAM-01", "status": "SECURE",
        "risk_score": 0.08, "worker_count": 4, "violations_count": 0,
        "ppe_state": {"helmet": True, "vest": True, "ear_protection": True, "gloves": True},
        "hazard_zone_intrusion": False, "last_update": datetime.utcnow().isoformat()
    },
    "WEAVE-BAY-01": {
        "zone_name": "High-Speed Weaving Loom Bay 1", "camera_id": "CAM-02", "status": "CRITICAL",
        "risk_score": 0.88, "worker_count": 5, "violations_count": 2,
        "ppe_state": {"helmet": True, "vest": True, "ear_protection": False, "gloves": True},
        "hazard_zone_intrusion": True, "last_update": datetime.utcnow().isoformat()
    },
    "CARDING-Z2": {
        "zone_name": "Fiber Carding & Spinning Zone 2", "camera_id": "CAM-03", "status": "SECURE",
        "risk_score": 0.12, "worker_count": 3, "violations_count": 0,
        "ppe_state": {"helmet": True, "vest": True, "ear_protection": True, "gloves": True},
        "hazard_zone_intrusion": False, "last_update": datetime.utcnow().isoformat()
    },
    "FINISHING-LINE-03": {
        "zone_name": "Stenter & Heat Finishing Line 3", "camera_id": "CAM-04", "status": "WARNING",
        "risk_score": 0.45, "worker_count": 2, "violations_count": 1,
        "ppe_state": {"helmet": True, "vest": True, "ear_protection": True, "gloves": False},
        "hazard_zone_intrusion": False, "last_update": datetime.utcnow().isoformat()
    }
}

violation_logs = [
    {
        "id": "EVT-8821",
        "timestamp": datetime.utcnow().isoformat(),
        "zone_id": "WEAVE-BAY-01",
        "camera_id": "CAM-02",
        "violation_type": "HAZARD_ZONE_INTRUSION",
        "severity": "CRITICAL",
        "worker_id": "W-4029",
        "action_taken": "Automated loom emergency pause signal emitted & Supervisor alert dispatched."
    },
    {
        "id": "EVT-8819",
        "timestamp": datetime.utcnow().isoformat(),
        "zone_id": "FINISHING-LINE-03",
        "camera_id": "CAM-04",
        "violation_type": "MISSING_GLOVES",
        "severity": "WARNING",
        "worker_id": "W-1108",
        "action_taken": "Audio floor chime played: 'Please wear protective chemical gloves'."
    }
]

class SafetyInspectionRequest(BaseModel):
    zone_id: str
    worker_count: int = 1
    helmet_present: bool = True
    vest_present: bool = True
    ear_protection_present: bool = True
    gloves_present: bool = True
    hazard_zone_intrusion: bool = False
    confidence: float = 0.94
    ambient_noise_db: float = 78.0
    light_level_lux: float = 450.0

@app.get("/agents/safety/health")
async def health_check():
    return {
        "status": "online",
        "agent": "Agent 07 - Worker Safety Agent",
        "timestamp": datetime.utcnow().isoformat(),
        "active_zones": len(zones_state),
        "model_status": "loaded" if predictor.model_bundle else "heuristic_fallback"
    }

@app.get("/agents/safety/zones")
async def get_zones():
    return zones_state

@app.get("/agents/safety/violations")
async def get_violations():
    return violation_logs

@app.post("/agents/safety/inspect")
async def inspect_safety(data: SafetyInspectionRequest):
    if data.zone_id not in zones_state:
        raise HTTPException(status_code=404, detail=f"Zone {data.zone_id} not registered.")
        
    res = predictor.inspect_frame(
        zone_id=data.zone_id,
        worker_count=data.worker_count,
        helmet_present=data.helmet_present,
        vest_present=data.vest_present,
        ear_protection_present=data.ear_protection_present,
        gloves_present=data.gloves_present,
        hazard_zone_intrusion=data.hazard_zone_intrusion,
        confidence=data.confidence,
        ambient_noise_db=data.ambient_noise_db,
        light_level_lux=data.light_level_lux
    )
    
    # Update live state
    zones_state[data.zone_id].update({
        "status": res["status"],
        "risk_score": res["risk_score"],
        "worker_count": data.worker_count,
        "violations_count": res["violations_count"],
        "ppe_state": res["ppe_state"],
        "hazard_zone_intrusion": res["hazard_zone_intrusion"],
        "last_update": datetime.utcnow().isoformat()
    })
    
    if res["violations"]:
        for v in res["violations"]:
            violation_logs.insert(0, {
                "id": f"EVT-{len(violation_logs)+8822}",
                "timestamp": datetime.utcnow().isoformat(),
                "zone_id": data.zone_id,
                "camera_id": zones_state[data.zone_id]["camera_id"],
                "violation_type": v["type"],
                "severity": v["severity"],
                "worker_id": "W-DEMO",
                "action_taken": f"Logged {v['severity']} alert & dispatched supervisor audio notification."
            })
            
    return res

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8007)
