import os
import time
import pandas as pd
import numpy as np
import joblib
from sklearn.model_selection import train_test_split
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.metrics import classification_report, mean_squared_error, r2_score

def train_safety_models(data_path, models_dir):
    print(f"Loading 10-Lakh safety telemetry dataset from {data_path}...")
    start_time = time.time()
    
    os.makedirs(models_dir, exist_ok=True)
    
    # Load dataset
    df = pd.read_csv(data_path)
    print(f"Loaded {len(df):,} rows in {time.time() - start_time:.2f}s.")
    
    # Feature engineering
    zone_mapping = {zone: idx for idx, zone in enumerate(df["zone_id"].unique())}
    df["zone_code"] = df["zone_id"].map(zone_mapping)
    
    feature_cols = [
        "zone_code", "worker_count", "helmet_present", "vest_present", 
        "ear_protection_present", "gloves_present", "hazard_zone_intrusion", 
        "confidence", "ambient_noise_db", "light_level_lux"
    ]
    
    X = df[feature_cols]
    y_violation = df["violation_type"]
    y_risk = df["risk_score"]
    
    # Train test split on sample or full dataset
    X_train, X_test, y_v_train, y_v_test, y_r_train, y_r_test = train_test_split(
        X, y_violation, y_risk, test_size=0.1, random_state=42
    )
    
    print(f"Training HistGradientBoostingClassifier on {len(X_train):,} samples...")
    t0 = time.time()
    classifier = HistGradientBoostingClassifier(max_iter=100, random_state=42)
    classifier.fit(X_train, y_v_train)
    print(f"Classifier trained in {time.time() - t0:.2f}s.")
    
    print(f"Training HistGradientBoostingRegressor for Risk Scoring...")
    t1 = time.time()
    regressor = HistGradientBoostingRegressor(max_iter=100, random_state=42)
    regressor.fit(X_train, y_r_train)
    print(f"Regressor trained in {time.time() - t1:.2f}s.")
    
    # Evaluation
    v_preds = classifier.predict(X_test)
    r_preds = regressor.predict(X_test)
    
    acc = np.mean(v_preds == y_v_test)
    rmse = np.sqrt(mean_squared_error(y_r_test, r_preds))
    r2 = r2_score(y_r_test, r_preds)
    
    print(f"\n--- MODEL PERFORMANCE ---")
    print(f"Violation Classifier Accuracy: {acc * 100:.2f}%")
    print(f"Risk Score Regressor RMSE: {rmse:.4f}")
    print(f"Risk Score Regressor R2: {r2:.4f}")
    
    model_bundle = {
        "classifier": classifier,
        "regressor": regressor,
        "zone_mapping": zone_mapping,
        "feature_cols": feature_cols,
        "trained_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "training_samples": len(X_train)
    }
    
    bundle_path = os.path.join(models_dir, "safety_risk_model.joblib")
    joblib.dump(model_bundle, bundle_path)
    print(f"Saved model bundle to {bundle_path}.")
    print(f"Total training pipeline completed in {time.time() - start_time:.2f}s.")

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(__file__))
    data_file = os.path.join(base_dir, "data", "safety_telemetry_10lakh.csv")
    models_dir = os.path.join(base_dir, "models")
    train_safety_models(data_file, models_dir)
