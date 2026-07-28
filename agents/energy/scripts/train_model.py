import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
import pickle
import os

def train_and_save_models(data_path, models_dir):
    print(f"Loading data from {data_path}...")
    df = pd.read_csv(data_path)
    
    # We will train a separate Isolation Forest for each machine
    machines = df["machine_id"].unique()
    
    os.makedirs(models_dir, exist_ok=True)
    
    for machine in machines:
        print(f"Training model for {machine}...")
        machine_df = df[df["machine_id"] == machine]
        
        # We'll use the power consumption as the primary feature
        # (Could also include time of day if we wanted to be more advanced)
        X = machine_df[["power_kwh"]].values
        
        # Initialize Isolation Forest
        # contamination sets the expected proportion of outliers (we injected 1%)
        clf = IsolationForest(n_estimators=100, contamination=0.01, random_state=42)
        
        # Train model
        clf.fit(X)
        
        # Save model
        model_path = os.path.join(models_dir, f"{machine}_model.pkl")
        with open(model_path, 'wb') as f:
            pickle.dump(clf, f)
        
        print(f"Saved model for {machine} to {model_path}")
        
    print("All models trained and saved successfully.")

def main():
    base_dir = os.path.dirname(os.path.dirname(__file__))
    data_path = os.path.join(base_dir, "data", "historical_energy_data.csv")
    models_dir = os.path.join(base_dir, "models")
    
    if not os.path.exists(data_path):
        print(f"Error: Data file not found at {data_path}")
        print("Please run generate_data.py first.")
        return
        
    train_and_save_models(data_path, models_dir)

if __name__ == "__main__":
    main()
