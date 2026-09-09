# AI/ML Prediction Pipeline — Multi-Hazard Early Warning System (Sikkim Prototype)

> **Team Role:** Member 3 — AI/ML & Risk Prediction  
> **Target Region:** Sikkim, Eastern Himalayas (Pilot Area: Lat 27.0°–28.1°N, Lon 88.0°–89.0°E)  
> **Problem Statement:** SIH Multi-Hazard Early Warning and Cascade Risk Assessment System

---

## ⚠️ Prototype Warning & Scientific Honesty Notice

```
This is a prototype system. Risk probabilities are estimates based on a simulated 
training dataset. The model has not yet been calibrated or validated against real 
Himalayan landslide events. Do not use for operational emergency decisions.
```

- **We do NOT claim the AI predicts the exact time a landslide will occur.**
- **We do NOT claim >97% accuracy.** High raw accuracy in imbalanced data (~8% positive events) is misleading. We optimize and select models strictly on **PR-AUC (Precision-Recall Area Under Curve)** and **Recall (Detection Rate)**.
- **We do NOT claim live satellite feeds without latency.** NASA GPM IMERG Early Run has ~4 hours latency; Sentinel-2 has a 5-day revisit cycle.

---

## Architecture & Data Flow

```
DATA SOURCES (NASA GPM IMERG, SRTM DEM, Sentinel-2 NDVI, ISRO Landslide Atlas, IoT Inclinometers)
  ↓
ml/src/data_loader.py (Chunked Ingestion & Correlated Synthetic Prototype Generator)
  ↓
ml/src/preprocessing.py (Validation, Plausibility Ranges, Median/Mode Imputation, Freshness Scoring)
  ↓
ml/src/features.py (Rainfall Intensity, Antecedent Anomaly, Soil Saturation, Log1p, One-Hot Encoding)
  ↓
ml/src/train.py (Temporal 80/20 Split, Class-Weighted Baselines: LR, RF, XGBoost, 5-Fold Stratified CV)
  ↓
ml/src/evaluate.py (PR-AUC Selection, Confusion Matrix, Recall Analysis, Reliability Diagrams)
  ↓
ml/src/explain.py (SHAP Global Beeswarm Summary & Local Top-5 Factor Explanations)
  ↓
ml/src/predict.py (Runtime Inference Function for FastAPI Backend & Cascade Engine Payload)
```

---

## Package Structure

```
ml/
├── data/
│   ├── README.md                  ← Data sources & replacement instructions
│   └── prototype_training_data.csv ← 5,000 rows correlated synthetic dataset
├── models/
│   ├── logistic_regression.joblib
│   ├── random_forest.joblib
│   ├── xgboost.joblib
│   ├── best_model.joblib          ← Highest PR-AUC model (persisted for inference)
│   ├── preprocessor.joblib        ← Imputer & encoder pipeline
│   └── model_metadata.json        ← Training date, features, CV metrics, hyperparams
├── reports/
│   ├── evaluation_report.txt      ← Comprehensive metrics report for all 3 models
│   ├── calibration_*.png          ← Reliability diagrams (calibration curves)
│   ├── shap_summary.png           ← Global feature importance beeswarm plot
│   └── shap_force_example.html    ← Interactive SHAP force plot for high-risk event
├── src/
│   ├── __init__.py
│   ├── config.py                  ← Single source of truth: constants, ranges, thresholds
│   ├── data_loader.py             ← Synthetic data generator & chunked CSV loader
│   ├── preprocessing.py           ← Cleaning, range validation, missing value imputation
│   ├── features.py                ← 20 engineered features & transformations
│   ├── train.py                   ← Model training, class imbalance, CV, persistence
│   ├── evaluate.py                ← PR-AUC evaluation, threshold analysis, reports
│   ├── explain.py                 ← SHAP TreeExplainer & local factor attribution
│   ├── predict.py                 ← Runtime predict_risk() inference endpoint
│   ├── api_stub.py                ← FastAPI router for Backend integration
│   └── utils.py                   ← Logging, data freshness scoring, helpers
├── run_training.py                ← Master end-to-end training entry point
├── requirements.txt               ← Dependency specifications
└── README.md                      ← This documentation
```

---

## Quick Start

### 1. Install Dependencies
```bash
pip install -r ml/requirements.txt
```

### 2. Run End-to-End Training Pipeline
```bash
python ml/run_training.py
```
This single command:
1. Bootstraps directories and generates `ml/data/prototype_training_data.csv` (5,000 correlated rows)
2. Preprocesses, validates ranges, and fits median/mode imputers
3. Engineers 20 geospatial and hydrometeorological features
4. Splits data temporally (80% train / 20% test) to prevent storm-event leakage
5. Trains Logistic Regression, Random Forest, and XGBoost with class weighting
6. Runs 5-fold cross-validation
7. Compares models by PR-AUC and saves `best_model.joblib`
8. Generates SHAP global summary plot and force plot
9. Saves `ml/reports/evaluation_report.txt` and prints side-by-side comparison table

---

## Using the Inference Function (`predict_risk`)

Member 5 (Backend) can import and call `predict_risk` directly:

```python
from ml.src.predict import predict_risk

# Example observation payload
observation = {
    "latitude": 27.33,
    "longitude": 88.61,
    "rainfall_24hr_mm": 125.0,
    "soil_moisture_pct": 82.0,
    "slope_deg": 41.5,
    "elevation_m": 1720.0,
    "land_cover_class": "bare",
    "historical_landslide_density": 15.0,
    "distance_to_river_km": 0.35,
    "tilt_change_deg": 0.92,
    # Any missing features are automatically imputed with stored medians
}

result = predict_risk(observation)
print(result)
```

### Response Schema

```json
{
  "location": {
    "latitude": 27.33,
    "longitude": 88.61
  },
  "timestamp": "2026-09-08T15:20:00Z",
  "risk_probability": 0.842,
  "risk_level": "VERY_HIGH",
  "risk_level_color": "red",
  "model_used": "RandomForestClassifier",
  "model_version": "v1.0.0-prototype",
  "confidence_note": "OK: Full observational data available",
  "data_freshness": "FRESH",
  "top_factors": [
    {"feature": "rainfall_24hr_mm", "shap_value": 0.31, "direction": "increases_risk", "contribution_pct": 32.5},
    {"feature": "soil_moisture_pct", "shap_value": 0.24, "direction": "increases_risk", "contribution_pct": 25.1},
    {"feature": "slope_deg", "shap_value": 0.18, "direction": "increases_risk", "contribution_pct": 18.8},
    {"feature": "tilt_change_deg", "shap_value": 0.12, "direction": "increases_risk", "contribution_pct": 12.6},
    {"feature": "distance_to_river_km", "shap_value": -0.06, "direction": "decreases_risk", "contribution_pct": 6.3}
  ],
  "input_feature_summary": {
    "rainfall_24hr_mm": 125.0,
    "rainfall_intensity_mm_hr": 42.0,
    "soil_moisture_pct": 82.0,
    "slope_deg": 41.5,
    "elevation_m": 1720.0,
    "historical_events_5km": 15.0,
    "distance_to_river_km": 0.35,
    "tilt_change_deg": 0.92
  },
  "cascade_input": {
    "landslide_probability": 0.842,
    "location": {"lat": 27.33, "lon": 88.61},
    "slope_deg": 41.5,
    "distance_to_river_km": 0.35
  },
  "prototype_warning": "This is a prototype system..."
}
```

---

## FastAPI Backend Integration

Include the pre-built router into the FastAPI application:

```python
from fastapi import FastAPI
from ml.src.api_stub import router as risk_router

app = FastAPI(title="SIH Multi-Hazard Early Warning API")
app.include_router(risk_router)
```

Available endpoints:
- `POST /api/v1/risk/predict`: Single coordinate inference with SHAP factor breakdown and cascade payload.
- `GET  /api/v1/risk/heatmap`: Grid-based bounding box risk calculation for GIS mapping.
- `GET  /api/v1/risk/model/info`: Current model version, training metrics, and feature audit.

---

## Risk Level Thresholds

Configured in `ml/src/config.py`:

| Risk Level | Probability Interval | Color | Action Protocol |
|---|---|---|---|
| **LOW** | 0.00 – 0.35 | Green | Routine monitoring; normal conditions |
| **MODERATE** | 0.35 – 0.55 | Yellow | Advisory bulletin; alert local field observers |
| **HIGH** | 0.55 – 0.75 | Orange | Early warning alert; inspect vulnerable road cuts & bridges |
| **VERY_HIGH** | 0.75 – 1.00 | Red | Urgent evacuation / road closure warning; trigger cascade engine |

---

## Cloud Deployment & Scalability

1. **Model Serving:** Packaged in Docker container deployed to **GCP Cloud Run** or **AWS ECS** with auto-scaling.
2. **Batch GIS Heatmaps:** Multi-core parallel grid inference via `joblib.Parallel(n_jobs=-1)` or cloud workers via **GCP Dataflow**.
3. **Automated Retraining:** `run_training.py` scheduled as a periodic Cloud Run Job when new monsoon observations or ISRO landslide updates arrive.
4. **Cascade Integration:** `cascade_input` payload feeds downstream hydraulic river blockage and flash flood simulation engines.
