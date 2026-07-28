# Agent 4 — Effluent Compliance Agent

## 1. Role in the System
Continuously watches the effluent treatment plant (ETP) discharge parameters and stops a compliance violation before it becomes a legal/environmental incident.

## 2. Real-World Problem It Solves
Textile dyeing effluent (color, high TDS, abnormal pH) is a well-documented environmental issue in textile clusters. Violations are often caught only during periodic inspections, long after discharge has happened. This agent monitors continuously and alerts immediately.

## 3. What You Need to Provide
| Item | Why it's needed | Example |
|---|---|---|
| ETP sensor feed | The actual thing being monitored | pH probe, TDS meter, color/turbidity sensor, BOD/COD lab readings (real, or simulated for the demo) |
| Regulatory discharge limits | The compliance threshold | State Pollution Control Board (e.g. TNPCB) discharge norms for your effluent category |
| Alert contact list | Who gets notified on violation | Plant compliance officer's phone/email |
| Historical violation log (if any) | To tune alert sensitivity | Past incident records |

## 4. Input / Output Contract
**Input (streamed):**
```json
{
  "timestamp": "2026-07-31T10:15:00Z",
  "ph": 9.4,
  "tds_mgL": 2100,
  "color_units": 350,
  "bod_mgL": 28
}
```
**Output:**
```json
{
  "timestamp": "2026-07-31T10:15:00Z",
  "status": "violation",
  "violated_parameters": ["ph"],
  "limit_ph": [6.5, 8.5],
  "severity": "high",
  "alert_sent": true
}
```

## 5. Internal Working — Step by Step
1. Ingest a reading (real sensor or simulated stream).
2. Compare each parameter against its documented regulatory limit.
3. Require N consecutive out-of-range readings (not a single blip) before declaring a violation — avoids false alarms from sensor noise.
4. On confirmed violation: raise severity based on how far out of range, trigger alert, log the incident with a timestamp and full reading snapshot for audit.
5. Write status to shared state — a live violation blocks the batch's sustainability report (Agent 10) from marking that period "compliant."

## 6. Model / Algorithm Details
- Primarily a **rule engine** against documented regulatory thresholds — this is a compliance function, not a prediction function, so keep the core logic deterministic and auditable.
- Optional enhancement: an anomaly-detection layer (isolation forest) on top, to catch *drifting toward* a violation early, before the hard limit is crossed — useful for proactive maintenance of the ETP itself.

## 7. Tech Stack
- Python, FastAPI
- A simple rule engine (plain Python conditionals are appropriate here — don't over-engineer)
- Time-series store: TimescaleDB (Postgres extension) or InfluxDB for the sensor stream
- Notification: Twilio/SMS or SMTP for alerts

## 8. Standalone API Contract
```
POST /agents/effluent/ingest      (single reading or batch of readings)
GET  /agents/effluent/status      -> current compliance status
GET  /agents/effluent/history?from=&to=
```

## 9. Standalone Deployment
```
agents/effluent/
├── main.py
├── rules.py          # documented limits, versioned and reviewable
├── alerting.py
├── Dockerfile
└── requirements.txt
```

## 10. How the Master Brain Calls It
Runs continuously and independently (it doesn't wait for a "batch" trigger like the production agents — it's always-on). The orchestrator subscribes to its violation events rather than polling; treat this as a background service that publishes to the shared state whenever a status change occurs.

## 11. Production Hardening
- **This agent has legal/compliance weight — treat its logic like financial code.** Every limit value must be traceable to the actual regulatory document, version-controlled, and reviewed by a human compliance officer before deployment, not just hardcoded by a developer.
- Sensor failure detection: if no reading arrives for X minutes, alert on "sensor offline," don't silently report "compliant."
- Full audit log retention (regulators may ask for historical discharge records — don't let this data get deleted or overwritten).

## 12. Testing Strategy
- Unit test every threshold boundary explicitly (just above/below/at each limit).
- Simulate sensor dropout and confirm the correct "sensor offline" alert path (not a false "compliant" status).
- Replay historical incident data (if available) and confirm the agent would have caught it.

## 13. Monitoring & Observability
- Track: violation count/month, mean time from violation to alert sent, sensor uptime percentage.
- This agent's dashboard view should be the most prominent one in a real deployment — compliance is the highest-stakes function in this whole system.

## 14. Environment Variables
```
PH_MIN=6.5
PH_MAX=8.5
TDS_MAX_MGL=2100
COLOR_MAX_UNITS=400
BOD_MAX_MGL=30
CONSECUTIVE_READINGS_FOR_VIOLATION=3
ALERT_PHONE_NUMBER=+91XXXXXXXXXX
```
