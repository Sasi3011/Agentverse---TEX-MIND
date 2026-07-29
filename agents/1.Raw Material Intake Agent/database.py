import os
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./intake_local.db")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class IntakeRecord(Base):
    __tablename__ = "intake_records"

    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(String, index=True, unique=True)
    supplier_id = Column(String, index=True)
    fiber_count = Column(Integer)
    tensile_strength = Column(Float)
    moisture = Column(Float)
    decision = Column(String)
    quality_score = Column(Float)
    confidence = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
