from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any
from datetime import datetime
import os

try:
    from anomaly_model import AnomalyModel
    from baseline import BaselineCalculator
except ImportError:
    try:
        from .anomaly_model import AnomalyModel
        from .baseline import BaselineCalculator
    except ImportError:
        from anomaly_model import AnomalyModel
        from baseline import BaselineCalculator

app = FastAPI(title="Agent 5 - Energy & Utility Optimization")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load models and baseline calculator
anomaly_model = AnomalyModel()
baseline_calc = BaselineCalculator(window_size=50)

# Environment variables
TARIFF_RATE_PER_KWH_INR = float(os.getenv("TARIFF_RATE_PER_KWH_INR", "7.5"))

class EnergyIngest(BaseModel):
    machine_id: str
    timestamp: str
    power_kwh: float

class EnergyReport(BaseModel):
    machine_id: str
    status: str
    baseline_kwh: float
    deviation_pct: float
    estimated_monthly_excess_cost_inr: float
    likely_cause_hint: str
    timestamp: str

# In-memory storage for latest report per machine
latest_reports = {}

@app.post("/agents/energy/ingest", response_model=EnergyReport)
async def ingest_energy_data(data: EnergyIngest):
    # Update baseline
    baseline_kwh, std_dev = baseline_calc.update_and_get_baseline(data.machine_id, data.power_kwh)
    
    # Predict anomaly using Isolation Forest
    is_anomaly = anomaly_model.predict(data.machine_id, data.power_kwh)
    
    # Calculate deviation
    deviation_pct = 0.0
    if baseline_kwh > 0:
        deviation_pct = ((data.power_kwh - baseline_kwh) / baseline_kwh) * 100.0
        
    status = "normal"
    excess_cost = 0.0
    hint = "Operating optimally"
    
    # Flag if model says anomaly AND it's higher than baseline
    if is_anomaly and data.power_kwh > baseline_kwh:
        status = "anomaly"
        
        # Estimate cost impact if this continues for a month (assuming 24/7 operation, 1 reading per hour for simplicity of math here, but adjust as needed)
        # Let's say this is excess kWh per hour * 24 hours * 30 days
        excess_kwh_per_hour = data.power_kwh - baseline_kwh
        excess_cost = excess_kwh_per_hour * 24 * 30 * TARIFF_RATE_PER_KWH_INR
        
        if "BOILER" in data.machine_id:
            hint = "Check insulation / thermostat calibration / scale buildup"
        elif "COMPRESSOR" in data.machine_id:
            hint = "Check for air leaks / frequent cycling / blocked filters"
        elif "MOTOR" in data.machine_id:
            hint = "Check for bearing wear / misalignment / unbalanced load"
        else:
            hint = "Investigate source of unusual consumption"
            
    report = EnergyReport(
        machine_id=data.machine_id,
        status=status,
        baseline_kwh=round(baseline_kwh, 2),
        deviation_pct=round(deviation_pct, 2),
        estimated_monthly_excess_cost_inr=round(excess_cost, 2),
        likely_cause_hint=hint,
        timestamp=data.timestamp
    )
    
    latest_reports[data.machine_id] = report
    
    return report

@app.get("/agents/energy/report")
async def get_energy_report(machine_id: str = None):
    if machine_id:
        if machine_id in latest_reports:
            return [latest_reports[machine_id]]
        return []
    
    return list(latest_reports.values())

@app.get("/agents/energy/health")
async def health_check():
    return {
        "status": "healthy",
        "models_loaded": len(anomaly_model.models),
        "machines_tracked": len(baseline_calc.history)
    }
