"""
test_api.py — End-to-end and integration tests for FastAPI backend and ML pipeline.
"""

import unittest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from backend.ml.src.api_stub import LocationInput
from backend.ml.src.main import app


class TestLocationInputValidation(unittest.TestCase):
    """Phase 1 validation: Geographic bounds and parameter aliases."""

    def test_all_eight_northeast_states_aliases(self):
        test_points = [
            ("Gangtok, Sikkim", 27.33, 88.61),
            ("Itanagar, Arunachal Pradesh", 27.1004, 93.6166),
            ("Kohima, Nagaland", 25.6751, 94.1086),
            ("Shillong, Meghalaya", 25.5788, 91.8933),
            ("Aizawl, Mizoram", 23.7271, 92.7176),
            ("Imphal, Manipur", 24.817, 93.9368),
            ("Agartala, Tripura", 23.8315, 91.2868),
            ("Guwahati, Assam", 26.1445, 91.7362),
        ]
        for name, lat, lon in test_points:
            # Test frontend alias (lat/lon)
            loc_alias = LocationInput(**{"lat": lat, "lon": lon})
            self.assertAlmostEqual(loc_alias.latitude, lat, places=3)
            self.assertAlmostEqual(loc_alias.longitude, lon, places=3)

            # Test standard names (latitude/longitude)
            loc_std = LocationInput(**{"latitude": lat, "longitude": lon})
            self.assertAlmostEqual(loc_std.latitude, lat, places=3)
            self.assertAlmostEqual(loc_std.longitude, lon, places=3)

    def test_out_of_bounds_rejection(self):
        # Out of bounds coordinates (Delhi, Mumbai, Chennai)
        oob_points = [
            ("Delhi", 28.6139, 77.2090),      # lon too low (< 87.0)
            ("Mumbai", 19.0760, 72.8777),     # lat too low (< 21.5), lon too low
            ("Kashmir", 34.0837, 74.7973),    # lat too high (> 30.0)
            ("Myanmar border east", 25.0, 99.0), # lon too high (> 98.0)
        ]
        for name, lat, lon in oob_points:
            with self.assertRaises(ValidationError, msg=f"Should reject {name}"):
                LocationInput(**{"lat": lat, "lon": lon})


class TestFastAPIEndpoints(unittest.TestCase):
    """FastAPI REST API integration tests."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_health_check(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get("service"), "Landguard AI/ML Predictive Analytics Engine")
        self.assertEqual(data.get("status"), "operational")

    def test_predict_endpoint_frontend_contract(self):
        payload = {"lat": 27.33, "lon": 88.61, "rainfall_24hr_mm": 115.0}
        resp = self.client.post("/api/v1/risk/predict", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        # Frontend expected keys
        expected_frontend_keys = ["lat", "lon", "risk", "prob", "factors", "modelUsed", "confidenceNote"]
        for key in expected_frontend_keys:
            self.assertIn(key, data, f"Missing key '{key}' in prediction response")

        self.assertIn(data["risk"], ["Low", "Moderate", "High", "Very High"])
        self.assertIsInstance(data["prob"], int)
        self.assertTrue(0 <= data["prob"] <= 100)
        self.assertIsInstance(data["factors"], list)
        if data["factors"]:
            factor = data["factors"][0]
            self.assertIn("label", factor)
            self.assertIn("percent", factor)
            self.assertIn("value", factor)

    def test_predict_all_eight_states(self):
        states = [
            ("Gangtok, Sikkim", 27.33, 88.61),
            ("Itanagar, Arunachal", 27.1, 93.62),
            ("Kohima, Nagaland", 25.68, 94.11),
            ("Shillong, Meghalaya", 25.58, 91.89),
            ("Guwahati, Assam", 26.14, 91.74),
            ("Aizawl, Mizoram", 23.73, 92.72),
            ("Imphal, Manipur", 24.82, 93.94),
            ("Agartala, Tripura", 23.83, 91.29),
        ]
        for name, lat, lon in states:
            resp = self.client.post("/api/v1/risk/predict", json={"lat": lat, "lon": lon})
            self.assertEqual(resp.status_code, 200, f"Failed for {name}: {resp.text}")
            data = resp.json()
            self.assertIn(data["risk"], ["Low", "Moderate", "High", "Very High"])

    def test_heatmap_endpoint(self):
        resp = self.client.get(
            "/api/v1/risk/heatmap?lat_min=27.0&lat_max=27.2&lon_min=88.0&lon_max=88.2&grid_resolution=0.1"
        )
        self.assertEqual(resp.status_code, 200)
        cells = resp.json()
        self.assertIsInstance(cells, list)
        self.assertGreater(len(cells), 0)
        for c in cells:
            self.assertIn("lat", c)
            self.assertIn("lon", c)
            self.assertIn("weight", c)
            self.assertIn("risk", c)
            self.assertTrue(0.0 <= c["weight"] <= 1.0)
            self.assertIn(c["risk"], ["Low", "Moderate", "High", "Very High"])

    def test_model_info_endpoint(self):
        resp = self.client.get("/api/v1/risk/model/info")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        expected_fields = [
            "modelName",
            "version",
            "accuracy",
            "precision",
            "recall",
            "f1Score",
            "datasetSize",
            "status",
            "lastTrained",
        ]
        for field in expected_fields:
            self.assertIn(field, data, f"Missing '{field}' in /model/info response")

    def test_locations_endpoint(self):
        resp = self.client.get("/api/v1/risk/locations")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 12)

        required_keys = ["id", "name", "state", "district", "lat", "lon", "risk", "prob", "factors"]
        for loc in data:
            for k in required_keys:
                self.assertIn(k, loc, f"Missing key '{k}' in location {loc.get('name')}")
            self.assertIn(loc["risk"], ["Low", "Moderate", "High", "Very High"])
            self.assertTrue(0 <= loc["prob"] <= 100)

    def test_locations_endpoint_region_filter(self):
        resp = self.client.get("/api/v1/risk/locations?region=Sikkim")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data), 2)
        for loc in data:
            self.assertEqual(loc["state"], "Sikkim")

    def test_heatmap_region_sikkim(self):
        resp = self.client.get("/api/v1/risk/heatmap?region=Sikkim")
        self.assertEqual(resp.status_code, 200)
        cells = resp.json()
        self.assertIsInstance(cells, list)
        self.assertGreater(len(cells), 10)
        for c in cells:
            self.assertIn("lat", c)
            self.assertIn("lon", c)
            self.assertIn("weight", c)
            self.assertIn("risk", c)


if __name__ == "__main__":
    unittest.main()
