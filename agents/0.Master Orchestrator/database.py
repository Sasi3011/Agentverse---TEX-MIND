import os
from sqlalchemy import create_engine, Column, Integer, String, JSON, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./orchestrator_local.db")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class BatchStateModel(Base):
    __tablename__ = "batch_states"

    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(String, index=True, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    state_json = Column(JSON) # Stores the serialized MillState

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
