"""
test_real_dataset.py — Real Dataset Ingestion & Testing Runner
==============================================================
Validates the AI/ML Prediction Pipeline using real environmental and geospatial
data (e.g. datasets2/final_ml_dataset_600000.csv with 54 columns).

Usage:
    # Quick Smoke Test on 10,000 rows (~60 seconds):
    python ml/test_real_dataset.py --sample 10000

    # Full Dataset Run on all 600,000 rows:
    python ml/test_real_dataset.py --full
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

# Add project root and ml directory to sys.path
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
import pandas as pd

from ml.src import (
    config,
    data_loader,
    evaluate,
    explain,
    features,
    predict,
    preprocessing,
    train,
    utils,
)

logger = utils.setup_logger("ml.test_real_dataset", log_level=logging.INFO)

DEFAULT_REAL_CSV = Path(r"D:\Apps\sih_2026\datasets2\final_ml_dataset_600000.csv")


def map_54_col_dataset(raw_df: pd.DataFrame) -> pd.DataFrame:
    """
    Map the 54-column real dataset to the canonical pipeline schema expected
    by preprocessing and feature engineering.
    """
    logger.info("Mapping columns from real dataset into pipeline canonical schema...")

    # Safe land-cover categorization mapping
    land_cover_map = {
        "Forest": "forest",
        "Grassland": "forest",
        "Agriculture": "agricultural",
        "Built-up": "built",
        "Bare land": "bare",
        "Water": "bare",
    }

    mapped = pd.DataFrame()

    # Coordinates & Timestamp
    mapped["latitude"] = raw_df["latitude"].astype(float)
    mapped["longitude"] = raw_df["longitude"].astype(float)
    if "date" in raw_df.columns:
        mapped["timestamp"] = pd.to_datetime(raw_df["date"]).dt.strftime("%Y-%m-%dT12:00:00")
    elif "timestamp" in raw_df.columns:
        mapped["timestamp"] = raw_df["timestamp"]
    else:
        mapped["timestamp"] = "2022-01-01T12:00:00"

    # Rainfall Accumulations (NASA GPM IMERG equivalent)
    if "max_rainfall_intensity_mm" in raw_df.columns:
        mapped["rainfall_30min_mm"] = (raw_df["max_rainfall_intensity_mm"] * 0.5).clip(lower=0.0)
        mapped["rainfall_intensity"] = raw_df["max_rainfall_intensity_mm"].clip(lower=0.0)
    else:
        mapped["rainfall_30min_mm"] = 0.0
        mapped["rainfall_intensity"] = 0.0

    if "rainfall_1d_mm" in raw_df.columns:
        mapped["rainfall_3hr_mm"] = (raw_df["rainfall_1d_mm"] / 8.0).clip(lower=0.0)
        mapped["rainfall_24hr_mm"] = raw_df["rainfall_1d_mm"].clip(lower=0.0)
    elif "rainfall_24hr_mm" in raw_df.columns:
        mapped["rainfall_3hr_mm"] = (raw_df["rainfall_24hr_mm"] / 8.0).clip(lower=0.0)
        mapped["rainfall_24hr_mm"] = raw_df["rainfall_24hr_mm"].clip(lower=0.0)
    else:
        mapped["rainfall_3hr_mm"] = 0.0
        mapped["rainfall_24hr_mm"] = 0.0

    mapped["rainfall_3day_mm"] = raw_df.get("rainfall_3d_mm", raw_df.get("rainfall_3day_mm", 0.0)).clip(lower=0.0)
    mapped["rainfall_7day_mm"] = raw_df.get("rainfall_7d_mm", raw_df.get("rainfall_7day_mm", 0.0)).clip(lower=0.0)

    # Rainfall anomaly
    if "rainfall_anomaly" in raw_df.columns:
        mapped["antecedent_rainfall_anomaly"] = raw_df["rainfall_anomaly"]
    elif "antecedent_rainfall_anomaly" in raw_df.columns:
        mapped["antecedent_rainfall_anomaly"] = raw_df["antecedent_rainfall_anomaly"]
    else:
        mapped["antecedent_rainfall_anomaly"] = mapped["rainfall_7day_mm"] - config.CLIMATOLOGICAL_7DAY_MEAN_MM

    # Soil Moisture (fraction -> percentage 0-100)
    if "soil_moisture" in raw_df.columns:
        sm = raw_df["soil_moisture"].astype(float)
        # If values are in ratio [0, 1], scale to percent [0, 100]
        if sm.max() <= 1.0:
            sm = sm * 100.0
        mapped["soil_moisture_pct"] = sm.clip(0.0, 100.0)
    elif "soil_moisture_pct" in raw_df.columns:
        mapped["soil_moisture_pct"] = raw_df["soil_moisture_pct"].clip(0.0, 100.0)
    else:
        mapped["soil_moisture_pct"] = 30.0

    mapped["soil_moisture_change_rate"] = 0.0

    # Topography / DEM
    mapped["elevation_m"] = raw_df.get("elevation_m", 1500.0).clip(lower=0.0)
    mapped["slope_deg"] = raw_df.get("slope_deg", 25.0).clip(0.0, 90.0)
    mapped["aspect_deg"] = raw_df.get("aspect_deg", 180.0).clip(0.0, 360.0)

    # Vegetation & Land Cover
    mapped["ndvi"] = raw_df.get("ndvi", 0.6).clip(-1.0, 1.0)
    raw_lc = raw_df.get("land_cover", raw_df.get("land_cover_class", "Forest"))
    mapped["land_cover_class"] = raw_lc.map(land_cover_map).fillna("forest")

    # Historical Density / Local Relief Proxy
    if "historical_landslide_density" in raw_df.columns:
        mapped["historical_landslide_density"] = raw_df["historical_landslide_density"]
    elif "local_relief_m" in raw_df.columns:
        mapped["historical_landslide_density"] = (raw_df["local_relief_m"] / 100.0).clip(0.0, 50.0)
    else:
        mapped["historical_landslide_density"] = 5.0

    # Proximity metrics
    mapped["distance_to_river_km"] = raw_df.get("distance_to_river_km", 1.0).clip(lower=0.0)
    mapped["distance_to_road_km"] = raw_df.get("distance_to_road_km", 1.0).clip(lower=0.0)

    # Inclinometer & Temperature
    mapped["tilt_change_deg"] = raw_df.get("tilt_change_deg", 0.0)
    mapped["temperature_C"] = raw_df.get("temperature_c", raw_df.get("temperature_C", 18.0))
    mapped["data_freshness_score"] = 1.0

    # ── Additional Rich Geophysical & Geological Features from 54-col schema ──
    for col in [
        "twi", "spi", "curvature", "roughness", "local_relief_m",
        "soil_depth_cm", "clay_pct", "sand_pct", "silt_pct",
        "water_holding_capacity", "distance_to_fault_km", "fault_presence",
        "drainage_density_km_per_km2", "flow_accumulation", "forest_pct",
        "built_up_pct", "bare_land_pct", "ndwi", "humidity_pct",
        "wind_speed_mps", "rainfall_30d_mm"
    ]:
        if col in raw_df.columns:
            mapped[col] = raw_df[col].astype(float)

    # ── Compound Multi-Hazard Physical Triggers ──
    if "slope_deg" in mapped.columns and "rainfall_7day_mm" in mapped.columns:
        mapped["slope_rainfall_trigger"] = (mapped["slope_deg"] / 45.0) * (mapped["rainfall_7day_mm"] / 100.0)
    if "twi" in mapped.columns and "soil_moisture_pct" in mapped.columns:
        mapped["saturation_hazard"] = (mapped["twi"] / 10.0) * (mapped["soil_moisture_pct"] / 50.0)
    if "distance_to_fault_km" in mapped.columns:
        mapped["fault_proximity_factor"] = 1.0 / (mapped["distance_to_fault_km"].clip(lower=0.0) + 0.5)

    # Target: binary landslide occurrence
    if "landslide_occurrence" in raw_df.columns:
        mapped["landslide_occurred"] = raw_df["landslide_occurrence"].astype(int)
    elif "landslide_occurred" in raw_df.columns:
        mapped["landslide_occurred"] = raw_df["landslide_occurred"].astype(int)
    else:
        raise KeyError("Could not find target column 'landslide_occurrence' or 'landslide_occurred'.")

    return mapped


def run_test(csv_path: Path, sample_size: int | None = None) -> None:
    """Execute training and testing on real dataset."""
    start_time = time.time()

    print("\n" + "=" * 80)
    print(" MULTI-HAZARD EARLY WARNING SYSTEM — REAL DATASET PIPELINE TEST")
    print("=" * 80)
    print(f" Source File : {csv_path}")
    print(f" Sample Size : {'ALL (Full 600,000 rows)' if sample_size is None else f'{sample_size:,} rows'}")
    print("=" * 80 + "\n")

    if not csv_path.exists():
        logger.error(f"Dataset file not found at: {csv_path}")
        sys.exit(1)

    # 1. Ingest Data
    logger.info(f"Loading data from {csv_path}...")
    if sample_size is not None:
        raw_df = pd.read_csv(csv_path, nrows=sample_size)
    else:
        raw_df = pd.read_csv(csv_path)

    logger.info(f"Loaded {len(raw_df):,} raw records with {raw_df.shape[1]} columns.")

    # 2. Map schema to canonical pipeline format
    df_canonical = map_54_col_dataset(raw_df)
    pos_count = int(df_canonical["landslide_occurred"].sum())
    pos_pct = (pos_count / len(df_canonical)) * 100.0
    logger.info(f"Canonical dataset prepared: {len(df_canonical):,} rows | Positives: {pos_count:,} ({pos_pct:.2f}%)")

    # 3. Preprocessing, Validation & Imputation
    logger.info("Executing preprocessing and validation pipeline...")
    df_clean, val_report = preprocessing.preprocess_pipeline(
        df_canonical,
        fit=True,
        preprocessor_path=config.PREPROCESSOR_PATH,
    )
    logger.info(
        f"Validation: {val_report['clean_rows']:,} clean rows | "
        f"Duplicates dropped: {val_report['duplicates_dropped']}"
    )

    # 4. Feature Engineering
    logger.info("Running feature engineering...")
    df_fe, feature_names = features.run_feature_engineering(df_clean)
    logger.info(f"Engineered {len(feature_names)} features: {feature_names[:6]}...")

    # 5. Temporal Train/Test Split
    logger.info("Splitting dataset temporally (80% train / 20% test)...")
    X_train, X_test, y_train, y_test = train.temporal_train_test_split(
        df_fe,
        feature_names=feature_names,
        train_ratio=config.TEMPORAL_TRAIN_RATIO,
    )
    logger.info(
        f"Train set: {len(X_train):,} rows ({int(y_train.sum()):,} positives) | "
        f"Test set: {len(X_test):,} rows ({int(y_test.sum()):,} positives)"
    )

    # 6. Train Models with Class Weighting
    logger.info("Training models (Logistic Regression, Random Forest, XGBoost)...")
    trained_models = train.train_all_models(
        X_train,
        y_train,
        feature_names=feature_names,
    )

    models_dict = {name: model for name, (model, cv_scores) in trained_models.items()}

    # 7. Evaluate on held-out test set
    logger.info("Evaluating models on held-out test partition...")
    eval_results = {}
    for name, model in models_dict.items():
        metrics = evaluate.evaluate_model(model, X_test, y_test, model_name=name)
        eval_results[name] = metrics

    best_model_name, best_model = evaluate.compare_models(models_dict, X_test, y_test)

    # Save evaluation report
    evaluate.generate_evaluation_report(
        eval_results,
        output_path=str(config.EVALUATION_REPORT_PATH),
    )
    logger.info(f"Evaluation report saved to: {config.EVALUATION_REPORT_PATH}")

    # 8. SHAP Explainability
    logger.info(f"Generating SHAP explainability plots for {best_model_name}...")
    try:
        explain_artifacts = explain.run_explainability(
            best_model,
            X_test=X_test,
            feature_names=feature_names,
            model_name=best_model_name,
        )
        logger.info(f"SHAP summary saved -> {explain_artifacts.get('shap_summary_path')}")
        logger.info(f"SHAP force plot saved -> {explain_artifacts.get('force_plot_path')}")
    except Exception as ex:
        logger.warning(f"SHAP generation warning: {ex}")

    # 9. Test Live Inference with predict_risk()
    logger.info("Testing live inference function predict_risk()...")
    sample_obs = {
        "latitude": 27.35,
        "longitude": 88.62,
        "rainfall_24hr_mm": float(X_test["rainfall_24hr_mm"].quantile(0.95)),
        "soil_moisture_pct": float(X_test["soil_moisture_pct"].quantile(0.95)),
        "slope_deg": float(X_test["slope_deg"].quantile(0.90)),
        "elevation_m": float(X_test["elevation_m"].median()),
        "land_cover_class": "forest",
        "distance_to_river_km": 0.25,
    }
    sample_pred = predict.predict_risk(sample_obs)

    elapsed = time.time() - start_time

    # Compute optimal operational threshold (maximizing F1 given class imbalance)
    from sklearn.metrics import precision_recall_curve, recall_score, precision_score
    y_prob = best_model.predict_proba(X_test)[:, 1]
    prec_curve, rec_curve, thresh_curve = precision_recall_curve(y_test, y_prob)
    f1_curve = 2 * (prec_curve * rec_curve) / (prec_curve + rec_curve + 1e-10)
    best_t_idx = int(np.argmax(f1_curve))
    opt_t = float(thresh_curve[best_t_idx]) if best_t_idx < len(thresh_curve) else 0.5
    opt_recall = float(recall_score(y_test, y_prob >= opt_t))
    opt_precision = float(precision_score(y_test, y_prob >= opt_t))

    print("\n" + "=" * 80)
    print(f" REAL DATASET PIPELINE TEST COMPLETE (Elapsed: {elapsed:.1f}s)")
    print("=" * 80)
    best_res = eval_results[best_model_name]
    print(f" Best Selected Model : {best_model_name.upper()}")
    print(f" Best PR-AUC         : {best_res['pr_auc']:.4f}")
    print(f" Best ROC-AUC        : {best_res['roc_auc']:.4f}")
    print(f"\n Threshold Analysis for Early Warning:")
    print(f"   [Default Threshold: 0.50] -> Detection Recall: {best_res.get('recall_positive', 0.0):.2%}, Precision: {best_res.get('precision_positive', 0.0):.2%}")
    print(f"   [Operational Threshold: {opt_t:.2f}] -> Detection Recall: {opt_recall:.2%}, Precision: {opt_precision:.2%}, F1: {f1_curve[best_t_idx]:.4f}")

    print("\n Model Comparison Table (Standard Cutoff):")
    print(f" {'Model':<22} | {'PR-AUC':<8} | {'Recall':<8} | {'Precision':<10} | {'ROC-AUC':<8}")
    print(" " + "-" * 66)
    for m_name, res in eval_results.items():
        rec = res.get('recall_positive', res.get('recall', 0.0))
        prec = res.get('precision_positive', res.get('precision', 0.0))
        print(
            f" {m_name:<22} | {res['pr_auc']:<8.4f} | {rec:<8.4f} | "
            f"{prec:<10.4f} | {res['roc_auc']:<8.4f}"
        )

    print("\n Live Prediction Test Result:")
    print(f"   Risk Probability : {sample_pred['risk_probability']:.4f}")
    print(f"   Risk Level       : {sample_pred['risk_level']} ({sample_pred['risk_level_color']})")
    print(f"   Top Risk Factors : {[f['feature'] for f in sample_pred.get('top_factors', [])[:3]]}")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test AI/ML pipeline with real dataset")
    parser.add_argument("--csv-path", type=Path, default=DEFAULT_REAL_CSV, help="Path to real dataset CSV")
    parser.add_argument("--sample", type=int, default=None, help="Sample N rows for fast smoke testing")
    parser.add_argument("--full", action="store_true", help="Run full 600,000 rows")

    args = parser.parse_args()
    sample = None if args.full else (args.sample or 30000)
    run_test(args.csv_path, sample_size=sample)
