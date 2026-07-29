"""
Agent 8 — Demand Forecasting: Synthetic Dataset Generator
Generates 1,000,000 order records (Jan 2020 – Dec 2025) with:
  - 20 product types (cotton, polyester, blend variants)
  - Festival peaks: Diwali (Oct), Eid (Apr), Christmas (Dec)
  - Export cycles: spring (Mar–Apr) and autumn (Sep–Oct) peaks
  - Buyer region diversity
  - Daily records, aggregated to weekly by the model trainer
"""

import os
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# ── Constants ─────────────────────────────────────────────────────────────────

TARGET_ROWS = 1_000_000
START_DATE  = datetime(2020, 1, 1)
END_DATE    = datetime(2025, 12, 31)
DATA_DIR    = os.path.join(os.path.dirname(__file__), "data")
OUTPUT_FILE = os.path.join(DATA_DIR, "orders.csv")

PRODUCT_TYPES = [
    # Cotton variants
    "cotton_poplin_navy",
    "cotton_poplin_white",
    "cotton_twill_khaki",
    "cotton_twill_black",
    "cotton_canvas_olive",
    "cotton_jersey_grey",
    "cotton_fleece_navy",
    # Polyester variants
    "polyester_satin_ivory",
    "polyester_georgette_blue",
    "polyester_crepe_black",
    "polyester_satin_red",
    # Blend variants
    "poly_cotton_white",
    "poly_cotton_navy",
    "linen_cotton_beige",
    "linen_cotton_khaki",
    "viscose_blend_burgundy",
    "viscose_blend_teal",
    # Premium blends
    "modal_cotton_grey",
    "bamboo_cotton_white",
    "tencel_blend_olive",
]

BUYER_REGIONS = ["North_India", "South_India", "West_India", "East_India",
                 "Europe_UK", "Europe_EU", "USA_East", "USA_West",
                 "Middle_East", "Southeast_Asia"]

# Base weekly order quantity (metres) per product type — some products ordered more
BASE_QTY = {
    "cotton_poplin_navy":       3800,
    "cotton_poplin_white":      4200,
    "cotton_twill_khaki":       3500,
    "cotton_twill_black":       3900,
    "cotton_canvas_olive":      2800,
    "cotton_jersey_grey":       3100,
    "cotton_fleece_navy":       2600,
    "polyester_satin_ivory":    3300,
    "polyester_georgette_blue": 2900,
    "polyester_crepe_black":    3600,
    "polyester_satin_red":      2700,
    "poly_cotton_white":        4500,
    "poly_cotton_navy":         4100,
    "linen_cotton_beige":       2400,
    "linen_cotton_khaki":       2200,
    "viscose_blend_burgundy":   2100,
    "viscose_blend_teal":       1900,
    "modal_cotton_grey":        1800,
    "bamboo_cotton_white":      1700,
    "tencel_blend_olive":       1600,
}


# ── Seasonality helpers ────────────────────────────────────────────────────────

def festival_multiplier(date: pd.Timestamp) -> float:
    """Returns a seasonal multiplier based on textile festival / export cycle."""
    month = date.month
    day   = date.day

    mult = 1.0

    # ── Export spring cycle (Feb 15 – Apr 30): +35%
    if month == 2 and day >= 15:
        mult += 0.35
    elif month in (3, 4):
        mult += 0.35
    elif month == 5 and day <= 15:
        mult += 0.20  # trailing

    # ── Export autumn cycle (Aug 15 – Oct 31): +30%
    if month == 8 and day >= 15:
        mult += 0.30
    elif month in (9, 10):
        mult += 0.30
    elif month == 11 and day <= 15:
        mult += 0.15  # trailing

    # ── Diwali build-up (Oct 1 – Oct 31): +25% (cumulative with export)
    if month == 10:
        mult += 0.25

    # ── Christmas / year-end (Dec 1 – Dec 25): +20%
    if month == 12 and day <= 25:
        mult += 0.20

    # ── Eid peak (Apr): +15% (cumulative with spring export)
    if month == 4:
        mult += 0.15

    # ── Low season (Jun–Jul, Jan): -15%
    if month in (6, 7):
        mult -= 0.15
    if month == 1:
        mult -= 0.10

    return max(0.5, mult)  # never drop below 50% of base


def trend_multiplier(date: pd.Timestamp) -> float:
    """Gentle 2% annual growth trend starting from 2020."""
    years_since_start = (date.year - 2020) + (date.month - 1) / 12
    return 1.0 + 0.02 * years_since_start


def day_of_week_factor(dow: int) -> float:
    """Orders less likely on weekends."""
    factors = {0: 1.1, 1: 1.15, 2: 1.1, 3: 1.05, 4: 1.0, 5: 0.6, 6: 0.4}
    return factors.get(dow, 1.0)


# ── Main generation logic ─────────────────────────────────────────────────────

def generate_orders(target_rows: int = TARGET_ROWS, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    date_range = pd.date_range(START_DATE, END_DATE, freq="D")
    total_days = len(date_range)

    # Compute rows per day (distributed to hit target_rows exactly)
    rows_per_day_base = target_rows // total_days  # ~454 rows/day
    remainder = target_rows - rows_per_day_base * total_days

    records = []

    for i, date in enumerate(date_range):
        n_rows = rows_per_day_base + (1 if i < remainder else 0)

        if n_rows == 0:
            continue

        fest_mult  = festival_multiplier(date)
        trend_mult = trend_multiplier(date)
        dow_factor = day_of_week_factor(date.dayofweek)

        # Sample product types for this day (weighted by base qty — popular products appear more)
        base_weights = np.array([BASE_QTY[p] for p in PRODUCT_TYPES], dtype=float)
        base_weights /= base_weights.sum()
        chosen_products = rng.choice(PRODUCT_TYPES, size=n_rows, p=base_weights)

        # Sample buyer regions (uniform)
        chosen_buyers = rng.choice(BUYER_REGIONS, size=n_rows)

        # Build quantities
        quantities = []
        for product in chosen_products:
            base = BASE_QTY[product] / 30  # daily slice of monthly base
            qty = base * fest_mult * trend_mult * dow_factor
            # Add noise: ±25%
            qty *= rng.uniform(0.75, 1.25)
            # Round to nearest 50m increment
            qty = max(50, round(qty / 50) * 50)
            quantities.append(int(qty))

        # is_confirmed: ~12% of orders are already confirmed in advance
        is_confirmed = rng.random(n_rows) < 0.12

        day_df = pd.DataFrame({
            "order_date":   [date.strftime("%Y-%m-%d")] * n_rows,
            "product_type": chosen_products,
            "buyer_region": chosen_buyers,
            "quantity_m":   quantities,
            "is_confirmed": is_confirmed.astype(int),
        })
        records.append(day_df)

    df = pd.concat(records, ignore_index=True)
    return df


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"Generating {TARGET_ROWS:,} synthetic order records ...")
    print(f"Date range : {START_DATE.date()} -> {END_DATE.date()}")
    print(f"Products   : {len(PRODUCT_TYPES)} types")
    print(f"Buyers     : {len(BUYER_REGIONS)} regions")

    os.makedirs(DATA_DIR, exist_ok=True)

    df = generate_orders(TARGET_ROWS)

    actual = len(df)
    print(f"\nActual rows generated : {actual:,}")
    print(f"Date range in data    : {df['order_date'].min()} -> {df['order_date'].max()}")
    print(f"Products covered      : {df['product_type'].nunique()}")
    print(f"Confirmed orders      : {df['is_confirmed'].sum():,} ({df['is_confirmed'].mean():.1%})")
    print(f"\nSaving to {OUTPUT_FILE} ...")

    df.to_csv(OUTPUT_FILE, index=False)
    size_mb = os.path.getsize(OUTPUT_FILE) / (1024 * 1024)
    print(f"Saved {actual:,} rows  ({size_mb:.1f} MB)")
    print("Dataset generation complete.")
