import requests
import json
import time

ORCHESTRATOR_URL = "http://localhost:8020"
EFFLUENT_URL = "http://localhost:8004"
NOTIFICATION_URL = "http://localhost:8011"

def run_integration_test():
    print("==================================================")
    print("TEXMIND MULTI-AGENT E2E INTEGRATION TEST")
    print("==================================================\n")

    # 1. Trigger Batch Pipeline
    print("[1] Triggering new fabric batch B-2026-TEST-99...")
    batch_payload = {
        "batch_id": "B-2026-TEST-99",
        "supplier_id": "SUP-01",
        "fiber_count": 32,
        "tensile_strength_g_tex": 19.5,
        "moisture_pct": 7.4,
        "target_shade_code": "BOTTLE-GREEN-30",
        "fabric_type": "nylon_taffeta"
    }
    
    try:
        res = requests.post(f"{ORCHESTRATOR_URL}/orchestrator/trigger-batch", json=batch_payload, timeout=15.0)
        if res.status_code == 200:
            state = res.json()
            print(f"Success! Batch Status: {state['status']}")
            print(f"Intake Decision: {state['intake_result']['decision'] if state['intake_result'] else 'N/A'}")
            print(f"Defect Decision: {state['defect_result']['decision'] if state['defect_result'] else 'N/A'}")
            print(f"Dye Recipe: {state['dye_recipe']['recommended_recipe'] if state['dye_recipe'] else 'N/A'}")
            print(f"Traceability Score: {state['traceability_record']['traceability_score'] if state['traceability_record'] else 'N/A'}")
            print(f"Sustainability Grade: {state['sustainability_report']['esg_grade'] if state['sustainability_report'] else 'N/A'}")
        else:
            print(f"Fail! Orchestrator returned status {res.status_code}: {res.text}")
    except Exception as e:
        print(f"Orchestrator not online or failed: {e}")

    # 2. Simulate Effluent Violation
    print("\n[2] Simulating Effluent Breach (pH 9.4) on Agent 04...")
    effluent_payload = {
        "ph": 9.4,
        "tds_mgL": 2400.0,
        "color_units": 150.0,
        "bod_mgL": 180.0
    }
    try:
        res = requests.post(f"{EFFLUENT_URL}/agents/effluent/ingest", json=effluent_payload, timeout=5.0)
        if res.status_code == 200:
            print("Effluent data ingested successfully.")
        else:
            print(f"Effluent Agent returned status {res.status_code}")
    except Exception as e:
        print(f"Effluent Agent not online: {e}")

    # 3. Verify Automatic Notification Trigger
    print("\n[3] Checking if Notification Agent automatically caught the breach...")
    time.sleep(2) # Wait briefly for loop processing
    try:
        res = requests.get(f"{NOTIFICATION_URL}/agents/notification/active-alerts", timeout=3.0)
        if res.status_code == 200:
            alerts = res.json()
            if len(alerts) > 0:
                latest = alerts[0]
                print(f"Found Triggered Alert! ID: {latest['alert_id']}")
                print(f"Source: {latest['source_agent']}")
                print(f"Severity: {latest['severity']}")
                print(f"Tamil Prompt Generated: True")
                print(f"Current Status: {latest['status']}")
            else:
                print("No alerts found in Notification database.")
        else:
            print(f"Notification Agent returned status {res.status_code}")
    except Exception as e:
        print(f"Notification Agent not online: {e}")

if __name__ == "__main__":
    run_integration_test()
