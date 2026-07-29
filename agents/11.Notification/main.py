import os
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import uvicorn
from dispatcher import NotificationDispatcher
from tamil_voice_engine import process_inbound_speech_query

from database import init_db, get_db, AlertRecordModel
from sqlalchemy.orm import Session

app = FastAPI(
    title="Agent 11 — Local Voice & Messaging Notification Agent",
    description="Multi-channel automated Tamil voice call (Softphone PBX), WhatsApp, and SMS alert dispatcher with escalation rules, DTMF acknowledgment, and Tamil inbound IVR query engine.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

dispatcher = NotificationDispatcher()

@app.on_event("startup")
def on_startup():
    init_db()
    # Seed alert if empty
    db = next(get_db())
    if db.query(AlertRecordModel).count() == 0:
        dispatcher.dispatch_alert(
            source_agent="Agent 04 (Effluent)",
            event_type="effluent_ph",
            severity="CRITICAL",
            details={"reading": 9.4}
        )
    db.close()

class AlertTriggerRequest(BaseModel):
    source_agent: str = Field(..., json_schema_extra={"example": "Agent 04 (Effluent)"})
    event_type: str = Field(..., json_schema_extra={"example": "effluent_ph"})
    severity: str = Field("CRITICAL", json_schema_extra={"example": "CRITICAL"})
    details: Optional[Dict[str, Any]] = Field(default_factory=lambda: {"reading": 9.4})

class AcknowledgeRequest(BaseModel):
    alert_id: str = Field(..., json_schema_extra={"example": "ALT-101"})
    acknowledged_by: Optional[str] = Field("Shift Supervisor (DTMF 1)", json_schema_extra={"example": "Shift Supervisor (DTMF 1)"})

class InboundIVRRequest(BaseModel):
    caller_extension: str = Field("Ext 101", json_schema_extra={"example": "Ext 101"})
    speech_transcription_tamil: str = Field("இன்று பிரச்சனை என்ன?", json_schema_extra={"example": "இன்று பிரச்சனை என்ன?"})

from pyvoip_sip_gateway import make_pyvoip_sip_call

class RealCallRequest(BaseModel):
    to_phone_number: str = os.getenv("ALERT_PHONE_NUMBER", "+918610500527")
    tamil_message: Optional[str] = "எச்சரிக்கை! கழிவுநீர் சுத்திகரிப்பு பிரிவில் pH அளவு 9.4 ஆக உயர்ந்துள்ளது."

@app.post("/agents/notification/dial-real-phone")
def dial_real_phone(req: RealCallRequest):
    return make_pyvoip_sip_call(
        to_phone_number=req.to_phone_number
    )

@app.get("/agents/notification/dial-real-phone")
def dial_real_phone_get(to_phone: str = os.getenv("ALERT_PHONE_NUMBER", "+918610500527")):
    return make_pyvoip_sip_call(
        to_phone_number=to_phone
    )

@app.get("/agents/notification/health")
def health_check(db: Session = Depends(get_db)):
    active_count = db.query(AlertRecordModel).filter(AlertRecordModel.status != "ACKNOWLEDGED").count()
    return {
        "status": "ok",
        "agent": "Agent 11 — Local Voice & Messaging Notification",
        "pbx_mode": "Local Asterisk PBX Simulation",
        "supported_channels": ["Softphone Tamil Voice Call", "WhatsApp Gateway", "SMS GSM"],
        "active_alerts_count": active_count
    }

@app.post("/agents/notification/trigger-alert")
def trigger_alert(req: AlertTriggerRequest):
    return dispatcher.dispatch_alert(
        source_agent=req.source_agent,
        event_type=req.event_type,
        severity=req.severity,
        details=req.details or {}
    )

@app.post("/agents/notification/acknowledge")
def acknowledge_alert(req: AcknowledgeRequest):
    return dispatcher.acknowledge_alert(
        alert_id=req.alert_id,
        acknowledged_by=req.acknowledged_by or "Shift Supervisor (DTMF 1)"
    )

@app.post("/agents/notification/escalate/{alert_id}")
def escalate_alert(alert_id: str):
    return dispatcher.escalate_alert(alert_id)

@app.post("/agents/notification/inbound-ivr-query")
def inbound_ivr_query(req: InboundIVRRequest):
    response_tamil = process_inbound_speech_query(req.speech_transcription_tamil)
    return {
        "caller_extension": req.caller_extension,
        "query_tamil": req.speech_transcription_tamil,
        "spoken_response_tamil": response_tamil
    }

@app.get("/agents/notification/active-alerts")
def list_active_alerts(db: Session = Depends(get_db)):
    # Return all unacknowledged alerts or all alerts
    alerts = db.query(AlertRecordModel).order_by(AlertRecordModel.timestamp.desc()).all()
    # Map back to dict
    return [
        {
            "alert_id": a.alert_id,
            "source_agent": a.source_agent,
            "event_type": a.event_type,
            "severity": a.severity,
            "tamil_prompt": a.tamil_prompt,
            "current_level": a.current_level,
            "current_role": a.current_role,
            "current_channel": a.current_channel,
            "current_contact": a.current_contact,
            "status": a.status,
            "escalation_chain": a.escalation_chain,
            "timestamp": a.timestamp.strftime("%Y-%m-%d %H:%M:%S") if a.timestamp else None,
            "acknowledged_by": a.acknowledged_by,
            "ack_timestamp": a.ack_timestamp.strftime("%Y-%m-%d %H:%M:%S") if a.ack_timestamp else None
        }
        for a in alerts
    ]

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8011)
