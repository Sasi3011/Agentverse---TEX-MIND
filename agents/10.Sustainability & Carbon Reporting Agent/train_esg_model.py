import pandas as pd
import numpy as np
import joblib
import os
import time
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, accuracy_score

def train_esg_grading_model(data_path="data/esg_reports_1m.csv", model_dir="weights"):
    os.makedirs(model_dir, exist_ok=True)
    print("Loading 1,000,000 ESG records...")
    start_time = time.time()
    
    df = pd.read_csv(data_path)
    X = df[['energy_kwh', 'estimated_co2e_kg', 'water_compliance_code', 'traceability_score']]
    y = df['esg_grade_code']

    print("Splitting dataset (Train 800,000 / Test 200,000)...")
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    print("Training Random Forest ESG Grader Model...")
    model = RandomForestClassifier(n_estimators=40, max_depth=14, n_jobs=-1, random_state=42)
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    print(f"ESG Model Classification Accuracy: {acc * 100:.2f}%")

    model_file = os.path.join(model_dir, "esg_grading_rf.pkl")
    joblib.dump(model, model_file)
    print(f"Saved trained ESG model to {model_file} in {time.time() - start_time:.2f}s")

if __name__ == "__main__":
    train_esg_grading_model()
