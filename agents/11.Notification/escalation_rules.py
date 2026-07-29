import os
from typing import Dict, Any, List

ALERT_PHONE = os.getenv("ALERT_PHONE_NUMBER", "+918610500527")

ESCALATION_MATRIX = {
    "CRITICAL": [
        {"level": 1, "role": "Shift Operator (Primary)", "contact": f"{ALERT_PHONE} (IVR Voice Call)", "channel": "Voice Call (Tamil)", "timeout_sec": 120},
        {"level": 2, "role": "Plant Supervisor", "contact": f"{ALERT_PHONE} (WhatsApp)", "channel": "WhatsApp", "timeout_sec": 300},
        {"level": 3, "role": "Factory VP / General Manager", "contact": f"{ALERT_PHONE} (SMS)", "channel": "SMS", "timeout_sec": 0}
    ],
    "WARNING": [
        {"level": 1, "role": "Section Technician", "contact": f"{ALERT_PHONE} (WhatsApp)", "channel": "WhatsApp", "timeout_sec": 600},
        {"level": 2, "role": "Plant Supervisor", "contact": f"{ALERT_PHONE} (SMS)", "channel": "SMS", "timeout_sec": 0}
    ],
    "INFO": [
        {"level": 1, "role": "QC Staff Log", "contact": "Dashboard Feed", "channel": "Dashboard Feed", "timeout_sec": 0}
    ]
}

def get_escalation_chain(severity: str) -> List[Dict[str, Any]]:
    sev = severity.upper()
    return ESCALATION_MATRIX.get(sev, ESCALATION_MATRIX["INFO"])
