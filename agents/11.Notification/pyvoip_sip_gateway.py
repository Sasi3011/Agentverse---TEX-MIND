import os
import sys
import time
from typing import Dict, Any

DEFAULT_PHONE = os.getenv("ALERT_PHONE_NUMBER", "+918610500527")

def make_pyvoip_sip_call(
    to_phone_number: str = DEFAULT_PHONE,
    sip_server: str = "sip.freevoip.org",
    sip_user: str = "1001",
    sip_password: str = "1001"
) -> Dict[str, Any]:
    """
    Pure Python SIP/VoIP Call Initiator using pyVoIP library.
    Initiates an outbound SIP RTP audio call strictly through code without third-party web cloud dashboards.
    """
    print(f"[PyVoIP Pure-Python Engine] Dialing {to_phone_number} via SIP Server {sip_server}...")

    try:
        from pyVoIP.VoIP import VoIPPhone, CallState
        
        # Initialize pure Python SIP phone engine
        phone = VoIPPhone(sip_server, 5060, sip_user, sip_password)
        phone.start()
        
        # Originate direct SIP call to target mobile number/extension
        call = phone.make_call(to_phone_number)
        print(f"SIP Call Initiated. Call State: {call.state}")
        
        return {
            "status": "SIP_CALL_INITIATED",
            "engine": "pyVoIP (Pure Python SIP Engine)",
            "to_phone_number": to_phone_number,
            "sip_server": sip_server,
            "sip_user": sip_user,
            "protocol": "SIP / RTP Direct Code Stream",
            "note": "100% Code-based SIP VoIP call dispatched. Zero Twilio cloud required."
        }
    except ImportError:
        print("pyVoIP library not installed.")
        return {
            "status": "FAILED",
            "error": "pyVoIP library not installed. Outbound VoIP call failed.",
            "to_phone_number": to_phone_number
        }
    except Exception as e:
        return {
            "status": "FAILED",
            "error": str(e),
            "to_phone_number": to_phone_number
        }

if __name__ == "__main__":
    make_pyvoip_sip_call(DEFAULT_PHONE)
