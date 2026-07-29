import os
import pandas as pd
import numpy as np
import joblib
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.preprocessing import LabelEncoder

# Hard rules based on user choice for default set
MOISTURE_MAX = 8.5
STRENGTH_MIN = 18.0

MODEL_PATH = os.path.join(os.path.dirname(__file__), "model_artifacts", "intake_model_latest.pkl")
ENCODER_PATH = os.path.join(os.path.dirname(__file__), "model_artifacts", "supplier_encoder_latest.pkl")
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

def train_model():
    """Trains the ML model using historical data."""
    historical_file = os.path.join(DATA_DIR, "historical_batches.csv")
    if not os.path.exists(historical_file):
        print("No historical data found. Skipping training.")
        return False
        
    df = pd.read_csv(historical_file)
    if len(df) < 200:
        print(f"Not enough data to train. Found {len(df)} rows, require 200.")
        return False

    # Encode supplier
    le = LabelEncoder()
    df['supplier_encoded'] = le.fit_transform(df['supplier_id'])
    
    X = df[['moisture_pct', 'tensile_strength_g_tex', 'fiber_count', 'supplier_encoded']]
    y = df['resulted_in_defect']
    
    # Train model
    clf = HistGradientBoostingClassifier(random_state=42)
    clf.fit(X, y)
    
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    joblib.dump(clf, MODEL_PATH)
    joblib.dump(le, ENCODER_PATH)
    
    print("Model trained and saved successfully.")
    return True

def get_supplier_defect_rate(supplier_id: str) -> float:
    historical_file = os.path.join(DATA_DIR, "historical_batches.csv")
    if not os.path.exists(historical_file):
        return 0.0
    
    df = pd.read_csv(historical_file)
    sup_df = df[df['supplier_id'] == supplier_id]
    if len(sup_df) < 10:
        return 0.0
    
    return sup_df['resulted_in_defect'].mean()

def evaluate_batch(batch_id: str, supplier_id: str, fiber_count: int, strength: float, moisture: float):
    flags = []
    
    # 1. Rule gates
    if moisture > MOISTURE_MAX:
        flags.append(f"Moisture {moisture}% exceeds max {MOISTURE_MAX}%")
    if strength < STRENGTH_MIN:
        flags.append(f"Strength {strength} below min {STRENGTH_MIN}")
        
    if flags:
        return {
            "batch_id": batch_id,
            "decision": "flag",
            "quality_score": 0.0,
            "flags": flags,
            "confidence": 1.0
        }
        
    # 2. Check supplier history
    defect_rate = get_supplier_defect_rate(supplier_id)
    if defect_rate > 0.20:
        flags.append(f"Supplier has high historical defect rate: {defect_rate:.0%}")
        
    # 3. Model Inference
    if os.path.exists(MODEL_PATH) and os.path.exists(ENCODER_PATH):
        clf = joblib.load(MODEL_PATH)
        le = joblib.load(ENCODER_PATH)
        
        try:
            # Handle unseen suppliers gracefully
            if supplier_id in le.classes_:
                sup_encoded = le.transform([supplier_id])[0]
            else:
                sup_encoded = -1
                
            X = pd.DataFrame([{
                'moisture_pct': moisture,
                'tensile_strength_g_tex': strength,
                'fiber_count': fiber_count,
                'supplier_encoded': sup_encoded
            }])
            
            defect_prob = clf.predict_proba(X)[0][1]
            quality_score = max(0.0, round((1.0 - defect_prob) * 100, 1))
            confidence = 0.90
            if flags:
                confidence -= 0.15 # Downgrade confidence if supplier flag exists
            
            decision = "pass" if quality_score > 70.0 else "flag"
            
            return {
                "batch_id": batch_id,
                "decision": decision,
                "quality_score": quality_score,
                "flags": flags,
                "confidence": max(0.0, min(1.0, confidence))
            }
        except Exception as e:
            print(f"Model inference failed: {e}")
            # Fallback to rule engine on error
            pass
            
    # Fallback if no model
    score = 80.0
    if flags:
        score = 60.0
    
    decision = "pass" if not flags else "flag"
    return {
        "batch_id": batch_id,
        "decision": decision,
        "quality_score": score,
        "flags": flags,
        "confidence": 0.70
    }

if __name__ == "__main__":
    train_model()
