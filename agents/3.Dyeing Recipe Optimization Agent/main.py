from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional
from sqlalchemy.orm import Session
import os

from database import init_db, get_db, DyeingOutcomeRecord
from model import get_dyeing_recommendation

app = FastAPI(title="Dyeing Recipe Optimization Agent", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Input Schemas
class DyeRecommendRequest(BaseModel):
    batch_id: str
    target_shade_code: str
    fabric_type: str

class DyeRecommendResponse(BaseModel):
    batch_id: str
    recommended_recipe: dict
    predicted_match_probability: float
    estimated_redye_risk: str
    prediction_source: str = "random_forest_ml"

class LogOutcomeRequest(BaseModel):
    batch_id: str
    outcome: str # "match" or "re-dye"

@app.on_event("startup")
def on_startup():
    init_db()

@app.get("/agents/dye/health")
def health_check():
    return {
        "status": "ok",
        "agent": "Dyeing Recipe Optimization Agent"
    }

@app.post("/agents/dye/recommend", response_model=DyeRecommendResponse)
def recommend_recipe(req: DyeRecommendRequest, db: Session = Depends(get_db)):
    existing = db.query(DyeingOutcomeRecord).filter(DyeingOutcomeRecord.batch_id == req.batch_id).first()
    if existing and existing.target_shade_code == req.target_shade_code and existing.fabric_type == req.fabric_type:
        return {
            "batch_id": existing.batch_id,
            "recommended_recipe": {
                "dye_pct": existing.dye_pct,
                "temperature_c": existing.temperature_c,
                "time_min": existing.time_min,
                "liquor_ratio": existing.liquor_ratio,
            },
            "predicted_match_probability": existing.match_probability,
            "estimated_redye_risk": "low" if existing.match_probability >= 0.8 else "medium",
            "prediction_source": "cached_record",
        }

    res = get_dyeing_recommendation(req.batch_id, req.target_shade_code, req.fabric_type)
    recipe = res["recommended_recipe"]

    if existing:
        existing.target_shade_code = req.target_shade_code
        existing.fabric_type = req.fabric_type
        existing.dye_pct = recipe["dye_pct"]
        existing.temperature_c = recipe["temperature_c"]
        existing.time_min = recipe["time_min"]
        existing.liquor_ratio = recipe["liquor_ratio"]
        existing.match_probability = res["predicted_match_probability"]
        existing.outcome = None
    else:
        record = DyeingOutcomeRecord(
            batch_id=req.batch_id,
            target_shade_code=req.target_shade_code,
            fabric_type=req.fabric_type,
            dye_pct=recipe["dye_pct"],
            temperature_c=recipe["temperature_c"],
            time_min=recipe["time_min"],
            liquor_ratio=recipe["liquor_ratio"],
            match_probability=res["predicted_match_probability"],
        )
        db.add(record)
    db.commit()

    return res

@app.post("/agents/dye/log-outcome")
def log_outcome(req: LogOutcomeRequest, db: Session = Depends(get_db)):
    if req.outcome not in ["match", "re-dye"]:
        raise HTTPException(status_code=400, detail="Outcome must be 'match' or 're-dye'")

    record = db.query(DyeingOutcomeRecord).filter(DyeingOutcomeRecord.batch_id == req.batch_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Batch recommendation not found. Must recommend recipe first.")

    record.outcome = req.outcome
    db.commit()

    return {"status": "success", "message": f"Logged outcome '{req.outcome}' for batch {req.batch_id}"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8003, reload=True)
