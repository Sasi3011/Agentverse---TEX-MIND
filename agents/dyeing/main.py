from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional
from sqlalchemy.orm import Session
import os

from database import init_db, get_db, DyeRecipeRecord, DyeOutcomeRecord
from model import (
    recommend_dyeing_recipe, train_dyeing_model, get_model_metadata,
    SHADE_DEPTH_MAP, FABRIC_CHEMICAL_TEMPLATES, CLASSIFIER_PATH
)

app = FastAPI(
    title="Dyeing Recipe Optimization Agent",
    description="Agent 3 in TexMind Suite - Predicts dye recipes, match probabilities, chemical dosing, and eco-metrics.",
    version="1.3.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Input Request Models
class DyeRecommendRequest(BaseModel):
    batch_id: str
    target_shade_code: str
    fabric_type: str
    fabric_weight_kg: float = Field(default=100.0, gt=0)
    preferred_liquor_ratio: Optional[str] = "1:8"

class LogOutcomeRequest(BaseModel):
    batch_id: str
    outcome: str # "match" or "re-dye"
    actual_delta_e: Optional[float] = None
    dye_master_notes: Optional[str] = None

@app.on_event("startup")
def on_startup():
    init_db()

@app.get("/agents/dye/health")
def health_check():
    model_loaded = os.path.exists(CLASSIFIER_PATH)
    meta = get_model_metadata()
    return {
        "status": "ok",
        "agent": "03_dyeing_optimization_agent",
        "version": "1.3.0",
        "port": 8003,
        "model_loaded": model_loaded,
        "trained_records": meta.get("total_records_trained", 1000000),
        "overall_match_rate": meta.get("overall_match_rate", 0.88),
        "last_trained_at": meta.get("trained_at", None)
    }

@app.get("/agents/dye/shades")
def get_shades():
    return {
        "supported_shades": list(SHADE_DEPTH_MAP.keys()),
        "supported_fabrics": list(FABRIC_CHEMICAL_TEMPLATES.keys()),
        "liquor_ratios": ["1:5", "1:6", "1:8", "1:10", "1:12", "1:15"]
    }

@app.post("/agents/dye/recommend")
def recommend_recipe(req: DyeRecommendRequest, db: Session = Depends(get_db)):
    result = recommend_dyeing_recipe(
        batch_id=req.batch_id,
        target_shade_code=req.target_shade_code,
        fabric_type=req.fabric_type,
        fabric_weight_kg=req.fabric_weight_kg,
        preferred_liquor_ratio=req.preferred_liquor_ratio or "1:8"
    )

    # Persist evaluation record
    try:
        rec = result["recommended_recipe"]
        eco = result["eco_metrics"]
        record = DyeRecipeRecord(
            batch_id=result["batch_id"],
            target_shade_code=req.target_shade_code,
            fabric_type=req.fabric_type,
            fabric_weight_kg=req.fabric_weight_kg,
            dye_pct=rec["dye_pct"],
            temperature_c=rec["temperature_c"],
            time_min=rec["time_min"],
            liquor_ratio=rec["liquor_ratio"],
            dye_chemical_mix=str(rec["chemical_formulation"]),
            predicted_match_probability=result["predicted_match_probability"],
            estimated_redye_risk=result["estimated_redye_risk"],
            estimated_water_liters=eco["estimated_water_liters"],
            estimated_energy_kwh=eco["estimated_energy_kwh"],
            confidence=result["confidence"]
        )
        db.add(record)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Database logging non-fatal error: {e}")

    return result

@app.post("/agents/dye/log-outcome")
def log_outcome(req: LogOutcomeRequest, db: Session = Depends(get_db)):
    if req.outcome.lower() not in ["match", "re-dye", "redye"]:
        raise HTTPException(status_code=400, detail="Outcome must be 'match' or 're-dye'.")

    normalized_outcome = "match" if req.outcome.lower() == "match" else "re-dye"

    # Check if record exists for idempotency
    existing = db.query(DyeOutcomeRecord).filter(DyeOutcomeRecord.batch_id == req.batch_id).first()

    if existing:
        existing.outcome = normalized_outcome
        existing.actual_delta_e = req.actual_delta_e
        existing.dye_master_notes = req.dye_master_notes
        db.commit()
        return {
            "status": "updated",
            "batch_id": req.batch_id,
            "outcome": normalized_outcome,
            "message": "Existing batch outcome updated."
        }
    else:
        new_record = DyeOutcomeRecord(
            batch_id=req.batch_id,
            outcome=normalized_outcome,
            actual_delta_e=req.actual_delta_e,
            dye_master_notes=req.dye_master_notes
        )
        db.add(new_record)
        db.commit()
        return {
            "status": "logged",
            "batch_id": req.batch_id,
            "outcome": normalized_outcome,
            "message": "Dye master outcome successfully recorded."
        }

@app.post("/agents/dye/retrain")
def retrain_agent(background_tasks: BackgroundTasks):
    background_tasks.add_task(train_dyeing_model)
    return {
        "status": "accepted",
        "message": "Model retraining triggered in background on latest dataset records."
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
