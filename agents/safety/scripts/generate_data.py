import os
import csv
import numpy as np
import time

def generate_safety_data(output_path, total_rows=1000000):
    print(f"Generating {total_rows:,} safety inspection records for Agent 07 - Worker Safety Agent...")
    start_time = time.time()
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    zones = ["DYE-FLOOR-A", "WEAVE-BAY-01", "CARDING-Z2", "FINISHING-LINE-03", "WAREHOUSE-BAY-B"]
    cameras = ["CAM-01", "CAM-02", "CAM-03", "CAM-04", "CAM-05"]
    violation_types = ["NONE", "MISSING_HELMET", "MISSING_GLOVES", "MISSING_EAR_PROTECTION", "HAZARD_ZONE_INTRUSION"]
    
    chunk_size = 100000
    headers = [
        "timestamp", "zone_id", "camera_id", "worker_count", 
        "helmet_present", "vest_present", "ear_protection_present", "gloves_present",
        "hazard_zone_intrusion", "confidence", "ambient_noise_db", "light_level_lux",
        "violation_type", "risk_score"
    ]
    
    np.random.seed(42)
    written = 0
    
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        
        while written < total_rows:
            current_chunk = min(chunk_size, total_rows - written)
            
            zone_indices = np.random.randint(0, len(zones), size=current_chunk)
            zone_arr = [zones[i] for i in zone_indices]
            camera_arr = [cameras[i] for i in zone_indices]
            
            worker_count = np.random.randint(1, 12, size=current_chunk)
            
            # Compliance probabilities
            helmet_present = np.random.choice([1, 0], size=current_chunk, p=[0.85, 0.15])
            vest_present = np.random.choice([1, 0], size=current_chunk, p=[0.90, 0.10])
            ear_protection_present = np.random.choice([1, 0], size=current_chunk, p=[0.80, 0.20])
            gloves_present = np.random.choice([1, 0], size=current_chunk, p=[0.82, 0.18])
            
            # Hazard zone intrusion (10% chance)
            hazard_intrusion = np.random.choice([1, 0], size=current_chunk, p=[0.10, 0.90])
            
            confidence = np.round(np.random.uniform(0.75, 0.99, size=current_chunk), 4)
            ambient_noise_db = np.round(np.random.uniform(55.0, 95.0, size=current_chunk), 1)
            light_level_lux = np.round(np.random.uniform(200.0, 850.0, size=current_chunk), 1)
            
            # Determine primary violation & calculate risk score (0.0 to 1.0)
            violation_arr = []
            risk_scores = []
            
            for i in range(current_chunk):
                r_score = 0.05  # baseline
                v_type = "NONE"
                
                if hazard_intrusion[i] == 1:
                    r_score += 0.45
                    v_type = "HAZARD_ZONE_INTRUSION"
                elif helmet_present[i] == 0:
                    r_score += 0.35
                    v_type = "MISSING_HELMET"
                elif gloves_present[i] == 0 and zone_arr[i] in ["DYE-FLOOR-A", "FINISHING-LINE-03"]:
                    r_score += 0.25
                    v_type = "MISSING_GLOVES"
                elif ear_protection_present[i] == 0 and ambient_noise_db[i] > 80.0:
                    r_score += 0.20
                    v_type = "MISSING_EAR_PROTECTION"
                
                if vest_present[i] == 0:
                    r_score += 0.10
                    
                r_score = min(1.0, r_score + np.random.normal(0, 0.02))
                risk_scores.append(round(max(0.0, r_score), 4))
                violation_arr.append(v_type)
            
            # Timestamps
            timestamps = [
                f"2026-07-28T{np.random.randint(0,24):02d}:{np.random.randint(0,60):02d}:{np.random.randint(0,60):02d}Z"
                for _ in range(current_chunk)
            ]
            
            rows = zip(
                timestamps, zone_arr, camera_arr, worker_count,
                helmet_present, vest_present, ear_protection_present, gloves_present,
                hazard_intrusion, confidence, ambient_noise_db, light_level_lux,
                violation_arr, risk_scores
            )
            
            writer.writerows(rows)
            written += current_chunk
            print(f"Generated {written:,}/{total_rows:,} records ({(written/total_rows)*100:.1f}%)...")
            
    elapsed = time.time() - start_time
    print(f"Safety dataset successfully generated at {output_path} in {elapsed:.2f} seconds.")

if __name__ == "__main__":
    out_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "safety_telemetry_10lakh.csv")
    generate_safety_data(out_file, total_rows=1000000)
