# SIH Internal Contest VNR - Project Structure

This document outlines the problem statement and team responsibilities for the SIH internal contest.

## Project Overview

The goal is to develop a system that estimates landslide risk/probability for a geographic location using environmental, terrain, and historical data. We are **not** claiming that AI can predict the exact time of a landslide.

**Target:** Estimate the probability/risk of landslide occurrence and explain the major factors contributing to that risk.

### Architecture (Software/AI/GIS Solution)

The project will be built as a software/AI/GIS solution without hardware sensors due to budget constraints.

Rainfall data + Satellite data + DEM/Terrain + Soil data + Historical landslides
↓
Data preprocessing
↓
GIS feature generation
↓
AI/ML model
↓
Landslide probability/risk
↓
GIS risk map
↓
Affected roads/villages/infrastructure
↓
Early warning / dashboard

*Note: Instead of claiming "Our system uses soil-moisture sensors for real-time prediction," state that "The system integrates available meteorological, satellite-derived, terrain, soil and historical landslide data to estimate landslide risk."*

\---

## 6-Member Team Structure

Since the team consists of 6 members, the roles have been consolidated. Testing, PPT, and Research will be handled by everyone at the end.

|Member|Main Responsibility|Priority|
|-|-|-|
|**Member 1**|🎨 Frontend + Dashboard|High|
|**Member 2**|📊 Data Collection + Data Pipeline|Very High|
|**Member 3**|🤖 AI/ML Prediction|Very High|
|**Member 4 (You)**|🗺️ GIS + Geospatial Analysis|Very High|
|**Member 5**|🖥️ Backend + Database|Very High|
|**Member 6**|🚨 Risk Engine + Alerts + Integration|High|
|*Everyone*|Testing + PPT + Research|*At end*|

### System Flow

1. **Collect data:** Rainfall + satellite + soil + DEM + historical landslides
2. **Process data:** Member 2
3. **Understand location/terrain:** Member 4 (You)
4. **Predict landslide probability:** Member 3
5. **Store \& serve everything:** Member 5
6. **Convert prediction → risk + alert:** Member 6
7. **Show it on map/dashboard:** Member 1

\---

## Member Responsibilities Detailed

### 👨‍💻 MEMBER 3 — ( YOU )  AI/ML \& RISK PREDICTION

**Goal:** Develop the model that estimates landslide risk/probability for a geographic location.

**1. First — research before coding**

* Do NOT immediately choose a model.
* Research historical landslide prediction/susceptibility using reliable papers and datasets (focusing on Northeast India, Sikkim, Arunachal Pradesh, Himalayan region, or India generally).
* Investigate features used in scientific studies: Rainfall, Antecedent rainfall, Soil moisture, Slope, Elevation, Aspect, Curvature, Lithology/geology, Land use / land cover, NDVI, Distance from river, Distance from road, Historical landslides, Temperature.

**2. Determine our prediction target**

* Investigate options:

  * Option A: Landslide (0 = No, 1 = Yes)
  * Option B: Risk probability (0 → 1)
  * Option C: Risk category (LOW, MODERATE, HIGH, VERY HIGH)
* *Preference:* Binary/event probability internally → convert calibrated probability into risk categories for the dashboard. Verify with available data.

**3. Dataset investigation**

* Coordinate with Member 2 (Data sources).
* Potential features include various rainfall intervals, soil moisture, terrain features (elevation, slope, etc.), NDVI, land cover, and distances to roads/rivers.
* *Important:* Begin with a historical/static prototype dataset while Member 2 obtains actual sources.

**4. Start with baseline models**

* Train baseline models: Logistic Regression, Random Forest, XGBoost.
* Evaluate beyond accuracy using Precision, Recall, F1-score, ROC-AUC, PR-AUC, Confusion Matrix, and Calibration.
* Recall is particularly important for disaster prediction.

**5. ⚠️ Avoid the accuracy trap**

* Do not rely solely on accuracy, especially with imbalanced datasets (e.g., 95% no landslide, 5% landslide).
* Investigate class imbalance, stratified splitting, appropriate sampling, precision/recall, PR-AUC, and probability calibration.

**6. VERY IMPORTANT — avoid data leakage**

* Do not mix observations from the same landslide event into both training and test sets.
* Investigate spatial and/or temporal validation (e.g., Past events → training, Later events → testing).

**7. Feature engineering**

* Create meaningful features beyond raw rainfall: Rainfall aggregations (1h, 3h, 24h, etc.), antecedent rainfall, maximum intensity, rainfall anomaly, soil moisture, slope, elevation.
* *Concept:* Antecedent rainfall is critical as soil saturation increases risk.

**8. Explainable AI ⭐**

* Use SHAP to explain major contributing factors to the predicted risk.
* Example output: Heavy rainfall (+31%), Soil moisture (+24%), Steep slope (+18%), etc.

**9. Risk score**

* Produce outputs like `{"risk\_probability": 0.87, "risk\_level": "VERY\_HIGH"}`.
* Determine thresholds objectively using validation data, calibration, operational objectives, and false-alarm tolerance. Document the chosen thresholds.

**10. Important research question**

* Investigate if the project should use one comprehensive model or separate hazard models (e.g., Rainfall → Landslide model; River conditions → Flood model) considering cascading hazards in the NER/Himalayan region.

**11. Model output for Backend**

* Coordinate with Member 5 (Backend) on a common JSON response format (including location, timestamp, probability, risk level, top factors).

**12. Suggested project structure**

* `ml/` directory containing `data/`, `notebooks/`, `src/` (preprocessing, features, train, evaluate, predict, explain), `models/`, `reports/`, `requirements.txt`, `README.md`.

**13. Your first milestone (Phase 1)**

1. Identify historical dataset and available predictor variables.
2. Create a clean training table.
3. Perform EDA.
4. Train Logistic Regression + Random Forest + XGBoost.
5. Compare properly and investigate spatial/temporal validation.
6. Produce feature importance/SHAP analysis.
* *Most important rule:* Do not fabricate a dataset for high accuracy. A scientifically honest 75% useful model is better than a fake 97% model.

**Dependencies for Member 3:**

* Member 2 (Data): actual datasets, feature availability.
* Member 4 (GIS): terrain and geospatial features.
* Member 5 (Backend): model integration and output schema.
* Member 6 (Risk Engine): probabilities and contributing factors.

### 🗺️ MEMBER 4 — GIS \& Geospatial Analysis

* Work closely with Member 3.
* Provide geospatial features: elevation, slope, aspect, curvature, distance to rivers, drainage, land use/land cover, historical landslide locations, soil/geology.

### 🖥️ MEMBER 5 \& 🚨 MEMBER 6 (Backend, Risk Engine, Alerts, Integration)

* Member 5 focuses on Backend and Database architecture.
* Member 6 handles the Risk Engine, Alerts, and Integration.
* *Note:* The backend and risk engine need to communicate constantly to convert predictions into actionable risk levels and alerts.

