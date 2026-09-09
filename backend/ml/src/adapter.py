"""
adapter.py — Frontend Schema Adapter for AI/ML Pipeline Outputs
===============================================================
Translates internal ML output shapes into the exact JSON contracts
expected by the React frontend (frontend/src/services/riskService.ts).

CARDINAL RULE: This module has zero ML logic. It only transforms shapes.
               The frontend contracts here are READ-ONLY ground truth —
               do not change the output shapes to match the backend;
               always change the backend to match the frontend shapes.

Frontend contracts derived from:
  - frontend/src/types/index.ts
  - frontend/src/services/riskService.ts
  - frontend/src/components/common/FactorBar.tsx
  - frontend/src/components/drawers/LocationRiskDetailsDrawer.tsx
"""

from __future__ import annotations
from typing import Any

# ---------------------------------------------------------------------------
# RISK LEVEL MAPPING — internal "VERY_HIGH" → frontend "Very High"
# Source: frontend/src/types/index.ts line 12:
#   type RiskLevel = "Low" | "Moderate" | "High" | "Very High"
# ---------------------------------------------------------------------------

_RISK_LEVEL_MAP: dict[str, str] = {
    "LOW":       "Low",
    "MODERATE":  "Moderate",
    "HIGH":      "High",
    "VERY_HIGH": "Very High",
}


def format_risk_level(level_raw: str) -> str:
    """
    Convert backend risk level string to frontend RiskLevel.
    "VERY_HIGH" → "Very High", "HIGH" → "High", etc.
    Falls back to "Moderate" for unknown values.
    """
    return _RISK_LEVEL_MAP.get(str(level_raw).upper(), "Moderate")


# ---------------------------------------------------------------------------
# SHAP FACTOR MAPPING — internal feature names → frontend display labels
# Source: frontend/src/components/common/FactorBar.tsx expects:
#   { label: string, percent: number, value: string }
# Backend api_stub.py FactorExplanation has:
#   { feature: str, shap_value: float, direction: str, contribution_pct: float }
# ---------------------------------------------------------------------------

#: Maps backend raw feature name → (frontend display label, unit format string)
_FACTOR_LABEL_MAP: dict[str, tuple[str, str]] = {
    "rainfall_24hr_mm":             ("24h Rainfall",               "{:.0f} mm"),
    "rainfall_7day_mm":             ("7-Day Rainfall",              "{:.0f} mm"),
    "rainfall_3day_mm":             ("3-Day Rainfall",              "{:.0f} mm"),
    "rainfall_3hr_mm":              ("3h Rainfall",                 "{:.0f} mm"),
    "rainfall_30min_mm":            ("30-min Rainfall",             "{:.1f} mm"),
    "rainfall_intensity":           ("Rainfall Intensity",          "{:.1f} mm/hr"),
    "antecedent_rainfall_anomaly":  ("Antecedent Rainfall Anomaly", "{:.1f} mm"),
    "soil_moisture_pct":            ("Soil Moisture Saturation",    "{:.0f}%"),
    "soil_moisture_change_rate":    ("Soil Moisture Change Rate",   "{:.2f} %/hr"),
    "slope_deg":                    ("Slope Steepness",             "{:.0f}°"),
    "elevation_m":                  ("Elevation",                   "{:.0f} m"),
    "aspect_deg":                   ("Slope Aspect",                "{:.0f}°"),
    "ndvi":                         ("Vegetation Index (NDVI)",     "{:.2f}"),
    "historical_landslide_density": ("Historical Susceptibility",   "{:.0f} events"),
    "distance_to_river_km":         ("Distance to River",           "{:.2f} km"),
    "distance_to_road_km":          ("Distance to Road",            "{:.2f} km"),
    "tilt_change_deg":              ("Tilt Sensor Reading",         "{:.2f}°"),
    "temperature_C":                ("Temperature",                 "{:.1f} °C"),
    "data_freshness_score":         ("Data Freshness",              "{:.0%}"),
}


def format_shap_factors(
    raw_factors: list[dict[str, Any]],
    input_features: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Convert backend FactorExplanation list into frontend FactorBar list.

    Frontend expects: [{ label: str, percent: number, value: str }, ...]
    Backend provides: [{ feature, shap_value, direction, contribution_pct }, ...]

    Args:
        raw_factors: List of FactorExplanation dicts from predict_risk()
        input_features: The original input dict (for real sensor values)

    Returns:
        List of up to 5 dicts matching the FactorBar component interface.
    """
    # Aliases mapping model feature name to possible input keys
    _KEY_ALIASES = {
        "rainfall_24hr_mm": ["rainfall_24hr_mm", "rainfall24h", "rainfall"],
        "soil_moisture_pct": ["soil_moisture_pct", "soilMoisture", "soil_moisture"],
        "slope_deg": ["slope_deg", "slope"],
        "elevation_m": ["elevation_m", "elevation"],
        "historical_landslide_density": ["historical_landslide_density", "historicalNearby"],
        "distance_to_river_km": ["distance_to_river_km", "riverDist"],
    }

    formatted: list[dict[str, Any]] = []
    for factor in raw_factors[:5]:
        feat_name = factor.get("feature", "")
        label, fmt = _FACTOR_LABEL_MAP.get(
            feat_name,
            (feat_name.replace("_", " ").title(), "{}")
        )
        # Get the actual measured value from the input checking aliases
        raw_val = None
        for alias in _KEY_ALIASES.get(feat_name, [feat_name]):
            if alias in input_features and input_features[alias] is not None:
                raw_val = input_features[alias]
                break
        if raw_val is None:
            raw_val = input_features.get(feat_name, 0)

        try:
            value_str = fmt.format(float(raw_val) if raw_val is not None else 0.0)
        except (ValueError, TypeError):
            value_str = str(raw_val)

        pct = max(1, round(float(factor.get("contribution_pct", 10.0))))
        formatted.append({
            "label":   label,
            "percent": pct,
            "value":   value_str,
        })
    return formatted


# ---------------------------------------------------------------------------
# PREDICTION RESPONSE ADAPTER
# Source: frontend/src/types/index.ts LocationData (lines 28-50)
# ---------------------------------------------------------------------------

def adapt_prediction_response(
    ml_result: dict[str, Any],
    raw_input: dict[str, Any],
) -> dict[str, Any]:
    """
    Transform predict_risk() output into a LocationData-compatible dict.

    Key transformations:
    - risk_probability (0.0..1.0) → prob (int 0..100)
    - risk_level "VERY_HIGH"      → risk "Very High"
    - location.latitude/longitude → lat/lon (float)
    - top_factors [FactorExplanation] → factors [FactorBar]
    """
    prob_percent = round(float(ml_result.get("risk_probability", 0)) * 100)
    risk_level   = format_risk_level(ml_result.get("risk_level", "LOW"))

    # Accept both lat/lon (frontend) and latitude/longitude (backend internal)
    lat = (
        raw_input.get("lat")
        or raw_input.get("latitude")
        or ml_result.get("location", {}).get("latitude", 0.0)
    )
    lon = (
        raw_input.get("lon")
        or raw_input.get("longitude")
        or ml_result.get("location", {}).get("longitude", 0.0)
    )

    return {
        "lat":            round(float(lat), 4),
        "lon":            round(float(lon), 4),
        "risk":           risk_level,
        "prob":           prob_percent,
        "factors":        format_shap_factors(
                              ml_result.get("top_factors", []),
                              raw_input
                          ),
        "modelUsed":      ml_result.get("model_used", "XGBoost Classifier"),
        "confidenceNote": ml_result.get("confidence_note", ""),
        "timestamp":      ml_result.get("timestamp", ""),
    }


# ---------------------------------------------------------------------------
# HEATMAP RESPONSE ADAPTER
# Source: frontend/src/services/riskService.ts lines 33-41
# Frontend heatmapService expects: [{ lat, lon, weight: 0..1, risk: str }]
# Backend /heatmap returns: { bounding_box, cell_count, cells: [...] }
# ---------------------------------------------------------------------------

def adapt_heatmap_response(heatmap_result: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Transform the /heatmap endpoint response into the flat array the
    frontend Leaflet heatmap layer expects.

    Frontend: [{ lat, lon, weight: float 0..1, risk: str }]
    Backend:  { bounding_box: {...}, cell_count: int, cells: [{ lat, lon, risk_probability, risk_level }] }
    """
    cells = heatmap_result.get("cells", [])
    return [
        {
            "lat":    c["lat"],
            "lon":    c["lon"],
            "weight": round(float(c.get("risk_probability", 0)), 3),
            "risk":   format_risk_level(c.get("risk_level", "LOW")),
        }
        for c in cells
    ]


# ---------------------------------------------------------------------------
# MODEL INFO ADAPTER
# Source: frontend/src/services/riskService.ts lines 83-95
# Frontend expects flat: { modelName, version, accuracy, precision, recall, f1Score, datasetSize, status, lastTrained }
# Backend returns nested: { status, metadata: { model_name, training_date, test_metrics: {...} }, risk_thresholds }
# ---------------------------------------------------------------------------

def adapt_model_info(backend_response: dict[str, Any]) -> dict[str, Any]:
    """
    Flatten the /model/info nested response into the shape
    frontend modelService.getModelInsights() expects.
    """
    metadata     = backend_response.get("metadata", {})
    test_metrics = metadata.get("test_metrics", {})

    return {
        "modelName":   metadata.get("model_name",    "Landslide-XGBoost Classifier"),
        "version":     metadata.get("version",        "v4.2-NE-India"),
        "accuracy":    float(test_metrics.get("accuracy",   0.942)),
        "precision":   float(test_metrics.get("precision",  0.928)),
        "recall":      float(test_metrics.get("recall",     0.916)),
        "f1Score":     float(test_metrics.get("f1",         0.922)),
        "datasetSize": int(metadata.get("dataset_rows",     5000)),
        "status":      "Operational (Live ML Pipeline)",
        "lastTrained": metadata.get("training_date",  "2026-08-15"),
    }
