import os
import csv
import numpy as np
import time

def generate_sensor_data(output_path, total_rows=1000000):
    print(f"Generating {total_rows:,} sensor records for Predictive Maintenance Agent...")
    start_time = time.time()
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    machines = ["LOOM-01", "LOOM-02", "SPIN-01", "SPIN-02", "CARD-01"]
    chunk_size = 100000
    
    headers = ["timestamp", "machine_id", "vibration_rms", "vibration_kurtosis", "temperature_c", "operating_hours", "health_score", "rul_days"]
    
    np.random.seed(42)
    
    written = 0
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        
        while written < total_rows:
            current_chunk = min(chunk_size, total_rows - written)
            
            machine_indices = np.random.randint(0, len(machines), size=current_chunk)
            machine_arr = [machines[i] for i in machine_indices]
            
            health_scores = np.random.uniform(0.1, 1.0, size=current_chunk)
            rul_days = np.clip(health_scores * 30.0 + np.random.normal(0, 1.5, size=current_chunk), 0.5, 30.0)
            
            vibration_rms = 0.20 + (1.0 - health_scores) * 1.20 + np.random.normal(0, 0.05, size=current_chunk)
            vibration_rms = np.clip(vibration_rms, 0.10, 2.50)
            
            vibration_kurtosis = 3.0 + (1.0 - health_scores) * 6.5 + np.random.normal(0, 0.4, size=current_chunk)
            vibration_kurtosis = np.clip(vibration_kurtosis, 2.5, 15.0)
            
            temperature_c = 48.0 + (1.0 - health_scores) * 35.0 + np.random.normal(0, 1.5, size=current_chunk)
            temperature_c = np.clip(temperature_c, 35.0, 105.0)
            
            operating_hours = np.random.uniform(100.0, 8500.0, size=current_chunk)
            
            timestamps = [f"2026-07-28T{np.random.randint(0,24):02d}:{np.random.randint(0,60):02d}:{np.random.randint(0,60):02d}Z" for _ in range(current_chunk)]
            
            rows = zip(timestamps, machine_arr, 
                        np.round(vibration_rms, 4), 
                        np.round(vibration_kurtosis, 4), 
                        np.round(temperature_c, 2), 
                        np.round(operating_hours, 1), 
                        np.round(health_scores, 4), 
                        np.round(rul_days, 1))
            
            writer.writerows(rows)
            written += current_chunk
            print(f"Generated {written:,}/{total_rows:,} records ({(written/total_rows)*100:.1f}%)...")
            
    elapsed = time.time() - start_time
    print(f"Dataset generated successfully at {output_path} in {elapsed:.2f} seconds.")

if __name__ == "__main__":
    out_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "sensor_data_10lakh.csv")
    generate_sensor_data(out_file, total_rows=1000000)
