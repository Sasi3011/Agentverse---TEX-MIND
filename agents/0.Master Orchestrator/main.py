import os
import asyncio
from dotenv import load_dotenv

# Load global environment variables from .env
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import Session
from datetime import datetime

from database import init_db, get_db, BatchStateModel
from shared_state import MillState
from orchestrator import run_batch_pipeline, poll_background_agents, background_snapshots
from copilot_engine import generate_copilot_response

def _serialize_state(state: MillState) -> dict:
    if hasattr(state, "model_dump"):
        return state.model_dump(mode="json")
    return state.dict()

app = FastAPI(title="TEXMIND Master Orchestrator Agent", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class TriggerBatchRequest(BaseModel):
    batch_id: str
    supplier_id: str = "SUP-01"
    fiber_count: int = 30
    tensile_strength_g_tex: float = 19.8
    moisture_pct: float = 7.2
    target_shade_code: str = "BOTTLE-GREEN-30"
    fabric_type: str = "nylon_taffeta"

@app.on_event("startup")
def on_startup():
    init_db()
    # Run background agent polling loop
    asyncio.create_task(poll_background_agents())

@app.get("/orchestrator/health")
def health():
    return {"status": "ok", "orchestrator": "active"}

@app.post("/orchestrator/trigger-batch", response_model=MillState)
async def trigger_batch(req: TriggerBatchRequest, db: Session = Depends(get_db)):
    # Run the pipeline
    final_state = await run_batch_pipeline(
        batch_id=req.batch_id,
        supplier_id=req.supplier_id,
        fiber_count=req.fiber_count,
        strength=req.tensile_strength_g_tex,
        moisture=req.moisture_pct,
        target_shade=req.target_shade_code,
        fabric_type=req.fabric_type
    )

    # Save to database
    # Check if exists
    existing = db.query(BatchStateModel).filter(BatchStateModel.batch_id == req.batch_id).first()
    payload = _serialize_state(final_state)
    if existing:
        existing.state_json = payload
    else:
        new_record = BatchStateModel(
            batch_id=req.batch_id,
            state_json=payload
        )
        db.add(new_record)
    db.commit()

    return final_state

@app.get("/orchestrator/state/{batch_id}", response_model=MillState)
def get_batch_state(batch_id: str, db: Session = Depends(get_db)):
    record = db.query(BatchStateModel).filter(BatchStateModel.batch_id == batch_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Batch state not found")
    return record.state_json

@app.get("/orchestrator/history", response_model=List[MillState])
def get_pipeline_history(db: Session = Depends(get_db)):
    records = db.query(BatchStateModel).order_by(BatchStateModel.created_at.desc()).all()
    return [r.state_json for r in records]

class CopilotChatRequest(BaseModel):
    query: str
    batch_id: Optional[str] = None


@app.post("/orchestrator/copilot-chat")
async def copilot_chat(req: CopilotChatRequest, db: Session = Depends(get_db)):
    latest_record = None
    if req.batch_id:
        latest_record = db.query(BatchStateModel).filter(BatchStateModel.batch_id == req.batch_id).first()
    if not latest_record:
        latest_record = db.query(BatchStateModel).order_by(BatchStateModel.created_at.desc()).first()

    latest_state = latest_record.state_json if latest_record else {}
    history_records = db.query(BatchStateModel).order_by(BatchStateModel.created_at.desc()).limit(5).all()
    pipeline_history = [r.state_json for r in history_records]

    try:
        return await generate_copilot_response(
            query=req.query,
            latest_state=latest_state,
            background_snapshots=background_snapshots,
            pipeline_history=pipeline_history,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Gemini copilot unavailable: {exc}",
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8020, reload=True)
