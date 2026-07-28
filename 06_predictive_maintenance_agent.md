# Agent 6 — Predictive Maintenance Agent

## 1. Role in the System
Watches machine vibration/temperature signals and forecasts failure before it happens, so maintenance can be scheduled instead of forced by a breakdown.

## 2. Real-World Problem It Solves
Unplanned loom/spinning-frame downtime stops production entirely and is far more expensive than scheduled maintenance. Most mills run maintenance on a fixed calendar schedule regardless of actual machine condition — this agent moves to condition-based maintenance.

## 3. What You Need to Provide
| Item | Why it's needed | Example |
|---|---|---|
| Vibration/temperature sensor feed per machine | Core signal | Accelerometer + thermocouple readings (real, or a public bearing dataset for the demo) |
| Machine maintenance history log | Ground truth for training | Past failure dates + which machine + what failed |
| Maintenance team contact/scheduling system | To act on the prediction | Your existing maintenance ticketing tool, or a simple internal queue |

If no real sensors exist yet, the **CWRU Bearing Dataset** or **NASA Prognostics dataset** (both public) can validate the approach before real hardware is installed.

## 4. Input / Output Contract
**Input (streamed):**
```json
{
  "machine_id": "LOOM-07",
  "timestamp": "2026-07-31T10:00:00Z",
  "vibration_rms": 0.42,
  "temperature_c": 68.5
}
```
**Output:**
```json
{
  "machine_id": "LOOM-07",
  "health_score": 0.61,
  "estimated_remaining_useful_life_days": 9,
  "priority": "high",
  "recommended_action": "schedule inspection within 3 days"
}
```

## 5. Internal Working — Step by Step
1. Ingest sensor readings continuously, maintain a rolling feature window (mean, RMS, kurtosis of vibration signal).
2. Feed the feature window into a degradation model to compute a health score (0–1).
3. Fit a simple trend line on the health score history to estimate days-to-failure.
4. Rank all machines by urgency and push a prioritized maintenance queue.
5. Write to shared state — cross-referenced by Agent 5 if a machine is also showing an energy anomaly (often correlated with mechanical wear).

## 6. Model / Algorithm Details
- **Feature extraction:** standard vibration signal statistics (RMS, kurtosis, crest factor) — well-established in industrial predictive maintenance.
- **Health scoring model:** gradient boosting regressor trained on historical run-to-failure data (public dataset for the demo, real data once sensors deployed).
- **Trend estimation:** simple linear/exponential decay fit on the health score to project remaining useful life — resist the urge to over-engineer this with deep learning for a hackathon timeline; explainable models win more trust here.

## 7. Tech Stack
- Python, FastAPI, scikit-learn, pandas, numpy (signal feature extraction)
- TimescaleDB/InfluxDB for sensor time series

## 8. Standalone API Contract
```
POST /agents/maintenance/ingest
GET  /agents/maintenance/queue     -> prioritized list of machines needing attention
GET  /agents/maintenance/health
```

## 9. Standalone Deployment
```
agents/maintenance/
├── main.py
├── feature_extraction.py
├── health_model.py
├── Dockerfile
└── requirements.txt
```

## 10. How the Master Brain Calls It
Runs continuously in the background. Its output can trigger a work order that competes for the same maintenance team resources as anything flagged by Agent 5 — the orchestrator should merge both into a single maintenance queue rather than sending conflicting requests to the same team.

## 11. Production Hardening
- False-alarm cost matters — an unnecessary maintenance call is expensive; tune thresholds against a validation set with real cost tradeoffs in mind, not just statistical significance.
- Sensor calibration drift: schedule periodic sensor recalibration checks, since a miscalibrated sensor silently degrades the whole agent's accuracy.
- Model retraining pipeline: as real failure data accumulates post-deployment, retrain and version the model — this agent should get measurably better over the mill's operating life.

## 12. Testing Strategy
- Backtest on historical run-to-failure sequences: does the predicted remaining-useful-life correlate with the actual failure date?
- Stress test with rapid sensor value changes to confirm no crash/latency spike.

## 13. Monitoring & Observability
- Track: prediction accuracy against actual failures over time, false-alarm rate, average lead time given before failure (the core value metric to report to plant management).

## 14. Environment Variables
```
HEALTH_SCORE_ALERT_THRESHOLD=0.65
FEATURE_WINDOW_MINUTES=30
MODEL_PATH=/app/model_artifacts/maintenance_model.pkl
```
