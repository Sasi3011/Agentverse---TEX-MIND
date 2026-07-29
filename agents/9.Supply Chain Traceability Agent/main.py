from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uvicorn
from inference import TraceabilityInspector
from validators import CERTIFICATE_REGISTRY

app = FastAPI(
    title="Agent 09 — Tamil Nadu Supply Chain Traceability Agent",
    description="Production-ready AI Agent validating textile batch custody, GOTS/OEKO-TEX certificates, transit speed, mass yield, and Explainable AI anomaly detection for Tamil Nadu mills (Coimbatore, Tiruppur, Pollachi, Erode, Udumalpet).",
    version="3.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

inspector = TraceabilityInspector()

class CustodyEntry(BaseModel):
    stage: str = Field(..., json_schema_extra={"example": "farm"})
    entity: str = Field(..., json_schema_extra={"example": "Kongu Organic Cotton Farmers Co-op"})
    cert_ref: Optional[str] = Field(None, json_schema_extra={"example": "GOTS-TN-101"})
    timestamp: str = Field(..., json_schema_extra={"example": "2026-06-01"})

class SubmitLogRequest(BaseModel):
    batch_id: str = Field(..., json_schema_extra={"example": "B-TN-2026-001"})
    total_distance_km: float = Field(..., json_schema_extra={"example": 100.0})
    transit_hours: float = Field(..., json_schema_extra={"example": 5.0})
    raw_cotton_kg: float = Field(..., json_schema_extra={"example": 1000.0})
    finished_fabric_kg: float = Field(..., json_schema_extra={"example": 850.0})
    custody_log: List[CustodyEntry]

# In-memory batch store initialized with valid Tamil Nadu default batch
BATCH_STORE: Dict[str, Dict[str, Any]] = {
    "B-TN-2026-001": inspector.inspect_batch(
        batch_id="B-TN-2026-001",
        total_distance_km=100.0,
        transit_hours=5.0,
        raw_cotton_kg=1000.0,
        finished_fabric_kg=850.0,
        custody_log=[
            {"stage": "farm", "entity": "Kongu Organic Cotton Farmers Co-op", "cert_ref": "GOTS-TN-101", "timestamp": "2026-06-01"},
            {"stage": "ginning", "entity": "Coimbatore Modern Ginning Works", "cert_ref": "GOTS-TN-201", "timestamp": "2026-06-05"},
            {"stage": "spinning", "entity": "Lakshmi Mills Co-op Ltd", "cert_ref": "OEKO-TN-301", "timestamp": "2026-06-10"},
            {"stage": "weaving", "entity": "Tiruppur Knitwear & Weaving Park", "cert_ref": "OEKO-TN-401", "timestamp": "2026-06-15"},
            {"stage": "dyeing", "entity": "ZLD Dyeing Park", "cert_ref": "GOTS-TN-501", "timestamp": "2026-06-20"}
        ]
    )
}

@app.get("/agents/traceability/health")
def health_check():
    return {
        "status": "ok",
        "agent": "Agent 09 — Supply Chain Traceability Agent",
        "ecosystem": "Tamil Nadu Textile Cluster (Coimbatore, Tiruppur, Pollachi, Erode, Udumalpet)",
        "model_loaded": inspector.model is not None,
        "dataset_trained_samples": 1000000
    }

@app.get("/agents/traceability/certificates")
def get_certificate_registry():
    return {"certificate_registry": CERTIFICATE_REGISTRY}

@app.post("/agents/traceability/submit-log")
def submit_custody_log(req: SubmitLogRequest):
    custody_list = [entry.model_dump() for entry in req.custody_log]
    result = inspector.inspect_batch(
        batch_id=req.batch_id,
        custody_log=custody_list,
        total_distance_km=req.total_distance_km,
        transit_hours=req.transit_hours,
        raw_cotton_kg=req.raw_cotton_kg,
        finished_fabric_kg=req.finished_fabric_kg
    )
    BATCH_STORE[req.batch_id] = result
    return result

@app.get("/agents/traceability/status/{batch_id}")
def get_batch_status(batch_id: str):
    if batch_id in BATCH_STORE:
        return BATCH_STORE[batch_id]
    raise HTTPException(status_code=404, detail=f"Batch ID '{batch_id}' not found")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8009)
