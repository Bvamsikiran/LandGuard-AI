# Frontend-to-Backend Communication (High Level)

Here's a clear and practical list of **buttons + UI components + backend services** that your frontend friend needs to build so the AI/ML pipeline is properly usable and impressive in the demo.

## 1. Main Screens Related to AI/ML

| Screen | Purpose | Priority |
|---|---|---|
| **Dashboard / Home** | Overall risk overview + heatmap | High |
| **Risk Map** | Interactive map with risk layers | High |
| **Location Risk Details** | Detailed prediction for a specific place | High |
| **Alerts Panel** | List of current high-risk areas | High |
| **Model Insights / Explainability** | Show why the model predicted high risk | Medium-High |
| **Field Report Upload** | Citizens/officials upload geo-tagged photos | Medium |
| **Admin / Model Status** | Show model version, last trained, etc. | Low (nice to have) |

## 2. Important Buttons & What They Should Do

### A. On the Risk Map Screen

| Button / Interaction | What it does | Backend Service it calls |
|---|---|---|
| **Click on Map** | Predict risk for that exact location | `POST /api/v1/risk/predict` |
| **Search Location (search bar)** | Search place -> auto predict | `POST /api/v1/risk/predict` |
| **"Show Risk Heatmap" toggle** | Turn heatmap on/off | `GET /api/v1/risk/heatmap` |
| **"Filter by Risk Level" (Low / Moderate / High / Very High)** | Filter markers/heatmap | Client-side + optional API filter |
| **"Refresh Risk Data" button** | Force refresh latest predictions | `GET /api/v1/risk/heatmap` or `/predict` |
| **"View Details" on any risk marker** | Open side panel with full explanation | Uses data from previous predict call |

### B. On Location Risk Details Panel (after clicking a location)

| Button / Element | What it does | Backend Service |
|---|---|---|
| **Risk Level Badge (VERY HIGH / HIGH etc.)** | Visual indicator | Comes from predict response |
| **"Why this risk?" / Explain button** | Shows top contributing factors (SHAP) | Already included in `POST /api/v1/risk/predict` response |
| **"View Historical Landslides nearby"** | Show past events around this point | `GET /api/v1/historical/landslides?lat=..&lon=..` |
| **"Subscribe to Alerts" for this location** | Save location for future alerts | `POST /api/v1/alerts/subscribe` |
| **"Share Risk Report"** | Generate shareable link/PDF | Optional |

### C. Alerts Section

| Button | Action | Backend Service |
|---|---|---|
| **"View All Active Alerts"** | Open full alerts list | `GET /api/v1/risk/alerts` |
| **"Acknowledge Alert"** | Mark as seen by authority | `POST /api/v1/alerts/{id}/acknowledge` |
| **"Filter Alerts" (by district / severity)** | Filter the list | Client-side or query params |

### D. Field Reporting (Citizen / Official)

| Button | Action | Backend Service |
|---|---|---|
| **"Report Slope Movement / Crack / Blocked Road"** | Open camera + form | `POST /api/v1/reports/upload` |
| **"Upload Photo + Location"** | Submit geo-tagged report | `POST /api/v1/reports/upload` |
| **"Submit Report"** | Final submission | Same as above |

## 3. Recommended Backend Services (APIs) your friend will need

These are the exact services the frontend should call:

```text
1. POST /api/v1/risk/predict
   -> Predict risk for one lat/lon (most important)

2. GET /api/v1/risk/heatmap
   -> Get risk values for the current map view (for heatmap)

3. GET /api/v1/risk/alerts
   -> Get list of current high-risk alerts

4. GET /api/v1/risk/location/{id}
   -> Get saved/latest prediction for a known location

5. POST /api/v1/reports/upload
   -> Upload geo-tagged photo/video + description

6. GET /api/v1/historical/landslides
   -> Nearby historical landslide points (optional but good)

7. GET /api/v1/model/info
   -> Model version, last updated, accuracy metrics (for credibility)
```

## 4. Suggested UI Flow (Simple & Impressive)

1. User opens the app -> sees **Risk Heatmap** on the map (default view).
2. User clicks anywhere on the map -> side panel opens with:
   - Risk Probability (e.g. 87%)
   - Risk Level badge (VERY HIGH)
   - Top 4-5 contributing factors with percentages
   - Button: **"Why this prediction?"**
3. User can toggle heatmap on/off and filter by risk level.
4. High risk areas automatically appear in the **Alerts** panel.
5. Officials can click **"Acknowledge"** on alerts.
6. Citizens can upload photos of cracks/slope movement.

## 5. Extra Recommendations for Good Demo

- Show a loading skeleton while waiting for the prediction (looks professional).
- Use color coding strongly:
  - Green = Low
  - Yellow = Moderate
  - Orange = Hig