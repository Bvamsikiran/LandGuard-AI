"""
data_loader.py — Data Ingestion & Synthetic Prototype Dataset Generator
========================================================================
Member 3 Responsibility: AI/ML Prediction Pipeline
Multi-Hazard Early Warning and Cascade Risk Assessment System (Sikkim Prototype)

REAL DATA REPLACEMENT NOTES:
# rainfall_30min_mm             → NASA GPM IMERG Early Run, ~4hr latency, 0.1deg grid, via NASA Earthdata API
# rainfall_3hr_mm, 24hr, 3d, 7d → NASA GPM IMERG rolling accumulations
# rainfall_intensity           → Derived: rainfall_30min_mm / 0.5 (mm/hour)
# antecedent_rainfall_anomaly  → 7-day IMERG rainfall minus IMD 30-year monsoon normals
# soil_moisture_pct            → IoT ESP32 capacitive sensor via POST /api/v1/sensor-data endpoint (or NASA SMAP proxy)
# soil_moisture_change_rate    → IoT temporal derivative (delta % / delta hour)
# elevation_m, slope_deg, aspect_deg → SRTM 30m DEM, processed via GDAL/rasterio
# ndvi                         → Sentinel-2 L2A band calculation (B8-B4)/(B8+B4) via Copernicus Hub / GEE API
# land_cover_class             → ESA WorldCover 10m or Sentinel-2 Land Cover classification
# historical_landslide_density → ISRO Landslide Atlas (80,000 events, 1998–2022), spatial join count within 5 km
# distance_to_river_km         → OpenStreetMap / Bhuvan drainage GIS vector layer
# distance_to_road_km          → OpenStreetMap / Border Roads Organisation (BRO) highway vector layer
# tilt_change_deg              → IoT MPU6050 inclinometer reading on vulnerable slope
# temperature_C                → IMD Automated Weather Station (AWS) API
# data_freshness_score         → Temporal latency tag computed at ingestion
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Union

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


def generate_synthetic_data(
    n_samples: int = config.N_SAMPLES_TOTAL,
    n_positives: int = config.N_POSITIVES,
    random_state: int = config.SYNTHETIC_RANDOM_STATE,
    output_path: Optional[Union[str, Path]] = None,
) -> pd.DataFrame:
    """
    Generate a scientifically plausible synthetic prototype dataset for Sikkim.

    Features simulate Himalayan landslide dynamics:
      - Positives (landslides=1) exhibit correlated triggering conditions:
        extreme rainfall, saturated soil, steep terrain, high historical density,
        disturbed/bare slopes, and active sensor tilt.
      - Negatives (landslides=0) reflect typical stable monsoon or dry conditions.
      - 5-10% random missing values (NaN) simulate real-world sensor/satellite outages.
      - Sikkim spatial bounds: Lat 27.0-28.1 N, Lon 88.0-89.0 E.
      - Timestamps spanning 2018-2023 for temporal validation.

    Args:
        n_samples: Total number of rows to generate (default 5000).
        n_positives: Number of landslide events (default 400, ~8% positive rate).
        random_state: Random seed for reproducibility.
        output_path: Destination CSV path. Defaults to config.TRAINING_DATA_PATH.

    Returns:
        pd.DataFrame containing 5000 rows with 20 features, coordinates, timestamp, and target.
    """
    if output_path is None:
        output_path = config.TRAINING_DATA_PATH

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(random_state)
    n_negatives = n_samples - n_positives

    logger.info(
        f"Generating synthetic dataset: {n_samples} total ({n_positives} positives, {n_negatives} negatives)"
    )

    # -------------------------------------------------------------------------
    # 1. Generate Positive Samples (Landslide Events = 1)
    # Triggered by high rainfall + saturated soil + steep slope + prior history
    # -------------------------------------------------------------------------
    pos_rain_30min = rng.gamma(shape=3.5, scale=8.0, size=n_positives) + 5.0
    pos_rain_30min = np.clip(pos_rain_30min, 5.0, 120.0)

    pos_rain_3hr = pos_rain_30min * rng.uniform(2.5, 4.5, size=n_positives) + rng.normal(15, 5, n_positives)
    pos_rain_3hr = np.clip(pos_rain_3hr, pos_rain_30min, 250.0)

    pos_rain_24hr = pos_rain_3hr * rng.uniform(1.8, 3.2, size=n_positives) + rng.normal(40, 15, n_positives)
    pos_rain_24hr = np.clip(pos_rain_24hr, np.maximum(pos_rain_3hr, 60.0), 450.0)

    pos_rain_3day = pos_rain_24hr * rng.uniform(1.3, 2.2, size=n_positives) + rng.normal(30, 15, n_positives)
    pos_rain_3day = np.clip(pos_rain_3day, pos_rain_24hr, 480.0)

    pos_rain_7day = pos_rain_3day * rng.uniform(1.2, 1.8, size=n_positives) + rng.normal(40, 20, n_positives)
    pos_rain_7day = np.clip(pos_rain_7day, pos_rain_3day, 500.0)

    pos_intensity = pos_rain_30min / 0.5  # mm/hr
    pos_anomaly = pos_rain_7day - config.CLIMATOLOGICAL_7DAY_MEAN_MM

    pos_soil_moisture = rng.beta(a=7, b=2, size=n_positives) * 40.0 + 58.0
    pos_soil_moisture = np.clip(pos_soil_moisture, 55.0, 98.0)

    pos_soil_change = rng.normal(loc=3.5, scale=1.5, size=n_positives)
    pos_soil_change = np.clip(pos_soil_change, 0.5, 15.0)

    pos_slope = rng.normal(loc=38.0, scale=8.0, size=n_positives)
    pos_slope = np.clip(pos_slope, 22.0, 75.0)

    pos_elevation = rng.uniform(800.0, 4200.0, size=n_positives)
    pos_aspect = rng.uniform(0.0, 360.0, size=n_positives)

    pos_ndvi = rng.beta(a=2, b=4, size=n_positives) * 0.5 + 0.05

    pos_lc_probs = [0.20, 0.45, 0.25, 0.10]
    pos_land_cover = rng.choice(config.LAND_COVER_CLASSES, size=n_positives, p=pos_lc_probs)

    pos_history = rng.negative_binomial(n=3, p=0.2, size=n_positives) + 4.0
    pos_history = np.clip(pos_history, 2.0, 60.0)

    pos_dist_river = rng.exponential(scale=1.5, size=n_positives) + 0.1
    pos_dist_river = np.clip(pos_dist_river, 0.05, 15.0)

    pos_dist_road = rng.exponential(scale=1.2, size=n_positives) + 0.05
    pos_dist_road = np.clip(pos_dist_road, 0.02, 10.0)

    pos_tilt = rng.exponential(scale=1.2, size=n_positives) + 0.4
    pos_tilt = np.clip(pos_tilt, 0.3, 8.5)

    pos_temp = rng.normal(loc=18.0, scale=5.0, size=n_positives)
    pos_temp = np.clip(pos_temp, 5.0, 32.0)

    pos_freshness = rng.choice([1.0, 0.7, 0.4], size=n_positives, p=[0.75, 0.20, 0.05])
    pos_target = np.ones(n_positives, dtype=int)

    # -------------------------------------------------------------------------
    # 2. Generate Negative Samples (Non-Events = 0)
    # Typical dry or moderate conditions
    # -------------------------------------------------------------------------
    neg_rain_30min = rng.exponential(scale=1.8, size=n_negatives)
    neg_rain_30min = np.clip(neg_rain_30min, 0.0, 25.0)

    neg_rain_3hr = neg_rain_30min * rng.uniform(1.2, 2.5, size=n_negatives) + rng.exponential(scale=3.0, size=n_negatives)
    neg_rain_3hr = np.clip(neg_rain_3hr, neg_rain_30min, 60.0)

    neg_rain_24hr = neg_rain_3hr * rng.uniform(1.5, 3.0, size=n_negatives) + rng.exponential(scale=8.0, size=n_negatives)
    neg_rain_24hr = np.clip(neg_rain_24hr, neg_rain_3hr, 120.0)

    neg_rain_3day = neg_rain_24hr * rng.uniform(1.1, 1.8, size=n_negatives) + rng.exponential(scale=12.0, size=n_negatives)
    neg_rain_3day = np.clip(neg_rain_3day, neg_rain_24hr, 180.0)

    neg_rain_7day = neg_rain_3day * rng.uniform(1.1, 1.5, size=n_negatives) + rng.exponential(scale=15.0, size=n_negatives)
    neg_rain_7day = np.clip(neg_rain_7day, neg_rain_3day, 220.0)

    neg_intensity = neg_rain_30min / 0.5
    neg_anomaly = neg_rain_7day - config.CLIMATOLOGICAL_7DAY_MEAN_MM

    neg_soil_moisture = rng.beta(a=3, b=4, size=n_negatives) * 50.0 + 8.0
    neg_soil_moisture = np.clip(neg_soil_moisture, 5.0, 62.0)

    neg_soil_change = rng.normal(loc=-0.1, scale=0.6, size=n_negatives)
    neg_soil_change = np.clip(neg_soil_change, -3.0, 1.2)

    neg_slope = rng.gamma(shape=2.5, scale=7.0, size=n_negatives)
    neg_slope = np.clip(neg_slope, 0.0, 42.0)

    neg_elevation = rng.uniform(300.0, 4800.0, size=n_negatives)
    neg_aspect = rng.uniform(0.0, 360.0, size=n_negatives)

    neg_ndvi = rng.beta(a=5, b=2, size=n_negatives) * 0.6 + 0.3
    neg_ndvi = np.clip(neg_ndvi, 0.20, 0.90)

    neg_lc_probs = [0.65, 0.08, 0.20, 0.07]
    neg_land_cover = rng.choice(config.LAND_COVER_CLASSES, size=n_negatives, p=neg_lc_probs)

    neg_history = rng.poisson(lam=0.8, size=n_negatives).astype(float)

    neg_dist_river = rng.uniform(0.2, 25.0, size=n_negatives)
    neg_dist_road = rng.uniform(0.1, 20.0, size=n_negatives)

    neg_tilt = rng.normal(loc=0.02, scale=0.08, size=n_negatives)
    neg_tilt = np.clip(neg_tilt, -0.25, 0.35)

    neg_temp = rng.normal(loc=16.0, scale=6.5, size=n_negatives)
    neg_temp = np.clip(neg_temp, -5.0, 35.0)

    neg_freshness = rng.choice([1.0, 0.7, 0.4, 0.0], size=n_negatives, p=[0.70, 0.20, 0.07, 0.03])
    neg_target = np.zeros(n_negatives, dtype=int)

    # -------------------------------------------------------------------------
    # 3. Concatenate and Build DataFrame
    # -------------------------------------------------------------------------
    data_dict = {
        "rainfall_30min_mm": np.concatenate([pos_rain_30min, neg_rain_30min]),
        "rainfall_3hr_mm": np.concatenate([pos_rain_3hr, neg_rain_3hr]),
        "rainfall_24hr_mm": np.concatenate([pos_rain_24hr, neg_rain_24hr]),
        "rainfall_3day_mm": np.concatenate([pos_rain_3day, neg_rain_3day]),
        "rainfall_7day_mm": np.concatenate([pos_rain_7day, neg_rain_7day]),
        "rainfall_intensity": np.concatenate([pos_intensity, neg_intensity]),
        "antecedent_rainfall_anomaly": np.concatenate([pos_anomaly, neg_anomaly]),
        "soil_moisture_pct": np.concatenate([pos_soil_moisture, neg_soil_moisture]),
        "soil_moisture_change_rate": np.concatenate([pos_soil_change, neg_soil_change]),
        "elevation_m": np.concatenate([pos_elevation, neg_elevation]),
        "slope_deg": np.concatenate([pos_slope, neg_slope]),
        "aspect_deg": np.concatenate([pos_aspect, neg_aspect]),
        "ndvi": np.concatenate([pos_ndvi, neg_ndvi]),
        "land_cover_class": np.concatenate([pos_land_cover, neg_land_cover]),
        "historical_landslide_density": np.concatenate([pos_history, neg_history]),
        "distance_to_river_km": np.concatenate([pos_dist_river, neg_dist_river]),
        "distance_to_road_km": np.concatenate([pos_dist_road, neg_dist_road]),
        "tilt_change_deg": np.concatenate([pos_tilt, neg_tilt]),
        "temperature_C": np.concatenate([pos_temp, neg_temp]),
        "data_freshness_score": np.concatenate([pos_freshness, neg_freshness]),
        config.TARGET_COLUMN: np.concatenate([pos_target, neg_target]),
    }

    df = pd.DataFrame(data_dict)

    # Sikkim coordinates
    df["latitude"] = rng.uniform(config.LAT_MIN, config.LAT_MAX, size=n_samples)
    df["longitude"] = rng.uniform(config.LON_MIN, config.LON_MAX, size=n_samples)

    # Dates spanning 2018-2023
    start_dt = datetime.strptime(config.TIMESTAMP_START, "%Y-%m-%d")
    total_days = (datetime.strptime(config.TIMESTAMP_END, "%Y-%m-%d") - start_dt).days
    random_days = rng.integers(0, total_days, size=n_samples)
    random_hours = rng.integers(0, 24, size=n_samples)
    timestamps = [
        (start_dt + timedelta(days=int(d), hours=int(h))).isoformat()
        for d, h in zip(random_days, random_hours)
    ]
    df["timestamp"] = timestamps

    # Inject 7% random missing values in numerical columns
    num_cols = [c for c in config.NUMERICAL_FEATURES if c in df.columns]
    for col in num_cols:
        mask = rng.random(size=n_samples) < config.MISSING_VALUE_FRACTION
        df.loc[mask, col] = np.nan

    # Sort chronologically to preserve temporal order
    df["timestamp_dt"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp_dt").reset_index(drop=True)
    df = df.drop(columns=["timestamp_dt"])

    # Persist to disk
    df.to_csv(output_path, index=False)
    logger.info(f"Synthetic training dataset saved successfully to {output_path} ({len(df)} rows)")

    return df


def load_training_data(
    filepath: Optional[Union[str, Path]] = None,
    chunksize: int = config.CSV_CHUNK_SIZE,
) -> pd.DataFrame:
    """
    Load training dataset from CSV using summarized chunked reading.

    If file does not exist, triggers generate_synthetic_data() automatically.

    Args:
        filepath: Path to CSV file. Defaults to config.TRAINING_DATA_PATH.
        chunksize: Number of rows per chunk for memory-efficient loading.

    Returns:
        pd.DataFrame containing full dataset.
    """
    if filepath is None:
        filepath = config.TRAINING_DATA_PATH

    filepath = Path(filepath)

    if not filepath.exists():
        logger.warning(
            f"Training data not found at {filepath}. Generating synthetic prototype dataset..."
        )
        return generate_synthetic_data(output_path=filepath)

    logger.info(f"Loading training data from {filepath} (chunksize={chunksize})...")
    chunks = []
    total_rows = 0

    for chunk in pd.read_csv(filepath, chunksize=chunksize):
        total_rows += len(chunk)
        chunks.append(chunk)

    df = pd.concat(chunks, ignore_index=True)
    logger.info(f"Successfully loaded {total_rows} rows from {filepath}")
    return df


def load_inference_input(input_data: dict) -> pd.DataFrame:
    """
    Convert a single inference request dictionary into a validated DataFrame row.

    Ensures all RAWFEATURE_NAMES are present; unsupplied values are initialized to NaN
    for proper imputation by the trained preprocessor.

    Args:
        input_data: Dictionary containing location and environmental features.

    Returns:
        Single-row pd.DataFrame ready for preprocessing.
    """
    row = {}

    row["latitude"] = float(input_data.get("latitude", 27.5))
    row["longitude"] = float(input_data.get("longitude", 88.5))
    row["timestamp"] = input_data.get("timestamp") or datetime.utcnow().isoformat()

    for feature in config.RAWFEATURE_NAMES:
        val = input_data.get(feature, None)
        if val is not None and feature != "land_cover_class":
            try:
                row[feature] = float(val)
            except (ValueError, TypeError):
                row[feature] = np.nan
        else:
            row[feature] = val

    df = pd.DataFrame([row])
    return df
