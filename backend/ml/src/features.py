"""
features.py — Feature Engineering Pipeline for Landslide Risk Modeling
======================================================================
Member 3 Responsibility: AI/ML Prediction Pipeline
Multi-Hazard Early Warning System (Sikkim Prototype)

Workflow 3 Implementation:
 1. Rainfall window aggregation & validation
 2. Rainfall intensity calculation (mm/hr equivalent)
 3. Antecedent rainfall anomaly (vs. Sikkim climatological mean)
 4. Soil moisture rate of change calculation
 5. Inclinometer tilt movement flag (tilt_movement_detected)
 6. Log1p transformation for heavily skewed geospatial features
 7. One-hot encoding for categorical land cover classes
 8. Feature audit and master run_feature_engineering() pipeline
"""

from __future__ import annotations

import logging
from typing import List, Tuple

import numpy as np
import pandas as pd

try:
    from ml.src import config
except ImportError:
    try:
        from . import config
    except ImportError:
        import config

logger = logging.getLogger(__name__)


def compute_rainfall_windows(df: pd.DataFrame) -> pd.DataFrame:
    """
    Validate and ensure rolling rainfall accumulation window columns are present.

    Expected windows:
      - rainfall_30min_mm (NASA GPM IMERG 30-minute)
      - rainfall_3hr_mm   (3-hour accumulation)
      - rainfall_24hr_mm  (24-hour daily accumulation)
      - rainfall_3day_mm  (3-day antecedent total)
      - rainfall_7day_mm  (7-day antecedent saturation total)

    Args:
        df: Input DataFrame.

    Returns:
        DataFrame with verified non-negative rainfall accumulation columns.
    """
    df = df.copy()
    windows = [
        "rainfall_30min_mm",
        "rainfall_3hr_mm",
        "rainfall_24hr_mm",
        "rainfall_3day_mm",
        "rainfall_7day_mm",
    ]

    for w in windows:
        if w not in df.columns:
            logger.warning(
                f"Rainfall window '{w}' not found in dataframe. "
                "In real pipeline, derive from rolling time-series aggregation. Setting to 0.0."
            )
            df[w] = 0.0
        else:
            # Enforce non-negativity
            df[w] = df[w].clip(lower=0.0)

    return df


def compute_rainfall_intensity(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute rainfall intensity in mm/hour from the 30-minute window.

    Formula:
        rainfall_intensity = rainfall_30min_mm / 0.5 (mm/hr)

    Args:
        df: Input DataFrame containing 'rainfall_30min_mm'.

    Returns:
        DataFrame with derived 'rainfall_intensity' column.
    """
    df = df.copy()
    if "rainfall_30min_mm" in df.columns:
        df["rainfall_intensity"] = df["rainfall_30min_mm"] / 0.5
    else:
        df["rainfall_intensity"] = 0.0

    return df


def compute_antecedent_rainfall_anomaly(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute antecedent rainfall anomaly against regional climatological baseline.

    Formula:
        antecedent_rainfall_anomaly = rainfall_7day_mm - config.CLIMATOLOGICAL_7DAY_MEAN_MM

    PROTOTYPE ASSUMPTION:
      Fixed 80.0 mm baseline derived from IMD 30-year monsoon normals for Sikkim.
      TODO: Replace with pixel-wise monthly climatology rasters from IMD/GPM IMERG.

    Args:
        df: Input DataFrame containing 'rainfall_7day_mm'.

    Returns:
        DataFrame with derived 'antecedent_rainfall_anomaly' column.
    """
    df = df.copy()
    baseline = config.CLIMATOLOGICAL_7DAY_MEAN_MM

    if "rainfall_7day_mm" in df.columns:
        df["antecedent_rainfall_anomaly"] = df["rainfall_7day_mm"] - baseline
    else:
        df["antecedent_rainfall_anomaly"] = 0.0

    return df


def compute_soil_moisture_change_rate(
    df: pd.DataFrame,
    time_delta_hours: float = 1.0,
) -> pd.DataFrame:
    """
    Compute or validate the rate of change of volumetric soil moisture (%/hour).

    If 'previous_soil_moisture' exists:
        soil_moisture_change_rate = (current - previous) / time_delta_hours
    Otherwise, retains the existing 'soil_moisture_change_rate' or defaults to 0.0.

    Args:
        df: Input DataFrame.
        time_delta_hours: Time interval between readings in hours.

    Returns:
        DataFrame with 'soil_moisture_change_rate'.
    """
    df = df.copy()

    if "previous_soil_moisture" in df.columns and "soil_moisture_pct" in df.columns:
        delta = df["soil_moisture_pct"] - df["previous_soil_moisture"]
        df["soil_moisture_change_rate"] = delta / time_delta_hours
    elif "soil_moisture_change_rate" not in df.columns:
        df["soil_moisture_change_rate"] = 0.0

    return df


def compute_tilt_movement_flag(df: pd.DataFrame) -> pd.DataFrame:
    """
    Generate a binary slope-movement flag from IoT inclinometer tilt changes.

    Formula:
        tilt_movement_detected = 1 if abs(tilt_change_deg) > threshold else 0

    Threshold configured via config.TILT_MOVEMENT_THRESHOLD_DEG (0.5 degrees).

    Args:
        df: Input DataFrame containing 'tilt_change_deg'.

    Returns:
        DataFrame with binary 'tilt_movement_detected' column (0 or 1).
    """
    df = df.copy()
    threshold = config.TILT_MOVEMENT_THRESHOLD_DEG

    if "tilt_change_deg" in df.columns:
        df["tilt_movement_detected"] = (df["tilt_change_deg"].abs() > threshold).astype(int)
    else:
        df["tilt_movement_detected"] = 0

    return df


def apply_log_transforms(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply natural log(1 + x) transforms to reduce skewness in long-tailed GIS distributions.

    Applied to:
      - historical_landslide_density (events/5km)
      - distance_to_river_km (distance to nearest drainage channel)

    Args:
        df: Input DataFrame.

    Returns:
        DataFrame with transformed columns.
    """
    df = df.copy()
    skewed_features = ["historical_landslide_density", "distance_to_river_km"]

    for col in skewed_features:
        if col in df.columns:
            # Ensure non-negative before log1p
            non_neg = df[col].clip(lower=0.0)
            df[col] = np.log1p(non_neg)

    return df


def encode_categorical(df: pd.DataFrame) -> pd.DataFrame:
    """
    One-hot encode categorical land cover classes with fixed column schema.

    Creates dummy columns for all classes in config.LAND_COVER_CLASSES
    (forest, bare, agricultural, built), ensuring consistent feature matrices
    even when single-sample inference requests contain only one category.

    Args:
        df: Input DataFrame containing 'land_cover_class'.

    Returns:
        DataFrame with original 'land_cover_class' removed and dummy columns appended.
    """
    df = df.copy()
    expected_classes = config.LAND_COVER_CLASSES

    if "land_cover_class" in df.columns:
        # Generate dummies
        dummies = pd.get_dummies(df["land_cover_class"], prefix="land_cover_class", dtype=float)

        # Ensure all expected classes exist
        for cls_name in expected_classes:
            col_name = f"land_cover_class_{cls_name}"
            if col_name not in dummies.columns:
                dummies[col_name] = 0.0

        # Drop original categorical column and concatenate dummies
        df = df.drop(columns=["land_cover_class"])
        df = pd.concat([df, dummies[[f"land_cover_class_{c}" for c in expected_classes]]], axis=1)
    else:
        # Default all dummies to 0.0 except forest = 1.0 (safest prior for Sikkim)
        for cls_name in expected_classes:
            col_name = f"land_cover_class_{cls_name}"
            df[col_name] = 1.0 if cls_name == "forest" else 0.0

    return df


def get_model_feature_names(df: pd.DataFrame) -> List[str]:
    """
    Identify and return the final list of feature names used for model input.

    Excludes coordinates, timestamps, target labels, and non-feature columns.

    Args:
        df: Feature-engineered DataFrame.

    Returns:
        List of feature column names in deterministic order.
    """
    excluded = set(config.META_COLUMNS) | {config.TARGET_COLUMN}
    features = [c for c in df.columns if c not in excluded]
    return sorted(features)


def run_feature_engineering(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
    """
    Execute complete feature engineering pipeline in sequence:
      1. Rainfall window aggregation & validation
      2. Rainfall intensity computation (mm/hr)
      3. Antecedent rainfall anomaly
      4. Soil moisture change rate
      5. Tilt movement trigger flag
      6. Log transforms for skewed geospatial features
      7. Categorical one-hot encoding

    Args:
        df: Clean, preprocessed DataFrame.

    Returns:
        Tuple of (feature-engineered DataFrame, list of model feature names).
    """
    logger.info(f"Starting feature engineering on {len(df)} rows...")

    df = compute_rainfall_windows(df)
    df = compute_rainfall_intensity(df)
    df = compute_antecedent_rainfall_anomaly(df)
    df = compute_soil_moisture_change_rate(df)
    df = compute_tilt_movement_flag(df)
    df = apply_log_transforms(df)
    df = encode_categorical(df)

    feature_names = get_model_feature_names(df)
    logger.info(f"Feature engineering completed. Generated {len(feature_names)} model features:")
    logger.debug(f"Features: {feature_names}")

    return df, feature_names
