# Agent 9 — Supply Chain Traceability Agent

## 1. Role in the System
Tracks a batch's full custody chain from raw cotton to finished fabric, and validates whether sustainability/certification claims (e.g. organic, GOTS) are actually backed by a consistent, complete record.

## 2. Real-World Problem It Solves
Export buyers increasingly demand proof of ethical/sustainable sourcing. Many mills currently can't produce a reliable chain-of-custody record on demand, and certification fraud (mislabeling conventional cotton as organic) is a known industry problem this agent directly guards against.

## 3. What You Need to Provide
| Item | Why it's needed | Example |
|---|---|---|
| Chain-of-custody log per batch | The core record | JSON log: farm/ginner → spinner → weaver → dyer, each with timestamp and certifying document reference |
| Certification body reference data | To validate claims | List of valid certificate numbers/issuers you accept (e.g. GOTS registry) |
| Buyer audit requirements | What proof format they expect | Buyer's compliance checklist template |

## 4. Input / Output Contract
**Input:**
```json
{
  "batch_id": "B-2026-0001",
  "custody_log": [
    {"stage": "farm", "entity": "Farm Co-op 12", "cert_ref": "GOTS-2026-889", "timestamp": "2026-06-01"},
    {"stage": "ginning", "entity": "Gin Unit 4", "timestamp": "2026-06-05"},
    {"stage": "spinning", "entity": "Spin Mill A", "timestamp": "2026-06-10"}
  ]
}
```
**Output:**
```json
{
  "batch_id": "B-2026-0001",
  "traceability_status": "incomplete",
  "missing_stages": ["dyeing", "weaving"],
  "certification_valid": true,
  "flags": []
}
```

## 5. Internal Working — Step by Step
1. Validate the custody log structure — required stages present, timestamps in logical order (no stage dated before its predecessor).
2. Cross-check any certificate reference against the known-valid certification registry.
3. Flag gaps (missing stages), inconsistencies (timestamp ordering errors), or mismatched entities (e.g. certificate belongs to a different farm than logged).
4. Produce a traceability completeness score and certification validity flag.
5. Feed the final validated record into Agent 10 for the sustainability report.

## 6. Model / Algorithm Details
- Primarily **structured validation logic**, not machine learning — traceability is a data-integrity problem, and deterministic rules are more trustworthy and auditable here than a probabilistic model.
- Optional enhancement: an anomaly-detection layer flagging unusual custody patterns (e.g. a batch moving between facilities faster than physically plausible) as a fraud-risk signal.

## 7. Tech Stack
- Python, FastAPI, Pydantic (schema validation), JSON Schema
- Postgres (append-only ledger table — never allow updates/deletes on custody records, only new entries, to preserve auditability)

## 8. Standalone API Contract
```
POST /agents/traceability/submit-log
GET  /agents/traceability/status/{batch_id}
GET  /agents/traceability/health
```

## 9. Standalone Deployment
```
agents/traceability/
├── main.py
├── validators.py
├── cert_registry.py
├── Dockerfile
└── requirements.txt
```

## 10. How the Master Brain Calls It
Called once weaving/dyeing stages have logged their custody entries — it's a validation checkpoint rather than a per-frame or per-reading stream. Its certified/flagged status is a hard input to Agent 10's sustainability report; a flagged batch should visibly exclude itself from any "certified sustainable" claim in the final report.

## 11. Production Hardening
- **Append-only data model is non-negotiable** — a traceability record that can be silently edited defeats its entire purpose. Use an audit-logged, insert-only table design (or a genuine append-only ledger/blockchain if the mill wants that extra assurance later).
- Certificate registry must be kept current — stale registry data could either wrongly validate an expired certificate or wrongly reject a valid new one.
- Access control: only authorized roles (QC/compliance staff) can submit custody log entries — this must not be an open write endpoint.

## 12. Testing Strategy
- Unit tests on ordering/consistency validation logic with deliberately broken sample logs.
- Certificate registry lookup tests including expired/revoked certificate scenarios.

## 13. Monitoring & Observability
- Track: % of batches with complete traceability, certification flag rate, average time-to-complete custody log per batch.

## 14. Environment Variables
```
DATABASE_URL=postgresql://user:pass@host:5432/texverse
CERT_REGISTRY_SOURCE=https://gots-registry-endpoint (or local synced copy)
REQUIRED_STAGES=farm,ginning,spinning,weaving,dyeing
```
