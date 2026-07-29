import pandas as pd
import numpy as np
import os
import pickle
from sklearn.ensemble import IsolationForest
from datetime import datetime
from pydantic import BaseModel, Field
from typing import List

MODEL_PATH = "model_artifacts/effluent_iso_forest.pkl"

# Regulatory limits
LIMITS = {
    "ph": (6.5, 8.5),
    "tds_mgL": (0, 2100),
    "color_units": (0, 400),
    "bod_mgL": (0, 30)
}
CONSECUTIVE_VIOLATIONS = 3

class SensorReading(BaseModel):
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    ph: float
    tds_mgL: float
    color_units: float
    bod_mgL: float

def train_isolation_forest():
    print("Training Isolation Forest on ETP data...")
    data_path = "data/effluent_data_1M.csv"
    if not os.path.exists(data_path):
        print(f"Data file not found at {data_path}")
        return False
        
    df = pd.read_csv(data_path)
    features = ['ph', 'tds_mgL', 'color_units', 'bod_mgL']
    X = df[features]
    
    # We use a small contamination because we injected 5% anomalies
    model = IsolationForest(contamination=0.05, random_state=42, n_jobs=-1)
    model.fit(X)
    
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    with open(MODEL_PATH, 'wb') as f:
        pickle.dump(model, f)
    print(f"Isolation Forest saved to {MODEL_PATH}")
    return True

def load_model():
    if not os.path.exists(MODEL_PATH):
        return None
    with open(MODEL_PATH, 'rb') as f:
        return pickle.load(f)

# Keep track of recent readings for consecutive checks
_recent_readings = []

def process_reading(reading: SensorReading, model):
    global _recent_readings
    
    # 1. Check strict limits
    violated_params = []
    if not (LIMITS["ph"][0] <= reading.ph <= LIMITS["ph"][1]):
        violated_params.append("ph")
    if reading.tds_mgL > LIMITS["tds_mgL"][1]:
        violated_params.append("tds_mgL")
    if reading.color_units > LIMITS["color_units"][1]:
        violated_params.append("color_units")
    if reading.bod_mgL > LIMITS["bod_mgL"][1]:
        violated_params.append("bod_mgL")
        
    # Append to recent and keep last N
    _recent_readings.append(violated_params)
    if len(_recent_readings) > CONSECUTIVE_VIOLATIONS:
        _recent_readings.pop(0)
        
    # 2. Rule Engine: Determine if it's a confirmed violation
    is_violation = False
    if len(_recent_readings) == CONSECUTIVE_VIOLATIONS:
        # Check if any parameter has been violated for N consecutive times
        for param in ["ph", "tds_mgL", "color_units", "bod_mgL"]:
            if all(param in v for v in _recent_readings):
                is_violation = True
                break
                
    # 3. ML Anomaly Detection (Drift)
    ml_anomaly = False
    if model is not None and not is_violation:
        X_new = pd.DataFrame([[reading.ph, reading.tds_mgL, reading.color_units, reading.bod_mgL]], 
                             columns=['ph', 'tds_mgL', 'color_units', 'bod_mgL'])
        prediction = model.predict(X_new)
        if prediction[0] == -1: # -1 indicates anomaly
            ml_anomaly = True

    status = "compliant"
    severity = "low"
    alert_sent = False
    
    if is_violation:
        status = "violation"
        severity = "high"
        alert_sent = True
    elif ml_anomaly:
        status = "drift_anomaly"
        severity = "medium"
        alert_sent = False # maybe warn in dashboard, no SMS yet

    return {
        "timestamp": reading.timestamp,
        "status": status,
        "violated_parameters": list(set([p for sublist in _recent_readings for p in sublist])) if is_violation else [],
        "severity": severity,
        "alert_sent": alert_sent
    }
