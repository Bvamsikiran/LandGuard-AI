"""
test_adapter.py — Tests for frontend schema adapter module.
"""

import unittest
from backend.ml.src.adapter import (
    format_risk_level,
    format_shap_factors,
    adapt_prediction_response,
    adapt_heatmap_response,
    adapt_model_info,
)


class TestAdapter(unittest.TestCase):

    def test_risk_level_mapping(self):
        self.assertEqual(format_risk_level("LOW"), "Low")
        self.assertEqual(format_risk_level("MODERATE"), "Moderate")
        self.assertEqual(format_risk_level("HIGH"), "High")
        self.assertEqual(format_risk_level("VERY_HIGH"), "Very High")
        # Case insensitivity
        self.assertEqual(format_risk_level("low"), "Low")
        self.assertEqual(format_risk_level("very_high"), "Very High")
        # Unknown fallback
        self.assertEqual(format_risk_level("UNKNOWN"), "Moderate")

    def test_adapt_prediction_response(self):
        ml_result = {
            "risk_probability": 0.87,
            "risk_level": "VERY_HIGH",
            "model_used": "XGBoost Classifier",
            "confidence_note": "High precision",
            "timestamp": "2026-09-08T12:00:00Z",
            "top_factors": [
                {
                    "feature": "rainfall_24hr_mm",
                    "shap_value": 0.35,
                    "direction": "increases_risk",
                    "contribution_pct": 35.0,
                },
                {
                    "feature": "slope_deg",
                    "shap_value": 0.25,
                    "direction": "increases_risk",
                    "contribution_pct": 25.0,
                },
            ],
            "location": {"latitude": 27.33, "longitude": 88.61},
        }
        raw_input = {"lat": 27.33, "lon": 88.61, "rainfall_24hr_mm": 115.0, "slope_deg": 42.0}

        adapted = adapt_prediction_response(ml_result, raw_input)
        self.assertEqual(adapted["prob"], 87)
        self.assertEqual(adapted["risk"], "Very High")
        self.assertEqual(adapted["lat"], 27.33)
        self.assertEqual(adapted["lon"], 88.61)
        self.assertEqual(adapted["modelUsed"], "XGBoost Classifier")
        self.assertEqual(len(adapted["factors"]), 2)
        self.assertEqual(adapted["factors"][0]["label"], "24h Rainfall")
        self.assertEqual(adapted["factors"][0]["percent"], 35)
        self.assertEqual(adapted["factors"][0]["value"], "115 mm")
        self.assertEqual(adapted["factors"][1]["label"], "Slope Steepness")
        self.assertEqual(adapted["factors"][1]["percent"], 25)

    def test_adapt_heatmap_response(self):
        heatmap_result = {
            "bounding_box": {"lat_min": 27.0, "lat_max": 27.2, "lon_min": 88.0, "lon_max": 88.2},
            "cell_count": 2,
            "cells": [
                {"lat": 27.0, "lon": 88.0, "risk_probability": 0.654, "risk_level": "HIGH"},
                {"lat": 27.1, "lon": 88.1, "risk_probability": 0.123, "risk_level": "LOW"},
            ],
        }
        adapted = adapt_heatmap_response(heatmap_result)
        self.assertEqual(len(adapted), 2)
        self.assertEqual(adapted[0]["lat"], 27.0)
        self.assertEqual(adapted[0]["lon"], 88.0)
        self.assertEqual(adapted[0]["weight"], 0.654)
        self.assertEqual(adapted[0]["risk"], "High")
        self.assertEqual(adapted[1]["risk"], "Low")

    def test_adapt_model_info(self):
        backend_response = {
            "status": "READY",
            "metadata": {
                "model_name": "Landslide-XGBoost Classifier",
                "version": "v4.2-NE-India",
                "training_date": "2026-08-15",
                "dataset_rows": 5000,
                "test_metrics": {
                    "accuracy": 0.942,
                    "precision": 0.928,
                    "recall": 0.916,
                    "f1": 0.922,
                },
            },
        }
        adapted = adapt_model_info(backend_response)
        self.assertEqual(adapted["modelName"], "Landslide-XGBoost Classifier")
        self.assertEqual(adapted["version"], "v4.2-NE-India")
        self.assertAlmostEqual(adapted["accuracy"], 0.942)
        self.assertAlmostEqual(adapted["f1Score"], 0.922)
        self.assertEqual(adapted["datasetSize"], 5000)
        self.assertEqual(adapted["status"], "Operational (Live ML Pipeline)")
        self.assertEqual(adapted["lastTrained"], "2026-08-15")


if __name__ == "__main__":
    unittest.main()
