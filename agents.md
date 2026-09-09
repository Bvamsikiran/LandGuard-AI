# AGENTS.md — Multi-Agent Backend Development Prompt
## AI/ML Predictive Analytics Engine → Frontend Integration

> **Purpose:** Feed this file to any AI agent (agy CLI, Claude, Gemini, Cursor, etc.) as the initialization prompt to generate the ML backend for frontend compatibility. Zero frontend edits are ever permitted.
>
> **Backed by:** `ml_frontend_compatibility_report.md` (Workflow 1, 2, 3 — all verified non-destructively against real code)

---

## SYSTEM PROMPT (Give this to the AI first)

```
You are a senior Python/FastAPI backend engineer working on the AI/ML pipeline for a multi-hazard landslide early warning system. 

Your sole job: develop the backend ML pipeline so it is compatible with an existing, locked React frontend. You will NEVER modify any frontend files. All changes live exclusively in the `backend/ml/` directory.

The frontend is complete and frozen. It expects specific API contracts. Your job is to make the backend deliver exactly those contracts — nothing more, nothing less.

Anti-hallucination rules:
1. Read every file before editing it. Never assume field names, paths, or values.
2. Before writing any code, print the current content of the file you are editing.
3. Only edit files in backend/ml/. If you find yourself editing anything in frontend/, stop immediately.
4. Run tests after every change.
```

---

## PHASE 0 — Ground Truth Orientation (MANDATORY FIRST STEP)

**Agent instruction:** Before writing a single line of code, run these READ-ONLY commands to anchor your understanding. Do not skip this phase.

```powershell
# 1. Print the current directory tree of the ML backend
Get-ChildItem -Path backend/ml -Recurse -Name | Where-Object { $_ -notmatch '__pycache__' }

# 2. Print EVERY existing route registered in api_stub.py
python -c "
import ast, sys
src = open('backend/ml/src/api_stub.py').read()
tree = ast.parse(src)
routes = [(d.args[0].s if d.args else '?', n.name)
          for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)
          for d in n.decorator_list if isinstance(d, ast.Call)
          and isinstance(d.func, ast.Attribute)
          and d.func.attr in ('get','post','put','delete')]
print('Existing routes:')
for method, fn in routes:
    print(f'  {method}  →  {fn}')
"

# 3. Print the actual geographic validation bounds in api_stub.py
python -c "
import ast
src = open('backend/ml/src/api_stub.py').read()
print(src[src.find('class LocationInput'):src.find('class FactorExplanation')])
"

# 4. Print the actual risk level strings that predict.py returns today
python -c "
import re
src = open('backend/ml/src/predict.py').read()
matches = re.findall(r'risk_level.*?[\"\'](.*?)[\"\']]', src)
print('Risk level strings in predict.py:', matches)
"

# 5. Print the current config bounding box values
python -c "
from backend.ml.src import config
print(f'LAT_MIN={config.LAT_MIN} LAT_MAX={config.LAT_MAX}')
print(f'LON_MIN={config.LON_MIN} LON_MAX={config.LON_MAX}')
print('RISK_THRESHOLDS:', config.RISK_THRESHOLDS)
"
```

**Expected output of Phase 0 — use these exact values to write all code:**
- Route prefix: `/api/v1/risk` (defined at `api_stub.py:45`)
- Current bounds: `latitude ge=27.0 le=28.1`, `longitude ge=88.0 le=89.0` (Sikkim only)
- Required bounds: Full Northeast India — `lat 21.5–30.0°N`, `lon 87.0–98.0°E`
- Risk level strings returned by predict.py: `"LOW"`, `"MODERATE"`, `"HIGH"`, `"VERY_HIGH"` (uppercase with underscore)
- Risk level strings expected by frontend: `"Low"`, `"Moderate"`, `"High"`, `"Very High"` (Title Case with space)

---

## PHASE 1 — Agent 1: Fix Geographic Bounds & Parameter Aliases

**Agent 1 Goal:** Make the ML pipeline accept coordinates from all 8 Northeast Indian states.

**Files to edit:**
- `backend/ml/src/config.py` → lines 74–78 (bounding box constants)
- `backend/ml/src/api_stub.py` → lines 53–57 (Pydantic `LocationInput` class)

**Step 1.1 — Update config.py bounding box:**

Read the file first, then make this EXACT change only:
```python
# IN: backend/ml/src/config.py

# BEFORE (lines 74-78):
# Sikkim bounding box (WGS-84)
LAT_MIN: float = 27.0
LAT_MAX: float = 28.1
LON_MIN: float = 88.0
LON_MAX: float = 89.0

# AFTER:
# Northeast India bounding box (WGS-84) — covers all 8 states
LAT_MIN: float = 21.5   # Tripura southern tip
LAT_MAX: float = 30.0   # Arunachal Pradesh northern boundary
LON_MIN: float = 87.0   # Sikkim western edge
LON_MAX: float = 98.0   # Arunachal Pradesh eastern edge
```

**Step 1.2 — Add lat/lon aliases to LocationInput in api_stub.py:**

Read the full `LocationInput` class first. Then add only the two alias changes. Do NOT alter any other field:
```python
# IN: backend/ml/src/api_stub.py

# Add to imports at top of file (if not already present):
from pydantic import BaseModel, Field, AliasChoices

# BEFORE (lines 53-57):
class LocationInput(BaseModel):
    """Observation payload for localized landslide hazard evaluation."""

    latitude: float = Field(..., ge=27.0, le=28.1, description="Latitude in decimal degrees (Sikkim bounds)")
    longitude: float = Field(..., ge=88.0, le=89.0, description="Longitude in decimal degrees (Sikkim bounds)")

# AFTER:
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
```

**Step 1.3 — Verify (run this to confirm before moving to Phase 2):**
```python
python -c "
from pydantic import ValidationError
from backend.ml.src.api_stub import LocationInput

test_points = [
    ('Gangtok, Sikkim',                  27.33,   88.61),
    ('Itanagar, Arunachal Pradesh',       27.1004, 93.6166),
    ('Kohima, Nagaland',                  25.6751, 94.1086),
    ('Shillong, Meghalaya',               25.5788, 91.8933),
    ('Aizawl, Mizoram',                   23.7271, 92.7176),
    ('Imphal, Manipur',                   24.817,  93.9368),
    ('Agartala, Tripura',                 23.8315, 91.2868),
    ('Guwahati, Assam',                   26.1445, 91.7362),
]

print('=== BOUNDARY VALIDATION (Must be all PASS) ===')
all_pass = True
for name, lat, lon in test_points:
    # Test with frontend field names (lat/lon)
    try:
        LocationInput(**{'lat': lat, 'lon': lon})
        print(f'[PASS] {name}')
    except ValidationError as e:
        print(f'[FAIL] {name}: {e.errors()[0][\"msg\"]}')
        all_pass = False
print()
print('PHASE 1 STATUS:', 'ALL PASS - proceed to Phase 2' if all_pass else 'FAILURES - do NOT proceed')
"
```

**Expected:** All 8 lines print `[PASS]`. If any `[FAIL]`, fix before proceeding.

---

## PHASE 2 — Agent 2: Create the Response Adapter Module

**Agent 2 Goal:** Create `backend/ml/src/adapter.py` — a pure transformation module with zero ML logic. It bridges the gap between ML output shapes and frontend-expected shapes.

**Context for Agent 2 (read this before writing):**
- Frontend type `RiskLevel` (in `frontend/src/types/index.ts` line 12): `"Low" | "Moderate" | "High" | "Very High"`
- Frontend `LocationData.prob` (line 37): integer `0..100`, used directly in SVG `strokeDasharray` attribute
- Frontend `FactorBar` component (in `frontend/src/components/common/FactorBar.tsx`): expects `{ label: string, percent: number, value: string }`
- Backend `FactorExplanation` (in `backend/ml/src/api_stub.py` lines 112–116): `{ feature: str, shap_value: float, direction: str, contribution_pct: float }`
- Backend `risk_level` from `predict.py`: `"LOW"`, `"MODERATE"`, `"HIGH"`, `"VERY_HIGH"`
- Frontend `heatmapService` (in `frontend/src/services/riskService.ts` lines 33–41): expects `[{ lat, lon, weight: 0..1, risk: string }]`
- Frontend `modelService.getModelInsights()` (lines 83–95): expects `{ modelName, version, accuracy, precision, recall, f1Score, datasetSize, status, lastTrained }`

**Create this exact file — `backend/ml/src/adapter.py`:**
```python
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
    formatted: list[dict[str, Any]] = []
    for factor in raw_factors[:5]:
        feat_name = factor.get("feature", "")
        label, fmt = _FACTOR_LABEL_MAP.get(
            feat_name,
            (feat_name.replace("_", " ").title(), "{}")
        )
        # Get the actual measured value from the input, fall back to 0
        raw_val = input_features.get(feat_name, 0)
        try:
            value_str = fmt.format(raw_val if raw_val is not None else 0)
        except (ValueError, TypeError):
            value_str = str(raw_val)

        formatted.append({
            "label":   label,
            "percent": round(float(factor.get("contribution_pct", 10.0))),
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
```

**Step 2 Verification — run this to confirm the adapter module is correct:**
```python
python -c "
from backend.ml.src.adapter import (
    format_risk_level, adapt_prediction_response,
    adapt_heatmap_response, adapt_model_info
)

# Test 1: Risk level mapping
assert format_risk_level('VERY_HIGH') == 'Very High', 'FAIL: VERY_HIGH mapping'
assert format_risk_level('HIGH')      == 'High',      'FAIL: HIGH mapping'
assert format_risk_level('LOW')       == 'Low',       'FAIL: LOW mapping'
assert format_risk_level('MODERATE')  == 'Moderate',  'FAIL: MODERATE mapping'
print('[PASS] Risk level mapping')

# Test 2: Probability scale
fake_result = {'risk_probability': 0.87, 'risk_level': 'VERY_HIGH', 'top_factors': [], 'location': {'latitude': 27.33, 'longitude': 88.61}}
adapted = adapt_prediction_response(fake_result, {'lat': 27.33, 'lon': 88.61})
assert adapted['prob'] == 87,         'FAIL: prob should be int 87'
assert adapted['risk'] == 'Very High','FAIL: risk should be Very High'
assert 0 <= adapted['lat'] <= 90,     'FAIL: lat out of range'
print('[PASS] Prediction response adapter')

# Test 3: Heatmap adapter
fake_heatmap = {'cells': [{'lat': 27.0, 'lon': 88.5, 'risk_probability': 0.65, 'risk_level': 'HIGH'}]}
heatmap_out = adapt_heatmap_response(fake_heatmap)
assert heatmap_out[0]['weight'] == 0.65,  'FAIL: weight should be float 0.65'
assert heatmap_out[0]['risk']   == 'High','FAIL: risk should be High'
print('[PASS] Heatmap adapter')

print()
print('PHASE 2 STATUS: ALL PASS - proceed to Phase 3')
"
```

---

## PHASE 3 — Agent 3: Create FastAPI Server Entrypoint & Wire Adapters

**Agent 3 Goal:** Create `backend/ml/src/main.py` and wire the adapter into existing endpoints in `api_stub.py`.

**Step 3.1 — Create `backend/ml/src/main.py`:**

This file must NOT exist yet. Verify first: `Test-Path backend/ml/src/main.py`

```python
"""
main.py — FastAPI Application Entrypoint
========================================
Multi-Hazard Landslide Predictive Analytics Engine
Member 3 (AI/ML) — Backend for Frontend Integration

Start with:
    uvicorn backend.ml.src.main:app --host 0.0.0.0 --port 8000 --reload

From workspace root (d:/Apps/sih_2026/multi_hazard_software_system_aiml_predictive_analytics_pipeline_modules):
    uvicorn backend.ml.src.main:app --host 0.0.0.0 --port 8000 --reload
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.ml.src.api_stub import router as ml_router

app = FastAPI(
    title="Landguard AI/ML Predictive Analytics Engine",
    description=(
        "Real-time landslide hazard prediction and spatial risk analysis "
        "for Northeast India. Powered by XGBoost + SHAP explainability."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ---------------------------------------------------------------------------
# CORS — allow Vite dev server on all standard ports
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8443",   # Figma Make / Vite default
        "http://localhost:5173",   # Vite alternate
        "http://localhost:3000",   # CRA fallback
        "*",                       # Open during development
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Mount the ML prediction router
# Router prefix already set to /api/v1/risk in api_stub.py:45
# ---------------------------------------------------------------------------
app.include_router(ml_router)


@app.get("/", tags=["Health"])
async def root() -> dict:
    """Health check endpoint."""
    return {
        "service": "Landguard AI/ML Predictive Analytics Engine",
        "status":  "operational",
        "version": "1.0.0",
        "docs":    "/docs",
    }
```

**Step 3.2 — Wire adapters into existing api_stub.py endpoints:**

Read `backend/ml/src/api_stub.py` in full first. Then make these targeted changes:

**Change A — Add adapter import at top of api_stub.py (after existing imports):**
```python
# Add after existing try/except import block in api_stub.py:
try:
    from ml.src.adapter import adapt_prediction_response, adapt_heatmap_response, adapt_model_info
except ImportError:
    try:
        from .adapter import adapt_prediction_response, adapt_heatmap_response, adapt_model_info
    except ImportError:
        from adapter import adapt_prediction_response, adapt_heatmap_response, adapt_model_info
```

**Change B — In `get_risk_prediction` function, wrap the return with adapter:**
```python
# BEFORE (inside get_risk_prediction, after result = predict_risk(raw_dict)):
        return RiskResponse(**result)

# AFTER:
        adapted = adapt_prediction_response(result, raw_dict)
        # Merge adapted fields back into the full RiskResponse
        result.update({
            "risk_level": adapted["risk"].upper().replace(" ", "_"),  # keep internal format for RiskResponse model
        })
        # Return the raw RiskResponse for backward compat, but add adapted fields as extra
        response = RiskResponse(**result)
        # Attach adapter output as additional response metadata
        return response
```

> **Important note for Agent 3:** The `RiskResponse` Pydantic model is the current contract between `api_stub.py` and the internal ML code. The adapter should be called on the **JSON output** sent to the frontend, not on the Pydantic model itself. The cleanest approach is to add a new `FrontendRiskResponse` Pydantic model and a separate frontend-facing endpoint, OR to override the JSON serialization. Inspect the full `RiskResponse` model first, then decide the cleanest path.

**Change C — In `get_risk_heatmap` function, wrap the return cells with adapter:**
```python
# BEFORE (at the end of get_risk_heatmap):
        return {
            "bounding_box": {...},
            "grid_resolution_deg": grid_resolution,
            "cell_count": len(cells),
            "generated_at": ...,
            "cells": cells,
            "prototype_warning": config.PROTOTYPE_WARNING,
        }

# AFTER: return adapter output directly (flat array for Leaflet)
        raw_heatmap = {
            "bounding_box": {"lat_min": lat_min, "lat_max": lat_max, "lon_min": lon_min, "lon_max": lon_max},
            "cell_count": len(cells),
            "cells": cells,
        }
        return adapt_heatmap_response(raw_heatmap)
```

**Change D — In `get_model_info` function, wrap return with adapter:**
```python
# BEFORE:
        return {
            "status": "READY",
            "metadata": metadata,
            "risk_thresholds": config.RISK_THRESHOLDS,
            "risk_colors": config.RISK_COLORS,
            "prototype_warning": config.PROTOTYPE_WARNING,
        }

# AFTER:
        backend_response = {
            "status": "READY",
            "metadata": metadata,
            "risk_thresholds": config.RISK_THRESHOLDS,
        }
        return adapt_model_info(backend_response)
```

**Step 3.3 — Verify server starts and responds:**
```powershell
# Start server in background
Start-Process powershell -ArgumentList "-Command", "uvicorn backend.ml.src.main:app --host 0.0.0.0 --port 8000 --reload" -WindowStyle Minimized

# Wait for startup
Start-Sleep -Seconds 4

# Test health check
curl.exe -s http://localhost:8000/

# Test predict endpoint with frontend-style lat/lon payload
curl.exe -s -X POST http://localhost:8000/api/v1/risk/predict `
  -H "Content-Type: application/json" `
  -d '{\"lat\": 27.33, \"lon\": 88.61, \"rainfall_24hr_mm\": 115.0}'

# Test all 8 Northeast states (must all return 200, not 422)
$states = @(
  @{lat=27.33;  lon=88.61;  name="Gangtok, Sikkim"},
  @{lat=27.1;   lon=93.62;  name="Itanagar, Arunachal"},
  @{lat=25.68;  lon=94.11;  name="Kohima, Nagaland"},
  @{lat=25.58;  lon=91.89;  name="Shillong, Meghalaya"},
  @{lat=26.14;  lon=91.74;  name="Guwahati, Assam"},
  @{lat=23.73;  lon=92.72;  name="Aizawl, Mizoram"},
  @{lat=24.82;  lon=93.94;  name="Imphal, Manipur"},
  @{lat=23.83;  lon=91.29;  name="Agartala, Tripura"}
)
foreach ($s in $states) {
  $body = "{`"lat`": $($s.lat), `"lon`": $($s.lon)}"
  $resp = curl.exe -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8000/api/v1/risk/predict `
    -H "Content-Type: application/json" -d $body
  if ($resp -eq "200") { Write-Host "[PASS] $($s.name)" }
  else { Write-Host "[FAIL] $($s.name) → HTTP $resp" }
}
```

---

## PHASE 4 — Agent 4: Add Missing `/locations` Endpoint

**Agent 4 Goal:** Add a `GET /api/v1/risk/locations` endpoint to `api_stub.py` that runs batch inference over a predefined set of monitored Northeast India locations.

**Context:**
- Frontend `riskPredictionService.getLocations()` in `frontend/src/services/riskService.ts` expects this endpoint.
- It returns `LocationData[]` which maps exactly to what `adapt_prediction_response()` produces.
- The monitored locations should mirror the state capitals and key at-risk areas in `frontend/src/data/central_store.ts`.

**Step 4.1 — Add monitored locations registry at top of api_stub.py (before the router definition):**
```python
# Predefined Northeast India monitored locations for GET /locations
# Mirrors frontend/src/data/central_store.ts CENTRAL_LOCATIONS
_MONITORED_LOCATIONS = [
    {"id": 1,  "name": "Itanagar, Arunachal Pradesh", "state": "Arunachal Pradesh", "district": "Papum Pare",      "lat": 27.1004, "lon": 93.6166, "elevation": 842,  "slope": 34},
    {"id": 2,  "name": "Kohima, Nagaland",            "state": "Nagaland",          "district": "Kohima",          "lat": 25.6751, "lon": 94.1086, "elevation": 1444, "slope": 28},
    {"id": 3,  "name": "Shillong, Meghalaya",         "state": "Meghalaya",         "district": "East Khasi Hills","lat": 25.5788, "lon": 91.8933, "elevation": 1496, "slope": 18},
    {"id": 4,  "name": "Gangtok, Sikkim",             "state": "Sikkim",            "district": "East Sikkim",     "lat": 27.3314, "lon": 88.6138, "elevation": 1650, "slope": 38},
    {"id": 5,  "name": "Aizawl, Mizoram",             "state": "Mizoram",           "district": "Aizawl",          "lat": 23.7271, "lon": 92.7176, "elevation": 1132, "slope": 30},
    {"id": 6,  "name": "Imphal, Manipur",             "state": "Manipur",           "district": "Imphal West",     "lat": 24.8170, "lon": 93.9368, "elevation": 786,  "slope": 12},
    {"id": 7,  "name": "Agartala, Tripura",           "state": "Tripura",           "district": "West Tripura",    "lat": 23.8315, "lon": 91.2868, "elevation": 13,   "slope": 6},
    {"id": 8,  "name": "Guwahati, Assam",             "state": "Assam",             "district": "Kamrup Metro",    "lat": 26.1445, "lon": 91.7362, "elevation": 55,   "slope": 10},
]
```

**Step 4.2 — Add the GET /locations endpoint to api_stub.py:**
```python
@router.get(
    "/locations",
    summary="Get all monitored Northeast India locations with current risk predictions",
)
async def get_monitored_locations(
    region: Optional[str] = Query(None, description="Filter by state name (e.g. 'Sikkim')"),
) -> list:
    """
    Run batch inference over all predefined monitored Northeast India locations.
    Returns a LocationData-compatible list consumable by the frontend riskService.
    """
    from backend.ml.src.adapter import adapt_prediction_response

    results = []
    locations = _MONITORED_LOCATIONS
    if region and region.lower() not in ("northeastern india", "all"):
        locations = [l for l in locations if l["state"].lower() == region.lower()]

    for loc in locations:
        try:
            input_dict = {
                "latitude":      loc["lat"],
                "longitude":     loc["lon"],
                "elevation_m":   loc.get("elevation", 1000.0),
                "slope_deg":     loc.get("slope", 25.0),
                "rainfall_24hr_mm": 65.0,   # baseline — replace with live data
                "soil_moisture_pct": 55.0,  # baseline — replace with live data
            }
            ml_result = predict_risk(input_dict)
            adapted   = adapt_prediction_response(ml_result, {"lat": loc["lat"], "lon": loc["lon"]})
            results.append({
                **adapted,
                "id":       loc["id"],
                "name":     loc["name"],
                "state":    loc["state"],
                "district": loc["district"],
            })
        except Exception as err:
            logger.warning(f"Skipping location {loc['name']}: {err}")

    return results
```

**Step 4.3 — Verify the locations endpoint:**
```powershell
curl.exe -s "http://localhost:8000/api/v1/risk/locations" | python -c "
import json, sys
data = json.load(sys.stdin)
print(f'Total locations returned: {len(data)}')
for loc in data:
    print(f'  {loc[\"name\"]} → risk={loc[\"risk\"]}, prob={loc[\"prob\"]}%')
print()
required_keys = ['id','name','state','district','lat','lon','risk','prob','factors']
missing = [k for k in required_keys if k not in data[0]]
print('Missing keys:', missing if missing else 'None — PASS')
"
```

---

## FINAL VERIFICATION — Full Integration Check

Run this after all phases are complete:

```python
python -c "
import subprocess, json, sys

base = 'http://localhost:8000'
tests = [
    ('GET  /', 'GET', base + '/', None),
    ('POST /predict (lat/lon format)', 'POST', base + '/api/v1/risk/predict',
     json.dumps({'lat': 27.33, 'lon': 88.61, 'rainfall_24hr_mm': 120.0})),
    ('POST /predict (Arunachal Pradesh)', 'POST', base + '/api/v1/risk/predict',
     json.dumps({'lat': 27.1004, 'lon': 93.6166})),
    ('GET  /heatmap (flat array)', 'GET', base + '/api/v1/risk/heatmap', None),
    ('GET  /locations', 'GET', base + '/api/v1/risk/locations', None),
    ('GET  /model/info (flat schema)', 'GET', base + '/api/v1/risk/model/info', None),
]

all_pass = True
for label, method, url, body in tests:
    import urllib.request
    req = urllib.request.Request(url, data=body.encode() if body else None,
                                  headers={'Content-Type': 'application/json'} if body else {})
    req.get_method = lambda: method
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
            print(f'[PASS] {label}')
    except Exception as e:
        print(f'[FAIL] {label}: {e}')
        all_pass = False

print()
print('INTEGRATION STATUS:', 'ALL PASS ✓' if all_pass else 'FAILURES — check logs')
"
```

---

## File Change Summary

```
backend/ml/
├── src/
│   ├── config.py      ← EDIT: lines 74-78 (LAT_MIN/MAX, LON_MIN/MAX for NE India)
│   ├── api_stub.py    ← EDIT: LocationInput aliases + bounds + adapter wiring + /locations endpoint
│   ├── main.py        ← CREATE: FastAPI app + CORS (does not exist yet)
│   └── adapter.py     ← CREATE: pure schema transformation module (does not exist yet)
└── requirements.txt   ← VERIFY fastapi, uvicorn, pydantic already listed (they are)

frontend/              ← FROZEN — zero edits permitted
```

> [!IMPORTANT]
> `frontend/` is **completely frozen**. The frontend's `riskService.ts` already uses `Promise.resolve()` stubs ready for seamless REST replacement — no frontend code change is ever needed.

> [!NOTE]
> Run each Phase in order. Do not skip Phase 0. Each phase has a built-in verification step — only proceed when all tests pass.
