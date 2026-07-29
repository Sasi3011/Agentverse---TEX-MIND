"""
Agent 8 — Demand Forecasting: Prophet Model Training & Inference
"""

import os
import json
import warnings
import pandas as pd
import numpy as np
import joblib
from datetime import datetime, timedelta
from typing import Optional

warnings.filterwarnings("ignore")

# ── Paths ─────────────────────────────────────────────────────────────────────

BASE_DIR       = os.path.dirname(__file__)
DATA_DIR       = os.path.join(BASE_DIR, "data")
ARTIFACTS_DIR  = os.path.join(BASE_DIR, "model_artifacts")
DATA_FILE      = os.path.join(DATA_DIR, "orders.csv")
META_FILE      = os.path.join(ARTIFACTS_DIR, "meta.json")

PRODUCT_TYPES = [
    "cotton_poplin_navy", "cotton_poplin_white", "cotton_twill_khaki",
    "cotton_twill_black", "cotton_canvas_olive", "cotton_jersey_grey",
    "cotton_fleece_navy", "polyester_satin_ivory", "polyester_georgette_blue",
    "polyester_crepe_black", "polyester_satin_red", "poly_cotton_white",
    "poly_cotton_navy", "linen_cotton_beige", "linen_cotton_khaki",
    "viscose_blend_burgundy", "viscose_blend_teal", "modal_cotton_grey",
    "bamboo_cotton_white", "tencel_blend_olive",
]


def model_path(product_type: str) -> str:
    safe = product_type.replace(" ", "_").replace("/", "_")
    return os.path.join(ARTIFACTS_DIR, f"demand_model_{safe}.pkl")


# ── Dataset helpers ───────────────────────────────────────────────────────────

def load_weekly_series(product_type: str) -> pd.DataFrame:
    """Load orders.csv and aggregate to weekly totals for one product type."""
    if not os.path.exists(DATA_FILE):
        raise FileNotFoundError(
            f"Dataset not found at {DATA_FILE}. "
            "Run generate_dataset.py first."
        )
    df = pd.read_csv(DATA_FILE, parse_dates=["order_date"])
    subset = df[df["product_type"] == product_type].copy()
    if subset.empty:
        raise ValueError(f"No data found for product type: {product_type}")

    subset["week"] = subset["order_date"].dt.to_period("W").apply(lambda p: p.start_time)
    weekly = (
        subset.groupby("week")["quantity_m"]
        .sum()
        .reset_index()
        .rename(columns={"week": "ds", "quantity_m": "y"})
        .sort_values("ds")
    )
    return weekly


# ── Training ──────────────────────────────────────────────────────────────────

def train_demand_models() -> bool:
    """Train one Prophet model per product type and save to disk."""
    try:
        from prophet import Prophet
    except ImportError:
        print("ERROR: prophet not installed. Run: pip install prophet")
        return False

    if not os.path.exists(DATA_FILE):
        print(f"Dataset missing: {DATA_FILE}")
        print("Generating dataset first …")
        from generate_dataset import generate_orders, TARGET_ROWS
        import os as _os
        _os.makedirs(DATA_DIR, exist_ok=True)
        df = generate_orders(TARGET_ROWS)
        df.to_csv(DATA_FILE, index=False)
        print(f"Dataset generated: {len(df):,} rows")

    os.makedirs(ARTIFACTS_DIR, exist_ok=True)
    trained = []
    failed  = []

    for i, product in enumerate(PRODUCT_TYPES, 1):
        print(f"[{i}/{len(PRODUCT_TYPES)}] Training: {product}")
        try:
            weekly = load_weekly_series(product)
            if len(weekly) < 20:
                print(f"  ⚠  Only {len(weekly)} weekly points — skipping (need ≥20)")
                failed.append(product)
                continue

            m = Prophet(
                yearly_seasonality=True,
                weekly_seasonality=False,
                daily_seasonality=False,
                seasonality_mode="multiplicative",
                changepoint_prior_scale=0.15,
                seasonality_prior_scale=10.0,
                interval_width=0.80,
            )
            # Custom textile industry seasonalities
            m.add_seasonality(
                name="export_spring",
                period=365.25,
                fourier_order=3,
                condition_name="spring_export",
            )

            weekly["spring_export"] = weekly["ds"].dt.month.isin([3, 4]).astype(int)
            m.fit(weekly)

            # Quick backtest MAPE (last 4 weeks held out)
            train_df = weekly.iloc[:-4]
            test_df  = weekly.iloc[-4:]
            m_bt = Prophet(
                yearly_seasonality=True,
                weekly_seasonality=False,
                daily_seasonality=False,
                seasonality_mode="multiplicative",
                changepoint_prior_scale=0.15,
            )
            m_bt.fit(train_df)
            future_bt = m_bt.make_future_dataframe(periods=4, freq="W")
            forecast_bt = m_bt.predict(future_bt)
            pred_vals = forecast_bt.iloc[-4:]["yhat"].values
            actual_vals = test_df["y"].values
            mape = float(np.mean(np.abs((actual_vals - pred_vals) / (actual_vals + 1e-8))) * 100)

            artifact = {"model": m, "mape": round(mape, 2), "product": product}
            joblib.dump(artifact, model_path(product))
            trained.append(product)
            print(f"  ✓  Saved | Backtest MAPE = {mape:.1f}%")

        except Exception as e:
            print(f"  ✗  Failed: {e}")
            failed.append(product)

    # Save meta
    meta = {
        "trained_at": datetime.utcnow().isoformat(),
        "model_version": "prophet_v1",
        "trained_products": trained,
        "failed_products": failed,
        "total": len(PRODUCT_TYPES),
        "success": len(trained),
    }
    with open(META_FILE, "w") as f:
        json.dump(meta, f, indent=2)

    print(f"\n{'='*50}")
    print(f"Training complete: {len(trained)}/{len(PRODUCT_TYPES)} models saved")
    if failed:
        print(f"Failed: {failed}")
    return len(trained) > 0


# ── Inference ─────────────────────────────────────────────────────────────────

def _moving_average_forecast(product_type: str, horizon_weeks: int) -> dict:
    """Cold-start fallback: moving average of last 8 weeks of data."""
    try:
        weekly = load_weekly_series(product_type)
        last_8 = weekly.tail(8)["y"].values
        base   = float(np.mean(last_8))
        std    = float(np.std(last_8))
    except Exception:
        base = 3000.0
        std  = 400.0

    last_date = datetime.utcnow()
    # Advance to next Monday
    days_ahead = (7 - last_date.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7
    next_monday = last_date + timedelta(days=days_ahead)

    forecast_weeks = []
    for w in range(horizon_weeks):
        week_start = next_monday + timedelta(weeks=w)
        week_label = f"{week_start.isocalendar()[0]}-W{week_start.isocalendar()[1]:02d}"
        forecast_weeks.append({
            "week": week_label,
            "predicted_qty_m": int(round(base / 50) * 50),
            "source": "moving_average",
        })

    return {
        "product_type":   product_type,
        "forecast":       forecast_weeks,
        "confidence_interval": [max(0, int(base - 2*std)), int(base + 2*std)],
        "recommended_production_plan_m_per_week": int(round(base / 50) * 50),
        "model_used":     "moving_average_fallback",
        "mape":           None,
    }


def run_forecast(
    product_type: str,
    horizon_weeks: int,
    confirmed_orders: Optional[list] = None,
) -> dict:
    """
    Run Prophet forecast for `product_type` over `horizon_weeks` weeks.
    Blends in any confirmed_orders (list of {week_label, quantity_m}).
    """
    if product_type not in PRODUCT_TYPES:
        raise ValueError(
            f"Unknown product type: {product_type}. "
            f"Valid: {PRODUCT_TYPES}"
        )

    horizon_weeks = max(1, min(12, horizon_weeks))

    mp = model_path(product_type)
    if not os.path.exists(mp):
        return _moving_average_forecast(product_type, horizon_weeks)

    try:
        artifact = joblib.load(mp)
        m        = artifact["model"]
        mape     = artifact.get("mape")

        future = m.make_future_dataframe(periods=horizon_weeks, freq="W")
        future["spring_export"] = future["ds"].dt.month.isin([3, 4]).astype(int)

        fc = m.predict(future)
        # Only last horizon_weeks rows are the forecast
        fc_future = fc.tail(horizon_weeks).copy()

        forecast_weeks = []
        all_predicted  = []
        confirmed_map  = {}

        if confirmed_orders:
            for co in confirmed_orders:
                confirmed_map[co["week_label"]] = co["quantity_m"]

        for _, row in fc_future.iterrows():
            dt = pd.Timestamp(row["ds"])
            iso_cal = dt.isocalendar()
            week_label = f"{iso_cal[0]}-W{iso_cal[1]:02d}"
            yhat  = max(0, float(row["yhat"]))
            ylow  = max(0, float(row["yhat_lower"]))
            yhigh = max(0, float(row["yhat_upper"]))

            predicted_qty = int(round(yhat / 50) * 50)
            all_predicted.append(predicted_qty)

            entry = {
                "week":          week_label,
                "predicted_qty_m": predicted_qty,
                "ci_lower":      int(round(ylow / 50) * 50),
                "ci_upper":      int(round(yhigh / 50) * 50),
                "source":        "prophet",
            }

            if week_label in confirmed_map:
                entry["confirmed_qty_m"] = int(confirmed_map[week_label])
                entry["effective_qty_m"] = int(confirmed_map[week_label])
                entry["source"]          = "confirmed_override"
            else:
                entry["effective_qty_m"] = predicted_qty

            forecast_weeks.append(entry)

        # Overall CI = avg lower / upper across horizon
        avg_lower = int(round(np.mean([e["ci_lower"] for e in forecast_weeks]) / 50) * 50)
        avg_upper = int(round(np.mean([e["ci_upper"] for e in forecast_weeks]) / 50) * 50)
        recommended = int(round(np.mean(all_predicted) / 50) * 50)

        # Past 6 weeks history
        fc_hist = fc.iloc[-(horizon_weeks + 6): -horizon_weeks] if len(fc) >= (horizon_weeks + 6) else fc.head(6)
        history_weeks = []
        for _, row in fc_hist.iterrows():
            dt = pd.Timestamp(row["ds"])
            iso_cal = dt.isocalendar()
            week_label = f"{iso_cal[0]}-W{iso_cal[1]:02d}"
            history_weeks.append({
                "week": week_label,
                "actual_qty_m": max(0, int(round(float(row["yhat"]) / 50) * 50))
            })

        return {
            "product_type":   product_type,
            "history":        history_weeks,
            "forecast":       forecast_weeks,
            "confidence_interval": [avg_lower, avg_upper],
            "recommended_production_plan_m_per_week": recommended,
            "model_used":     "prophet_v1",
            "mape":           mape,
        }

    except Exception as e:
        print(f"Prophet inference failed for {product_type}: {e}")
        return _moving_average_forecast(product_type, horizon_weeks)


def get_meta() -> dict:
    if not os.path.exists(META_FILE):
        return {"status": "no_models", "trained_at": None}
    with open(META_FILE) as f:
        return json.load(f)


def model_is_available(product_type: str) -> bool:
    return os.path.exists(model_path(product_type))
