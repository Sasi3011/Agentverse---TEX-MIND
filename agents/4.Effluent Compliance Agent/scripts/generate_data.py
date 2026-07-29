import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os

def generate_etp_data(num_records=1_000_000, output_path="data/effluent_data_1M.csv"):
    print(f"Generating {num_records} ETP sensor records...")
    
    # Base timestamp
    start_time = datetime(2025, 1, 1, 0, 0)
    timestamps = [start_time + timedelta(minutes=5 * i) for i in range(num_records)]
    
    # Normal operating ranges (safe)
    # pH: 6.5 to 8.5
    # TDS: < 2100
    # Color: < 400
    # BOD: < 30
    
    # Generate base signals with random walks and daily seasonality
    t = np.arange(num_records)
    daily_cycle = np.sin(2 * np.pi * t / (24 * 60 / 5)) # Daily cycle
    
    ph = 7.5 + 0.3 * daily_cycle + np.random.normal(0, 0.1, num_records)
    tds = 1500 + 200 * daily_cycle + np.random.normal(0, 50, num_records)
    color = 250 + 50 * daily_cycle + np.random.normal(0, 20, num_records)
    bod = 15 + 5 * daily_cycle + np.random.normal(0, 2, num_records)
    
    # Inject anomalies (drifts and spikes)
    num_anomalies = int(num_records * 0.05) # 5% anomalies
    anomaly_indices = np.random.choice(num_records, num_anomalies, replace=False)
    
    for idx in anomaly_indices:
        anomaly_type = np.random.choice(['ph_spike', 'tds_drift', 'color_bod_spike'])
        
        # We will make anomalies last for a few readings (e.g., 3 to 10 readings)
        duration = np.random.randint(3, 11)
        end_idx = min(idx + duration, num_records)
        
        if anomaly_type == 'ph_spike':
            ph[idx:end_idx] += np.random.uniform(1.0, 2.5) # pushes ph > 8.5 or < 6.5
            # randomly flip sign for acidic or basic spike
            if np.random.rand() > 0.5:
                ph[idx:end_idx] -= 3.0
                
        elif anomaly_type == 'tds_drift':
            # Drift gradually over the duration
            drift = np.linspace(300, 800, end_idx - idx)
            tds[idx:end_idx] += drift
            
        elif anomaly_type == 'color_bod_spike':
            color[idx:end_idx] += np.random.uniform(100, 250)
            bod[idx:end_idx] += np.random.uniform(10, 25)
            
    # Clip to physical limits
    ph = np.clip(ph, 0, 14)
    tds = np.clip(tds, 0, 5000)
    color = np.clip(color, 0, 1000)
    bod = np.clip(bod, 0, 200)
    
    df = pd.DataFrame({
        "timestamp": timestamps,
        "ph": ph,
        "tds_mgL": tds,
        "color_units": color,
        "bod_mgL": bod
    })
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"Dataset generated and saved to {output_path}")

if __name__ == "__main__":
    generate_etp_data()
