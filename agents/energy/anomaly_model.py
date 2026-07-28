import pickle
import os
import numpy as np

class AnomalyModel:
    def __init__(self):
        self.models = {}
        self.models_dir = os.path.join(os.path.dirname(__file__), "models")
        self._load_models()

    def _load_models(self):
        if not os.path.exists(self.models_dir):
            print(f"Warning: Models directory {self.models_dir} not found.")
            return
            
        for filename in os.listdir(self.models_dir):
            if filename.endswith("_model.pkl"):
                machine_id = filename.replace("_model.pkl", "")
                filepath = os.path.join(self.models_dir, filename)
                try:
                    with open(filepath, "rb") as f:
                        self.models[machine_id] = pickle.load(f)
                    print(f"Loaded model for {machine_id}")
                except Exception as e:
                    print(f"Error loading model for {machine_id}: {e}")

    def predict(self, machine_id: str, power_kwh: float) -> bool:
        """
        Returns True if anomaly, False otherwise.
        """
        if machine_id not in self.models:
            # Fallback if no model exists for this machine
            return False
            
        model = self.models[machine_id]
        # Isolation forest expects 2D array
        X = np.array([[power_kwh]])
        
        # predict returns 1 for inliers, -1 for outliers
        prediction = model.predict(X)[0]
        
        return prediction == -1
