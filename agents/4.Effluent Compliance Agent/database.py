from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
import os

DATABASE_URL = "sqlite:///./agents/effluent/effluent.db"

os.makedirs(os.path.dirname(DATABASE_URL.replace("sqlite:///", "")), exist_ok=True)

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class EffluentLog(Base):
    __tablename__ = "effluent_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    ph = Column(Float)
    tds_mgL = Column(Float)
    color_units = Column(Float)
    bod_mgL = Column(Float)
    
    # ML & Compliance metadata
    status = Column(String) # 'compliant', 'drift_anomaly', 'violation'
    violated_parameters = Column(String, nullable=True) # JSON string of list
    severity = Column(String, nullable=True)
    alert_sent = Column(Integer, default=0) # boolean int

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
