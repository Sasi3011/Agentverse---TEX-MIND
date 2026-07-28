import pandas as pd
import numpy as np
import os

def generate_data(num_samples=500):
    np.random.seed(42)
    
    # 1. Generate Suppliers
    suppliers = [f"SUP-{i:02d}" for i in range(1, 21)]
    supplier_base_defect_rate = {sup: np.random.uniform(0.01, 0.25) for sup in suppliers}
    
    # Ensure a few "bad" suppliers for testing
    supplier_base_defect_rate["SUP-04"] = 0.30
    supplier_base_defect_rate["SUP-15"] = 0.35
    
    supplier_df = pd.DataFrame([
        {"supplier_id": sup, "contact": f"contact_{sup}@example.com", "region": np.random.choice(["North", "South", "East", "West"])}
        for sup in suppliers
    ])
    
    # 2. Generate Batches
    data = []
    for i in range(num_samples):
        sup = np.random.choice(suppliers)
        
        # Base realistic values
        moisture = np.random.normal(6.5, 1.0)
        strength = np.random.normal(20.0, 1.5)
        count = int(np.random.choice([20, 30, 40, 50]))
        
        # Determine defect
        # Defect likely if moisture > 8.5, strength < 18, or just randomly based on supplier rate
        prob = supplier_base_defect_rate[sup]
        if moisture > 8.5:
            prob += 0.4
        if strength < 18.0:
            prob += 0.4
            
        prob = min(0.99, prob)
        resulted_in_defect = 1 if np.random.random() < prob else 0
        
        data.append({
            "batch_id": f"B-2026-{i+1:04d}",
            "supplier_id": sup,
            "moisture_pct": round(moisture, 2),
            "tensile_strength_g_tex": round(strength, 2),
            "fiber_count": count,
            "resulted_in_defect": resulted_in_defect
        })
        
    batches_df = pd.DataFrame(data)
    
    # Create data dir
    os.makedirs(os.path.join(os.path.dirname(__file__), '..', 'data'), exist_ok=True)
    
    supplier_df.to_csv(os.path.join(os.path.dirname(__file__), '..', 'data', 'suppliers.csv'), index=False)
    batches_df.to_csv(os.path.join(os.path.dirname(__file__), '..', 'data', 'historical_batches.csv'), index=False)
    print("Generated data/suppliers.csv and data/historical_batches.csv")

if __name__ == "__main__":
    generate_data(1000000)
