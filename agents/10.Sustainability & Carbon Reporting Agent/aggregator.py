import os
import joblib
import pandas as pd
from typing import Dict, Any
from grading import compute_carbon_footprint, compute_deterministic_esg_grade, ESG_GRADE_MAP

MODEL_PATH = os.path.join(os.path.dirname(__file__), "weights", "esg_grading_rf.pkl")

class SustainabilityAggregator:
    def __init__(self):
        self.model = None
        if os.path.exists(MODEL_PATH):
            try:
                self.model = joblib.load(MODEL_PATH)
                print(f"Loaded trained 1M-record ESG Model from {MODEL_PATH}")
            except Exception as e:
                print(f"Warning loading ESG model: {e}")

    def generate_batch_report(
        self,
        batch_id: str,
        period: str = "2026-07",
        buyer_template: str = "H&M Export Standard",
        energy_used_kwh: float = 3820.0,
        water_compliance: str = "compliant",
        traceability_status: str = "verified_sustainable",
        traceability_score: float = 100.0
    ) -> Dict[str, Any]:
        
        # 1. Compute Deterministic Carbon Footprint
        estimated_co2e_kg = compute_carbon_footprint(energy_used_kwh)

        # 2. Compute Deterministic ESG Grade
        deterministic_grade = compute_deterministic_esg_grade(
            energy_kwh=energy_used_kwh,
            water_compliance=water_compliance,
            traceability_status=traceability_status,
            traceability_score=traceability_score
        )

        # 3. Model Benchmark Prediction (if loaded)
        model_predicted_grade = deterministic_grade
        if self.model is not None:
            w_code = 0 if "compliant" in water_compliance.lower() else (1 if "variance" in water_compliance.lower() else 2)
            feature_df = pd.DataFrame([{
                'energy_kwh': energy_used_kwh,
                'estimated_co2e_kg': estimated_co2e_kg,
                'water_compliance_code': w_code,
                'traceability_score': traceability_score
            }])
            pred_code = int(self.model.predict(feature_df)[0])
            model_predicted_grade = ESG_GRADE_MAP.get(pred_code, deterministic_grade)

        report_url = f"file:///c:/Users/Sasikiran/Documents/Agent/reports/{batch_id}_{period}.pdf"

        return {
            "batch_id": batch_id,
            "period": period,
            "buyer_template": buyer_template,
            "water_compliance": water_compliance,
            "energy_used_kwh": energy_used_kwh,
            "grid_emission_factor_kg_per_kwh": 0.82,
            "estimated_co2e_kg": estimated_co2e_kg,
            "traceability_status": traceability_status,
            "traceability_completeness_score": traceability_score,
            "overall_sustainability_grade": deterministic_grade,
            "model_benchmark_grade": model_predicted_grade,
            "report_url": report_url,
            "status": "report_ready"
        }
