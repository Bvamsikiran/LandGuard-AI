"""
preprocessing.py — Data Preprocessing, Validation & Imputation Pipeline
=======================================================================
Member 3 Responsibility: AI/ML Prediction Pipeline
Multi-Hazard Early Warning System (Sikkim Prototype)

Workflow 2 implementation:
 1. Presence check (validate columns)
 2. Timestamp validation (parse, flag future timestamps)
 3. Range validation (min/max plausibility check from config)
 4. Missing value handling (median for numeric, mode for categorical, persist imputer)
 5. Duplicate detection & removal
 6. Data freshness tagging
 7. Master preprocess_pipeline() returning clean DataFrame + validation report
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

import joblib
import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer

try:
    from ml.src import config
except ImportError:
    try:
        from . import config
    except ImportError:
        import config

logger = logging.getLogger(__name__)


def validate_columns(df: pd.DataFrame) -> Dict[str, str]:
    """
    Confirm all expected feature columns exist in the DataFrame.

    Logs a warning for any missing column and returns a status dict.

    Args:
        df: Input DataFrame to check.

    Returns:
        Dict mapping column name -> 'present' or 'missing'.
    """
    report = {}
    missing_cols = []

    for col in config.RAWFEATURE_NAMES:
        if col in df.columns:
            report[col] = "present"
        else:
            report[col] = "missing"
            missing_cols.append(col)

    if missing_cols:
        logger.warning(
            f"Missing expected columns in DataFrame: {missing_cols}. "
            "These will be created with NaN values for imputation."
        )
        for col in missing_cols:
            df[col] = np.nan

    return report


def validate_timestamps(df: pd.DataFrame) -> Tuple[pd.DataFrame, int]:
    """
    Parse and validate timestamps.

    Converts 'timestamp' to datetime. Flags and logs any future timestamps
    (> current UTC time), replacing them with current UTC time.

    Args:
        df: Input DataFrame with 'timestamp' column.

    Returns:
        Tuple of (DataFrame with parsed timestamps, count of future timestamps flagged).
    """
    df = df.copy()
    now_utc = pd.Timestamp.now(tz=timezone.utc)
    future_count = 0

    if "timestamp" in df.columns:
        # Convert to datetime with UTC awareness
        df["timestamp_parsed"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")

        future_mask = df["timestamp_parsed"] > now_utc
        future_count = int(future_mask.sum())

        if future_count > 0:
            logger.warning(
                f"Flagged {future_count} future-dated timestamps. Replacing with current UTC time."
            )
            df.loc[future_mask, "timestamp_parsed"] = now_utc

        # Retain original string column for metadata consistency
        df["timestamp"] = df["timestamp_parsed"].dt.strftime("%Y-%m-%dT%H:%M:%S")
        df = df.drop(columns=["timestamp_parsed"])

    return df, future_count


def validate_ranges(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, int]]:
    """
    Apply min/max plausibility checks per feature from config.FEATURE_VALID_RANGES.

    Out-of-range values are set to NaN so that they are handled by the imputer
    rather than corrupting model fitting.

    Args:
        df: Input DataFrame.

    Returns:
        Tuple of (DataFrame with out-of-range values replaced with NaN, dict of violation counts per column).
    """
    df = df.copy()
    violation_report = {}

    for col, (min_val, max_val) in config.FEATURE_VALID_RANGES.items():
        if col in df.columns and pd.api.types.is_numeric_dtype(df[col]):
            mask_out = (df[col] < min_val) | (df[col] > max_val)
            n_violations = int(mask_out.sum())
            if n_violations > 0:
                logger.warning(
                    f"Column '{col}' has {n_violations} values outside [{min_val}, {max_val}]. Setting to NaN."
                )
                df.loc[mask_out, col] = np.nan
            violation_report[col] = n_violations

    return df, violation_report


def drop_duplicates(df: pd.DataFrame) -> Tuple[pd.DataFrame, int]:
    """
    Detect and remove duplicate observations (same latitude, longitude, and timestamp).

    Args:
        df: Input DataFrame.

    Returns:
        Tuple of (deduplicated DataFrame, number of dropped rows).
    """
    n_before = len(df)
    subset_cols = [c for c in ["latitude", "longitude", "timestamp"] if c in df.columns]

    if subset_cols:
        df_clean = df.drop_duplicates(subset=subset_cols).reset_index(drop=True)
    else:
        df_clean = df.drop_duplicates().reset_index(drop=True)

    n_dropped = n_before - len(df_clean)
    if n_dropped > 0:
        logger.info(f"Dropped {n_dropped} duplicate observation rows.")

    return df_clean, n_dropped


def tag_data_freshness(
    df: pd.DataFrame,
    inference_time: Optional[datetime] = None,
) -> pd.DataFrame:
    """
    Compute data_freshness_score based on observation age relative to inference time.

    Freshness score mapping from config.FRESHNESS_THRESHOLDS:
      - FRESH   (< 6h)   -> 1.0
      - RECENT  (6-24h)  -> 0.7
      - STALE   (24-72h) -> 0.4
      - MISSING (> 72h)  -> 0.0

    Args:
        df: DataFrame with 'timestamp' column.
        inference_time: Reference datetime. Defaults to current UTC time.

    Returns:
        DataFrame with updated 'data_freshness_score' column.
    """
    df = df.copy()

    if inference_time is None:
        ref_time = datetime.now(timezone.utc)
    else:
        ref_time = inference_time if inference_time.tzinfo else inference_time.replace(tzinfo=timezone.utc)

    if "timestamp" in df.columns:
        parsed_ts = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
        age_hours = (ref_time - parsed_ts).dt.total_seconds() / 3600.0
        age_hours = age_hours.clip(lower=0.0)

        scores = pd.Series(0.0, index=df.index)
        for label, (low, high, score) in config.FRESHNESS_THRESHOLDS.items():
            mask = (age_hours >= low) & (age_hours < high)
            scores.loc[mask] = score

        # If timestamp was NaT, score is 0.0
        scores.loc[parsed_ts.isna()] = 0.0
        df["data_freshness_score"] = scores
    else:
        df["data_freshness_score"] = 0.0

    return df


def handle_missing_values(
    df: pd.DataFrame,
    fit: bool = True,
    preprocessor_path: Optional[Union[str, Path]] = None,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Impute missing values in numerical and categorical features.

      - Numerical features: imputed with median (learned on training set).
      - Categorical features (land_cover_class): imputed with mode.
      - Target variable: NOT imputed — rows missing the target are dropped.
      - Fitted imputers are saved to preprocessor_path for runtime inference.

    Args:
        df: Input DataFrame.
        fit: If True, fit imputers and save artifact. If False, load and transform.
        preprocessor_path: Destination path for saved preprocessor.

    Returns:
        Tuple of (clean DataFrame, stats dictionary).
    """
    if preprocessor_path is None:
        preprocessor_path = config.PREPROCESSOR_PATH

    preprocessor_path = Path(preprocessor_path)
    df = df.copy()

    # Drop rows missing the target variable (training data only)
    if config.TARGET_COLUMN in df.columns:
        n_before = len(df)
        df = df.dropna(subset=[config.TARGET_COLUMN]).reset_index(drop=True)
        dropped_targets = n_before - len(df)
        if dropped_targets > 0:
            logger.info(f"Dropped {dropped_targets} rows with missing target '{config.TARGET_COLUMN}'.")

    num_cols = [c for c in config.NUMERICAL_FEATURES if c in df.columns]
    cat_cols = [c for c in config.CATEGORICAL_FEATURES if c in df.columns]

    stats = {}

    if fit:
        num_imputer = SimpleImputer(strategy="median")
        cat_imputer = SimpleImputer(strategy="most_frequent")

        if num_cols:
            df[num_cols] = num_imputer.fit_transform(df[num_cols])
            stats["num_medians"] = dict(zip(num_cols, num_imputer.statistics_))

        if cat_cols:
            df[cat_cols] = cat_imputer.fit_transform(df[cat_cols])
            stats["cat_modes"] = dict(zip(cat_cols, cat_imputer.statistics_))

        preprocessor = {
            "num_imputer": num_imputer,
            "cat_imputer": cat_imputer,
            "num_cols": num_cols,
            "cat_cols": cat_cols,
            "stats": stats,
        }

        preprocessor_path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(preprocessor, preprocessor_path)
        logger.info(f"Preprocessor artifact saved to {preprocessor_path}")

    else:
        # Load fitted preprocessor from disk
        if not preprocessor_path.exists():
            logger.warning(
                f"Preprocessor artifact not found at {preprocessor_path}. "
                "Fitting inline fallback imputer on current batch."
            )
            return handle_missing_values(df, fit=True, preprocessor_path=preprocessor_path)

        preprocessor = joblib.load(preprocessor_path)
        num_imputer = preprocessor["num_imputer"]
        cat_imputer = preprocessor["cat_imputer"]
        stored_num_cols = preprocessor["num_cols"]
        stored_cat_cols = preprocessor["cat_cols"]

        # Ensure all columns expected by imputer exist
        for col in stored_num_cols:
            if col not in df.columns:
                df[col] = np.nan
        for col in stored_cat_cols:
            if col not in df.columns:
                df[col] = "forest"

        df[stored_num_cols] = num_imputer.transform(df[stored_num_cols])
        df[stored_cat_cols] = cat_imputer.transform(df[stored_cat_cols])
        stats = preprocessor.get("stats", {})

    return df, stats


def preprocess_pipeline(
    df: pd.DataFrame,
    fit: bool = True,
    preprocessor_path: Optional[Union[str, Path]] = None,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Execute full preprocessing and validation pipeline in sequence:
      1. Validate columns
      2. Validate timestamps
      3. Apply range validation
      4. Deduplicate rows
      5. Tag data freshness
      6. Impute missing values

    Args:
        df: Raw input DataFrame.
        fit: If True, fit and persist preprocessors. If False, transform using saved preprocessor.
        preprocessor_path: Path for saving/loading preprocessor artifact.

    Returns:
        Tuple of (clean DataFrame, validation report dict).
    """
    logger.info(f"Starting preprocessing pipeline (fit={fit}, {len(df)} initial rows)...")

    # 1. Presence check
    col_report = validate_columns(df)

    # 2. Timestamp validation
    df, future_count = validate_timestamps(df)

    # 3. Range plausibility validation
    df, range_violations = validate_ranges(df)

    # 4. Duplicate removal
    df, n_duplicates = drop_duplicates(df)

    # 5. Data freshness tagging
    df = tag_data_freshness(df)

    # 6. Missing value imputation
    df, imputer_stats = handle_missing_values(df, fit=fit, preprocessor_path=preprocessor_path)

    validation_report = {
        "columns_status": col_report,
        "future_timestamps_flagged": future_count,
        "range_violations": range_violations,
        "duplicates_dropped": n_duplicates,
        "imputer_stats": imputer_stats,
        "clean_rows": len(df),
    }

    logger.info(f"Preprocessing completed. Clean dataset contains {len(df)} rows.")
    return df, validation_report