"""
run_live_integration.py — Live HTTP integration test matching AGENTS.md FINAL VERIFICATION
plus comprehensive contract audits.
"""

import json
import sys
import urllib.error
import urllib.request

base = "http://127.0.0.1:8000"


def run_tests():
    all_pass = True

    print("=== 1. CORE ROUTE VERIFICATION ===")
    core_tests = [
        ("GET  /", "GET", base + "/", None),
        (
            "POST /predict (lat/lon format)",
            "POST",
            base + "/api/v1/risk/predict",
            json.dumps({"lat": 27.33, "lon": 88.61, "rainfall_24hr_mm": 120.0}),
        ),
        (
            "POST /predict (Arunachal Pradesh)",
            "POST",
            base + "/api/v1/risk/predict",
            json.dumps({"lat": 27.1004, "lon": 93.6166}),
        ),
        ("GET  /heatmap (flat array)", "GET", base + "/api/v1/risk/heatmap", None),
        ("GET  /locations", "GET", base + "/api/v1/risk/locations", None),
        ("GET  /model/info (flat schema)", "GET", base + "/api/v1/risk/model/info", None),
    ]

    for label, method, url, body in core_tests:
        req = urllib.request.Request(
            url,
            data=body.encode() if body else None,
            headers={"Content-Type": "application/json"} if body else {},
        )
        req.get_method = lambda: method
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
                print(f"[PASS] {label}")
        except Exception as e:
            print(f"[FAIL] {label}: {e}")
            all_pass = False

    print("\n=== 2. ALL 8 NORTHEAST STATES LIVE INFERENCE ===")
    states = [
        {"lat": 27.33, "lon": 88.61, "name": "Gangtok, Sikkim"},
        {"lat": 27.1004, "lon": 93.6166, "name": "Itanagar, Arunachal Pradesh"},
        {"lat": 25.6751, "lon": 94.1086, "name": "Kohima, Nagaland"},
        {"lat": 25.5788, "lon": 91.8933, "name": "Shillong, Meghalaya"},
        {"lat": 26.1445, "lon": 91.7362, "name": "Guwahati, Assam"},
        {"lat": 23.7271, "lon": 92.7176, "name": "Aizawl, Mizoram"},
        {"lat": 24.8170, "lon": 93.9368, "name": "Imphal, Manipur"},
        {"lat": 23.8315, "lon": 91.2868, "name": "Agartala, Tripura"},
    ]
    for s in states:
        body = json.dumps({"lat": s["lat"], "lon": s["lon"]}).encode("utf-8")
        req = urllib.request.Request(
            base + "/api/v1/risk/predict",
            data=body,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                data = json.loads(r.read())
                if r.status == 200 and data.get("risk") in ["Low", "Moderate", "High", "Very High"]:
                    print(f"[PASS] {s['name']} -> HTTP 200, risk={data.get('risk')}, prob={data.get('prob')}%")
                else:
                    print(f"[FAIL] {s['name']} -> HTTP {r.status}, response={data}")
                    all_pass = False
        except Exception as e:
            print(f"[FAIL] {s['name']}: {e}")
            all_pass = False

    print("\n=== 3. OUT-OF-BOUNDS REJECTION (HTTP 422) ===")
    oob_coords = [
        ("Delhi", 28.6139, 77.2090),
        ("Mumbai", 19.0760, 72.8777),
    ]
    for name, lat, lon in oob_coords:
        body = json.dumps({"lat": lat, "lon": lon}).encode("utf-8")
        req = urllib.request.Request(
            base + "/api/v1/risk/predict",
            data=body,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                print(f"[FAIL] {name} was unexpectedly accepted with HTTP {r.status}")
                all_pass = False
        except urllib.error.HTTPError as e:
            if e.code == 422:
                print(f"[PASS] Out-of-bounds {name} correctly rejected with HTTP 422")
            else:
                print(f"[FAIL] {name} returned HTTP {e.code} instead of 422")
                all_pass = False

    print("\n=== 4. LOCATIONS CONTRACT VALIDATION ===")
    try:
        req = urllib.request.Request(base + "/api/v1/risk/locations")
        with urllib.request.urlopen(req, timeout=10) as r:
            locs = json.loads(r.read())
            print(f"Total monitored locations: {len(locs)}")
            required_keys = ["id", "name", "state", "district", "lat", "lon", "risk", "prob", "factors"]
            missing = [k for k in required_keys if k not in locs[0]]
            if not missing and len(locs) == 8:
                print(f"[PASS] Locations schema has all required keys: {required_keys}")
            else:
                print(f"[FAIL] Locations schema missing keys: {missing}, count={len(locs)}")
                all_pass = False
    except Exception as e:
        print(f"[FAIL] /locations query error: {e}")
        all_pass = False

    print("\n=== 5. HEATMAP CONTRACT VALIDATION ===")
    try:
        req = urllib.request.Request(base + "/api/v1/risk/heatmap")
        with urllib.request.urlopen(req, timeout=15) as r:
            heatmap = json.loads(r.read())
            if isinstance(heatmap, list) and len(heatmap) > 0:
                sample = heatmap[0]
                if all(k in sample for k in ("lat", "lon", "weight", "risk")):
                    print(f"[PASS] Heatmap is flat array with {len(heatmap)} cells, sample={sample}")
                else:
                    print(f"[FAIL] Heatmap cell missing required keys: {sample}")
                    all_pass = False
            else:
                print(f"[FAIL] Heatmap is not a list or is empty: {type(heatmap)}")
                all_pass = False
    except Exception as e:
        print(f"[FAIL] /heatmap query error: {e}")
        all_pass = False

    print("\n=== 6. MODEL INFO CONTRACT VALIDATION ===")
    try:
        req = urllib.request.Request(base + "/api/v1/risk/model/info")
        with urllib.request.urlopen(req, timeout=10) as r:
            info = json.loads(r.read())
            required_info_keys = ["modelName", "version", "accuracy", "precision", "recall", "f1Score", "datasetSize", "status", "lastTrained"]
            missing_info = [k for k in required_info_keys if k not in info]
            if not missing_info:
                print(f"[PASS] Model info schema matches frontend expectations: {info['modelName']} ({info['version']})")
            else:
                print(f"[FAIL] Model info missing keys: {missing_info}")
                all_pass = False
    except Exception as e:
        print(f"[FAIL] /model/info query error: {e}")
        all_pass = False

    print("\n=============================================")
    print("INTEGRATION STATUS:", "ALL PASS" if all_pass else "FAILURES - check logs")
    print("=============================================")
    if not all_pass:
        sys.exit(1)


if __name__ == "__main__":
    run_tests()
