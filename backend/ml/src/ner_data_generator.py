"""
ner_data_generator.py — Multi-State NER Synthetic Training Data Generator
==========================================================================
Generates terrain-accurate synthetic landslide data for all 8 Northeast
Indian states with state-specific geological, climatic, and topographic profiles.

State Profiles:
  - Sikkim          : Himalayan glacial terrain, very steep, extreme rainfall
  - Arunachal Pradesh: Eastern Himalaya, dense forest, high elevation, remote
  - Nagaland        : Naga Hills, moderate slopes, erosion-prone clay soils
  - Manipur         : Manipur Hills + valley, variable slope, Barak basin
  - Mizoram         : Lushai Hills, very steep parallel ridges, moderate rain
  - Tripura         : Low hill ranges, moderate slope, heavy monsoon flooding
  - Meghalaya       : Khasi & Jaintia Hills, highest rainfall on Earth (Mawsynram)
  - Assam           : Largely floodplains + Karbi Anglong hills, low slope

Usage:
    python -m ml.src.ner_data_generator
    # or from project root:
    python backend/ml/src/ner_data_generator.py
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional

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

# ---------------------------------------------------------------------------
# Per-State Terrain & Climate Profiles
# Each profile controls the statistical distributions used to generate
# realistic synthetic data for positive (landslide) and negative (stable) rows.
# ---------------------------------------------------------------------------

NER_STATE_PROFILES: Dict[str, dict] = {
    "Sikkim": {
        "lat_range": (27.0, 28.1),
        "lon_range": (88.0, 89.0),
        "samples": 1000,
        "positive_rate": 0.12,          # 12% — highest risk state
        "climatological_baseline_mm": 80.0,
        # Positive (landslide) terrain params
        "pos_slope_mean": 40.0,
        "pos_slope_std": 8.0,
        "pos_elevation_range": (800, 4500),
        "pos_rain_24hr_min": 80.0,
        "pos_rain_24hr_max": 480.0,
        "pos_soil_moisture_range": (62, 98),
        "pos_ndvi_beta": (2, 5),
        # Negative (stable) terrain params
        "neg_slope_gamma": (2.5, 7.0),
        "neg_slope_max": 42.0,
        "neg_elevation_range": (300, 5500),
        "neg_rain_24hr_max": 120.0,
        "description": "Eastern Himalaya — glacial terrain, extreme orographic rainfall",
    },
    "Arunachal Pradesh": {
        "lat_range": (26.5, 29.5),
        "lon_range": (91.5, 97.5),
        "samples": 1500,
        "positive_rate": 0.10,
        "climatological_baseline_mm": 75.0,
        "pos_slope_mean": 36.0,
        "pos_slope_std": 9.0,
        "pos_elevation_range": (500, 4000),
        "pos_rain_24hr_min": 70.0,
        "pos_rain_24hr_max": 400.0,
        "pos_soil_moisture_range": (58, 95),
        "pos_ndvi_beta": (2, 4),
        "neg_slope_gamma": (2.0, 8.0),
        "neg_slope_max": 38.0,
        "neg_elevation_range": (200, 4500),
        "neg_rain_24hr_max": 100.0,
        "description": "Eastern Himalaya — remote, dense forest, large river gorges",
    },
    "Nagaland": {
        "lat_range": (25.1, 27.0),
        "lon_range": (93.3, 95.3),
        "samples": 800,
        "positive_rate": 0.08,
        "climatological_baseline_mm": 55.0,
        "pos_slope_mean": 30.0,
        "pos_slope_std": 7.0,
        "pos_elevation_range": (400, 2500),
        "pos_rain_24hr_min": 60.0,
        "pos_rain_24hr_max": 280.0,
        "pos_soil_moisture_range": (55, 90),
        "pos_ndvi_beta": (3, 4),
        "neg_slope_gamma": (2.0, 6.5),
        "neg_slope_max": 35.0,
        "neg_elevation_range": (200, 3000),
        "neg_rain_24hr_max": 90.0,
        "description": "Naga Hills — moderate slopes, clay-rich soils prone to slip",
    },
    "Manipur": {
        "lat_range": (23.8, 25.7),
        "lon_range": (93.0, 94.8),
        "samples": 800,
        "positive_rate": 0.07,
        "climatological_baseline_mm": 50.0,
        "pos_slope_mean": 28.0,
        "pos_slope_std": 8.0,
        "pos_elevation_range": (800, 2800),
        "pos_rain_24hr_min": 55.0,
        "pos_rain_24hr_max": 260.0,
        "pos_soil_moisture_range": (52, 88),
        "pos_ndvi_beta": (3, 4),
        "neg_slope_gamma": (2.0, 6.0),
        "neg_slope_max": 30.0,
        "neg_elevation_range": (780, 3000),
        "neg_rain_24hr_max": 85.0,
        "description": "Manipur Hills + Imphal Valley — variable slope, road-cut failures common",
    },
    "Mizoram": {
        "lat_range": (21.9, 24.5),
        "lon_range": (92.2, 93.5),
        "samples": 700,
        "positive_rate": 0.09,
        "climatological_baseline_mm": 65.0,
        "pos_slope_mean": 35.0,
        "pos_slope_std": 7.5,
        "pos_elevation_range": (400, 2100),
        "pos_rain_24hr_min": 65.0,
        "pos_rain_24hr_max": 320.0,
        "pos_soil_moisture_range": (58, 92),
        "pos_ndvi_beta": (2, 4),
        "neg_slope_gamma": (2.5, 7.0),
        "neg_slope_max": 38.0,
        "neg_elevation_range": (200, 2200),
        "neg_rain_24hr_max": 95.0,
        "description": "Lushai Hills — steep parallel ridges, high slope failures along NH-54",
    },
    "Tripura": {
        "lat_range": (22.9, 24.5),
        "lon_range": (91.1, 92.4),
        "samples": 600,
        "positive_rate": 0.05,
        "climatological_baseline_mm": 45.0,
        "pos_slope_mean": 20.0,
        "pos_slope_std": 6.0,
        "pos_elevation_range": (200, 900),
        "pos_rain_24hr_min": 45.0,
        "pos_rain_24hr_max": 200.0,
        "pos_soil_moisture_range": (48, 82),
        "pos_ndvi_beta": (4, 3),
        "neg_slope_gamma": (1.5, 5.0),
        "neg_slope_max": 22.0,
        "neg_elevation_range": (5, 1000),
        "neg_rain_24hr_max": 70.0,
        "description": "Low hill ranges — moderate landslide risk, heavy monsoon & flooding",
    },
    "Meghalaya": {
        "lat_range": (25.0, 26.1),
        "lon_range": (89.8, 92.8),
        "samples": 900,
        "positive_rate": 0.11,          # High — world's highest rainfall (Mawsynram)
        "climatological_baseline_mm": 120.0,
        "pos_slope_mean": 33.0,
        "pos_slope_std": 7.0,
        "pos_elevation_range": (400, 1900),
        "pos_rain_24hr_min": 90.0,
        "pos_rain_24hr_max": 500.0,     # Mawsynram extreme events
        "pos_soil_moisture_range": (65, 99),
        "pos_ndvi_beta": (3, 4),
        "neg_slope_gamma": (2.0, 6.0),
        "neg_slope_max": 35.0,
        "neg_elevation_range": (100, 2000),
        "neg_rain_24hr_max": 140.0,     # Even negatives see high rainfall here
        "description": "Khasi & Jaintia Hills — highest rainfall on Earth, karst terrain",
    },
    "Assam": {
        "lat_range": (24.1, 28.0),
        "lon_range": (89.7, 96.0),
        "samples": 700,
        "positive_rate": 0.04,          # Lower — mostly floodplains
        "climatological_baseline_mm": 40.0,
        "pos_slope_mean": 15.0,
        "pos_slope_std": 5.0,
        "pos_elevation_range": (50, 1200),  # Karbi Anglong hills
        "pos_rain_24hr_min": 40.0,
        "pos_rain_24hr_max": 160.0,
        "pos_soil_moisture_range": (45, 80),
        "pos_ndvi_beta": (4, 3),
        "neg_slope_gamma": (1.0, 4.0),
        "neg_slope_max": 18.0,
        "neg_elevation_range": (28, 1500),
        "neg_rain_24hr_max": 60.0,
        "description": "Brahmaputra floodplains + Karbi Anglong — low slope, flood-dominated risk",
    },
}


def _generate_state_samples(
    state: str,
    profile: dict,
    rng: np.random.Generator,
) -> pd.DataFrame:
    """
    Generate synthetic landslide data rows for a single NER state.

    Args:
        state: State name string.
        profile: State-specific terrain & climate profile dict.
        rng: NumPy random generator for reproducibility.

    Returns:
        pd.DataFrame with labelled rows for the given state.
    """
    n_samples = profile["samples"]
    pos_rate = profile["positive_rate"]
    n_positives = max(10, int(n_samples * pos_rate))
    n_negatives = n_samples - n_positives
    baseline = profile.get("climatological_baseline_mm", 80.0)

    # -------------------------------------------------------------------------
    # 1. POSITIVE SAMPLES (Landslide Events = 1)
    # -------------------------------------------------------------------------
    # Rainfall cascade (correlated windows)
    p_r30 = rng.gamma(shape=3.5, scale=8.0, size=n_positives) + 5.0
    p_r30 = np.clip(p_r30, 5.0, 120.0)
    p_r3h = p_r30 * rng.uniform(2.5, 4.5, n_positives) + rng.normal(15, 5, n_positives)
    p_r3h = np.clip(p_r3h, p_r30, 260.0)

    rain_min = profile["pos_rain_24hr_min"]
    rain_max = profile["pos_rain_24hr_max"]
    p_r24 = rng.uniform(rain_min, rain_max, size=n_positives)
    p_r24 = np.maximum(p_r24, p_r3h)

    p_r3d = p_r24 * rng.uniform(1.3, 2.2, n_positives) + rng.normal(30, 15, n_positives)
    p_r3d = np.clip(p_r3d, p_r24, 520.0)
    p_r7d = p_r3d * rng.uniform(1.2, 1.8, n_positives) + rng.normal(40, 20, n_positives)
    p_r7d = np.clip(p_r7d, p_r3d, 560.0)

    p_intensity = p_r30 / 0.5
    p_anomaly = p_r7d - baseline

    # Soil
    sm_lo, sm_hi = profile["pos_soil_moisture_range"]
    p_sm = rng.uniform(sm_lo, sm_hi, size=n_positives)
    p_sm_rate = rng.normal(3.5, 1.5, n_positives).clip(0.5, 15.0)

    # Terrain
    p_slope = rng.normal(profile["pos_slope_mean"], profile["pos_slope_std"], n_positives)
    p_slope = np.clip(p_slope, 12.0, 80.0)
    elev_lo, elev_hi = profile["pos_elevation_range"]
    p_elevation = rng.uniform(elev_lo, elev_hi, size=n_positives)
    p_aspect = rng.uniform(0.0, 360.0, size=n_positives)

    # Vegetation
    a, b = profile["pos_ndvi_beta"]
    p_ndvi = rng.beta(a, b, size=n_positives) * 0.5 + 0.05

    # Land cover (bare & built more likely on landslide rows)
    p_lc = rng.choice(
        config.LAND_COVER_CLASSES, size=n_positives, p=[0.20, 0.45, 0.25, 0.10]
    )

    # Historical density (higher near active slopes)
    p_hist = rng.negative_binomial(n=3, p=0.2, size=n_positives) + 3.0
    p_hist = np.clip(p_hist, 1.0, 60.0)

    p_dist_river = rng.exponential(1.5, n_positives).clip(0.05, 15.0) + 0.1
    p_dist_road = rng.exponential(1.2, n_positives).clip(0.02, 10.0) + 0.05
    p_tilt = (rng.exponential(1.2, n_positives) + 0.4).clip(0.3, 8.5)
    p_temp = rng.normal(18.0, 5.0, n_positives).clip(0.0, 35.0)
    p_fresh = rng.choice([1.0, 0.7, 0.4], n_positives, p=[0.75, 0.20, 0.05])

    # -------------------------------------------------------------------------
    # 2. NEGATIVE SAMPLES (Stable = 0)
    # -------------------------------------------------------------------------
    n_r30 = rng.exponential(1.8, n_negatives).clip(0.0, 25.0)
    n_r3h = (n_r30 * rng.uniform(1.2, 2.5, n_negatives) + rng.exponential(3.0, n_negatives)).clip(n_r30, 60.0)
    n_r24 = (n_r3h * rng.uniform(1.5, 3.0, n_negatives) + rng.exponential(8.0, n_negatives)).clip(n_r3h, profile["neg_rain_24hr_max"])
    n_r3d = (n_r24 * rng.uniform(1.1, 1.8, n_negatives) + rng.exponential(12.0, n_negatives)).clip(n_r24, profile["neg_rain_24hr_max"] * 1.8)
    n_r7d = (n_r3d * rng.uniform(1.1, 1.5, n_negatives) + rng.exponential(15.0, n_negatives)).clip(n_r3d, profile["neg_rain_24hr_max"] * 2.2)

    n_intensity = n_r30 / 0.5
    n_anomaly = n_r7d - baseline

    n_sm = rng.beta(3, 4, n_negatives) * 50.0 + 8.0
    n_sm = np.clip(n_sm, 5.0, 62.0)
    n_sm_rate = rng.normal(-0.1, 0.6, n_negatives).clip(-3.0, 1.2)

    g_shape, g_scale = profile["neg_slope_gamma"]
    n_slope = rng.gamma(g_shape, g_scale, n_negatives).clip(0.0, profile["neg_slope_max"])
    elev_lo2, elev_hi2 = profile["neg_elevation_range"]
    n_elevation = rng.uniform(elev_lo2, elev_hi2, n_negatives)
    n_aspect = rng.uniform(0.0, 360.0, n_negatives)

    n_ndvi = rng.beta(5, 2, n_negatives) * 0.6 + 0.3
    n_ndvi = np.clip(n_ndvi, 0.20, 0.90)

    n_lc = rng.choice(
        config.LAND_COVER_CLASSES, size=n_negatives, p=[0.65, 0.08, 0.20, 0.07]
    )

    n_hist = rng.poisson(0.8, n_negatives).astype(float)
    n_dist_river = rng.uniform(0.2, 25.0, n_negatives)
    n_dist_road = rng.uniform(0.1, 20.0, n_negatives)
    n_tilt = rng.normal(0.02, 0.08, n_negatives).clip(-0.25, 0.35)
    n_temp = rng.normal(16.0, 6.5, n_negatives).clip(-5.0, 38.0)
    n_fresh = rng.choice([1.0, 0.7, 0.4, 0.0], n_negatives, p=[0.70, 0.20, 0.07, 0.03])

    # -------------------------------------------------------------------------
    # 3. Combine into DataFrame
    # -------------------------------------------------------------------------
    data = {
        "rainfall_30min_mm": np.concatenate([p_r30, n_r30]),
        "rainfall_3hr_mm": np.concatenate([p_r3h, n_r3h]),
        "rainfall_24hr_mm": np.concatenate([p_r24, n_r24]),
        "rainfall_3day_mm": np.concatenate([p_r3d, n_r3d]),
        "rainfall_7day_mm": np.concatenate([p_r7d, n_r7d]),
        "rainfall_intensity": np.concatenate([p_intensity, n_intensity]),
        "antecedent_rainfall_anomaly": np.concatenate([p_anomaly, n_anomaly]),
        "soil_moisture_pct": np.concatenate([p_sm, n_sm]),
        "soil_moisture_change_rate": np.concatenate([p_sm_rate, n_sm_rate]),
        "elevation_m": np.concatenate([p_elevation, n_elevation]),
        "slope_deg": np.concatenate([p_slope, n_slope]),
        "aspect_deg": np.concatenate([p_aspect, n_aspect]),
        "ndvi": np.concatenate([p_ndvi, n_ndvi]),
        "land_cover_class": np.concatenate([p_lc, n_lc]),
        "historical_landslide_density": np.concatenate([p_hist, n_hist]),
        "distance_to_river_km": np.concatenate([p_dist_river, n_dist_river]),
        "distance_to_road_km": np.concatenate([p_dist_road, n_dist_road]),
        "tilt_change_deg": np.concatenate([p_tilt, n_tilt]),
        "temperature_C": np.concatenate([p_temp, n_temp]),
        "data_freshness_score": np.concatenate([p_fresh, n_fresh]),
        config.TARGET_COLUMN: np.concatenate([
            np.ones(n_positives, dtype=int),
            np.zeros(n_negatives, dtype=int),
        ]),
    }

    df = pd.DataFrame(data)

    # State coordinates
    lat_lo, lat_hi = profile["lat_range"]
    lon_lo, lon_hi = profile["lon_range"]
    df["latitude"] = rng.uniform(lat_lo, lat_hi, size=n_samples)
    df["longitude"] = rng.uniform(lon_lo, lon_hi, size=n_samples)
    df["state"] = state

    # Timestamps 2018-2026 with monsoon clustering (Jun-Sep heavier)
    start_dt = datetime(2018, 1, 1)
    total_days = (datetime(2026, 9, 1) - start_dt).days
    random_days = rng.integers(0, total_days, size=n_samples)
    random_hours = rng.integers(0, 24, size=n_samples)
    df["timestamp"] = [
        (start_dt + timedelta(days=int(d), hours=int(h))).isoformat()
        for d, h in zip(random_days, random_hours)
    ]

    # Inject ~7% missing values in numerical columns (sensor gaps)
    num_cols = [c for c in config.NUMERICAL_FEATURES if c in df.columns]
    missing_frac = getattr(config, "MISSING_VALUE_FRACTION", 0.07)
    for col in num_cols:
        mask = rng.random(size=n_samples) < missing_frac
        df.loc[mask, col] = np.nan

    return df


def generate_ner_wide_data(
    output_path: Optional[str] = None,
    random_state: int = 42,
    overwrite: bool = False,
) -> pd.DataFrame:
    """
    Generate synthetic training data for all 8 NER states and save as CSV.

    Total rows: ~7,000 across 8 states with state-appropriate terrain/climate profiles.

    Args:
        output_path: CSV destination. Defaults to config.TRAINING_DATA_PATH.
        random_state: Seed for reproducibility.
        overwrite: If False, skips generation if file already exists.

    Returns:
        Combined pd.DataFrame with a 'state' column.
    """
    if output_path is None:
        output_path = str(config.TRAINING_DATA_PATH)

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    if out.exists() and not overwrite:
        logger.info(
            f"NER data file already exists at {out}. "
            "Pass overwrite=True to regenerate. Loading existing file."
        )
        return pd.read_csv(out)

    rng = np.random.default_rng(random_state)
    all_frames = []

    total_positive = 0
    total_samples = 0

    for state, profile in NER_STATE_PROFILES.items():
        logger.info(
            f"  Generating {profile['samples']} rows for {state} "
            f"({profile['positive_rate']*100:.0f}% positive rate) — {profile['description']}"
        )
        state_df = _generate_state_samples(state, profile, rng)
        n_pos = int(state_df[config.TARGET_COLUMN].sum())
        total_positive += n_pos
        total_samples += len(state_df)
        logger.info(f"    → {len(state_df)} rows | {n_pos} positives")
        all_frames.append(state_df)

    df = pd.concat(all_frames, ignore_index=True)

    # Chronological sort for temporal split integrity
    df["_ts"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("_ts").reset_index(drop=True)
    df = df.drop(columns=["_ts"])

    df.to_csv(out, index=False)

    pos_rate = total_positive / total_samples * 100
    logger.info(
        f"\n✅ NER-wide dataset saved to {out}\n"
        f"   Total rows    : {total_samples:,}\n"
        f"   Total positives: {total_positive:,} ({pos_rate:.1f}%)\n"
        f"   States covered : {list(NER_STATE_PROFILES.keys())}\n"
    )

    return df


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    print("\nLandGuard AI -- NER Multi-State Training Data Generator")
    print("=" * 60)
    print("Generating terrain-accurate synthetic data for all 8 NER states...\n")

    df = generate_ner_wide_data(overwrite=True)

    print("\n[Dataset Summary by State]:")
    print("-" * 55)
    summary = (
        df.groupby("state")
        .agg(
            total_rows=("state", "count"),
            positives=(config.TARGET_COLUMN, "sum"),
            pos_rate=(config.TARGET_COLUMN, "mean"),
            avg_slope=("slope_deg", "mean"),
            avg_rainfall_24h=("rainfall_24hr_mm", "mean"),
        )
        .round(2)
    )
    summary["pos_rate"] = (summary["pos_rate"] * 100).round(1).astype(str) + "%"
    print(summary.to_string())
    print("\nDone. Run 'python run_training.py' to retrain the model on NER-wide data.")
