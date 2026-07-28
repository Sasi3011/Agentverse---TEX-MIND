import os
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./dyeing_agent.db")

# Fix postgresql:// prefix if needed for SQLAlchemy 2.0
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class DyeRecipeRecord(BaseModel := Base):
    __tablename__ = "dye_recipe_records"

    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(String, index=True)
    target_shade_code = Column(String, index=True)
    fabric_type = Column(String)
    fabric_weight_kg = Column(Float, default=100.0)
    dye_pct = Column(Float)
    temperature_c = Column(Float)
    time_min = Column(Integer)
    liquor_ratio = Column(String)
    dye_chemical_mix = Column(Text)
    predicted_match_probability = Column(Float)
    estimated_redye_risk = Column(String)
    estimated_water_liters = Column(Float)
    estimated_energy_kwh = Column(Float)
    confidence = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

class DyeOutcomeRecord(Base):
    __tablename__ = "dye_outcome_records"

    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(String, unique=True, index=True)
    outcome = Column(String) # "match" or "re-dye"
    actual_delta_e = Column(Float, nullable=True)
    dye_master_notes = Column(Text, nullable=True)
    logged_at = Column(DateTime, default=datetime.utcnow)

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
