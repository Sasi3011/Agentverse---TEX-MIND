from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import uvicorn
from aggregator import SustainabilityAggregator

app = FastAPI(
    title="Agent 10 — Sustainability & Carbon Reporting Agent",
    description="Aggregates outputs from Agent 4 (effluent), Agent 5 (energy), and Agent 9 (traceability) into consolidated ESG export reports for export buyers (H&M, Marks & Spencer, Zara). Trained on 1,000,000 historical ESG audit records.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

aggregator = SustainabilityAggregator()

class ReportRequest(BaseModel):
    batch_id: str = Field(..., json_schema_extra={"example": "B-2026-0001"})
    period: Optional[str] = Field("2026-07", json_schema_extra={"example": "2026-07"})
    buyer_template: Optional[str] = Field("H&M Export Standard", json_schema_extra={"example": "H&M Export Standard"})
    energy_used_kwh: Optional[float] = Field(3820.0, json_schema_extra={"example": 3820.0})
    water_compliance: Optional[str] = Field("compliant", json_schema_extra={"example": "compliant"})
    traceability_status: Optional[str] = Field("verified_sustainable", json_schema_extra={"example": "verified_sustainable"})
    traceability_score: Optional[float] = Field(100.0, json_schema_extra={"example": 100.0})

# In-memory storage for reports
REPORT_STORE: Dict[str, Dict[str, Any]] = {
    "B-2026-0001": aggregator.generate_batch_report(
        batch_id="B-2026-0001",
        period="2026-07",
        buyer_template="H&M Export Standard",
        energy_used_kwh=3820.0,
        water_compliance="compliant",
        traceability_status="verified_sustainable",
        traceability_score=100.0
    )
}

@app.get("/agents/sustainability/health")
def health_check():
    return {
        "status": "ok",
        "agent": "Agent 10 — Sustainability & Carbon Reporting",
        "model_loaded": aggregator.model is not None,
        "grid_emission_factor": 0.82,
        "dataset_trained_samples": 1000000
    }

@app.post("/agents/sustainability/generate-report")
def generate_report(req: ReportRequest):
    result = aggregator.generate_batch_report(
        batch_id=req.batch_id,
        period=req.period or "2026-07",
        buyer_template=req.buyer_template or "H&M Export Standard",
        energy_used_kwh=req.energy_used_kwh or 3820.0,
        water_compliance=req.water_compliance or "compliant",
        traceability_status=req.traceability_status or "verified_sustainable",
        traceability_score=req.traceability_score if req.traceability_score is not None else 100.0
    )
    REPORT_STORE[req.batch_id] = result
    return result

@app.get("/agents/sustainability/report/{batch_id}")
def get_report(batch_id: str):
    if batch_id in REPORT_STORE:
        return REPORT_STORE[batch_id]
    raise HTTPException(status_code=404, detail=f"Report for Batch ID '{batch_id}' not found")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8010)
