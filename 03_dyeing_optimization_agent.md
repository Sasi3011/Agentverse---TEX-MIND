# Agent 3 — Dyeing Recipe Optimization Agent

## 1. Role in the System
Takes a batch that has passed intake and weaving inspection, and recommends the dye recipe (dye %, temperature, time, liquor ratio) most likely to hit the target shade on the first attempt.

## 2. Real-World Problem It Solves
Re-dyeing is one of the biggest hidden costs in a mill — every failed shade match wastes water, dye chemicals, energy, and time. Experienced dye masters do this from memory; this agent encodes that memory and improves it with data.

## 3. What You Need to Provide
| Item | Why it's needed | Example |
|---|---|---|
| Historical recipe → outcome log | Core training data | CSV: `shade_code, fabric_type, dye_pct, temp_c, time_min, liquor_ratio, outcome (match/re-dye)` |
| Target shade card | What "correct" means | Standard shade card codes used by your mill |
| Dye chemical cost sheet (optional) | To also optimize for cost, not just match probability | `dye_costs.csv` |

If no historical log exists yet, start the agent in "recommendation from nearest-neighbor of a small seed dataset" mode and let it learn as real outcomes are logged back in.

## 4. Input / Output Contract
**Input:**
```json
{
  "batch_id": "B-2026-0001",
  "target_shade_code": "NAVY-204",
  "fabric_type": "cotton_poplin"
}
```
**Output:**
```json
{
  "batch_id": "B-2026-0001",
  "recommended_recipe": {
    "dye_pct": 2.4,
    "temperature_c": 90,
    "time_min": 45,
    "liquor_ratio": "1:8"
  },
  "predicted_match_probability": 0.88,
  "estimated_redye_risk": "low"
}
```

## 5. Internal Working — Step by Step
1. Look up historical recipes for the same/similar shade + fabric combination.
2. If enough history exists, run the trained outcome-prediction model across candidate recipe variations, pick the highest match-probability candidate.
3. If sparse history, fall back to k-nearest-neighbor lookup on shade code similarity.
4. Return top recommendation with a confidence score and, optionally, 2 alternative recipes for the dye master to choose from (never fully remove human override in early deployment).
5. Log the eventual real-world outcome back into the training set (closed feedback loop) once the dye master reports match/re-dye.

## 6. Model / Algorithm Details
- **Model:** Gradient-boosted regressor predicting match probability from recipe parameters + fabric type + shade embedding.
- **Cold-start fallback:** k-NN over encoded shade codes.
- **Continuous learning:** retrain weekly as new match/re-dye outcomes are logged — this agent should visibly get smarter over the mill's lifetime, which is a strong point for your pitch.

## 7. Tech Stack
- Python, FastAPI, scikit-learn, pandas
- Postgres for the growing recipe-outcome log (this table is the agent's core IP over time)

## 8. Standalone API Contract
```
POST /agents/dye/recommend
POST /agents/dye/log-outcome   {"batch_id": "...", "outcome": "match"|"re-dye"}
GET  /agents/dye/health
```

## 9. Standalone Deployment
```
agents/dye/
├── main.py
├── model.py
├── retrain_job.py     # scheduled weekly retrain
├── Dockerfile
└── requirements.txt
```

## 10. How the Master Brain Calls It
Called after Agent 2 confirms the fabric roll is acceptable. Runs **before** the resource/safety stages since dyeing parameters affect downstream energy (Agent 5) and effluent (Agent 4) load.

## 11. Production Hardening
- Never auto-execute a recipe without a human confirmation step in early deployment — this agent recommends, a dye master approves. Full automation only after a track record is established.
- Confidence floor: if predicted match probability < 0.5, explicitly say "insufficient historical data — defer to manual recipe" rather than guessing.
- Outcome-logging endpoint must be idempotent (same batch_id logged twice shouldn't double-count).

## 12. Testing Strategy
- Backtest: hold out the most recent 20% of historical recipes, check if the model's top recommendation would have matched the recorded outcome.
- Cold-start test: confirm sensible k-NN fallback behavior with an empty/sparse database.

## 13. Monitoring & Observability
- Track: recommendation acceptance rate (did the dye master follow it), real match rate vs predicted, retrain frequency and resulting accuracy change.

## 14. Environment Variables
```
DATABASE_URL=postgresql://user:pass@host:5432/texverse
MIN_CONFIDENCE_TO_RECOMMEND=0.5
RETRAIN_SCHEDULE_CRON=0 2 * * 0
```
