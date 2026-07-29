import os
import sys

# Ensure the demand agent root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from generate_dataset import generate_orders, TARGET_ROWS, OUTPUT_FILE, DATA_DIR
from model import train_demand_models

if __name__ == "__main__":
    print("=" * 60)
    print("Agent 8 - Demand Forecasting: Model Training Pipeline")
    print("=" * 60)

    # Step 1: Generate dataset if missing
    if not os.path.exists(OUTPUT_FILE):
        print(f"\nStep 1: Generating {TARGET_ROWS:,}-row synthetic dataset ...")
        os.makedirs(DATA_DIR, exist_ok=True)
        df = generate_orders(TARGET_ROWS)
        df.to_csv(OUTPUT_FILE, index=False)
        print(f"  OK  Dataset saved: {len(df):,} rows -> {OUTPUT_FILE}")
    else:
        import pandas as _pd
        existing = _pd.read_csv(OUTPUT_FILE, nrows=5)
        print(f"\nStep 1: Dataset already exists at {OUTPUT_FILE} - skipping generation.")

    # Step 2: Train Prophet models
    print("\nStep 2: Training Prophet models (one per product type) ...")
    success = train_demand_models()

    if success:
        print("\nOK - Agent 8 Training Pipeline Completed Successfully.")
        print("   You can now start the API: uvicorn main:app --port 8008")
    else:
        print("\nFAIL - Training Pipeline Failed. Check logs above.")
        sys.exit(1)
