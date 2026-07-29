import os
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./dyeing_local.db")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class DyeingOutcomeRecord(Base):
    __tablename__ = "dyeing_outcomes"

    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(String, index=True, unique=True)
    target_shade_code = Column(String, index=True)
    fabric_type = Column(String)
    dye_pct = Column(Float)
    temperature_c = Column(Integer)
    time_min = Column(Integer)
    liquor_ratio = Column(String)
    match_probability = Column(Float)
    outcome = Column(String, nullable=True) # "match" or "re-dye"
    created_at = Column(DateTime, default=datetime.utcnow)

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
