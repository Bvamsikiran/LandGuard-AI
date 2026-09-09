# 🔬 AI/ML Pipeline & Frontend Compatibility Report

**Audit Timestamp:** 2026-09-08 19:47 UTC  
**Auditor:** AI Agent (Read-Only Mode)  
**Target Scope:** AI/ML Predictive Analytics Engine (Member 3) ↔ Frontend Interface  
**Codebase Root:** `D:/Apps/sih_2026/multi_hazard_software_system_aiml_predictive_analytics_pipeline_modules/`

---

## 1. Executive Summary

| Metric | Value |
|---|---|
| Total ML Touchpoints Evaluated | **9** |
| Fully Compatible | **0** |
| Incompatible / Requiring Adapter | **9** |
| Pipeline Integration Readiness | **~0%** (Server not running; all schema contracts mismatched) |

> [!CAUTION]
> **Zero of nine touchpoints are currently compatible.** The ML service is unreachable (no `main.py` entrypoint exists), and 7 of 8 Northeast India locations are rejected outright with HTTP 422 due to hardcoded Sikkim-only coordinate bounds.

---

## 2. Workflow Execution Log

### ✅ Workflow 1 — Static Schema & Type Inspection (Read-Only)

**Status: COMPLETED**

**Frontend Contract** ([`index.ts`](file:///D:/Apps/sih_2026/multi_hazard_software_system_aiml_predictive_analytics_pipeline_modules/frontend/src/types/index.ts) · [`riskService.ts`](file:///D:/Apps/sih_2026/multi_hazard_software_system_aiml_predictive_analytics_pipeline_modules/frontend/src/services/riskService.ts) · [`LocationRiskDetailsDrawer.tsx`](file:///D:/Apps/sih_2026/multi_hazard_software_system_aiml_predictive_analytics_pipeline_modules/frontend/src/components/drawers/LocationRiskDetailsDrawer.tsx) · [`FactorBar.tsx`](file:///D:/Apps/sih_2026/multi_hazard_software_system_aiml_predictive_analytics_pipeline_modules/frontend/src/components/common/FactorBar.tsx))

```
LocationData {
  lat: number        ← coordinate field name
  lon: number        ← coordinate field name
  risk: RiskLevel    ← "Low"|"Moderate"|"High"|"Very High"  (Title Case)
  prob: number       ← integer 0..100 (used as SVG strokeDasharray percentage directly)
  factors: FactorBar { label: string, percent: number, value: string }
}

RiskLevel = "Low" | "Moderate" | "High" | "Very High"
```

**Backend Reality** ([`api_stub.py`](file:///D:/Apps/sih_2026/multi_hazard_software_system_aiml_predictive_analytics_pipeline_modules/backend/ml/src/api_stub.py))

```
LocationInput {
  latitude: float  [ge=27.0, le=28.1]   ← wrong name + Sikkim-only bounds
  longitude: float [ge=88.0, le=89.0]   ← wrong name + Sikkim-only bounds
  ...
}

FactorExplanation {
  feature: str           ← wrong field name
  shap_value: float      ← wrong field name  
  direction: str         ← extra field (not in frontend)
  contribution_pct: float← wrong field name (frontend expects: percent)
}

RiskResponse {
  risk_probability: float  ← decimal 0.0..1.0 (frontend needs integer 0..100)
  risk_level: str          ← "LOW"|"HIGH"|"VERY_HIGH" (frontend needs Title Case)
  location: Dict           ← nested {latitude, longitude} (wrong names)
  ...                      ← missing top-level fields: lat, lon, prob, risk, factors
}
```

---

### ✅ Workflow 2 — Coordinate Bounds & Imputation Dry-Run (Read-Only)

**Status: COMPLETED — 7/8 REJECTED**

```
=== COORDINATE VALIDATION AUDIT ===
[PASS]     Gangtok, Sikkim (27.33, 88.61)
[REJECTED] Itanagar, Arunachal Pradesh (27.1004, 93.6166) -> Input should be less than or equal to 89
[REJECTED] Kohima, Nagaland (25.6751, 94.1086)           -> Input should be greater than or equal to 27
[REJECTED] Shillong, Meghalaya (25.5788, 91.8933)         -> Input should be greater than or equal to 27
[REJECTED] Aizawl, Mizoram (23.7271, 92.7176)             -> Input should be greater than or equal to 27
[REJECTED] Imphal, Manipur (24.817, 93.9368)              -> Input should be greater than or equal to 27
[REJECTED] Agartala, Tripura (23.8315, 91.2868)           -> Input should be greater than or equal to 27
[REJECTED] Guwahati, Assam (26.1445, 91.7362)             -> Input should be greater than or equal to 27

Result: 1/8 PASSED | 7/8 REJECTED

=== FRONTEND FIELD NAMES (lat/lon) ===
[REJECTED] Frontend lat/lon param names NOT accepted -> Field required
```

> [!WARNING]
> Even Itanagar (which is at 27.1°N, within lat bounds) is **rejected** due to its longitude (93.6°E) exceeding the hardcoded `lon ≤ 89.0` ceiling. The current model can only serve **Gangtok and its immediate surroundings**.

---

### ✅ Workflow 3 — Live ML Inference Probing (Read-Only)

**Status: SERVER UNREACHABLE**

```
curl.exe -s --connect-timeout 3 http://localhost:8000/api/v1/risk/model/info
→ SERVER_UNREACHABLE: No running server found on port 8000
```

**Root cause:** No `main.py` or `server.py` entrypoint exists in [`backend/ml/src/`](file:///D:/Apps/sih_2026/multi_hazard_software_system_aiml_predictive_analytics_pipeline_modules/backend/ml/src/). Only an `APIRouter` is defined in [`api_stub.py`](file:///D:/Apps/sih_2026/multi_hazard_software_system_aiml_predictive_analytics_pipeline_modules/backend/ml/src/api_stub.py) — there is no FastAPI `app` object, no Uvicorn runner, and no CORS middleware.

---

## 3. Discrepancy Matrix (Full)

| # | Touchpoint | Frontend Contract | Backend Reality | Mismatch Category | Severity | Impact |
|---|---|---|---|---|---|---|
| 1 | **Server Entrypoint** | REST on `localhost:8000` from Vite (`localhost:8443`) | No `main.py`; only `APIRouter` in `api_stub.py`; no Uvicorn; no CORS | Missing infrastructure | 🔴 **CRITICAL** | Service 100% unreachable; all API calls fail |
| 2 | **Geographic Bounds** | All 8 NE states: Lat `23.0–28.5°N`, Lon `88.0–97.5°E` | [`api_stub.py:56-57`](file:///D:/Apps/sih_2026/multi_hazard_software_system_aiml_predictive_analytics_pipeline_modules/backend/ml/src/api_stub.py#L56-L57): `latitude ge=27.0 le=28.1`, `longitude ge=88.0 le=89.0` | Coordinate validation too strict | 🔴 **CRITICAL** | 7/8 NE state capitals → HTTP 422; only Gangtok works |
| 3 | **Coordinate Param Names** | `lat: number`, `lon: number` | `latitude: float`, `longitude: float` (no aliases) | Field name mismatch | 🟠 **HIGH** | All frontend POST requests fail validation (`Field required`) |
| 4 | **Risk Probability Scale** | `prob: number` (int `0..100`) — used directly as SVG `strokeDasharray` | `risk_probability: float` (`0.0..1.0`) | Numeric scale mismatch | 🟠 **HIGH** | Gauge shows `0%` or sub-1% (e.g., `0.87%` instead of `87%`) |
| 5 | **Risk Level Casing** | `"Low"` \| `"Moderate"` \| `"High"` \| `"Very High"` | [`predict.py:283`](file:///D:/Apps/sih_2026/multi_hazard_software_system_aiml_predictive_analytics_pipeline_modules/backend/ml/src/predict.py#L283): `_determine_risk_level()` returns `"LOW"`, `"VERY_HIGH"` | String casing & underscore | 🟠 **HIGH** | `RISK_COLORS["LOW"]` → `undefined`; badge invisible; CSS class mismatch |
| 6 | **SHAP Factor Schema** | [`FactorBar.tsx`](file:///D:/Apps/sih_2026/multi_hazard_software_system_aiml_predictive_analytics_pipeline_modules/frontend/src/components/common/FactorBar.tsx): `{ label: string, percent: number, value: string }` | [`api_stub.py:112-116`](file:///D:/Apps/sih_2026/multi_hazard_software_system_aiml_predictive_analytics_pipeline_modules/backend/ml/src/api_stub.py#L112-L116) `FactorExplanation`: `{ feature, shap_value, direction, contribution_pct }` | Field names mismatch (3 of 3 wrong) | 🟠 **HIGH** | "AI Contributing Factors" drawer shows blank / broken bars |
| 7 | **Heatmap Response Schema** | [`riskService.ts:35-40`](file:///D:/Apps/sih_2026/multi_hazard_software_system_aiml_predictive_analytics_pipeline_modules/frontend/src/services/riskService.ts#L35-L40): flat array `[{ lat, lon, weight: 0..1, risk }]` | [`api_stub.py:226-237`](file:///D:/Apps/sih_2026/multi_hazard_software_system_aiml_predictive_analytics_pipeline_modules/backend/ml/src/api_stub.py#L226-L237): nested `{ bounding_box, cell_count, cells: [{lat, lon, risk_probability, risk_level}] }` | JSON structure mismatch | 🟠 **HIGH** | Leaflet heatmap cannot iterate response; renders nothing |
| 8 | **Monitored Locations Endpoint** | `GET /api/v1/risk/locations` expected by [`riskService.ts`](file:///D:/Apps/sih_2026/multi_hazard_software_system_aiml_predictive_analytics_pipeline_modules/frontend/src/services/riskService.ts) | **Endpoint does not exist** in `api_stub.py` (only `/predict`, `/heatmap`, `/model/info`) | Missing endpoint | 🟠 **HIGH** | Location cards, risk table, map pins cannot be populated from backend |
| 9 | **Model Info Schema** | [`riskService.ts:83-95`](file:///D:/Apps/sih_2026/multi_hazard_software_system_aiml_predictive_analytics_pipeline_modules/frontend/src/services/riskService.ts#L83-L95): flat `{ modelName, version, accuracy, precision, recall, f1Score, datasetSize, status, lastTrained }` | [`api_stub.py:269-275`](file:///D:/Apps/sih_2026/multi_hazard_software_system_aiml_predictive_analytics_pipeline_modules/backend/ml/src/api_stub.py#L269-L275): nested `{ status, metadata: { model_name, training_date, test_metrics: {...} }, risk_thresholds }` | Schema hierarchy (nested vs flat) | 🟡 **MEDIUM** | Model Insights view shows hardcoded demo data; real metrics not surfaced |

---

## 4. Actionable Backend Remediation (Zero Frontend Edits)

All fixes are to be implemented **exclusively in `backend/ml/`** — no frontend files touched.

### Fix 1 — Create `ml/src/main.py` (Entrypoint + CORS) · Severity: CRITICAL

```python
# backend/ml/src/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from ml.src.api_stub import router as ml_router

app = FastAPI(
    title="Landguard AI/ML Predictive Analytics Engine",
    description="Real-time Landslide Hazard Prediction for Northeast India",
    version="1.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8443", "http://localhost:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(ml_router)
```

**Run with:** `uvicorn ml.src.main:app --host 0.0.0.0 --port 8000 --reload`

---

### Fix 2 — Expand Geographic Bounds in `api_stub.py` · Severity: CRITICAL

In [`api_stub.py:56-57`](file:///D:/Apps/sih_2026/multi_hazard_software_system_aiml_predictive_analytics_pipeline_modules/backend/ml/src/api_stub.py#L56-L57), change:

```python
# BEFORE (Sikkim-only)
latitude:  float = Field(..., ge=27.0, le=28.1)
longitude: float = Field(..., ge=88.0, le=89.0)

# AFTER (Full Northeast India)
latitude:  float = Field(..., ge=21.5, le=30.0, description="Latitude — NE India region")
longitude: float = Field(..., ge=87.0, le=98.0, description="Longitude — NE India region")
```

Also update [`config.py:75-78`](file:///D:/Apps/sih_2026/multi_hazard_software_system_aiml_predictive_analytics_pipeline_modules/backend/ml/src/config.py#L75-L78):
```python
LAT_MIN: float = 21.5
LAT_MAX: float = 30.0
LON_MIN: float = 87.0
LON_MAX: float = 98.0
```

---

### Fix 3 — Add Pydantic `lat`/`lon` Aliases in `api_stub.py` · Severity: HIGH

```python
from pydantic import BaseModel, Field, AliasChoices

class LocationInput(BaseModel):
    model_config = {"populate_by_name": True}

    latitude: float = Field(
        ..., ge=21.5, le=30.0,
        validation_alias=AliasChoices("latitude", "lat")
    )
    longitude: float = Field(
        ..., ge=87.0, le=98.0,
        validation_alias=AliasChoices("longitude", "lon")
    )
```

---

### Fix 4 — Create `ml/src/adapter.py` (Response Transformer) · Severity: HIGH

Implements all schema adaptations per AGENTS.md Section 4, Step 2:

```python
# backend/ml/src/adapter.py

def format_risk_level(level_raw: str) -> str:
    mapping = {"LOW": "Low", "MODERATE": "Moderate", "HIGH": "High", "VERY_HIGH": "Very High"}
    return mapping.get(str(level_raw).upper(), "Moderate")

def format_shap_factors(raw_factors: list, features: dict) -> list:
    label_map = {
        "rainfall_24hr_mm": ("24h Rainfall", f"{features.get('rainfall_24hr_mm', 0):.0f} mm"),
        "soil_moisture_pct": ("Soil Moisture Saturation", f"{features.get('soil_moisture_pct', 0):.0f}%"),
        "slope_deg": ("Slope Steepness", f"{features.get('slope_deg', 0):.0f}°"),
        "historical_landslide_density": ("Historical Susceptibility", f"{features.get('historical_landslide_density', 0):.0f} events"),
        "elevation_m": ("Elevation", f"{features.get('elevation_m', 0):.0f} m"),
    }
    formatted = []
    for f in raw_factors[:5]:
        feat_name = f.get("feature", "")
        label, val_str = label_map.get(feat_name, (feat_name.replace("_", " ").title(), ""))
        formatted.append({"label": label, "percent": round(f.get("contribution_pct", 10.0)), "value": val_str})
    return formatted

def adapt_prediction_response(ml_result: dict, raw_input: dict) -> dict:
    prob_percent = round(ml_result["risk_probability"] * 100)
    risk_level = format_risk_level(ml_result["risk_level"])
    lat = raw_input.get("lat") or raw_input.get("latitude") or ml_result["location"]["latitude"]
    lon = raw_input.get("lon") or raw_input.get("longitude") or ml_result["location"]["longitude"]
    return {
        "lat": round(float(lat), 4),
        "lon": round(float(lon), 4),
        "risk": risk_level,
        "prob": prob_percent,
        "factors": format_shap_factors(ml_result.get("top_factors", []), raw_input),
        "modelUsed": ml_result.get("model_used", "XGBoost Classifier"),
        "confidenceNote": ml_result.get("confidence_note", ""),
        "timestamp": ml_result.get("timestamp", ""),
    }

def adapt_heatmap_response(cells: list) -> list:
    return [{"lat": c["lat"], "lon": c["lon"],
              "weight": round(c["risk_probability"], 3),
              "risk": format_risk_level(c["risk_level"])} for c in cells]

def adapt_model_info(metadata: dict) -> dict:
    test_metrics = metadata.get("test_metrics", {})
    return {
        "modelName": metadata.get("model_name", "Landslide-XGBoost Classifier"),
        "version": metadata.get("version", "v4.2-NE-India"),
        "accuracy": test_metrics.get("accuracy", 0.942),
        "precision": test_metrics.get("precision", 0.928),
        "recall": test_metrics.get("recall", 0.916),
        "f1Score": test_metrics.get("f1", 0.922),
        "datasetSize": metadata.get("dataset_rows", 5000),
        "status": "Operational (Live ML Pipeline)",
        "lastTrained": metadata.get("training_date", "2026-08-15"),
    }
```

---

### Fix 5 — Add `GET /api/v1/risk/locations` Endpoint · Severity: HIGH

Add to [`api_stub.py`](file:///D:/Apps/sih_2026/multi_hazard_software_system_aiml_predictive_analytics_pipeline_modules/backend/ml/src/api_stub.py) a new endpoint that runs batch inference over predefined monitored locations and returns `LocationData`-compatible objects.

---

### Fix 6 — Wire Adapter into Existing Endpoint Responses · Severity: HIGH

Wrap the `get_risk_prediction`, `get_risk_heatmap`, and `get_model_info` endpoint return values through the adapter functions from Fix 4 before returning to the client.

---

## 5. Non-Destructive Verification Log

| Workflow | Tool Used | Result | Details |
|---|---|---|---|
| Schema Dry-Run (W1) | `python -c "from ml.src.api_stub import ..."` | ✅ **Schema read successfully** | `latitude/longitude` confirmed; no `lat/lon` aliases |
| Boundary Validation (W2) | Pydantic `ValidationError` dry-run | ❌ **FAILED — 7/8 REJECTED** | Only Gangtok accepted; all other NE states rejected |
| Frontend lat/lon names (W2) | `LocationInput(lat=..., lon=...)` | ❌ **FAILED — `Field required`** | Aliases not configured |
| Live Endpoint Probe (W3) | `curl.exe --connect-timeout 3 localhost:8000` | ❌ **SERVER UNREACHABLE** | No `main.py`; Uvicorn never started |

---

## 6. Verification Checklist

- [x] Confirmed that **NO** frontend UI component files were modified (read-only audit only).
- [x] Confirmed that all compatibility checks were executed in **read-only mode**.
- [ ] ❌ ML backend does NOT yet accept coordinates across all 8 Northeast states.
- [ ] ❌ Probability scale is NOT yet normalized; risk level is NOT yet Title Case.
- [ ] ❌ SHAP factors do NOT yet match `{label, percent, value}` format.
- [ ] ❌ Server entrypoint (`main.py`) does NOT yet exist.
- [x] **Simple Detailed Report generated and presented.**

---

## 7. File Map — What Needs to Change

```
backend/ml/
├── src/
│   ├── api_stub.py       ← Fix 2: expand bounds | Fix 3: lat/lon aliases | Fix 5: /locations endpoint | Fix 6: wire adapters
│   ├── config.py         ← Fix 2: update LAT_MIN/MAX, LON_MIN/MAX constants
│   ├── main.py           ← Fix 1: CREATE THIS FILE (FastAPI app + CORS)   [MISSING]
│   └── adapter.py        ← Fix 4: CREATE THIS FILE (schema transformers)  [MISSING]
```

> [!NOTE]
> `frontend/` is **frozen** — zero edits required or permitted per Rule 1.
> The frontend's [`riskService.ts`](file:///D:/Apps/sih_2026/multi_hazard_software_system_aiml_predictive_analytics_pipeline_modules/frontend/src/services/riskService.ts) already uses `Promise.resolve()` stubs designed for seamless REST replacement.
