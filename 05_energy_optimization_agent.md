# Agent 5 — Energy & Utility Optimization Agent

## 1. Role in the System
Watches power consumption across boilers, compressors, and motors, and flags waste before it shows up as a shocking electricity bill at month-end.

## 2. Real-World Problem It Solves
Mills run heavy utilities (boilers for dyeing heat, compressors for pneumatic systems) around the clock. Small inefficiencies — a compressor cycling when it shouldn't, a boiler running hotter than needed — compound into large costs. Nobody watches this in real time today.

## 3. What You Need to Provide
| Item | Why it's needed | Example |
|---|---|---|
| Power meter feed per machine | The actual consumption data | kWh readings per machine per interval (real smart meters, or simulated) |
| Machine baseline specs | To know what "normal" looks like | Rated power, expected duty cycle per machine type |
| Tariff structure | To translate kWh into cost/savings | Your electricity board's tariff slabs, peak/off-peak rates |

## 4. Input / Output Contract
**Input (streamed per machine per interval):**
```json
{
  "machine_id": "BOILER-01",
  "timestamp": "2026-07-31T10:00:00Z",
  "power_kwh": 145.2
}
```
**Output:**
```json
{
  "machine_id": "BOILER-01",
  "status": "anomaly",
  "baseline_kwh": 110.0,
  "deviation_pct": 32.0,
  "estimated_monthly_excess_cost_inr": 18500,
  "likely_cause_hint": "check insulation / thermostat calibration"
}
```

## 5. Internal Working — Step by Step
1. Maintain a rolling baseline (moving average) of normal consumption per machine, per time-of-day (accounts for shift patterns).
2. Compare each new reading against the baseline using a z-score or isolation forest.
3. If deviation exceeds a threshold, compute the cost impact using the tariff structure and raise a flag.
4. Aggregate flags into a daily/weekly energy efficiency report.
5. Write to shared state — this feeds into Agent 10's sustainability/carbon report.

## 6. Model / Algorithm Details
- **Baseline model:** rolling average + standard deviation per machine per shift period (simple, explainable, good enough to start).
- **Enhanced model:** `IsolationForest` (scikit-learn) trained per machine on historical multivariate readings for more nuanced anomaly detection.
- Deliberately avoid an opaque deep-learning model here — plant engineers need to *trust and understand* why something was flagged.

## 7. Tech Stack
- Python, FastAPI, scikit-learn, pandas
- TimescaleDB/InfluxDB for the time-series data
- A small rules table for tariff calculation

## 8. Standalone API Contract
```
POST /agents/energy/ingest
GET  /agents/energy/report?machine_id=&range=
GET  /agents/energy/health
```

## 9. Standalone Deployment
```
agents/energy/
├── main.py
├── baseline.py
├── anomaly_model.py
├── Dockerfile
└── requirements.txt
```

## 10. How the Master Brain Calls It
Runs continuously in the background alongside Agent 4 (they're both always-on utility monitors). Its output is consumed by Agent 10 for the sustainability report and can independently trigger a maintenance ticket if a sustained deviation suggests mechanical failure (cross-reference with Agent 6).

## 11. Production Hardening
- Baselines must be recalculated periodically (seasonal effects — a boiler works harder in winter) — don't freeze a baseline forever.
- Guard against meter dropout being misread as "zero consumption anomaly" — distinguish "no data" from "actually zero."
- Cost estimates should be clearly labeled as estimates, with the tariff assumptions shown, so plant managers can sanity-check them.

## 12. Testing Strategy
- Backtest against historical consumption data with known inefficiency events (if you have any past incident to validate against).
- Synthetic injection test: feed a deliberately spiked reading, confirm detection within N readings.

## 13. Monitoring & Observability
- Track: total flagged anomalies/week, estimated cumulative cost savings if addressed, per-machine trend charts.

## 14. Environment Variables
```
ANOMALY_ZSCORE_THRESHOLD=2.5
TARIFF_RATE_PER_KWH_INR=7.5
BASELINE_WINDOW_DAYS=14
```
