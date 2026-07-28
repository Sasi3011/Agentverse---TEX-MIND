# Agent 10 — Sustainability & Carbon Reporting Agent

## 1. Role in the System
The final agent in the pipeline. Aggregates every other agent's output into one consolidated sustainability/ESG report that a mill can actually hand to an export buyer or auditor.

## 2. Real-World Problem It Solves
Export buyers (H&M, Marks & Spencer, and similar) increasingly require documented ESG data before placing orders. Mills often assemble this manually, inconsistently, and slowly. This agent produces it automatically from data the other 9 agents already generated.

## 3. What You Need to Provide
| Item | Why it's needed | Example |
|---|---|---|
| Emission factor reference | To convert energy/water into CO2e | Grid emission factor for your region (e.g. kg CO2 per kWh), published by CEA/grid authority |
| Buyer report template (optional) | To match the exact format a buyer expects | Buyer's ESG reporting template, if one exists |
| Reporting period | Time window to summarize | Monthly, quarterly, per shipment |

## 4. Input / Output Contract
**Input:**
```json
{
  "batch_id": "B-2026-0001",
  "period": "2026-07"
}
```
**Output (summary):**
```json
{
  "batch_id": "B-2026-0001",
  "period": "2026-07",
  "water_compliance": "compliant",
  "energy_used_kwh": 3820,
  "estimated_co2e_kg": 3134,
  "traceability_status": "verified",
  "overall_sustainability_grade": "B+",
  "report_url": "s3://texverse/reports/B-2026-0001_2026-07.pdf"
}
```

## 5. Internal Working — Step by Step
1. Pull the latest state from Agents 4 (effluent), 5 (energy), 9 (traceability) for the requested batch/period.
2. Apply emission-factor formulas to convert energy and water usage into a carbon estimate.
3. Compute a composite sustainability grade using a documented, transparent weighting (not a black-box score — buyers and auditors need to see the formula).
4. Render a formatted report (PDF/Markdown) with all supporting figures and source references.
5. Store the report and expose it via the dashboard and a downloadable link.

## 6. Model / Algorithm Details
- **No ML required here** — this is a deterministic aggregation and reporting function. Keep the scoring formula simple, documented, and auditable; sustainability reports carry real business consequences if they're wrong or seem manipulated.
- Example grading formula (must be tuned to your actual thresholds, this is illustrative):
  `grade = f(compliance_status, energy_efficiency_percentile, traceability_completeness)`

## 7. Tech Stack
- Python, FastAPI, pandas
- Report rendering: Jinja2 templates → WeasyPrint (HTML→PDF) or a Markdown export
- Postgres (read-only aggregation queries against the other agents' data)

## 8. Standalone API Contract
```
POST /agents/sustainability/generate-report
GET  /agents/sustainability/report/{batch_id}
GET  /agents/sustainability/health
```

## 9. Standalone Deployment
```
agents/sustainability/
├── main.py
├── aggregator.py
├── grading.py
├── templates/report_template.html
├── Dockerfile
└── requirements.txt
```

## 10. How the Master Brain Calls It
Runs **last** in the pipeline — it is explicitly dependent on Agents 4, 5, and 9 having already produced their outputs for the relevant batch/period. The orchestrator should not call this agent until those three have returned, since a report generated on incomplete data would be misleading.

## 11. Production Hardening
- Every number in the report must be traceable back to its source agent and formula — no unexplained composite scores. This matters for real buyer audits, which will ask "how was this calculated."
- Version the grading formula — if it changes, historical reports should show which formula version generated them, so scores remain comparable over time.
- Report generation should fail loudly (not silently produce a partial/misleading report) if any dependent agent's data is missing or stale.

## 12. Testing Strategy
- Unit test the emission-factor math against manually calculated examples.
- Snapshot test the rendered report template for formatting regressions.
- Test the "missing dependency data" failure path explicitly.

## 13. Monitoring & Observability
- Track: reports generated/month, average sustainability grade trend over time, time from request to report delivery.

## 14. Environment Variables
```
GRID_EMISSION_FACTOR_KG_PER_KWH=0.82
REPORT_OUTPUT_DIR=/app/reports/generated
REPORT_TEMPLATE_PATH=/app/templates/report_template.html
```
