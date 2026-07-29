import os
import requests
import json
from typing import Dict, Any

# Local Asterisk PBX REST Interface (ARI) Configuration
ASTERISK_ARI_URL = os.getenv("ASTERISK_ARI_URL", "http://localhost:8088/ari")
ASTERISK_USER = os.getenv("ASTERISK_USER", "ariuser")
ASTERISK_PASS = os.getenv("ASTERISK_PASS", "aripass")
DEFAULT_PHONE = os.getenv("ALERT_PHONE_NUMBER", "+918610500527")

def originate_asterisk_ivr_call(
    phone_number: str = DEFAULT_PHONE, 
    tamil_message: str = "எச்சரிக்கை! கழிவுநீர் சுத்திகரிப்பு பிரிவில் pH அளவு 9.4 ஆக உயர்ந்துள்ளது."
) -> Dict[str, Any]:
    """
    Originate an outbound IVR voice call using local self-hosted Asterisk PBX REST Interface (ARI).
    Eliminates Twilio dependency entirely for 100% local, zero-cost PBX operations.
    """
    print(f"Placing local Asterisk ARI call to {phone_number}...")

    # Asterisk REST Interface originate call endpoint
    url = f"{ASTERISK_ARI_URL}/channels"
    
    params = {
        "endpoint": f"PJSIP/{phone_number}",
        "app": "texmind_notification_app",
        "appArgs": f"msg={tamil_message},lang=ta-IN,ack_key=1",
        "callerId": "TexMind AI Mill System <1000>"
    }

    try:
        response = requests.post(
            url, 
            params=params, 
            auth=(ASTERISK_USER, ASTERISK_PASS),
            timeout=3.0
        )
        if response.status_code in [200, 201]:
            return response.json()
        else:
            return {
                "status": "FAILED",
                "error": f"Asterisk returned status {response.status_code}: {response.text}",
                "to_extension": phone_number
            }
    except Exception as e:
        print(f"Asterisk ARI server not connected on port 8088: {e}")
        return {
            "status": "FAILED",
            "error": f"Failed to connect to Asterisk ARI server: {e}",
            "to_extension": phone_number
        }

if __name__ == "__main__":
    originate_asterisk_ivr_call(DEFAULT_PHONE, "எச்சரிக்கை! கழிவுநீர் சுத்திகரிப்பு பிரிவில் pH அளவு 9.4 ஆக உயர்ந்துள்ளது.")
