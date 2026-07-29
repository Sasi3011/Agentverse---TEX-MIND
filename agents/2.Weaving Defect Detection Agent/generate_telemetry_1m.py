import pandas as pd
import numpy as np
import os
import time

def generate_telemetry_1m(output_path="data/defect_telemetry_1m.csv", num_records=1000000):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    print(f"Generating {num_records:,} fabric inspection telemetry records...")
    start_time = time.time()
    np.random.seed(42)

    looms = np.random.choice([f"LOOM-{i:02d}" for i in range(1, 13)], size=num_records)
    roll_positions = np.round(np.random.uniform(0.5, 250.0, size=num_records), 2)
    defect_counts = np.random.choice([0, 1, 2, 3, 4, 5], size=num_records, p=[0.75, 0.15, 0.05, 0.03, 0.015, 0.005])
    defect_types = np.random.choice(["defect free", "hole", "horizontal", "lines", "stain", "Vertical"], size=num_records, p=[0.75, 0.06, 0.05, 0.05, 0.05, 0.04])
    
    # Decisions: continue, flag, reject roll
    decisions = []
    for count in defect_counts:
        if count > 3:
            decisions.append("reject roll")
        elif count > 0:
            decisions.append("flag")
        else:
            decisions.append("continue")

    df = pd.DataFrame({
        'loom_id': looms,
        'roll_position_m': roll_positions,
        'defect_count': defect_counts,
        'primary_defect_type': defect_types,
        'decision': decisions
    })

    df.to_csv(output_path, index=False)
    print(f"Saved {num_records:,} inspection telemetry records to {output_path} in {time.time() - start_time:.2f}s")

if __name__ == "__main__":
    generate_telemetry_1m()
