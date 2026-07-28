import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os

# Number of rows to generate: 1,000,000
# Assuming data is recorded every 5 minutes
NUM_ROWS_PER_MACHINE = 250000 
MACHINES = ["BOILER-01", "COMPRESSOR-01", "COMPRESSOR-02", "MOTOR-01"]

def generate_machine_data(machine_id, base_kwh, noise_std, start_date, num_rows, anomaly_fraction=0.01):
    timestamps = [start_date + timedelta(minutes=5*i) for i in range(num_rows)]
    
    # Base power consumption with daily seasonality (sin wave) and random noise
    # Sin wave represents higher usage during day shift, lower at night
    time_factors = np.array([np.sin(2 * np.pi * (t.hour * 60 + t.minute) / (24 * 60)) for t in timestamps])
    
    # Adjust base based on time factor (day vs night)
    base_consumption = base_kwh + (time_factors * (base_kwh * 0.2)) # +/- 20% swing
    
    # Add noise
    power_readings = base_consumption + np.random.normal(0, noise_std, num_rows)
    
    # Ensure no negative power
    power_readings = np.clip(power_readings, 0, None)
    
    # Inject anomalies (higher consumption)
    num_anomalies = int(num_rows * anomaly_fraction)
    anomaly_indices = np.random.choice(num_rows, num_anomalies, replace=False)
    
    # Anomalies represent a 30% to 100% spike in power
    power_readings[anomaly_indices] += np.random.uniform(0.3, 1.0, num_anomalies) * base_kwh
    
    # Generate DataFrame
    df = pd.DataFrame({
        "machine_id": machine_id,
        "timestamp": timestamps,
        "power_kwh": power_readings
    })
    
    return df

def main():
    print("Generating 1,000,000 rows of energy consumption data...")
    start_date = datetime(2025, 1, 1)
    
    # Define baseline behaviors for each machine
    machine_configs = [
        {"machine_id": "BOILER-01", "base_kwh": 120.0, "noise_std": 5.0},
        {"machine_id": "COMPRESSOR-01", "base_kwh": 45.0, "noise_std": 2.0},
        {"machine_id": "COMPRESSOR-02", "base_kwh": 50.0, "noise_std": 2.5},
        {"machine_id": "MOTOR-01", "base_kwh": 80.0, "noise_std": 3.0}
    ]
    
    all_data = []
    for config in machine_configs:
        print(f"Generating data for {config['machine_id']}...")
        df = generate_machine_data(
            machine_id=config["machine_id"],
            base_kwh=config["base_kwh"],
            noise_std=config["noise_std"],
            start_date=start_date,
            num_rows=NUM_ROWS_PER_MACHINE
        )
        all_data.append(df)
        
    final_df = pd.concat(all_data, ignore_index=True)
    
    # Sort by timestamp to simulate real data stream
    print("Sorting data by timestamp...")
    final_df.sort_values(by="timestamp", inplace=True)
    
    # Round power readings to 2 decimal places
    final_df["power_kwh"] = final_df["power_kwh"].round(2)
    
    # Save to CSV
    output_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "historical_energy_data.csv")
    
    print(f"Saving to {output_path}...")
    final_df.to_csv(output_path, index=False)
    print(f"Successfully generated {len(final_df)} rows of data.")

if __name__ == "__main__":
    main()
