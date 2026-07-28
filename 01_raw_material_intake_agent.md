# Agent 1 — Raw Material Intake Agent

## 1. Role in the System
First agent in the pipeline. Every fabric batch starts here. It decides whether an incoming yarn/fiber batch is fit for production before a single machine touches it. No other agent runs meaningfully until this one passes a batch.

## 2. Real-World Problem It Solves
Mills currently accept raw material based on a manual visual check and a paper test report. Bad batches (high moisture, low tensile strength) slip through, causing downstream weaving defects and wasted dye cycles. This agent catches that at the door.

## 3. What You Need to Provide
| Item | Why it's needed | Example |
|---|---|---|
| Batch metadata source | Where intake records come from | CSV upload, ERP API, or manual form in the dashboard |
| Historical batch → defect-rate data | To train/calibrate the quality-scoring model | `historical_batches.csv` with columns: `moisture, strength, count, supplier_id, resulted_in_defect (0/1)` |
| Supplier master list | To flag repeat problem suppliers | `suppliers.csv` |
| Acceptance thresholds | Your mill's actual quality policy | e.g. moisture max 8.5%, strength min 18 g/tex — ask your QC head, don't guess these |

If you don't have historical data, the agent ships with sane rule-based defaults (documented in Section 6) and upgrades to the ML model once you feed it 200+ real batch records.

## 4. Input / Output Contract
**Input (JSON):**
```json
{
  "batch_id": "B-2026-0001",
  "supplier_id": "SUP-14",
  "fiber_count": 30,
  "tensile_strength_g_tex": 19.2,
  "moisture_pct": 7.8
}
```
**Output (JSON):**
```json
{
  "batch_id": "B-2026-0001",
  "decision": "pass",
  "quality_score": 87.4,
  "flags": [],
  "confidence": 0.91
}
```

## 5. Internal Working — Step by Step
1. Validate incoming payload against schema (reject malformed requests immediately, return 422).
2. Apply hard rule gates first (fast-fail): moisture out of range → `decision: flag`, skip model.
3. If it passes rule gates, run the trained regression/classifier for a soft quality score.
4. Cross-check supplier history — if this supplier has >20% historical defect rate, downgrade confidence and add a flag.
5. Write result to shared state (`MillState.intake_result`) and emit an event for the orchestrator.

## 6. Model / Algorithm Details
- **Default (no historical data yet):** rule engine — thresholds on moisture, strength, count.
- **Upgraded (200+ records available):** `scikit-learn` `GradientBoostingClassifier` predicting defect probability from `[moisture, strength, count, supplier_encoded]`. Retrain weekly via a scheduled job as new data accumulates.
- **Explainability:** log SHAP values or simple feature-importance so QC staff can see *why* a batch was flagged — required for trust in a real deployment.

## 7. Tech Stack
- Python 3.11, FastAPI (service wrapper)
- pandas, scikit-learn (model)
- SQLite/Postgres (batch history storage — Postgres for production)
- Pydantic (schema validation)

## 8. Standalone API Contract
```
POST /agents/intake/evaluate
Body: input schema above
Response: output schema above
GET /agents/intake/health
Response: {"status": "ok", "model_version": "1.2.0"}
```

## 9. Standalone Deployment
```
texverse-ai/agents/intake/
├── main.py            # FastAPI app
├── model.py           # training + inference logic
├── Dockerfile
├── requirements.txt
└── model_artifacts/   # saved .pkl model, versioned
```
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
```
Run alone: `docker build -t intake-agent . && docker run -p 8001:8001 intake-agent`

## 10. How the Master Brain Calls It
The orchestrator calls `POST http://intake-agent:8001/agents/intake/evaluate` as the first node in the graph and writes the response into `MillState.intake_result`. It is a **blocking** call — every downstream agent depends on this result, so the graph must wait for it (no parallel execution here).

## 11. Production Hardening
- Input validation via Pydantic — reject bad data before it reaches the model.
- Timeout + retry (max 2 retries, exponential backoff) on the orchestrator's call to this service.
- Log every decision with a request ID for audit trail (required if this ever gates real production material).
- Model versioning: never silently swap models — log `model_version` in every response.
- Rate limiting on the public endpoint if exposed beyond the internal network.

## 12. Testing Strategy
- Unit tests on rule-gate logic (boundary values: exactly at threshold, just above, just below).
- Model regression test: fixed test set, assert accuracy doesn't drop below a baseline after retraining.
- Integration test: mock orchestrator call, confirm shared-state write is correct.

## 13. Monitoring & Observability
- Track: requests/min, average quality score trend, flag rate over time, model drift (accuracy on labeled feedback loop).
- Alert if flag rate suddenly spikes >2x baseline (could mean a supplier quality issue *or* a broken sensor upstream).

## 14. Environment Variables
```
DATABASE_URL=postgresql://user:pass@host:5432/texverse
MODEL_PATH=/app/model_artifacts/intake_model_v1.2.0.pkl
MOISTURE_MAX=8.5
STRENGTH_MIN=18.0
LOG_LEVEL=INFO
```
