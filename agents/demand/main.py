"""
Agent 8 — Demand Forecasting: FastAPI Application
Endpoints:
  POST /agents/demand/forecast
  GET  /agents/demand/health
  GET  /agents/demand/confirmed-orders
  POST /agents/demand/confirmed-orders
  GET  /agents/demand/history
  GET  /agents/demand/products
"""

import json
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import init_db, get_db, ForecastRecord, ConfirmedOrder
from model import (
    run_forecast,
    get_meta,
    model_is_available,
    PRODUCT_TYPES,
)

# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Demand Forecasting Agent",
    description="Agent 8 — Predicts weekly textile order volumes using Facebook Prophet",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()


# ── Schemas ───────────────────────────────────────────────────────────────────

class ForecastRequest(BaseModel):
    product_type: str
    forecast_horizon_weeks: int = Field(default=4, ge=1, le=12)


class WeekForecast(BaseModel):
    week: str
    predicted_qty_m: int
    ci_lower: Optional[int] = None
    ci_upper: Optional[int] = None
    confirmed_qty_m: Optional[int] = None
    effective_qty_m: Optional[int] = None
    source: str = "prophet"


class ForecastResponse(BaseModel):
    product_type: str
    forecast: List[WeekForecast]
    confidence_interval: List[int]
    recommended_production_plan_m_per_week: int
    model_used: str
    mape: Optional[float] = None


class ConfirmedOrderCreate(BaseModel):
    product_type: str
    week_label: str          # e.g. "2026-W32"
    buyer: str
    quantity_m: float = Field(gt=0)


class ConfirmedOrderOut(BaseModel):
    id: int
    product_type: str
    week_label: str
    buyer: str
    quantity_m: float
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/agents/demand/health")
def health_check():
    meta = get_meta()
    models_ready = sum(1 for p in PRODUCT_TYPES if model_is_available(p))
    return {
        "status": "ok",
        "agent": "Agent 8 — Demand Forecasting",
        "version": "1.0.0",
        "models_trained": models_ready,
        "total_product_types": len(PRODUCT_TYPES),
        "trained_at": meta.get("trained_at"),
        "model_version": meta.get("model_version", "unknown"),
        "last_backtest_mape": meta.get("avg_mape"),
    }


@app.get("/agents/demand/products")
def list_products():
    """List all supported product types and whether a model is trained for each."""
    return {
        "products": [
            {
                "product_type": p,
                "model_available": model_is_available(p),
            }
            for p in PRODUCT_TYPES
        ]
    }


@app.post("/agents/demand/forecast", response_model=ForecastResponse)
def forecast(req: ForecastRequest, db: Session = Depends(get_db)):
    if req.product_type not in PRODUCT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown product_type '{req.product_type}'. "
                   f"Call GET /agents/demand/products for valid types.",
        )

    # Pull any active confirmed orders for this product
    confirmed_db = (
        db.query(ConfirmedOrder)
        .filter(
            ConfirmedOrder.product_type == req.product_type,
            ConfirmedOrder.is_active == True,
        )
        .all()
    )
    confirmed_list = [
        {"week_label": c.week_label, "quantity_m": c.quantity_m}
        for c in confirmed_db
    ]

    result = run_forecast(
        product_type=req.product_type,
        horizon_weeks=req.forecast_horizon_weeks,
        confirmed_orders=confirmed_list if confirmed_list else None,
    )

    # Persist the forecast record
    try:
        record = ForecastRecord(
            product_type=req.product_type,
            horizon_weeks=req.forecast_horizon_weeks,
            forecast_json=json.dumps(result["forecast"]),
            ci_lower=result["confidence_interval"][0],
            ci_upper=result["confidence_interval"][1],
            recommended_m=result["recommended_production_plan_m_per_week"],
            mape=result.get("mape"),
            model_version=result.get("model_used", "unknown"),
        )
        db.add(record)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Failed to persist forecast: {e}")

    return result


@app.get("/agents/demand/confirmed-orders", response_model=List[ConfirmedOrderOut])
def list_confirmed_orders(
    product_type: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(ConfirmedOrder).filter(ConfirmedOrder.is_active == True)
    if product_type:
        q = q.filter(ConfirmedOrder.product_type == product_type)
    return q.order_by(ConfirmedOrder.created_at.desc()).all()


@app.post("/agents/demand/confirmed-orders", response_model=ConfirmedOrderOut)
def add_confirmed_order(order: ConfirmedOrderCreate, db: Session = Depends(get_db)):
    if order.product_type not in PRODUCT_TYPES:
        raise HTTPException(status_code=400, detail=f"Unknown product_type '{order.product_type}'")

    record = ConfirmedOrder(
        product_type=order.product_type,
        week_label=order.week_label,
        buyer=order.buyer,
        quantity_m=order.quantity_m,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@app.delete("/agents/demand/confirmed-orders/{order_id}")
def cancel_confirmed_order(order_id: int, db: Session = Depends(get_db)):
    record = db.query(ConfirmedOrder).filter(ConfirmedOrder.id == order_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Order not found")
    record.is_active = False
    db.commit()
    return {"status": "cancelled", "id": order_id}


@app.get("/agents/demand/history")
def forecast_history(
    product_type: Optional[str] = None,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    q = db.query(ForecastRecord)
    if product_type:
        q = q.filter(ForecastRecord.product_type == product_type)
    records = q.order_by(ForecastRecord.created_at.desc()).limit(limit).all()

    return {
        "history": [
            {
                "id":             r.id,
                "product_type":   r.product_type,
                "horizon_weeks":  r.horizon_weeks,
                "recommended_m":  r.recommended_m,
                "ci_lower":       r.ci_lower,
                "ci_upper":       r.ci_upper,
                "mape":           r.mape,
                "model_version":  r.model_version,
                "created_at":     r.created_at.isoformat() if r.created_at else None,
            }
            for r in records
        ]
    }
