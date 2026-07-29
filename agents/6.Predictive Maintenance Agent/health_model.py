import os
import joblib
import pandas as pd
import numpy as np

class MaintenancePredictor:
    def __init__(self, model_path: str = None):
        if model_path is None:
            base_dir = os.path.dirname(__file__)
            model_path = os.path.join(base_dir, "models", "maintenance_model.pkl")
            
        self.model_path = model_path
        self.model_bundle = None
        self.load_model()

    def load_model(self):
        if os.path.exists(self.model_path):
            try:
                self.model_bundle = joblib.load(self.model_path)
                print(f"Successfully loaded maintenance model bundle from {self.model_path}")
            except Exception as e:
                print(f"Error loading model from {self.model_path}: {e}")
                self.model_bundle = None
        else:
            print(f"Model file not found at {self.model_path}. Will use analytical heuristic mode until trained.")
            self.model_bundle = None

    def predict(self, vibration_rms: float, vibration_kurtosis: float, temperature_c: float, operating_hours: float):
        if self.model_bundle:
            features_df = pd.DataFrame([{
                "vibration_rms": vibration_rms,
                "vibration_kurtosis": vibration_kurtosis,
                "temperature_c": temperature_c,
                "operating_hours": operating_hours
            }])
            
            health_score = float(self.model_bundle["model_health"].predict(features_df)[0])
            rul_days = float(self.model_bundle["model_rul"].predict(features_df)[0])
        else:
            # Fallback heuristic calculation if model file missing
            health_score = 1.0 - min(0.9, (vibration_rms / 2.0) * 0.5 + (temperature_c / 100.0) * 0.3 + (vibration_kurtosis / 15.0) * 0.2)
            rul_days = health_score * 30.0
            
        health_score = max(0.01, min(round(health_score, 4), 1.0))
        rul_days = max(0.5, round(rul_days, 1))
        
        # Determine priority and recommended action
        if health_score < 0.40 or rul_days <= 3.0:
            priority = "critical"
            action = "Immediate bearing inspection & bearing replacement scheduled within 24h"
        elif health_score < 0.70 or rul_days <= 7.0:
            priority = "warning"
            action = "Schedule alignment and lubrication check during next shift change"
        else:
            priority = "healthy"
            action = "Normal operation — routine monitoring active"
            
        return {
            "health_score": health_score,
            "estimated_remaining_useful_life_days": rul_days,
            "priority": priority,
            "recommended_action": action
        }
