import os
from sqlalchemy import create_engine, Column, Integer, String, JSON, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./notification_local.db")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class AlertRecordModel(Base):
    __tablename__ = "notification_alerts"

    id = Column(Integer, primary_key=True, index=True)
    alert_id = Column(String, index=True, unique=True)
    source_agent = Column(String)
    event_type = Column(String)
    severity = Column(String)
    tamil_prompt = Column(String)
    current_level = Column(Integer)
    current_role = Column(String)
    current_channel = Column(String)
    current_contact = Column(String)
    status = Column(String)
    escalation_chain = Column(JSON)
    timestamp = Column(DateTime, default=datetime.utcnow)
    acknowledged_by = Column(String, nullable=True)
    ack_timestamp = Column(DateTime, nullable=True)

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
