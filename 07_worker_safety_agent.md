# Agent 7 — Worker Safety Agent

## 1. Role in the System
Watches the factory floor camera feed for PPE compliance and hazard-zone intrusion, alerting supervisors in real time.

## 2. Real-World Problem It Solves
Safety walk-throughs happen periodically; violations between checks go unnoticed until an incident occurs. This agent watches continuously without needing a person to physically patrol every zone.

## 3. What You Need to Provide
| Item | Why it's needed | Example |
|---|---|---|
| Floor camera feed | The actual visual input | RTSP stream from existing CCTV, or sample images/video for the demo |
| PPE policy per zone | What compliance means where | e.g. "dyeing floor requires gloves + apron, weaving floor requires ear protection" |
| Hazard zone map | Where restricted areas are | Floor plan with marked zones/coordinates |
| Supervisor alert contacts | Who gets notified | Shift supervisor's phone/messaging channel |
| Employee privacy policy | To handle footage responsibly | Your data-retention and consent policy for camera footage |

**Important:** this agent processes footage of real people — face-blur or non-identifying detection (bounding boxes only, no facial recognition/identification) should be the default for privacy and labor-law compliance. Don't add facial identification unless you have an explicit legal and consent basis to do so.

## 4. Input / Output Contract
**Input:** camera frame + zone_id.
```json
{
  "zone_id": "DYE-FLOOR-A",
  "camera_id": "CAM-03",
  "frame_ref": "s3://texverse/safety/f001.jpg"
}
```
**Output:**
```json
{
  "zone_id": "DYE-FLOOR-A",
  "violations": [
    {"type": "missing_gloves", "bbox": [200, 140, 260, 300], "confidence": 0.88}
  ],
  "zone_intrusion": false,
  "alert_sent": true
}
```

## 5. Internal Working — Step by Step
1. Receive frame, preprocess.
2. Run PPE-detection model → identify people and their PPE state (helmet/no-helmet, gloves/no-gloves, etc.).
3. Cross-check detected person locations against the hazard zone map for intrusion.
4. If violation confidence exceeds threshold and persists across consecutive frames (avoid one-frame false positives from occlusion), raise an alert.
5. Log the event (without storing identifying data beyond what's operationally necessary) and notify the shift supervisor.

## 6. Model / Algorithm Details
- **Model:** YOLOv8 fine-tuned on a public PPE-detection dataset (several exist on Roboflow specifically for hard-hat/gloves/vest detection).
- **Zone intrusion:** simple geometric check — is a detected person's bounding-box centroid inside a restricted polygon on the floor map.
- Deliberately no facial recognition — bounding box + PPE class is enough for the safety function and avoids unnecessary privacy risk.

## 7. Tech Stack
- Python, FastAPI, Ultralytics YOLOv8, OpenCV
- A simple polygon-based zone-mapping utility (Shapely)

## 8. Standalone API Contract
```
POST /agents/safety/inspect
GET  /agents/safety/health
GET  /agents/safety/violations?zone_id=&range=
```

## 9. Standalone Deployment
```
agents/safety/
├── main.py
├── ppe_model.py
├── zone_map.json
├── Dockerfile
└── requirements.txt
```

## 10. How the Master Brain Calls It
Runs continuously and independently, similar to Agents 4/5/6 — it's not tied to a specific fabric batch, it's a plant-wide background monitor. Publishes violation events to shared state and directly to a supervisor alert channel (doesn't need to wait for the orchestrator to relay it — safety alerts should be as low-latency as possible).

## 11. Production Hardening
- Store the minimum footage necessary — short retention window for raw frames, keep only annotated event logs long-term, in line with labor and privacy regulations.
- Clear escalation policy: repeated same-worker violations should route to a different (HR/training) workflow, not just repeated alerts.
- Fail-safe default: if the camera feed drops, alert on "monitoring offline," never silently report "no violations."

## 12. Testing Strategy
- Precision/recall on a held-out labeled PPE dataset.
- Zone-intrusion logic unit tests with known coordinate edge cases.
- Occlusion/lighting-variance robustness tests.

## 13. Monitoring & Observability
- Track: violations/day by zone and type, camera uptime, alert response time (time from alert to supervisor acknowledgment).

## 14. Environment Variables
```
PPE_MODEL_PATH=/app/weights/ppe_best.pt
CONFIDENCE_THRESHOLD=0.65
ZONE_MAP_PATH=/app/zone_map.json
SUPERVISOR_ALERT_WEBHOOK=https://...
```
