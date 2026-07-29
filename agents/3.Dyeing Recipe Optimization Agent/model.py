import os
import json
import pandas as pd
import numpy as np

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
CSV_PATH = os.path.join(DATA_DIR, "historical_dyeing_recipes.csv")
MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")
MODEL_PATH = os.path.join(MODEL_DIR, "dyeing_rf.joblib")
META_PATH = os.path.join(MODEL_DIR, "dyeing_meta.json")

DEFAULT_RECIPE = {
    "dye_pct": 2.5,
    "temperature_c": 90,
    "time_min": 45,
    "liquor_ratio": "1:10",
}

_cached_df = None
_model_bundle = None


def get_df():
    global _cached_df
    if _cached_df is None and os.path.exists(CSV_PATH):
        try:
            _cached_df = pd.read_csv(CSV_PATH)
        except Exception as exc:
            print(f"Error loading CSV: {exc}")
    return _cached_df


def load_model_bundle():
    global _model_bundle
    if _model_bundle is not None:
        return _model_bundle
    if not os.path.exists(MODEL_PATH):
        return None
    try:
        import joblib

        _model_bundle = joblib.load(MODEL_PATH)
        return _model_bundle
    except Exception as exc:
        print(f"Error loading dyeing model: {exc}")
        return None


def train_dyeing_model(sample_size: int = 120_000):
    """Train Random Forest regressors on historical dyeing records."""
    import joblib
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.preprocessing import LabelEncoder

    if not os.path.exists(CSV_PATH):
        print(f"Dataset missing: {CSV_PATH}")
        return False

    print(f"Loading up to {sample_size:,} rows from historical dataset...")
    df = pd.read_csv(CSV_PATH, nrows=sample_size)
    if df.empty:
        print("Dataset is empty.")
        return False

    shade_enc = LabelEncoder()
    fabric_enc = LabelEncoder()
    liquor_enc = LabelEncoder()

    df = df.copy()
    df["shade_id"] = shade_enc.fit_transform(df["target_shade_code"].astype(str))
    df["fabric_id"] = fabric_enc.fit_transform(df["fabric_type"].astype(str))
    df["liquor_id"] = liquor_enc.fit_transform(df["liquor_ratio"].astype(str))

    features = df[["shade_id", "fabric_id"]].values
    targets = {
        "dye_pct": df["dye_pct"].values,
        "temperature_c": df["temperature_c"].values,
        "time_min": df["time_min"].values,
        "liquor_id": df["liquor_id"].values,
    }

    regressors = {}
    for name, y in targets.items():
        print(f"Training {name} model...")
        model = RandomForestRegressor(
            n_estimators=80,
            max_depth=18,
            min_samples_leaf=4,
            random_state=42,
            n_jobs=-1,
        )
        model.fit(features, y)
        regressors[name] = model

    os.makedirs(MODEL_DIR, exist_ok=True)
    bundle = {
        "regressors": regressors,
        "shade_enc": shade_enc,
        "fabric_enc": fabric_enc,
        "liquor_enc": liquor_enc,
    }
    joblib.dump(bundle, MODEL_PATH)

    meta = {
        "rows_trained": len(df),
        "shade_classes": list(shade_enc.classes_),
        "fabric_classes": list(fabric_enc.classes_),
    }
    with open(META_PATH, "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2)

    global _model_bundle
    _model_bundle = bundle
    print(f"Saved dyeing model to {MODEL_PATH}")
    return True


def _encode_pair(bundle, target_shade_code: str, fabric_type: str):
    shade_enc = bundle["shade_enc"]
    fabric_enc = bundle["fabric_enc"]

    shade = target_shade_code if target_shade_code in shade_enc.classes_ else None
    fabric = fabric_type if fabric_type in fabric_enc.classes_ else None

    if shade is None and len(shade_enc.classes_) > 0:
        shade = shade_enc.classes_[0]
    if fabric is None and len(fabric_enc.classes_) > 0:
        fabric = fabric_enc.classes_[0]

    return np.array([[shade_enc.transform([shade])[0], fabric_enc.transform([fabric])[0]]])


def _predict_with_model(bundle, target_shade_code: str, fabric_type: str):
    x = _encode_pair(bundle, target_shade_code, fabric_type)
    regs = bundle["regressors"]
    liquor_enc = bundle["liquor_enc"]

    dye_pct = float(max(0.05, round(regs["dye_pct"].predict(x)[0], 3)))
    temperature_c = int(round(np.clip(regs["temperature_c"].predict(x)[0], 60, 140)))
    time_min = int(round(np.clip(regs["time_min"].predict(x)[0], 20, 90)))
    liquor_idx = int(round(np.clip(regs["liquor_id"].predict(x)[0], 0, len(liquor_enc.classes_) - 1)))
    liquor_ratio = str(liquor_enc.classes_[liquor_idx])

    df = get_df()
    prob = 0.82
    if df is not None:
        subset = df[
            (df["target_shade_code"] == target_shade_code)
            & (df["fabric_type"] == fabric_type)
        ]
        if len(subset) == 0:
            subset = df[df["target_shade_code"] == target_shade_code]
        if len(subset) > 0:
            total = len(subset)
            successes = len(subset[subset["outcome_match"] == 1])
            prob = round(successes / total, 2)

    risk = "low" if prob >= 0.80 else ("medium" if prob >= 0.60 else "high")
    return {
        "recommended_recipe": {
            "dye_pct": dye_pct,
            "temperature_c": temperature_c,
            "time_min": time_min,
            "liquor_ratio": liquor_ratio,
        },
        "predicted_match_probability": prob,
        "estimated_redye_risk": risk,
        "prediction_source": "random_forest_ml",
    }


def _lookup_csv(batch_id: str, target_shade_code: str, fabric_type: str):
    df = get_df()
    if df is None:
        return {
            "batch_id": batch_id,
            "recommended_recipe": DEFAULT_RECIPE,
            "predicted_match_probability": 0.80,
            "estimated_redye_risk": "low",
            "prediction_source": "default_fallback",
        }

    try:
        subset = df[
            (df["target_shade_code"] == target_shade_code)
            & (df["fabric_type"] == fabric_type)
        ]
        if len(subset) == 0:
            subset = df[df["target_shade_code"] == target_shade_code]
        if len(subset) == 0:
            subset = df[df["fabric_type"] == fabric_type]

        if len(subset) > 0:
            success_subset = subset[subset["outcome_match"] == 1]
            best_match = (
                success_subset.sort_values(by="delta_e").iloc[0]
                if len(success_subset) > 0
                else subset.sort_values(by="delta_e").iloc[0]
            )
            recipe = {
                "dye_pct": float(round(best_match["dye_pct"], 3)),
                "temperature_c": int(best_match["temperature_c"]),
                "time_min": int(best_match["time_min"]),
                "liquor_ratio": str(best_match["liquor_ratio"]),
            }
            total = len(subset)
            successes = len(subset[subset["outcome_match"] == 1])
            prob = round(successes / total, 2) if total > 0 else 0.85
            risk = "low" if prob >= 0.80 else ("medium" if prob >= 0.60 else "high")
            return {
                "batch_id": batch_id,
                "recommended_recipe": recipe,
                "predicted_match_probability": prob,
                "estimated_redye_risk": risk,
                "prediction_source": "historical_knn",
            }
    except Exception as exc:
        print(f"Error in recommendation logic: {exc}")

    return {
        "batch_id": batch_id,
        "recommended_recipe": DEFAULT_RECIPE,
        "predicted_match_probability": 0.75,
        "estimated_redye_risk": "medium",
        "prediction_source": "default_fallback",
    }


def get_dyeing_recommendation(batch_id: str, target_shade_code: str, fabric_type: str):
    bundle = load_model_bundle()
    if bundle is not None:
        result = _predict_with_model(bundle, target_shade_code, fabric_type)
    else:
        result = _lookup_csv(batch_id, target_shade_code, fabric_type)

    result["batch_id"] = batch_id
    return result
