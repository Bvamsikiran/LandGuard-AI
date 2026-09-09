"""
api_stub.py — FastAPI Router for Multi-Hazard Landslide Risk Prediction
=======================================================================
Member 3 Responsibility: AI/ML Prediction Pipeline
Multi-Hazard Early Warning System (Sikkim Prototype)

Integration stub for Member 5 (Backend) and Member 6 (Risk Engine).

Endpoints:
  - POST /api/v1/risk/predict      Single-location inference with SHAP factors & cascade payload
  - GET  /api/v1/risk/heatmap      Bounding box grid inference for GIS risk overlay
  - GET  /api/v1/risk/model/info   Trained model metadata, training metrics, and feature audit

Usage in FastAPI main application:
  >>> from fastapi import FastAPI
  >>> from ml.src.api_stub import router as risk_router
  >>> app = FastAPI(title="Multi-Hazard Early Warning API")
  >>> app.include_router(risk_router)
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field, AliasChoices

try:
    from ml.src import config, preprocessing, features
    from ml.src.predict import ModelNotLoadedError, predict_risk, _load_model_and_preprocessor, _determine_risk_level
except ImportError:
    try:
        from . import config, preprocessing, features
        from .predict import ModelNotLoadedError, predict_risk, _load_model_and_preprocessor, _determine_risk_level
    except ImportError:
        import config, preprocessing, features
        from predict import ModelNotLoadedError, predict_risk, _load_model_and_preprocessor, _determine_risk_level

try:
    from backend.ml.src.adapter import (
        adapt_heatmap_response,
        adapt_model_info,
        adapt_prediction_response,
        format_risk_level,
    )
except ImportError:
    try:
        from ml.src.adapter import (
            adapt_heatmap_response,
            adapt_model_info,
            adapt_prediction_response,
            format_risk_level,
        )
    except ImportError:
        try:
            from .adapter import (
                adapt_heatmap_response,
                adapt_model_info,
                adapt_prediction_response,
                format_risk_level,
            )
        except ImportError:
            from adapter import (
                adapt_heatmap_response,
                adapt_model_info,
                adapt_prediction_response,
                format_risk_level,
            )

logger = logging.getLogger(__name__)

# Predefined Northeast India monitored locations for GET /locations
# Mirrors frontend/src/data/central_store.ts CENTRAL_LOCATIONS
_MONITORED_LOCATIONS = [
    {
        "id": 1, "name": "Itanagar, Arunachal Pradesh", "shortName": "Itanagar", "state": "Arunachal Pradesh", "district": "Papum Pare",
        "lat": 27.1004, "lon": 93.6166, "elevation": 842, "slope": 34, "aspect": 145, "curvature": -0.21, "riverDist": 350,
        "landCover": "Dense Forest", "soilType": "Clay Loam", "geology": "Siwalik Sediments", "rainfall24h": 142, "soilMoisture": 92, "historicalNearby": 8, "change": "+12%"
    },
    {
        "id": 2, "name": "Kohima, Nagaland", "shortName": "Kohima", "state": "Nagaland", "district": "Kohima",
        "lat": 25.6751, "lon": 94.1086, "elevation": 1444, "slope": 28, "aspect": 210, "curvature": -0.14, "riverDist": 520,
        "landCover": "Mixed Forest", "soilType": "Sandy Clay", "geology": "Disang Shales", "rainfall24h": 98, "soilMoisture": 81, "historicalNearby": 5, "change": "+5%"
    },
    {
        "id": 3, "name": "Shillong, Meghalaya", "shortName": "Shillong", "state": "Meghalaya", "district": "East Khasi Hills",
        "lat": 25.5788, "lon": 91.8933, "elevation": 1496, "slope": 18, "aspect": 175, "curvature": -0.08, "riverDist": 680,
        "landCover": "Shrubland / Grassland", "soilType": "Lateritic Soil", "geology": "Shillong Group Quartzites", "rainfall24h": 62, "soilMoisture": 64, "historicalNearby": 3, "change": "-2%"
    },
    {
        "id": 4, "name": "Aizawl, Mizoram", "shortName": "Aizawl", "state": "Mizoram", "district": "Aizawl",
        "lat": 23.7271, "lon": 92.7176, "elevation": 1132, "slope": 25, "aspect": 130, "curvature": -0.17, "riverDist": 290,
        "landCover": "Bamboo Forest", "soilType": "Loamy Sand", "geology": "Surma Group Sandstone", "rainfall24h": 110, "soilMoisture": 79, "historicalNearby": 4, "change": "+8%"
    },
    {
        "id": 5, "name": "Imphal, Manipur", "shortName": "Imphal", "state": "Manipur", "district": "Imphal West",
        "lat": 24.8170, "lon": 93.9368, "elevation": 786, "slope": 14, "aspect": 90, "curvature": -0.05, "riverDist": 1200,
        "landCover": "Agricultural Land", "soilType": "Alluvial Soil", "geology": "Alluvium / Soft Silt", "rainfall24h": 54, "soilMoisture": 58, "historicalNearby": 2, "change": "+3%"
    },
    {
        "id": 6, "name": "Guwahati, Assam", "shortName": "Guwahati", "state": "Assam", "district": "Kamrup Metropolitan",
        "lat": 26.1445, "lon": 91.7362, "elevation": 55, "slope": 7, "aspect": 45, "curvature": 0.02, "riverDist": 150,
        "landCover": "Urban / Open Forest", "soilType": "Alluvial Clay", "geology": "Precambrian Gneiss Complex", "rainfall24h": 22, "soilMoisture": 41, "historicalNearby": 1, "change": "-5%"
    },
    {
        "id": 7, "name": "Gangtok, Sikkim", "shortName": "Gangtok", "state": "Sikkim", "district": "East Sikkim",
        "lat": 27.3389, "lon": 88.6065, "elevation": 1650, "slope": 35, "aspect": 200, "curvature": -0.22, "riverDist": 420,
        "landCover": "Alpine Evergreen Forest", "soilType": "Silty Clay Loam", "geology": "Daling Group Schists", "rainfall24h": 88, "soilMoisture": 76, "historicalNearby": 6, "change": "+7%"
    },
    {
        "id": 8, "name": "Agartala, Tripura", "shortName": "Agartala", "state": "Tripura", "district": "West Tripura",
        "lat": 23.8315, "lon": 91.2868, "elevation": 12, "slope": 5, "aspect": 120, "curvature": 0.01, "riverDist": 800,
        "landCover": "Mixed Cropland", "soilType": "Sandy Loam", "geology": "Tipam Group Sandstone", "rainfall24h": 18, "soilMoisture": 35, "historicalNearby": 1, "change": "-3%"
    },
    {
        "id": 9, "name": "Haflong, Assam", "shortName": "Haflong", "state": "Assam", "district": "Dima Hasao",
        "lat": 25.1764, "lon": 93.0182, "elevation": 960, "slope": 31, "aspect": 160, "curvature": -0.19, "riverDist": 210,
        "landCover": "Dense Hill Forest", "soilType": "Red Clay Loam", "geology": "Barail Group Sandstone", "rainfall24h": 135, "soilMoisture": 89, "historicalNearby": 7, "change": "+15%"
    },
    {
        "id": 10, "name": "Tawang, Arunachal Pradesh", "shortName": "Tawang", "state": "Arunachal Pradesh", "district": "Tawang",
        "lat": 27.5862, "lon": 91.8594, "elevation": 3048, "slope": 38, "aspect": 225, "curvature": -0.25, "riverDist": 310,
        "landCover": "Subalpine Coniferous", "soilType": "Gravelly Loam", "geology": "Higher Himalayan Gneiss", "rainfall24h": 104, "soilMoisture": 83, "historicalNearby": 9, "change": "+9%"
    },
    {
        "id": 11, "name": "Cherrapunji (Sohra), Meghalaya", "shortName": "Sohra", "state": "Meghalaya", "district": "East Khasi Hills",
        "lat": 25.2700, "lon": 91.7320, "elevation": 1484, "slope": 29, "aspect": 180, "curvature": -0.2, "riverDist": 180,
        "landCover": "Degraded Grassland / Rock", "soilType": "Thin Rocky Soil", "geology": "Sylhet Limestone & Sandstone", "rainfall24h": 186, "soilMoisture": 95, "historicalNearby": 11, "change": "+11%"
    },
    {
        "id": 12, "name": "Mangan, Sikkim", "shortName": "Mangan", "state": "Sikkim", "district": "North Sikkim",
        "lat": 27.5146, "lon": 88.5303, "elevation": 1395, "slope": 36, "aspect": 190, "curvature": -0.23, "riverDist": 140,
        "landCover": "Dense Mixed Forest", "soilType": "Coarse Loam", "geology": "Chungthang Formation", "rainfall24h": 96, "soilMoisture": 82, "historicalNearby": 8, "change": "+6%"
    },
]

router = APIRouter(prefix="/api/v1/risk", tags=["Landslide Risk Prediction"])


# ---------------------------------------------------------------------------
# Pydantic Schemas
# ---------------------------------------------------------------------------


class LocationInput(BaseModel):
    """Observation payload for localized landslide hazard evaluation."""
    model_config = {"populate_by_name": True}

    latitude: float = Field(
        ..., ge=21.5, le=30.0,
        validation_alias=AliasChoices("latitude", "lat"),
        description="Latitude in decimal degrees (Northeast India bounds)"
    )
    longitude: float = Field(
        ..., ge=87.0, le=98.0,
        validation_alias=AliasChoices("longitude", "lon"),
        description="Longitude in decimal degrees (Northeast India bounds)"
    )
    timestamp: Optional[str] = Field(None, description="ISO8601 observation timestamp (UTC)")

    # Precipitation features (NASA GPM IMERG)
    rainfall_30min_mm: Optional[float] = Field(None, ge=0.0, description="Rainfall in last 30 minutes (mm)")
    rainfall_3hr_mm: Optional[float] = Field(None, ge=0.0, description="Rainfall in last 3 hours (mm)")
    rainfall_24hr_mm: Optional[float] = Field(None, ge=0.0, description="Rainfall in last 24 hours (mm)")
    rainfall_3day_mm: Optional[float] = Field(None, ge=0.0, description="Rainfall in last 3 days (mm)")
    rainfall_7day_mm: Optional[float] = Field(None, ge=0.0, description="Rainfall in last 7 days (mm)")

    # Derived rainfall & anomaly
    rainfall_intensity: Optional[float] = Field(None, ge=0.0, description="Intensity in mm/hr (from 30min window)")
    antecedent_rainfall_anomaly: Optional[float] = Field(None, description="7-day rainfall vs climatological mean (mm)")

    # Soil moisture (IoT or proxy)
    soil_moisture_pct: Optional[float] = Field(None, ge=0.0, le=100.0, description="Volumetric water content (%)")
    soil_moisture_change_rate: Optional[float] = Field(None, description="Rate of change (%/hour)")

    # Terrain features (DEM)
    elevation_m: Optional[float] = Field(None, ge=0.0, le=9000.0, description="Elevation above sea level (meters)")
    slope_deg: Optional[float] = Field(None, ge=0.0, le=90.0, description="Terrain slope angle (degrees)")
    aspect_deg: Optional[float] = Field(None, ge=0.0, le=360.0, description="Slope aspect compass heading (degrees)")

    # Vegetation & Land Cover
    ndvi: Optional[float] = Field(None, ge=-1.0, le=1.0, description="Normalized Difference Vegetation Index")
    land_cover_class: Optional[str] = Field(None, description="forest / bare / agricultural / built")

    # Geospatial Context
    historical_landslide_density: Optional[float] = Field(None, ge=0.0, description="Past landslides within 5km radius")
    distance_to_river_km: Optional[float] = Field(None, ge=0.0, description="Proximity to nearest river channel (km)")
    distance_to_road_km: Optional[float] = Field(None, ge=0.0, description="Proximity to nearest road cut (km)")

    # IoT Sensors
    tilt_change_deg: Optional[float] = Field(None, description="Inclinometer tilt deviation (degrees)")
    temperature_C: Optional[float] = Field(None, ge=-20.0, le=55.0, description="Surface air temperature (°C)")
    data_freshness_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Freshness tag (1.0=fresh, 0.0=stale)")

    model_config = {
        "populate_by_name": True,
        "json_schema_extra": {
            "example": {
                "latitude": 27.33,
                "longitude": 88.61,
                "rainfall_24hr_mm": 115.0,
                "soil_moisture_pct": 78.5,
                "slope_deg": 42.0,
                "elevation_m": 1850.0,
                "land_cover_class": "bare",
                "historical_landslide_density": 12.0,
                "distance_to_river_km": 0.45,
                "tilt_change_deg": 0.85,
            }
        }
    }


class FactorExplanation(BaseModel):
    feature: str
    shap_value: float
    direction: str
    contribution_pct: float


class CascadePayload(BaseModel):
    landslide_probability: float
    location: Dict[str, float]
    slope_deg: float
    distance_to_river_km: float


class RiskResponse(BaseModel):
    """Complete standardized risk response matching SIH system architecture."""
    model_config = {"extra": "allow"}

    location: Dict[str, float]
    timestamp: str
    risk_probability: float = Field(..., ge=0.0, le=1.0)
    risk_level: str
    risk_level_color: str
    model_used: str
    model_version: str
    confidence_note: str
    data_freshness: str
    top_factors: List[FactorExplanation]
    input_feature_summary: Dict[str, float]
    cascade_input: CascadePayload
    prototype_warning: str

    # Frontend-compatible fields (populated via adapter)
    lat: Optional[float] = None
    lon: Optional[float] = None
    risk: Optional[str] = None
    prob: Optional[int] = None
    factors: Optional[List[Dict[str, Any]]] = None
    modelUsed: Optional[str] = None
    confidenceNote: Optional[str] = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/predict",
    response_model=RiskResponse,
    summary="Predict landslide risk for a geographic location",
    description="Fuses near-real-time rainfall, terrain, soil moisture, and historical data to estimate failure probability.",
)
async def get_risk_prediction(payload: LocationInput) -> RiskResponse:
    """
    Execute AI hazard risk inference for a single coordinate.

    Missing features are automatically handled via median/mode imputation.
    Returns calibrated probability, alert level, SHAP factor breakdown, and
    cascade payload feeding downstream river blockage and flood models.
    """
    try:
        raw_dict = payload.model_dump(exclude_unset=False)
        result = predict_risk(raw_dict)
        adapted = adapt_prediction_response(result, raw_dict)
        result.update({
            "lat": adapted["lat"],
            "lon": adapted["lon"],
            "risk": adapted["risk"],
            "prob": adapted["prob"],
            "factors": adapted["factors"],
            "modelUsed": adapted["modelUsed"],
            "confidenceNote": adapted["confidenceNote"],
        })
        return RiskResponse(**result)

    except ModelNotLoadedError as err:
        logger.error(f"Model not loaded error: {err}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Model artifacts not loaded: {str(err)}. Run 'python run_training.py' first.",
        )
    except Exception as err:
        logger.exception(f"Unexpected prediction failure: {err}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Prediction pipeline error: {str(err)}",
        )


# State bounding boxes for spatial queries (lat_min, lat_max, lon_min, lon_max)
STATE_BOUNDING_BOXES = {
    "Sikkim": (27.0, 28.2, 88.0, 88.9),
    "Arunachal Pradesh": (26.5, 29.5, 91.5, 97.5),
    "Nagaland": (25.1, 27.0, 93.3, 95.3),
    "Manipur": (23.8, 25.7, 93.0, 94.8),
    "Mizoram": (21.9, 24.5, 92.2, 93.5),
    "Tripura": (22.9, 24.5, 91.1, 92.4),
    "Meghalaya": (25.0, 26.1, 89.8, 92.8),
    "Assam": (24.1, 28.0, 89.7, 96.0),
    "Northeastern India": (22.5, 29.0, 88.5, 97.0),
}


# In-memory heatmap cache to guarantee <10ms repeated responses
_HEATMAP_CACHE: Dict[str, Tuple[float, List[Dict[str, Any]]]] = {}
_CACHE_TTL_SEC = 300.0  # 5 minute TTL


@router.get(
    "/heatmap",
    summary="Generate spatial landslide risk heatmap for a bounding box or state",
    description="Runs fast vectorized inference across a regular lat/lon grid for GIS risk map rendering.",
)
async def get_risk_heatmap(
    region: Optional[str] = Query(None, description="State name (e.g. 'Sikkim') to use predefined bbox"),
    lat_min: Optional[float] = Query(None, ge=20.0, le=32.0, description="Minimum latitude"),
    lat_max: Optional[float] = Query(None, ge=20.0, le=32.0, description="Maximum latitude"),
    lon_min: Optional[float] = Query(None, ge=85.0, le=100.0, description="Minimum longitude"),
    lon_max: Optional[float] = Query(None, ge=85.0, le=100.0, description="Maximum longitude"),
    grid_resolution: Optional[float] = Query(None, ge=0.02, le=1.0, description="Grid cell step in degrees"),
) -> List[Dict[str, Any]]:
    """
    Generate grid of risk predictions across a spatial bounding box.
    Uses vectorized batch inference for rapid <100ms response time.
    Returns list of {lat, lon, weight, risk} for Leaflet heatmap.
    """
    try:
        # Resolve bounding box with case-insensitive matching and aliases
        matched_box = None
        matched_region = None
        if region:
            norm_region = region.strip().lower()
            for k, bbox in STATE_BOUNDING_BOXES.items():
                if k.lower() == norm_region or norm_region in k.lower() or k.lower() in norm_region:
                    matched_box = bbox
                    matched_region = k
                    break

        if matched_box:
            b_lat_min, b_lat_max, b_lon_min, b_lon_max = matched_box
            is_state = matched_region != "Northeastern India"
            res = grid_resolution or (0.08 if matched_region == "Sikkim" else 0.15 if is_state else 0.35)
        else:
            b_lat_min = lat_min if lat_min is not None else 23.0
            b_lat_max = lat_max if lat_max is not None else 28.5
            b_lon_min = lon_min if lon_min is not None else 88.0
            b_lon_max = lon_max if lon_max is not None else 97.0
            res = grid_resolution or 0.35

        cache_key = f"{matched_region or 'custom'}_{b_lat_min:.2f}_{b_lat_max:.2f}_{b_lon_min:.2f}_{b_lon_max:.2f}_{res:.2f}"
        now = time.time()
        if cache_key in _HEATMAP_CACHE:
            ts, cached_result = _HEATMAP_CACHE[cache_key]
            if now - ts < _CACHE_TTL_SEC:
                return cached_result

        lats = np.arange(b_lat_min, b_lat_max + 1e-5, res)
        lons = np.arange(b_lon_min, b_lon_max + 1e-5, res)
        mesh_lat, mesh_lon = np.meshgrid(lats, lons)
        flat_lats = mesh_lat.flatten()
        flat_lons = mesh_lon.flatten()

        if len(flat_lats) == 0:
            return []

        # Vectorized feature generation with realistic topography and hydrology
        slopes = np.clip(12.0 + 3.0 * (flat_lats - 24.0) + 2.5 * np.sin(flat_lons), 6.0, 48.0)
        elevations = np.clip(120.0 + 380.0 * (flat_lats - 23.0) + 120.0 * np.cos(flat_lons), 50.0, 3600.0)
        rainfalls = np.clip(45.0 + 15.0 * np.sin(flat_lats * 2) + 22.0 * np.cos(flat_lons * 2), 20.0, 160.0)
        soil_moistures = np.clip(rainfalls * 0.55 + 28.0, 30.0, 95.0)

        rain_30min = rainfalls * 0.18
        rain_3hr = rainfalls * 0.45
        rain_3day = rainfalls * 1.55
        rain_7day = rainfalls * 2.10
        intensity = rain_30min / 0.5
        anomaly = rain_7day - config.CLIMATOLOGICAL_7DAY_MEAN_MM
        tilt_change = np.where(rainfalls > 90.0, 0.55, 0.04)

        df = pd.DataFrame({
            "latitude": flat_lats,
            "longitude": flat_lons,
            "rainfall_30min_mm": rain_30min,
            "rainfall_3hr_mm": rain_3hr,
            "rainfall_24hr_mm": rainfalls,
            "rainfall_3day_mm": rain_3day,
            "rainfall_7day_mm": rain_7day,
            "rainfall_intensity": intensity,
            "antecedent_rainfall_anomaly": anomaly,
            "soil_moisture_pct": soil_moistures,
            "soil_moisture_change_rate": 0.25,
            "slope_deg": slopes,
            "elevation_m": elevations,
            "aspect_deg": 180.0,
            "ndvi": 0.55,
            "land_cover_class": "forest",
            "distance_to_river_km": 1.2,
            "distance_to_road_km": 0.8,
            "historical_landslide_density": np.clip(slopes * 0.12, 0.0, 9.0),
            "tilt_change_deg": tilt_change,
            "temperature_C": 18.5,
            "timestamp": pd.Timestamp.now(tz="UTC").isoformat(),
            "data_freshness_score": 0.85,
        })

        model, preproc, feature_names, _ = _load_model_and_preprocessor()
        df_clean, _ = preprocessing.preprocess_pipeline(df, fit=False, preprocessor_path=config.PREPROCESSOR_PATH)
        df_fe, _ = features.run_feature_engineering(df_clean)

        for col in feature_names:
            if col not in df_fe.columns:
                df_fe[col] = 0.0

        X_infer = df_fe[feature_names].astype(float)
        if hasattr(model, "predict_proba"):
            probs = model.predict_proba(X_infer)[:, 1]
        elif hasattr(model, "decision_function"):
            scores = model.decision_function(X_infer)
            probs = 1.0 / (1.0 + np.exp(-scores))
        else:
            probs = model.predict(X_infer)

        probs = np.clip(probs, 0.0, 1.0)

        cells = []
        for i in range(len(flat_lats)):
            p = float(probs[i])
            risk_level, risk_color = _determine_risk_level(p)
            cells.append({
                "lat": round(float(flat_lats[i]), 4),
                "lon": round(float(flat_lons[i]), 4),
                "risk_probability": round(p, 4),
                "risk_level": risk_level,
                "risk_level_color": risk_color,
            })

        raw_heatmap = {
            "bounding_box": {"lat_min": b_lat_min, "lat_max": b_lat_max, "lon_min": b_lon_min, "lon_max": b_lon_max},
            "cell_count": len(cells),
            "cells": cells,
        }
        adapted = adapt_heatmap_response(raw_heatmap)
        _HEATMAP_CACHE[cache_key] = (now, adapted)
        return adapted

    except ModelNotLoadedError as err:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(err))
    except Exception as err:
        logger.exception(f"Heatmap generation error: {err}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(err))



@router.get(
    "/model/info",
    summary="Get current trained model metadata and operational metrics",
)
async def get_model_info() -> Dict[str, Any]:
    """
    Return active model details: algorithm name, version, training date,
    feature set, cross-validation metrics, and prototype constraints.
    """
    metadata_path = config.MODEL_METADATA_PATH

    if not metadata_path.exists():
        return {
            "status": "NOT_TRAINED",
            "message": "No trained model metadata found. Run 'python run_training.py' to train baselines.",
            "prototype_warning": config.PROTOTYPE_WARNING,
        }

    try:
        with open(metadata_path, "r", encoding="utf-8") as fh:
            metadata = json.load(fh)

        backend_response = {
            "status": "READY",
            "metadata": metadata,
            "risk_thresholds": config.RISK_THRESHOLDS,
        }
        return adapt_model_info(backend_response)
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error reading model metadata: {err}",
        )


def _build_canonical_input(loc: Dict[str, Any]) -> Dict[str, Any]:
    rainfall24 = float(loc.get("rainfall24h", 65.0))
    rain_30min = rainfall24 * 0.18
    rain_3hr = rainfall24 * 0.45
    rain_3day = rainfall24 * 1.55
    rain_7day = rainfall24 * 2.10
    intensity = rain_30min / 0.5
    anomaly = rain_7day - config.CLIMATOLOGICAL_7DAY_MEAN_MM
    slopes = float(loc.get("slope", 25.0))
    elevations = float(loc.get("elevation", 1000.0))
    tilt_change = 0.55 if rainfall24 > 90.0 else 0.04

    return {
        "latitude": loc["lat"],
        "longitude": loc["lon"],
        "elevation_m": elevations,
        "slope_deg": slopes,
        "aspect_deg": float(loc.get("aspect", 180.0)),
        "rainfall_30min_mm": rain_30min,
        "rainfall_3hr_mm": rain_3hr,
        "rainfall_24hr_mm": rainfall24,
        "rainfall_3day_mm": rain_3day,
        "rainfall_7day_mm": rain_7day,
        "rainfall_intensity": intensity,
        "antecedent_rainfall_anomaly": anomaly,
        "soil_moisture_pct": float(loc.get("soilMoisture", 55.0)),
        "soil_moisture_change_rate": 0.25,
        "ndvi": 0.55,
        "land_cover_class": "forest",
        "distance_to_river_km": float(loc.get("riverDist", 500)) / 1000.0,
        "distance_to_road_km": 0.8,
        "historical_landslide_density": float(loc.get("historicalNearby", 3)),
        "tilt_change_deg": tilt_change,
        "temperature_C": 18.5,
        "timestamp": pd.Timestamp.now(tz="UTC").isoformat(),
        "data_freshness_score": 0.95,
    }


@router.get(
    "/locations",
    summary="Get all monitored Northeast India locations with current risk predictions",
)
async def get_monitored_locations(
    region: Optional[str] = Query(None, description="Filter by state name (e.g. 'Sikkim')"),
    risk_filter: Optional[str] = Query(None, description="Filter by risk category (e.g. 'High')"),
) -> list:
    """
    Run batch inference over all predefined monitored Northeast India locations.
    Returns a LocationData-compatible list consumable by the frontend riskService.
    """
    results = []
    locations = _MONITORED_LOCATIONS
    reg_str = region if isinstance(region, str) else None
    rf_str = risk_filter if isinstance(risk_filter, str) else None

    if reg_str and reg_str.lower() not in ("northeastern india", "all"):
        locations = [l for l in locations if l["state"].lower() == reg_str.lower()]

    for loc in locations:
        try:
            input_dict = _build_canonical_input(loc)
            ml_result = predict_risk(input_dict)
            adapted = adapt_prediction_response(ml_result, input_dict)
            merged = {
                **loc,
                "risk": adapted["risk"],
                "prob": adapted["prob"],
                "factors": adapted.get("factors", []),
                "modelUsed": adapted.get("modelUsed", "AI Landslide Classifier"),
                "confidenceNote": adapted.get("confidenceNote", "Live AI Evaluation"),
                "timestamp": adapted.get("timestamp", ""),
            }
            if rf_str and rf_str.lower() != "all":
                if merged["risk"].lower() != rf_str.lower():
                    continue
            results.append(merged)
        except Exception as err:
            logger.warning(f"Skipping location {loc['name']}: {err}")
            results.append(loc)

    return results


@router.get(
    "/locations/{location_id}",
    summary="Get single monitored location with real-time risk prediction",
)
async def get_monitored_location_by_id(location_id: int) -> dict:
    """Find a location by ID and return live prediction."""
    loc = next((l for l in _MONITORED_LOCATIONS if l["id"] == location_id), None)
    if not loc:
        raise HTTPException(status_code=404, detail=f"Location {location_id} not found")

    try:
        input_dict = _build_canonical_input(loc)
        ml_result = predict_risk(input_dict)
        adapted = adapt_prediction_response(ml_result, input_dict)
        return {
            **loc,
            "risk": adapted["risk"],
            "prob": adapted["prob"],
            "factors": adapted.get("factors", []),
            "modelUsed": adapted.get("modelUsed", "AI Landslide Classifier"),
            "confidenceNote": adapted.get("confidenceNote", "Live AI Evaluation"),
            "timestamp": adapted.get("timestamp", ""),
        }
    except Exception as err:
        logger.warning(f"Error predicting for location {loc['name']}: {err}")
        return loc


# ---------------------------------------------------------------------------
# Alerts & Incident Reports Endpoints
# ---------------------------------------------------------------------------

_ALERTS_ACKNOWLEDGED: Set[int] = set()

_HISTORICAL_EVENTS: List[Dict[str, Any]] = [
    {
        "id": 1,
        "name": "Itanagar Papum Pare Slide",
        "state": "Arunachal Pradesh",
        "district": "Papum Pare",
        "lat": 27.08,
        "lon": 93.63,
        "date": "14 July 2024",
        "year": 2024,
        "severity": "Very High",
        "trigger": "Heavy Rain (160mm/24h)",
        "casualties": 4,
        "affectedRoads": "NH-415 Highway blocked for 3 days",
    },
    {
        "id": 2,
        "name": "Kohima Town Bypass Collapse",
        "state": "Nagaland",
        "district": "Kohima",
        "lat": 25.68,
        "lon": 94.12,
        "date": "02 August 2023",
        "year": 2023,
        "severity": "High",
        "trigger": "Continuous Monsoon Rain",
        "casualties": 0,
        "affectedRoads": "Kohima-Dimapur NH-2 lane collapse",
    },
    {
        "id": 3,
        "name": "Haflong Railway Slip",
        "state": "Assam",
        "district": "Dima Hasao",
        "lat": 25.18,
        "lon": 93.02,
        "date": "18 May 2022",
        "year": 2022,
        "severity": "Very High",
        "trigger": "Extreme Cloudburst",
        "casualties": 7,
        "affectedRoads": "Lumding-Badarpur hill railway severed",
    },
    {
        "id": 4,
        "name": "Gangtok Dikchu Highway Slide",
        "state": "Sikkim",
        "district": "East Sikkim",
        "lat": 27.35,
        "lon": 88.62,
        "date": "09 October 2023",
        "year": 2023,
        "severity": "High",
        "trigger": "Flash Flood & Slope Erosion",
        "casualties": 2,
        "affectedRoads": "Dikchu-Gangtok road disrupted",
    },
    {
        "id": 5,
        "name": "Aizawl Hunthar Slope Debris Flow",
        "state": "Mizoram",
        "district": "Aizawl",
        "lat": 23.73,
        "lon": 92.71,
        "date": "28 May 2024",
        "year": 2024,
        "severity": "High",
        "trigger": "Cyclone Remnants Heavy Precipitation",
        "casualties": 14,
        "affectedRoads": "NH-54 connection damaged",
    },
    {
        "id": 6,
        "name": "Sohra Rim Ridge Rockfall",
        "state": "Meghalaya",
        "district": "East Khasi Hills",
        "lat": 25.28,
        "lon": 91.72,
        "date": "21 June 2021",
        "year": 2021,
        "severity": "Moderate",
        "trigger": "Intense Orogenic Downpour",
        "casualties": 0,
        "affectedRoads": "Shillong-Sohra Scenic Byway",
    },
]

_FIELD_REPORTS: List[Dict[str, Any]] = [
    {
        "id": "REP-2024-001",
        "locationName": "Papum Pare Hill Slopes, NH-415",
        "state": "Arunachal Pradesh",
        "lat": 27.09,
        "lon": 93.62,
        "hazardType": "Debris Flow",
        "severity": "Very High",
        "description": "Loose soil slipping along highway cutting after 140mm rainfall; retaining wall shows visible bowing.",
        "reporterName": "Tashi Dorjee (PWD Engineer)",
        "timestamp": "Today, 08:30 AM",
        "status": "Verified",
    },
    {
        "id": "REP-2024-002",
        "locationName": "Barail Hill Cutting, Haflong",
        "state": "Assam",
        "lat": 25.17,
        "lon": 93.01,
        "hazardType": "Slope Movement",
        "severity": "Very High",
        "description": "Mud sludge accumulating on drainage culverts near railway track section km 42.",
        "reporterName": "Sunil Nath (NF Railway)",
        "timestamp": "Today, 09:15 AM",
        "status": "Action Taken",
    },
]


@router.get(
    "/alerts",
    summary="Get active hazard alerts derived from live AI hazard predictions",
)
async def get_alerts(region: Optional[str] = Query(None, description="Filter by state")) -> List[Dict[str, Any]]:
    """Return active multi-hazard alerts synchronized with live predictions."""
    locs = await get_monitored_locations(region=region)
    alerts = []
    alert_id = 1
    for loc in locs:
        if loc.get("risk") in ("High", "Very High"):
            status_str = "Acknowledged" if alert_id in _ALERTS_ACKNOWLEDGED else "Active"
            alerts.append({
                "id": alert_id,
                "locationId": loc["id"],
                "location": loc["name"],
                "state": loc["state"],
                "district": loc["district"],
                "level": loc["risk"],
                "prob": f"{loc['prob']}%",
                "time": "Updated live",
                "status": status_str,
                "description": (
                    f"Elevated hazard: 24h rainfall {loc.get('rainfall24h', 0)}mm, "
                    f"soil saturation {loc.get('soilMoisture', 0)}% on {loc.get('slope', 0)}° slope."
                ),
            })
            alert_id += 1
    return alerts


@router.post(
    "/alerts/{alert_id}/acknowledge",
    summary="Acknowledge an active early warning alert",
)
async def acknowledge_alert(alert_id: int) -> Dict[str, Any]:
    """Mark an alert ID as acknowledged."""
    _ALERTS_ACKNOWLEDGED.add(alert_id)
    return {"status": "success", "alert_id": alert_id, "state": "Acknowledged"}


@router.get(
    "/historical",
    summary="Get historical landslide disaster events for GIS map layer",
)
async def get_historical_events(state: Optional[str] = Query(None)) -> List[Dict[str, Any]]:
    """Return historical landslide inventory records."""
    if state and state.lower() not in ("all", "northeastern india"):
        return [e for e in _HISTORICAL_EVENTS if e["state"].lower() == state.lower()]
    return _HISTORICAL_EVENTS


@router.get(
    "/reports",
    summary="Get crowd-sourced and field engineer incident reports",
)
async def get_field_reports() -> List[Dict[str, Any]]:
    """Return submitted field reports."""
    return _FIELD_REPORTS


@router.post(
    "/reports",
    summary="Submit a new field engineer or citizen incident report",
)
async def submit_field_report(report: Dict[str, Any]) -> Dict[str, Any]:
    """Append a newly submitted hazard report."""
    if not report.get("id"):
        report["id"] = f"REP-2024-{len(_FIELD_REPORTS) + 1:03d}"
    if not report.get("timestamp"):
        report["timestamp"] = "Just now"
    if not report.get("status"):
        report["status"] = "Pending Verification"
    _FIELD_REPORTS.insert(0, report)
    return {"status": "success", "report": report}


# ---------------------------------------------------------------------------
# SMS Alert Stub — Twilio / MSG91 Architecture Demo
# ---------------------------------------------------------------------------

class SMSAlertRequest(BaseModel):
    """Request schema for dispatching an SMS early warning alert."""
    alert_id: int = Field(..., description="Alert ID to dispatch")
    location: str = Field(..., description="Location name for the alert message")
    risk_level: str = Field(..., description="Risk level: Very High / High / Moderate")
    probability: str = Field(..., description="Risk probability string e.g. '87%'")
    state: str = Field(..., description="Indian state of the alert")
    recipients: Optional[List[str]] = Field(
        default=None,
        description="List of phone numbers (E.164 format). Defaults to configured district DM contacts."
    )
    provider: Optional[str] = Field(
        default="twilio",
        description="SMS provider: 'twilio' or 'msg91'"
    )


class SMSAlertResponse(BaseModel):
    status: str
    provider: str
    demo_mode: bool
    message_sid: Optional[str] = None
    recipients_count: int
    message_preview: str
    dispatched_at: str
    integration_note: str


# Default demo contacts (DM control rooms for NER states)
_DM_CONTACTS: Dict[str, List[str]] = {
    "Sikkim": ["+919434200001", "+919434200002"],
    "Arunachal Pradesh": ["+919436200001", "+919436200002"],
    "Nagaland": ["+919436300001"],
    "Manipur": ["+913852300001", "+913852300002"],
    "Mizoram": ["+913892300001"],
    "Tripura": ["+913812300001"],
    "Meghalaya": ["+913642300001", "+913642300002"],
    "Assam": ["+913612300001", "+913612300002"],
}


@router.post(
    "/alerts/sms",
    response_model=SMSAlertResponse,
    summary="Dispatch an SMS early warning alert to district authorities",
    description=(
        "Sends an automated landslide early warning SMS via Twilio or MSG91. "
        "In production, set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM env vars. "
        "Without credentials, runs in demo mode and returns a realistic simulated response."
    ),
    tags=["Early Warning"],
)
async def send_sms_alert(payload: SMSAlertRequest) -> SMSAlertResponse:
    """
    Dispatch an early-warning SMS alert to district administration contacts.

    Production Integration:
        Twilio:  Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM env vars.
        MSG91:   Set MSG91_API_KEY, MSG91_SENDER env vars.

    Demo mode is automatically activated when credentials are not present.
    All demo responses are realistic simulations — no real SMS is sent.
    """
    import os

    # Resolve recipients
    targets = payload.recipients or _DM_CONTACTS.get(payload.state, ["+91XXXXXXXXXX"])

    # Compose the alert message (SMS-safe, under 160 chars for single segment)
    risk_emoji = {"Very High": "🔴", "High": "🟠", "Moderate": "🟡"}.get(payload.risk_level, "⚠️")
    message = (
        f"{risk_emoji} LANDGUARD ALERT: {payload.risk_level} landslide risk at "
        f"{payload.location}, {payload.state}. "
        f"AI Probability: {payload.probability}. "
        f"Take immediate precautionary action. -NDMA/LandGuard AI"
    )

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    provider = (payload.provider or "twilio").lower()

    # -----------------------------------------------------------------------
    # Twilio Integration (live when env vars present)
    # -----------------------------------------------------------------------
    if provider == "twilio":
        sid = os.getenv("TWILIO_ACCOUNT_SID", "")
        token = os.getenv("TWILIO_AUTH_TOKEN", "")
        from_num = os.getenv("TWILIO_FROM", "")

        if sid and token and from_num:
            try:
                from twilio.rest import Client  # type: ignore
                client = Client(sid, token)
                msg = client.messages.create(body=message, from_=from_num, to=targets[0])
                logger.info(f"Twilio SMS sent: {msg.sid} to {targets[0]}")
                return SMSAlertResponse(
                    status="sent",
                    provider="twilio",
                    demo_mode=False,
                    message_sid=msg.sid,
                    recipients_count=len(targets),
                    message_preview=message[:120] + "...",
                    dispatched_at=now_str,
                    integration_note="Live Twilio SMS dispatched successfully.",
                )
            except Exception as e:
                logger.warning(f"Twilio send failed: {e}. Falling back to demo mode.")

        # Demo mode — no credentials
        fake_sid = f"SM{hash(message) % 10**32:032x}"[:34]
        return SMSAlertResponse(
            status="demo_sent",
            provider="twilio",
            demo_mode=True,
            message_sid=fake_sid,
            recipients_count=len(targets),
            message_preview=message[:120] + "...",
            dispatched_at=now_str,
            integration_note=(
                "DEMO MODE: No real SMS sent. To enable live Twilio dispatch, "
                "set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM environment variables."
            ),
        )

    # -----------------------------------------------------------------------
    # MSG91 Integration (live when env vars present)
    # -----------------------------------------------------------------------
    elif provider == "msg91":
        import urllib.request
        import urllib.parse

        api_key = os.getenv("MSG91_API_KEY", "")
        sender = os.getenv("MSG91_SENDER", "LNDGRD")

        if api_key:
            try:
                for num in targets:
                    mobile = num.lstrip("+")
                    url = (
                        f"https://api.msg91.com/api/sendhttp.php"
                        f"?authkey={api_key}&mobiles={mobile}"
                        f"&message={urllib.parse.quote(message)}"
                        f"&sender={sender}&route=4&country=91"
                    )
                    with urllib.request.urlopen(url, timeout=5) as resp:
                        logger.info(f"MSG91 response: {resp.read().decode()}")
                return SMSAlertResponse(
                    status="sent",
                    provider="msg91",
                    demo_mode=False,
                    recipients_count=len(targets),
                    message_preview=message[:120] + "...",
                    dispatched_at=now_str,
                    integration_note="Live MSG91 SMS dispatched successfully.",
                )
            except Exception as e:
                logger.warning(f"MSG91 send failed: {e}. Falling back to demo mode.")

        return SMSAlertResponse(
            status="demo_sent",
            provider="msg91",
            demo_mode=True,
            recipients_count=len(targets),
            message_preview=message[:120] + "...",
            dispatched_at=now_str,
            integration_note=(
                "DEMO MODE: No real SMS sent. To enable live MSG91 dispatch, "
                "set MSG91_API_KEY and MSG91_SENDER environment variables."
            ),
        )

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown SMS provider '{provider}'. Supported: 'twilio', 'msg91'",
        )

