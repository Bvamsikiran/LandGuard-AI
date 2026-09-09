# AI Prompt: Build the Predictive AI/ML Pipeline — Multi-Hazard Early Warning System (Prototype)

> **Instructions for use:** Copy everything below the horizontal rule and paste it directly to your AI of choice (Claude, GPT-4o, Gemini, etc.). Do not modify the structure — the AI needs every section to build correctly.

---
## ROLE

You are a Senior ML Engineer and Python Backend Developer. You are building the **AI/ML Prediction Pipeline** (Member 3 responsibility) for a prototype multi-hazard early warning system targeting the Himalayan/Northeastern region of India (pilot area: **Sikkim**). This is a **prototype** — prioritize working, honest, runnable code over completeness. Do not hallucinate features or accuracy claims.

---

## PROJECT CONTEXT (READ FULLY BEFORE CODING)

The overall system is called the **AI-Assisted Multi-Hazard Early Warning and Cascade Risk Assessment System**. It fuses near-real-time satellite-derived precipitation, terrain (DEM), land-cover (Sentinel-2/NDVI), historical landslide data, and optionally IoT sensor observations to estimate localized landslide hazard risk and cascade potential (landslide → river blockage → flood).

### The chain this pipeline implements:
```
DATA SOURCES (satellite rainfall, DEM, NDVI, historical landslides, IoT)
  → Data Ingestion + Validation
  → Spatial/Temporal Normalization
  → Feature Engineering
  → AI Risk Model Inference (Random Forest + XGBoost as baselines)
  → SHAP Explainability
  → Risk Score + Risk Level output
  → JSON response to FastAPI backend
```

### What this pipeline is NOT:
- It does NOT predict the exact time a landslide will occur.
- It does NOT claim real-time live sensor feeds (satellite data has latency).
- It does NOT claim >97% accuracy (honest evaluation only).
- It does NOT replace the cascade engine or GIS overlay (those are separate modules).

---

## SCOPE: WHAT TO BUILD

Build the following self-contained Python ML pipeline as a package called `ml/`. It must be importable by a FastAPI backend via a single inference function. The pipeline has **two modes**: a training mode (offline, run once) and an inference mode (called at runtime per request).

### Package Structure to Create:

```
ml/
├── data/
│   └── README.md                  ← describe what synthetic/real data goes here
├── notebooks/
│   └── 01_eda_and_training.ipynb  ← (optional, create if you can)
├── src/
│   ├── __init__.py
│   ├── config.py                  ← all constants, thresholds, feature names
│   ├── data_loader.py             ← load raw CSV / simulate prototype data
│   ├── preprocessing.py           ← clean, validate, handle missing values
│   ├── features.py                ← feature engineering (rainfall windows, etc.)
│   ├── train.py                   ← training pipeline (RF + XGB, CV, metrics)
│   ├── evaluate.py                ← evaluation: precision, recall, F1, ROC-AUC, PR-AUC, calibration
│   ├── predict.py                 ← inference function called by FastAPI
│   ├── explain.py                 ← SHAP explainability
│   └── utils.py                   ← logging, data freshness tagging, helpers
├── models/
│   └── .gitkeep
├── reports/
│   └── .gitkeep
├── requirements.txt
└── README.md
```

---

## DETAILED WORKFLOW SPECIFICATIONS

### WORKFLOW 1: Data Ingestion + Prototype Dataset

**Goal:** For prototype, generate a realistic synthetic dataset that mimics real feature distributions. Document how real data (GPM IMERG, DEM, NDVI, historical landslide atlas) would replace it.

**Features to engineer (minimum set — do not skip any):**

| Feature Name | Source | Description |
|---|---|---|
| `rainfall_30min_mm` | NASA GPM IMERG | Rainfall in last 30 min |
| `rainfall_3hr_mm` | NASA GPM IMERG | Rainfall in last 3 hours |
| `rainfall_24hr_mm` | NASA GPM IMERG | Rainfall in last 24 hours |
| `rainfall_3day_mm` | NASA GPM IMERG | Rainfall in last 3 days |
| `rainfall_7day_mm` | NASA GPM IMERG | Rainfall in last 7 days |
| `rainfall_intensity` | Derived | mm/hour from 30min window |
| `antecedent_rainfall_anomaly` | Derived | 7-day total vs. climatological mean |
| `soil_moisture_pct` | IoT sensor / proxy | % volumetric water content |
| `soil_moisture_change_rate` | Derived | Change per hour |
| `elevation_m` | DEM | Meters above sea level |
| `slope_deg` | DEM derived | Slope in degrees |
| `aspect_deg` | DEM derived | Aspect in degrees (0–360) |
| `ndvi` | Sentinel-2 derived | Vegetation index (−1 to 1) |
| `land_cover_class` | Sentinel-2 classified | Categorical (forest/bare/agri/built) |
| `historical_landslide_density` | ISRO Landslide Atlas | Count of past events within 5km radius |
| `distance_to_river_km` | GIS | Nearest river distance |
| `distance_to_road_km` | GIS | Nearest road distance |
| `tilt_change_deg` | IoT sensor / proxy | Change in tilt from inclinometer |
| `temperature_C` | IMD AWS / proxy | Surface air temperature |
| `data_freshness_score` | Derived | Freshness tag: FRESH/RECENT/STALE/MISSING mapped to 1.0/0.7/0.4/0.0 |

**Target variable:** `landslide_occurred` (binary: 1 = event, 0 = non-event)

**Prototype synthetic data generation rules:**
- Create 5,000 rows: 400 positives (landslide=1), 4,600 negatives (landslide=0).
- Positives must have correlated patterns: high rainfall + high soil moisture + steep slope + high historical density.
- Add 5–10% missing values randomly across features to simulate real-world gaps.
- Attach a `latitude` and `longitude` column (random points within Sikkim bounding box: lat 27.0–28.1, lon 88.0–89.0).
- Attach `timestamp` column (random dates 2018–2023).
- Save as `ml/data/prototype_training_data.csv`.

**IMPORTANT:** Add a comment block in `data_loader.py` explaining how real data sources replace each simulated column:
```python
# REAL DATA REPLACEMENT NOTES:
# rainfall_30min_mm → NASA GPM IMERG Early Run, ~4hr latency, 0.1deg grid, via NASA Earthdata API
# soil_moisture_pct → IoT ESP32 sensor via POST /api/v1/sensor-data endpoint
# elevation_m, slope_deg, aspect_deg → SRTM 30m DEM, processed via GDAL/rasterio
# ndvi → Sentinel-2 L2A band calculation (B8-B4)/(B8+B4) via Copernicus Hub
# historical_landslide_density → ISRO Landslide Atlas (80,000 events, 1998–2022), spatial join
# distance_to_river_km, distance_to_road_km → OpenStreetMap / Bhuvan GIS layers
```

---

### WORKFLOW 2: Data Preprocessing + Validation

**File:** `ml/src/preprocessing.py`

Implement in order:

1. **Presence check:** Confirm all expected feature columns exist. Log missing columns.
2. **Timestamp validation:** Parse and validate timestamps. Flag FUTURE timestamps as invalid.
3. **Range validation:** Apply min/max plausibility checks per feature:
   - `rainfall_*` ≥ 0, ≤ 500 mm
   - `soil_moisture_pct` 0–100%
   - `slope_deg` 0–90°
   - `ndvi` −1 to 1
   - `temperature_C` −20 to 55°C
   - `elevation_m` 0–9000 m
4. **Missing value handling:**
   - For numerical features: impute with median (computed on training set, saved to disk).
   - For categorical (`land_cover_class`): impute with mode.
   - Do NOT impute target variable — drop rows with missing `landslide_occurred`.
5. **Duplicate detection:** Drop duplicate rows (same lat/lon/timestamp).
6. **Data freshness tagging:** Compute `data_freshness_score` = float value based on age of observation relative to inference time.
7. **Output:** Return a clean pandas DataFrame + a validation report dict `{column: status}`.

---

### WORKFLOW 3: Feature Engineering

**File:** `ml/src/features.py`

Implement these transformations:

1. **Rainfall window aggregation:** The raw data contains individual rainfall readings — compute rolling windows of 30min, 3hr, 24hr, 3day, 7day accumulations. (If already pre-aggregated in the dataset, validate they are present.)

2. **Rainfall intensity:** `rainfall_intensity = rainfall_30min_mm / 0.5` (mm/hour equivalent)

3. **Antecedent rainfall anomaly:** `antecedent_rainfall_anomaly = rainfall_7day_mm - climatological_7day_mean`. For prototype, use a fixed reference mean (e.g., 80mm for Sikkim monsoon season). Document this assumption.

4. **Soil moisture rate of change:** `soil_moisture_change_rate = (current_soil_moisture - previous_soil_moisture) / time_delta_hours`. For prototype, simulate or set to 0 if not available.

5. **Tilt change trend:** `tilt_change_deg` as provided. Add a binary flag `tilt_movement_detected = 1 if tilt_change_deg > threshold`.

6. **Log transforms:** Apply `log1p` to `historical_landslide_density` and `distance_to_river_km` to normalize skew.

7. **Categorical encoding:** One-hot encode `land_cover_class`.

8. **Feature scaling:** StandardScaler for Logistic Regression only. Tree models (RF, XGB) do not need scaling — keep a separate pipeline.

9. **Feature importance audit output:** After engineering, print a summary table of all final features going into the model.

---

### WORKFLOW 4: Model Training (Honest Baseline)

**File:** `ml/src/train.py`

#### Class Imbalance Strategy:
- Use `class_weight='balanced'` for Random Forest and Logistic Regression.
- Use `scale_pos_weight = n_neg / n_pos` for XGBoost.
- **Do NOT oversample/undersample blindly.** Document why class weighting is used.

#### Train/Validation Split Strategy:
- **Temporal split:** Sort by `timestamp`. Use earliest 80% for training, latest 20% for testing. This prevents data leakage across time.
- Add a comment explaining spatial leakage risk: events from the same storm should not appear in both train and test sets.

#### Models to train:

**Model 1: Logistic Regression (baseline)**
```python
from sklearn.linear_model import LogisticRegression
model = LogisticRegression(class_weight='balanced', max_iter=1000, random_state=42)
```

**Model 2: Random Forest Classifier (primary candidate)**
```python
from sklearn.ensemble import RandomForestClassifier
model = RandomForestClassifier(
    n_estimators=200,
    max_depth=None,
    min_samples_leaf=5,
    class_weight='balanced',
    oob_score=True,
    n_jobs=-1,
    random_state=42
)
```
Key RF notes for this project:
- Use OOB score as an unbiased performance estimate.
- `min_samples_leaf=5` helps smooth predictions in imbalanced geospatial data.
- `n_jobs=-1` for parallel training — important for >10k grid cells at inference.
- The RF natively handles missing values (NaN) via surrogate splits.

**Model 3: XGBoost Classifier (boosting candidate)**
```python
import xgboost as xgb
model = xgb.XGBClassifier(
    n_estimators=300,
    max_depth=6,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    scale_pos_weight=<n_neg/n_pos>,
    use_label_encoder=False,
    eval_metric='aucpr',
    random_state=42,
    tree_method='hist'
)
```

#### Cross-validation:
- Use `StratifiedKFold(n_splits=5, shuffle=False)` (no shuffle to preserve temporal order approximately).
- Compute mean ± std for: Precision, Recall, F1, ROC-AUC, PR-AUC.

#### Model persistence:
- Save trained models to `ml/models/` using `joblib.dump`.
- Save the preprocessing pipeline (imputer + scaler) separately.
- Save a `model_metadata.json` with: model name, training date, feature list, training data shape, CV scores.

---

### WORKFLOW 5: Evaluation

**File:** `ml/src/evaluate.py`

Generate a full evaluation report per model. Print and save to `ml/reports/evaluation_report.txt`.

#### Metrics (implement all — do NOT skip because of imbalance):

```
1. Confusion Matrix (absolute counts)
2. Classification Report (precision, recall, F1 per class)
3. ROC-AUC score
4. PR-AUC (average_precision_score) — PRIMARY METRIC for this use case
5. Calibration curve (reliability diagram)
6. Feature importance (RF: MDI importance; XGB: gain importance)
```

#### Important notes for the evaluation code:
- Print a clear warning if accuracy > 95%: `"WARNING: High accuracy may reflect class imbalance, not model quality. Check PR-AUC and Recall for class=1."`
- Print Recall for the positive class separately with emphasis: `"RECALL (landslide detection rate): {value:.3f}"`. This is the most important metric for disaster prediction.
- Threshold analysis: plot precision vs. recall for different probability thresholds (0.1 to 0.9 in steps of 0.1). Report the threshold that gives Recall ≥ 0.75 with best precision.
- Select best model by PR-AUC. Save it as `ml/models/best_model.joblib`.

---

### WORKFLOW 6: SHAP Explainability

**File:** `ml/src/explain.py`

Implement:

1. **Global feature importance via SHAP:**
   ```python
   import shap
   explainer = shap.TreeExplainer(best_model)
   shap_values = explainer.shap_values(X_test)
   shap.summary_plot(shap_values[1], X_test, show=False)
   # Save to ml/reports/shap_summary.png
   ```

2. **Per-prediction explanation function:**
   ```python
   def explain_prediction(model, X_single_row, feature_names) -> dict:
       """
       Returns top 5 contributing features for a single prediction.
       Output format:
       {
         "top_factors": [
           {"feature": "rainfall_24hr_mm", "shap_value": 0.31, "direction": "increases_risk"},
           {"feature": "soil_moisture_pct", "shap_value": 0.24, "direction": "increases_risk"},
           {"feature": "slope_deg", "shap_value": 0.18, "direction": "increases_risk"},
           {"feature": "ndvi", "shap_value": -0.09, "direction": "decreases_risk"},
           {"feature": "distance_to_river_km", "shap_value": -0.07, "direction": "decreases_risk"}
         ]
       }
       """
   ```

3. SHAP force plot for a single high-risk example (save as HTML: `ml/reports/shap_force_example.html`).

---

### WORKFLOW 7: Inference / Predict Function

**File:** `ml/src/predict.py`

This is the most critical function — it will be called by the FastAPI backend at runtime.

```python
def predict_risk(input_data: dict) -> dict:
    """
    Main inference endpoint.
    
    Args:
        input_data: dict with keys matching the feature list in config.py
        Must include: latitude, longitude, and all environmental features.
        Missing features are filled using stored imputer medians (not invented).
    
    Returns:
        {
          "location": {"latitude": float, "longitude": float},
          "timestamp": "ISO8601 string",
          "risk_probability": float,           # 0.0 to 1.0
          "risk_level": str,                   # LOW / MODERATE / HIGH / VERY_HIGH
          "risk_level_color": str,             # green / yellow / orange / red
          "model_used": str,                   # "RandomForest_v1.0"
          "model_version": str,
          "confidence_note": str,              # e.g. "DEGRADED: soil_moisture data stale"
          "data_freshness": str,               # FRESH / RECENT / STALE
          "top_factors": [                     # from SHAP
            {"feature": str, "contribution_pct": float, "direction": str}
          ],
          "input_feature_summary": dict,       # echo back key inputs for transparency
          "cascade_input": {                   # for cascade engine downstream
            "landslide_probability": float,
            "location": {"lat": float, "lon": float},
            "slope_deg": float,
            "distance_to_river_km": float
          }
        }
    """
```

#### Risk level thresholds (configurable in `config.py`):
```python
RISK_THRESHOLDS = {
    "LOW":       (0.0, 0.35),
    "MODERATE":  (0.35, 0.55),
    "HIGH":      (0.55, 0.75),
    "VERY_HIGH": (0.75, 1.01)
}
RISK_COLORS = {
    "LOW": "green",
    "MODERATE": "yellow",
    "HIGH": "orange",
    "VERY_HIGH": "red"
}
```
Add a docstring: `# Thresholds are provisional prototype values. They must be validated against real operational data before production use.`

#### Graceful degradation:
- If any feature is missing at inference time → use stored imputed median and set `confidence_note` to reflect which features were missing.
- If model file not found → raise a clear `ModelNotLoadedError` with instructions.
- Log every inference call with timestamp, location, probability, and any warnings.

---

### WORKFLOW 8: Training Entry Point

**File:** `ml/src/train.py` (also create `ml/run_training.py`)

The training script must be runnable end-to-end with:
```bash
cd ml/
python run_training.py
```

It should execute:
1. Load data from `ml/data/prototype_training_data.csv`
2. Preprocess + validate
3. Feature engineering
4. Train all 3 models
5. Evaluate all 3 models
6. Select best model
7. Generate SHAP explanations
8. Save all artifacts to `ml/models/` and `ml/reports/`
9. Print a final summary table

---

### WORKFLOW 9: FastAPI Integration Stub

**File:** `ml/src/api_stub.py`

Create a minimal FastAPI router that the backend team can import:

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ml.src.predict import predict_risk

router = APIRouter(prefix="/api/v1/risk", tags=["risk"])

class LocationInput(BaseModel):
    latitude: float
    longitude: float
    rainfall_30min_mm: float = None
    rainfall_3hr_mm: float = None
    rainfall_24hr_mm: float = None
    rainfall_3day_mm: float = None
    rainfall_7day_mm: float = None
    soil_moisture_pct: float = None
    slope_deg: float = None
    elevation_m: float = None
    ndvi: float = None
    # ... all other features optional, will be imputed if missing

@router.post("/predict")
async def get_risk_prediction(input: LocationInput):
    try:
        result = predict_risk(input.dict())
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/heatmap")
async def get_risk_heatmap(lat_min: float, lat_max: float, lon_min: float, lon_max: float, grid_resolution: float = 0.1):
    """
    Generate a risk heatmap by running inference on a grid of points.
    Returns a list of {lat, lon, risk_probability, risk_level} objects.
    For prototype: uses terrain + average rainfall values per cell.
    """
    # Implementation: iterate over lat/lon grid, call predict_risk per cell
    pass

@router.get("/model/info")
async def get_model_info():
    """Return model version, last trained date, training metrics."""
    pass
```

---

### WORKFLOW 10: Scalability + Cloud-Readiness Annotations

In `ml/src/predict.py` and `ml/src/train.py`, add the following code comments documenting how to scale:

```python
# SCALABILITY NOTES:
# 1. MODEL SERVING: This pipeline can be wrapped in a FastAPI service and deployed
#    as a Docker container on GCP Cloud Run (auto-scaling) or AWS ECS.
#
# 2. BATCH GRID INFERENCE: For heatmap generation over a 100x100 grid:
#    - Use joblib.Parallel(n_jobs=-1) for multi-core local inference
#    - For cloud: parallelize via GCP Dataflow or AWS Lambda per grid cell
#
# 3. MODEL RETRAINING: The train.py pipeline can be scheduled as a Cloud Run Job
#    (daily/weekly) when new historical landslide data becomes available.
#
# 4. DATA INGESTION SCALING: Replace data_loader.py stub with:
#    - NASA Earthdata API connector for GPM IMERG (authenticated)
#    - Google Earth Engine Python API for Sentinel-2 NDVI
#    - IMD API connector (requires IP whitelisting)
#    - ESP32 sensor → MQTT → backend → DB pipeline
#
# 5. VECTOR DATABASE (optional for RAG on historical data):
#    Store embeddings of historical landslide reports in Pinecone/ChromaDB
#    for semantic similarity retrieval during risk context generation.
#
# 6. MULTI-INPUT TYPE SUPPORT:
#    The predict_risk() function accepts:
#    - JSON dict (from API call)
#    - pandas DataFrame row (batch mode)
#    - CSV file path (batch processing)
```

---

## TECHNICAL CONSTRAINTS

- **Language:** Python 3.10+
- **Primary ML:** scikit-learn, xgboost, shap
- **Data:** pandas, numpy, scipy
- **Serialization:** joblib (models), json (metadata)
- **Logging:** Python `logging` module (structured logs with timestamp + level)
- **Config:** All magic numbers in `config.py` — no hardcoded values scattered in code
- **No hallucinated accuracy:** Do not put any accuracy number that wasn't computed from actual model training. If showing example output, label it clearly as `# EXAMPLE OUTPUT — actual values will vary`.
- **Prototype honesty:** Add a `PROTOTYPE_WARNING` string in `config.py`:
  ```python
  PROTOTYPE_WARNING = (
      "This is a prototype system. Risk probabilities are estimates based on "
      "a simulated training dataset. Model has not been validated against real "
      "Himalayan landslide events. Do not use for operational emergency decisions."
  )
  ```

---

## REQUIREMENTS.TXT TO GENERATE

```
scikit-learn>=1.4.0
xgboost>=2.0.0
shap>=0.45.0
pandas>=2.0.0
numpy>=1.26.0
scipy>=1.12.0
joblib>=1.3.0
matplotlib>=3.8.0
seaborn>=0.13.0
fastapi>=0.110.0
pydantic>=2.0.0
uvicorn>=0.27.0
python-dotenv>=1.0.0
```

---

## OUTPUT EXPECTATIONS

After running the pipeline (`python run_training.py`), the following must exist:

```
ml/
├── data/
│   └── prototype_training_data.csv        ← 5000 rows synthetic data
├── models/
│   ├── logistic_regression.joblib
│   ├── random_forest.joblib
│   ├── xgboost.joblib
│   ├── best_model.joblib                  ← copy of highest PR-AUC model
│   ├── preprocessor.joblib                ← imputer + scaler
│   └── model_metadata.json                ← version, date, features, metrics
├── reports/
│   ├── evaluation_report.txt              ← full metrics for all 3 models
│   ├── shap_summary.png                   ← global SHAP feature importance
│   └── shap_force_example.html            ← single prediction explanation
└── src/
    └── (all Python files as specified)
```

And calling `predict_risk({"latitude": 27.5, "longitude": 88.5, "rainfall_24hr_mm": 120, ...})` must return a valid JSON dict.

---

## FINAL INSTRUCTIONS TO AI

1. Build all files in the `ml/` package structure exactly as specified.
2. Implement all 10 workflows. If a workflow requires a placeholder (e.g., real API call), implement it as a stub with a clear `# TODO: replace with real API call` comment.
3. The synthetic data generator must produce realistic correlated patterns — not random noise.
4. Every function must have a docstring explaining inputs, outputs, and any assumptions.
5. Do not skip the SHAP explainability — it is required for the demo.
6. Do not skip the `cascade_input` key in the `predict_risk()` output — it feeds the downstream cascade engine.
7. Use `summarized chunking` in the data loader: when loading large datasets, read in chunks using `pd.read_csv(chunksize=10000)` and process iteratively.
8. The `config.py` file is the single source of truth — all thresholds, feature names, file paths defined there.
9. Run `python run_training.py` at the end and confirm all 3 models train and evaluate without errors.
10. Print a final summary table comparing all 3 models side by side on: Precision, Recall, F1, ROC-AUC, PR-AUC.

---

*This prompt was generated from the official SIH project knowledge base documents. All source-derived facts are preserved. Proposed/to-be-decided items are clearly labeled as prototype assumptions.*
