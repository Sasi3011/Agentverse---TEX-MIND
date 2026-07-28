import os
import pandas as pd
import numpy as np
import joblib
import time
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, r2_score

def train_maintenance_model():
    base_dir = os.path.dirname(os.path.dirname(__file__))
    data_path = os.path.join(base_dir, "data", "sensor_data_10lakh.csv")
    model_dir = os.path.join(base_dir, "models")
    os.makedirs(model_dir, exist_ok=True)
    model_path = os.path.join(model_dir, "maintenance_model.pkl")
    
    print(f"Loading 10 Lakh dataset from {data_path}...")
    start_time = time.time()
    
    # Load dataset
    df = pd.read_csv(data_path)
    print(f"Loaded {len(df):,} rows in {time.time() - start_time:.2f}s.")
    
    features = ["vibration_rms", "vibration_kurtosis", "temperature_c", "operating_hours"]
    X = df[features]
    y_health = df["health_score"]
    y_rul = df["rul_days"]
    
    print("Training HistGradientBoostingRegressor for Health Score (0-1)...")
    h_start = time.time()
    model_health = HistGradientBoostingRegressor(max_iter=100, random_state=42)
    model_health.fit(X, y_health)
    print(f"Health score model trained in {time.time() - h_start:.2f}s.")
    
    print("Training HistGradientBoostingRegressor for RUL (Days)...")
    r_start = time.time()
    model_rul = HistGradientBoostingRegressor(max_iter=100, random_state=42)
    model_rul.fit(X, y_rul)
    print(f"RUL model trained in {time.time() - r_start:.2f}s.")
    
    # Evaluate sample validation
    sample_df = df.sample(n=50000, random_state=42)
    X_val = sample_df[features]
    
    pred_health = model_health.predict(X_val)
    pred_rul = model_rul.predict(X_val)
    
    mae_h = mean_absolute_error(sample_df["health_score"], pred_health)
    r2_h = r2_score(sample_df["health_score"], pred_health)
    mae_r = mean_absolute_error(sample_df["rul_days"], pred_rul)
    r2_r = r2_score(sample_df["rul_days"], pred_rul)
    
    print("\n--- Model Evaluation Results (Validation 50,000 samples) ---")
    print(f"Health Score - MAE: {mae_h:.4f}, R2: {r2_h:.4f}")
    print(f"RUL (Days)   - MAE: {mae_r:.4f}, R2: {r2_r:.4f}")
    
    model_bundle = {
        "model_health": model_health,
        "model_rul": model_rul,
        "features": features,
        "trained_on_records": len(df),
        "trained_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    joblib.dump(model_bundle, model_path)
    print(f"Saved complete predictive maintenance model bundle to {model_path}.")

if __name__ == "__main__":
    train_maintenance_model()
