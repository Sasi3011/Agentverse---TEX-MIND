import time
import uuid
import requests
import os
from typing import Dict, Any, List

from database import SessionLocal, AlertRecordModel
from escalation_rules import get_escalation_chain
from tamil_voice_engine import generate_tamil_alert_text, generate_tamil_tts_audio
from asterisk_telecom_gateway import originate_asterisk_ivr_call

WHATSAPP_SERVICE_URL = os.getenv("WHATSAPP_SERVICE_URL", "http://localhost:3000")

class NotificationDispatcher:
    def __init__(self):
        # Keeps basic local history but delegates persistence to the DB
        self.notification_logs: List[Dict[str, Any]] = []

    def dispatch_alert(self, source_agent: str, event_type: str, severity: str, details: dict) -> Dict[str, Any]:
        alert_id = f"ALT-{uuid.uuid4().hex[:6].upper()}"
        tamil_text = generate_tamil_alert_text(event_type, details)
        escalation_chain = get_escalation_chain(severity)

        current_level = escalation_chain[0]
        db = SessionLocal()

        alert_record = {
            "alert_id": alert_id,
            "source_agent": source_agent,
            "event_type": event_type,
            "severity": severity.upper(),
            "tamil_prompt": tamil_text,
            "current_level": current_level["level"],
            "current_role": current_level["role"],
            "current_channel": current_level["channel"],
            "current_contact": current_level["contact"],
            "status": "DISPATCHED_WAITING_ACK",
            "escalation_chain": escalation_chain,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }

        # --- Automatic Gateway Execution ---
        # 1. Generate Tamil Speech Audio (.mp3)
        audio_filename = f"audio_alerts/alert_{alert_id}.mp3"
        generate_tamil_tts_audio(tamil_text, output_path=os.path.join(os.path.dirname(__file__), "static", audio_filename))

        # 2. Call Gateway based on contact channel
        channel = current_level["channel"]
        contact = current_level["contact"].split(" ")[0] # extract pure phone number
        
        gateway_response = None
        if "Voice Call" in channel:
            # Trigger real Asterisk REST Interface Call
            gateway_response = originate_asterisk_ivr_call(contact, tamil_text)
        elif "WhatsApp" in channel:
            # Trigger local Node whatsapp-web.js service
            try:
                res = requests.post(f"{WHATSAPP_SERVICE_URL}/send", json={"phone": contact, "message": tamil_text}, timeout=3.0)
                gateway_response = res.json()
            except Exception as e:
                print(f"[WhatsApp Offline Fallback] Logging sandbox alert to: {contact}. Msg: {tamil_text}. Error: {e}")
                gateway_response = {"status": "SANDBOX_LOGGED", "note": "Node WhatsApp service offline"}
        elif "SMS" in channel:
            # Clear sandbox logging for GSM simulation
            print(f"\n========================================================")
            print(f"[SIMULATED SMS DISPATCHED]")
            print(f"To: {contact}")
            print(f"Message: {tamil_text}")
            print(f"========================================================\n")
            gateway_response = {"status": "SMS_SIMULATED", "to": contact}

        # Update record status with gateway response info if applicable
        if gateway_response and gateway_response.get("status") == "FAILED":
            alert_record["status"] = "GATEWAY_FAILURE"

        # Save to database
        db_record = AlertRecordModel(
            alert_id=alert_id,
            source_agent=source_agent,
            event_type=event_type,
            severity=severity.upper(),
            tamil_prompt=tamil_text,
            current_level=current_level["level"],
            current_role=current_level["role"],
            current_channel=current_level["channel"],
            current_contact=current_level["contact"],
            status=alert_record["status"],
            escalation_chain=escalation_chain
        )
        db.add(db_record)
        db.commit()
        db.close()

        self.notification_logs.insert(0, alert_record)
        return alert_record

    def acknowledge_alert(self, alert_id: str, acknowledged_by: str = "Operator (DTMF Key 1)") -> Dict[str, Any]:
        db = SessionLocal()
        record = db.query(AlertRecordModel).filter(AlertRecordModel.alert_id == alert_id).first()
        if record:
            record.status = "ACKNOWLEDGED"
            record.acknowledged_by = acknowledged_by
            record.ack_timestamp = datetime.utcnow()
            db.commit()
            
            # Serialize for return
            res = {
                "alert_id": record.alert_id,
                "status": record.status,
                "acknowledged_by": record.acknowledged_by,
                "ack_timestamp": record.ack_timestamp.strftime("%Y-%m-%d %H:%M:%S")
            }
            db.close()
            return res
        db.close()
        return {"error": f"Alert ID '{alert_id}' not found or already acknowledged"}

    def escalate_alert(self, alert_id: str) -> Dict[str, Any]:
        db = SessionLocal()
        record = db.query(AlertRecordModel).filter(AlertRecordModel.alert_id == alert_id).first()
        if record:
            curr_lvl = record.current_level
            chain = record.escalation_chain

            if curr_lvl < len(chain):
                next_step = chain[curr_lvl]
                record.current_level = next_step["level"]
                record.current_role = next_step["role"]
                record.current_channel = next_step["channel"]
                record.current_contact = next_step["contact"]
                record.status = f"ESCALATED_TO_LEVEL_{next_step['level']}"
                
                # --- Auto-retrigger call on new escalated channel ---
                contact = next_step["contact"].split(" ")[0]
                channel = next_step["channel"]
                tamil_text = record.tamil_prompt
                
                if "Voice Call" in channel:
                    originate_asterisk_ivr_call(contact, tamil_text)
                elif "WhatsApp" in channel:
                    try:
                        requests.post(f"{WHATSAPP_SERVICE_URL}/send", json={"phone": contact, "message": tamil_text}, timeout=3.0)
                    except Exception:
                        pass
                elif "SMS" in channel:
                    print(f"\n[SIMULATED ESCALATION SMS] To: {contact} | Msg: {tamil_text}\n")
            else:
                record.status = "MAX_ESCALATION_REACHED"

            db.commit()
            res = {
                "alert_id": record.alert_id,
                "status": record.status,
                "current_level": record.current_level,
                "current_role": record.current_role,
                "current_channel": record.current_channel,
                "current_contact": record.current_contact
            }
            db.close()
            return res
        db.close()
        return {"error": f"Alert ID '{alert_id}' not found"}
