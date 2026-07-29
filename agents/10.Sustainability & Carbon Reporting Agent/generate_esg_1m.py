import numpy as np
import pandas as pd
import os
import time

def generate_esg_1m_dataset(output_path="data/esg_reports_1m.csv", num_records=1000000):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    print(f"Generating {num_records:,} ESG sustainability audit records...")
    
    start_time = time.time()
    np.random.seed(42)

    # Energy used in kWh (1000 kWh to 8000 kWh per batch)
    energy_kwh = np.random.uniform(1200, 7500, size=num_records)
    
    # Grid emission factor: default 0.82 kg CO2e / kWh
    grid_factor = 0.82
    estimated_co2e_kg = energy_kwh * grid_factor
    
    # Water compliance: 0=Compliant, 1=Minor Variance, 2=Non-Compliant
    water_compliance_code = np.random.choice([0, 1, 2], size=num_records, p=[0.85, 0.10, 0.05])
    
    # Traceability score (60% to 100%)
    traceability_score = np.random.choice([100, 80, 60], size=num_records, p=[0.82, 0.12, 0.06])
    
    # Determine ESG Grade: 0=A+, 1=A, 2=B+, 3=B, 4=C, 5=F
    esg_grades = []
    for i in range(num_records):
        w_code = water_compliance_code[i]
        t_score = traceability_score[i]
        co2 = estimated_co2e_kg[i]
        
        if w_code == 2 or t_score < 80:
            esg_grades.append(4) # C or F
        elif w_code == 1 or co2 > 5000:
            esg_grades.append(2) # B+
        elif co2 < 3000 and t_score == 100 and w_code == 0:
            esg_grades.append(0) # A+
        else:
            esg_grades.append(1) # A

    df = pd.DataFrame({
        'energy_kwh': np.round(energy_kwh, 2),
        'estimated_co2e_kg': np.round(estimated_co2e_kg, 2),
        'water_compliance_code': water_compliance_code,
        'traceability_score': traceability_score,
        'esg_grade_code': esg_grades
    })

    df.to_csv(output_path, index=False)
    elapsed = time.time() - start_time
    print(f"Saved 1,000,000 ESG records to {output_path} in {elapsed:.2f}s")

if __name__ == "__main__":
    generate_esg_1m_dataset()
