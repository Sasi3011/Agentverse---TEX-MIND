"""
Agent 8 — Demand Forecasting: Database Layer (SQLite / Postgres compatible)
"""

import os
from datetime import datetime
from sqlalchemy import (
    create_engine, Column, Integer, String,
    Float, DateTime, Boolean, Text
)
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./demand_agent.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine       = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base         = declarative_base()


# ── ORM Models ────────────────────────────────────────────────────────────────

class ForecastRecord(Base):
    """Stores each forecast run and its results."""
    __tablename__ = "forecast_records"

    id             = Column(Integer, primary_key=True, index=True)
    product_type   = Column(String, index=True, nullable=False)
    horizon_weeks  = Column(Integer, nullable=False)
    forecast_json  = Column(Text, nullable=False)   # JSON: list of {week, predicted_qty_m}
    ci_lower       = Column(Float)
    ci_upper       = Column(Float)
    recommended_m  = Column(Float)
    mape           = Column(Float, nullable=True)
    model_version  = Column(String, default="prophet_v1")
    created_at     = Column(DateTime, default=datetime.utcnow)


class ConfirmedOrder(Base):
    """Stores confirmed (hard) orders that override the pure forecast."""
    __tablename__ = "confirmed_orders"

    id           = Column(Integer, primary_key=True, index=True)
    product_type = Column(String, index=True, nullable=False)
    week_label   = Column(String, nullable=False)   # e.g. "2026-W32"
    buyer        = Column(String, nullable=False)
    quantity_m   = Column(Float, nullable=False)
    is_active    = Column(Boolean, default=True)
    created_at   = Column(DateTime, default=datetime.utcnow)


# ── Init ──────────────────────────────────────────────────────────────────────

def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
