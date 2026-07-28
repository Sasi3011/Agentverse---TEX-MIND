import numpy as np
import pandas as pd
import os
import time

# Tamil Nadu Textile Hub Facilities (Coimbatore, Tiruppur, Erode, Karur, Dindigul, Rajapalayam)
TN_FACILITIES = {
    "farm": [
        {"name": "Kongu Organic Cotton Farmers Co-op (Coimbatore)", "cert": "GOTS-TN-101"},
        {"name": "Pollachi Sustainable Farms (Pollachi)", "cert": "GOTS-TN-102"},
        {"name": "Amaravathi Organic Cotton Collective (Udumalpet)", "cert": "GOTS-TN-103"},
        {"name": "Cauvery Delta Organic Planters (Erode)", "cert": "GOTS-REVOKED-99"}
    ],
    "ginning": [
        {"name": "Tiruppur Cotton Ginning Mills (Tiruppur)", "cert": "GOTS-TN-201"},
        {"name": "Coimbatore Modern Ginning Works (Coimbatore)", "cert": "GOTS-TN-202"},
        {"name": "Kovai Ginning & Pressing Ltd (Coimbatore)", "cert": "GOTS-TN-203"}
    ],
    "spinning": [
        {"name": "Lakshmi Mills Co-op Ltd (Coimbatore)", "cert": "OEKO-TN-301"},
        {"name": "KPR Mill Spinning Division (Tiruppur)", "cert": "OEKO-TN-302"},
        {"name": "Bannari Amman Spinning Mills (Erode)", "cert": "OEKO-TN-303"}
    ],
    "weaving": [
        {"name": "Tiruppur Knitwear & Weaving Park (Tiruppur)", "cert": "OEKO-TN-401"},
        {"name": "Karur Home Textiles Weaving Co (Karur)", "cert": "OEKO-TN-402"},
        {"name": "Rajapalayam Weaving Mills (Rajapalayam)", "cert": "OEKO-TN-403"}
    ],
    "dyeing": [
        {"name": "Zero Liquid Discharge Dyeing Park (Tiruppur)", "cert": "GOTS-TN-501"},
        {"name": "Cauvery Processing & Dyeing Unit (Erode)", "cert": "GOTS-TN-502"},
        {"name": "Kovai Sustainable Dyers (Coimbatore)", "cert": "GOTS-EXPIRED-01"}
    ]
}

def generate_tn_10lakh_dataset(output_path="data/traceability_tn_1m.csv", num_records=1000000):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    print(f"Generating {num_records:,} Tamil Nadu (Coimbatore & Tiruppur) supply chain records...")
    
    start_time = time.time()
    np.random.seed(42)

    stages = np.random.choice([0, 1, 2, 3], size=num_records)
    
    # Realistic distances between Coimbatore, Tiruppur, Erode, Karur (15km to 150km)
    distance_km = np.random.uniform(15, 180, size=num_records)
    
    # Expected speed ~ 30-50 km/h on TN state highways + loading delays
    normal_transit_hours = (distance_km / np.random.uniform(30, 50, size=num_records)) + np.random.uniform(1, 8, size=num_records)
    
    # Introduce speed anomalies (teleportation fraud: 150km covered in 0.1 hrs)
    speed_anomaly_mask = np.random.rand(num_records) < 0.03
    transit_hours = normal_transit_hours.copy()
    transit_hours[speed_anomaly_mask] = np.random.uniform(0.05, 0.5, size=np.sum(speed_anomaly_mask))
    
    # Mass balance ratio (Ginning/Spinning/Dyeing yield). Normal: 82% to 96%
    mass_ratio = np.random.uniform(0.82, 0.96, size=num_records)
    mass_anomaly_mask = np.random.rand(num_records) < 0.03
    mass_ratio[mass_anomaly_mask] = np.random.choice([0.3, 0.4, 1.15, 1.35], size=np.sum(mass_anomaly_mask))
    
    # Certificate status: 0=Valid GOTS/OEKO, 1=Expired, 2=Revoked, 3=Mismatched Facility
    cert_status = np.random.choice([0, 1, 2, 3], size=num_records, p=[0.88, 0.05, 0.03, 0.04])
    
    timestamp_order_valid = np.random.choice([1, 0], size=num_records, p=[0.96, 0.04])
    
    is_anomaly = (
        speed_anomaly_mask | 
        mass_anomaly_mask | 
        (cert_status > 0) | 
        (timestamp_order_valid == 0)
    ).astype(int)

    df = pd.DataFrame({
        'stage': stages,
        'distance_km': np.round(distance_km, 2),
        'transit_hours': np.round(transit_hours, 2),
        'calculated_speed_kmh': np.round(distance_km / np.maximum(transit_hours, 0.01), 2),
        'mass_ratio': np.round(mass_ratio, 4),
        'cert_status': cert_status,
        'timestamp_order_valid': timestamp_order_valid,
        'is_anomaly': is_anomaly
    })

    df.to_csv(output_path, index=False)
    elapsed = time.time() - start_time
    print(f"Saved {num_records:,} Tamil Nadu supply chain records to {output_path} in {elapsed:.2f}s")
    print(f"Anomaly Ratio: {df['is_anomaly'].mean() * 100:.2f}%")

if __name__ == "__main__":
    generate_tn_10lakh_dataset()
