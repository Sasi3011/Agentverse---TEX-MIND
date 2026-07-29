import pandas as pd
import numpy as np
import joblib
import os
import time
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, roc_auc_score

def train_tn_traceability_model(data_path="data/traceability_tn_1m.csv", model_dir="weights"):
    os.makedirs(model_dir, exist_ok=True)
    print("Loading 1,000,000 Tamil Nadu supply chain records...")
    start_time = time.time()
    
    df = pd.read_csv(data_path)
    X = df[['stage', 'distance_km', 'transit_hours', 'calculated_speed_kmh', 'mass_ratio', 'cert_status', 'timestamp_order_valid']]
    y = df['is_anomaly']

    print(f"Splitting Tamil Nadu dataset (Train 800,000 / Test 200,000)...")
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    print("Training Random Forest Classifier on 800,000 Tamil Nadu records...")
    model = RandomForestClassifier(
        n_estimators=50,
        max_depth=16,
        n_jobs=-1,
        random_state=42
    )
    model.fit(X_train, y_train)

    print("Evaluating model performance on 200,000 test set records...")
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]
    
    auc = roc_auc_score(y_test, y_proba)
    print(f"Tamil Nadu Model ROC-AUC Score: {auc:.4f}")
    print("\nClassification Report:\n", classification_report(y_test, y_pred))

    model_file = os.path.join(model_dir, "traceability_anomaly_rf.pkl")
    joblib.dump(model, model_file)
    print(f"Successfully retrained & saved Tamil Nadu model to {model_file} in {time.time() - start_time:.2f}s")

if __name__ == "__main__":
    train_tn_traceability_model()
