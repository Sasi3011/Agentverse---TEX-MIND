import os
import time
import numpy as np
import pandas as pd

def generate_dyeing_dataset(num_samples=1000000):
    """
    Generates 1,000,000 (10 Lakh) highly realistic historical dyeing recipe records
    covering edge cases, diverse shade depths, chemical dynamics, and thermal kinetics.
    """
    print(f"Starting generation of {num_samples:,} (10 Lakh) edge-case robust dyeing records...")
    start_time = time.time()
    np.random.seed(42)

    # 1. Fabrics (10 fabric types for broader coverage)
    fabrics = [
        "cotton_poplin", "polyester_blend", "silk_satin", "wool_blend", "denim_twill",
        "viscose_rayon", "nylon_taffeta", "linen_weave", "acrylic_fleece", "elastane_cotton_blend"
    ]

    # 2. Diverse Shade Spectrum (30 distinct shade codes across dark, medium, light, pastel, neon, deep)
    shades = [
        "NAVY-204", "RUBY-501", "EMERALD-302", "SKY-105", "CHARCOAL-808",
        "KHAKI-404", "CRIMSON-707", "ROYAL-909", "OLIVE-606", "SUNSET-101",
        "PASTEL-PINK-01", "PASTEL-MINT-02", "NEON-YELLOW-99", "DEEP-BLACK-00", "BOTTLE-GREEN-30",
        "MUSTARD-YELLOW-12", "PLUM-PURPLE-88", "TERRACOTTA-55", "IVORY-WHITE-05", "BURGUNDY-77",
        "OCEAN-BLUE-44", "CORAL-ORANGE-33", "TEAL-22", "LAVENDER-11", "TAUPE-66",
        "SLATE-GREY-90", "MAGENTA-80", "CHOCOLATE-BROWN-70", "TURQUOISE-40", "MAROON-85"
    ]

    liquor_ratios = ["1:5", "1:6", "1:8", "1:10", "1:12", "1:15"]

    # Sample random index selections
    fabric_idx = np.random.choice(len(fabrics), size=num_samples)
    shade_idx = np.random.choice(len(shades), size=num_samples)
    liquor_idx = np.random.choice(len(liquor_ratios), size=num_samples)

    fabric_arr = np.array(fabrics)[fabric_idx]
    shade_arr = np.array(shades)[shade_idx]
    liquor_arr = np.array(liquor_ratios)[liquor_idx]

    # Shade Base Depth Map (dye % required based on shade intensity)
    shade_depth_map = {
        "PASTEL-PINK-01": 0.35, "PASTEL-MINT-02": 0.40, "IVORY-WHITE-05": 0.15, "SKY-105": 0.65,
        "KHAKI-404": 1.20, "SUNSET-101": 1.50, "MUSTARD-YELLOW-12": 1.80, "TERRACOTTA-55": 2.10,
        "CORAL-ORANGE-33": 2.20, "TEAL-22": 2.30, "TURQUOISE-40": 2.40, "EMERALD-302": 2.50,
        "RUBY-501": 2.80, "CRIMSON-707": 3.00, "NAVY-204": 3.20, "ROYAL-909": 3.50,
        "BURGUNDY-77": 3.60, "PLUM-PURPLE-88": 3.70, "MAGENTA-80": 3.80, "CHARCOAL-808": 4.00,
        "DEEP-BLACK-00": 4.50, "CHOCOLATE-BROWN-70": 3.90, "MAROON-85": 3.40, "SLATE-GREY-90": 2.90,
        "OCEAN-BLUE-44": 3.10, "BOTTLE-GREEN-30": 3.30, "NEON-YELLOW-99": 2.00, "LAVENDER-11": 0.90,
        "TAUPE-66": 1.40, "OLIVE-606": 2.20
    }
    ideal_dye_pct = np.array([shade_depth_map.get(s, 2.0) for s in shade_arr])

    # Sample actual recipe values
    dye_pct = np.round(np.random.normal(ideal_dye_pct, ideal_dye_pct * 0.15), 3)
    dye_pct = np.clip(dye_pct, 0.05, 6.5)

    # Ideal Temperatures per fabric type
    ideal_temp_map = {
        "cotton_poplin": 90.0, "polyester_blend": 130.0, "silk_satin": 85.0,
        "wool_blend": 95.0, "denim_twill": 80.0, "viscose_rayon": 85.0,
        "nylon_taffeta": 98.0, "linen_weave": 92.0, "acrylic_fleece": 102.0,
        "elastane_cotton_blend": 80.0
    }
    ideal_temps = np.array([ideal_temp_map[f] for f in fabric_arr])
    temperature_c = np.round(np.random.normal(ideal_temps, 6.0), 1)
    temperature_c = np.clip(temperature_c, 50.0, 140.0)

    # Ideal Hold Time (min)
    ideal_time_map = {
        "cotton_poplin": 45, "polyester_blend": 60, "silk_satin": 40,
        "wool_blend": 55, "denim_twill": 50, "viscose_rayon": 45,
        "nylon_taffeta": 50, "linen_weave": 60, "acrylic_fleece": 65,
        "elastane_cotton_blend": 40
    }
    ideal_times = np.array([ideal_time_map[f] for f in fabric_arr])
    time_min = np.round(np.random.normal(ideal_times, 9.0)).astype(int)
    time_min = np.clip(time_min, 15, 120)

    # Electrolyte (Salt g/L) & Buffer (g/L)
    # Salt requirement scales with dye depth
    ideal_salt = np.clip(ideal_dye_pct * 8.0 + 5.0, 10.0, 65.0)
    salt_g_l = np.round(np.random.normal(ideal_salt, 5.0), 1)
    salt_g_l = np.clip(salt_g_l, 2.0, 80.0)

    acid_buffer_g_l = np.round(np.random.uniform(0.3, 3.5, size=num_samples), 2)
    fabric_weight_kg = np.round(np.random.uniform(10.0, 800.0, size=num_samples), 1)

    # Realistic Physics Equation for Color Difference (Delta E)
    temp_diff = np.abs(temperature_c - ideal_temps) / ideal_temps
    time_diff = np.abs(time_min - ideal_times) / ideal_times
    dye_diff = np.abs(dye_pct - ideal_dye_pct) / ideal_dye_pct
    salt_diff = np.abs(salt_g_l - ideal_salt) / ideal_salt

    # Polyester thermal threshold penalty (under 120C polyester won't absorb disperse dye)
    poly_penalty = np.where((fabric_arr == "polyester_blend") & (temperature_c < 120.0), 2.5, 0.0)
    # Silk/Wool overheat penalty (over 100C damages protein fibers)
    protein_penalty = np.where(((fabric_arr == "silk_satin") | (fabric_arr == "wool_blend")) & (temperature_c > 98.0), 1.8, 0.0)

    delta_e = 0.25 + (dye_diff * 1.6) + (temp_diff * 2.8) + (time_diff * 1.4) + (salt_diff * 0.9) + poly_penalty + protein_penalty + np.random.exponential(scale=0.25, size=num_samples)
    delta_e = np.round(delta_e, 2)

    # Match outcome: delta_e <= 1.2 is a match
    outcome_match = (delta_e <= 1.2).astype(int)

    batch_ids = [f"B-2026-{i+1:07d}" for i in range(num_samples)]

    df = pd.DataFrame({
        "batch_id": batch_ids,
        "target_shade_code": shade_arr,
        "fabric_type": fabric_arr,
        "fabric_weight_kg": fabric_weight_kg,
        "dye_pct": dye_pct,
        "temperature_c": temperature_c,
        "time_min": time_min,
        "liquor_ratio": liquor_arr,
        "salt_g_l": salt_g_l,
        "acid_buffer_g_l": acid_buffer_g_l,
        "delta_e": delta_e,
        "outcome_match": outcome_match
    })

    output_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    os.makedirs(output_dir, exist_ok=True)
    file_path = os.path.join(output_dir, "historical_dyeing_recipes.csv")

    print(f"Writing enhanced dataset CSV to {file_path}...")
    df.to_csv(file_path, index=False)

    elapsed = time.time() - start_time
    print(f"Successfully generated {len(df):,} records with 30 shade codes & 10 fabric types in {elapsed:.2f}s.")
    print(f"Overall Match Rate: {df['outcome_match'].mean():.2%}, Mean Delta E: {df['delta_e'].mean():.2f}")
    return file_path

if __name__ == "__main__":
    generate_dyeing_dataset(1000000)
