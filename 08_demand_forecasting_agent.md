# Agent 8 — Demand Forecasting Agent

## 1. Role in the System
Predicts upcoming order volume so production scheduling (and everything upstream — intake, dyeing capacity, energy planning) can be planned ahead of actual orders arriving.

## 2. Real-World Problem It Solves
Mills often react to orders after they land, causing rushed production, overtime costs, and inconsistent quality. A forecast — even a directional one — lets planning happen ahead of time.

## 3. What You Need to Provide
| Item | Why it's needed | Example |
|---|---|---|
| Historical order data | Core training data | `orders.csv`: date, product type, quantity, buyer |
| Seasonality context | Textile demand is seasonal (festival/export cycles) | Known peak months for your buyer mix |
| Current open order book | To combine forecast with known commitments | Live ERP order feed, or manual entry |

## 4. Input / Output Contract
**Input:**
```json
{
  "product_type": "cotton_poplin_navy",
  "forecast_horizon_weeks": 4
}
```
**Output:**
```json
{
  "product_type": "cotton_poplin_navy",
  "forecast": [
    {"week": "2026-W32", "predicted_qty_m": 4200},
    {"week": "2026-W33", "predicted_qty_m": 4600}
  ],
  "confidence_interval": [3800, 5000],
  "recommended_production_plan_m_per_week": 4400
}
```

## 5. Internal Working — Step by Step
1. Pull historical order time series for the requested product type.
2. Decompose into trend + seasonality (standard time-series decomposition).
3. Fit a forecasting model and project forward for the requested horizon.
4. Blend the statistical forecast with any known confirmed orders already in the pipeline (a confirmed order should override the pure forecast for that period).
5. Output a recommended weekly production target, which becomes an input constraint the orchestrator can pass toward scheduling decisions.

## 6. Model / Algorithm Details
- **Model:** Facebook Prophet or a simple SARIMA model — both handle seasonality well and are explainable to non-technical plant managers, which matters more here than squeezing out marginal accuracy with a black-box deep model.
- **Cold start (little history):** fall back to a moving-average + manual seasonality multiplier the plant manager provides.

## 7. Tech Stack
- Python, FastAPI, Prophet (or statsmodels SARIMA), pandas
- Postgres for order history

## 8. Standalone API Contract
```
POST /agents/demand/forecast
GET  /agents/demand/health
```

## 9. Standalone Deployment
```
agents/demand/
├── main.py
├── forecast_model.py
├── Dockerfile
└── requirements.txt
```

## 10. How the Master Brain Calls It
Called on a schedule (e.g. weekly) rather than per-batch — it feeds a planning horizon, not a single transaction. Its output can be read by the orchestrator to pre-allocate expected load across Agents 1, 3, 5, and 6 (e.g. warn maintenance to schedule downtime in a predicted low-demand week, not a predicted peak week).

## 11. Production Hardening
- Confidence intervals must always be shown alongside the point forecast — a bare number invites over-trust in a genuinely uncertain estimate.
- Re-fit the model on a regular schedule (weekly/monthly) as new order data arrives; don't let it run indefinitely on stale training data.
- Clearly separate "confirmed orders" from "forecasted demand" in every output — never blend them without labeling which is which.

## 12. Testing Strategy
- Backtest: train on data up to time T, forecast T+1..T+4, compare against actual — report MAPE (mean absolute percentage error).
- Seasonality sanity check: confirm the model reproduces known peak/trough patterns from history.

## 13. Monitoring & Observability
- Track: forecast accuracy (rolling MAPE), forecast vs actual variance trend over time.

## 14. Environment Variables
```
DATABASE_URL=postgresql://user:pass@host:5432/texverse
FORECAST_MODEL=prophet
RETRAIN_SCHEDULE_CRON=0 3 * * 1
```
