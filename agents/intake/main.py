from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional
from sqlalchemy.orm import Session
import os

from database import init_db, get_db, IntakeRecord
from model import evaluate_batch, MODEL_PATH

app = FastAPI(title="Raw Material Intake Agent", version="1.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Input Schema
class IntakeRequest(BaseModel):
    batch_id: str
    supplier_id: str
    fiber_count: int = Field(gt=0)
    tensile_strength_g_tex: float = Field(gt=0)
    moisture_pct: float = Field(ge=0)

# Output Schema
class IntakeResponse(BaseModel):
    batch_id: str
    decision: str
    quality_score: float
    flags: List[str]
    confidence: float

@app.on_event("startup")
def on_startup():
    init_db()

@app.get("/agents/intake/health")
def health_check():
    model_loaded = os.path.exists(MODEL_PATH)
    return {
        "status": "ok", 
        "model_version": "1.2.0", 
        "model_loaded": model_loaded
    }

@app.post("/agents/intake/evaluate", response_model=IntakeResponse)
def evaluate_material(req: IntakeRequest, db: Session = Depends(get_db)):
    # 1. Evaluate
    result = evaluate_batch(
        batch_id=req.batch_id,
        supplier_id=req.supplier_id,
        fiber_count=req.fiber_count,
        strength=req.tensile_strength_g_tex,
        moisture=req.moisture_pct
    )
    
    # 2. Persist
    try:
        record = IntakeRecord(
            batch_id=result["batch_id"],
            supplier_id=req.supplier_id,
            fiber_count=req.fiber_count,
            tensile_strength=req.tensile_strength_g_tex,
            moisture=req.moisture_pct,
            decision=result["decision"],
            quality_score=result["quality_score"],
            confidence=result["confidence"]
        )
        db.add(record)
        db.commit()
    except Exception as e:
        db.rollback()
        # Non-fatal error, but log it
        print(f"Failed to persist record: {e}")
        
    return result
