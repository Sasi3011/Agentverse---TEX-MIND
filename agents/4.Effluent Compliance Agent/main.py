from fastapi import FastAPI, Depends, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import json
from datetime import datetime

from database import init_db, get_db, EffluentLog
from model import load_model, process_reading, train_isolation_forest, SensorReading

app = FastAPI(title="Agent 4: Effluent Compliance")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load ML model at startup
ml_model = None

@app.on_event("startup")
def startup_event():
    global ml_model
    init_db()
    ml_model = load_model()
    if not ml_model:
        print("Warning: ML model not found. Run /retrain to build the model.")

@app.post("/agents/effluent/ingest")
def ingest_reading(reading: SensorReading, db: Session = Depends(get_db)):
    global ml_model
    
    # Process logic (Rule engine + ML anomaly detection)
    result = process_reading(reading, ml_model)
    
    # Log to DB
    log_entry = EffluentLog(
        timestamp=datetime.fromisoformat(reading.timestamp.replace("Z", "+00:00")),
        ph=reading.ph,
        tds_mgL=reading.tds_mgL,
        color_units=reading.color_units,
        bod_mgL=reading.bod_mgL,
        status=result["status"],
        violated_parameters=json.dumps(result["violated_parameters"]),
        severity=result["severity"],
        alert_sent=1 if result["alert_sent"] else 0
    )
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)
    
    return result

@app.get("/agents/effluent/status")
def get_status(db: Session = Depends(get_db)):
    last_log = db.query(EffluentLog).order_by(EffluentLog.timestamp.desc()).first()
    if not last_log:
        return {"status": "unknown", "message": "No data ingested yet."}
        
    # Check for consecutive violations or active anomalies
    active_alerts = db.query(EffluentLog).filter(
        EffluentLog.status.in_(["violation", "drift_anomaly"])
    ).order_by(EffluentLog.timestamp.desc()).limit(10).all()
    
    return {
        "current_status": last_log.status,
        "last_reading": {
            "timestamp": last_log.timestamp.isoformat(),
            "ph": last_log.ph,
            "tds": last_log.tds_mgL,
            "color": last_log.color_units,
            "bod": last_log.bod_mgL
        },
        "recent_alerts": [
            {
                "timestamp": a.timestamp.isoformat(),
                "status": a.status,
                "severity": a.severity,
                "violated_parameters": json.loads(a.violated_parameters) if a.violated_parameters else []
            } for a in active_alerts
        ]
    }

@app.get("/agents/effluent/history")
def get_history(limit: int = 100, db: Session = Depends(get_db)):
    logs = db.query(EffluentLog).order_by(EffluentLog.timestamp.desc()).limit(limit).all()
    return [{
        "timestamp": log.timestamp.isoformat(),
        "ph": log.ph,
        "tds_mgL": log.tds_mgL,
        "color_units": log.color_units,
        "bod_mgL": log.bod_mgL,
        "status": log.status
    } for log in reversed(logs)]

@app.post("/agents/effluent/retrain")
def retrain_model(background_tasks: BackgroundTasks):
    def background_train():
        global ml_model
        train_isolation_forest()
        ml_model = load_model()
        
    background_tasks.add_task(background_train)
    return {"message": "Retraining started in the background on the 10-Lakh dataset"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)
