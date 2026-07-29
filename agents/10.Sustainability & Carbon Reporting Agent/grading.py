import os
import joblib
import pandas as pd

GRID_EMISSION_FACTOR_KG_PER_KWH = 0.82

ESG_GRADE_MAP = {
    0: "A+",
    1: "A",
    2: "B+",
    3: "B",
    4: "C",
    5: "F"
}

MODEL_PATH = os.path.join(os.path.dirname(__file__), "weights", "esg_grading_rf.pkl")
_esg_model = None

if os.path.exists(MODEL_PATH):
    try:
        _esg_model = joblib.load(MODEL_PATH)
    except Exception as e:
        print(f"Failed loading ML ESG model: {e}")

def compute_carbon_footprint(energy_used_kwh: float) -> float:
    """Calculates CO2e footprint in kg based on grid emission factor."""
    return round(energy_used_kwh * GRID_EMISSION_FACTOR_KG_PER_KWH, 2)

def compute_deterministic_esg_grade(
    energy_kwh: float, 
    water_compliance: str, 
    traceability_status: str, 
    traceability_score: float
) -> str:
    """
    ML Random Forest + Rule-aware ESG Grade Classifier.
    """
    co2e_kg = compute_carbon_footprint(energy_kwh)
    w_code = 0 if ("non" in water_compliance.lower() or "fail" in water_compliance.lower()) else 1
    
    if _esg_model is not None:
        try:
            feat = pd.DataFrame([{
                'energy_kwh': energy_kwh,
                'estimated_co2e_kg': co2e_kg,
                'water_compliance_code': w_code,
                'traceability_score': traceability_score
            }])
            pred_code = int(_esg_model.predict(feat)[0])
            return ESG_GRADE_MAP.get(pred_code, "A")
        except Exception:
            pass

    # Fallback rule logic if model is not loaded
    if w_code == 0 or traceability_score < 80:
        return "C"
    elif energy_kwh > 5000:
        return "B+"
    elif energy_kwh < 3000 and traceability_score == 100:
        return "A+"
    else:
        return "A"
