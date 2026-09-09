"""
ml/src/__init__.py
==================
Package initializer for the Multi-Hazard AI/ML Prediction Pipeline.
Member 3 Responsibility: AI/ML Prediction

Exposes the public inference API so downstream consumers (FastAPI backend)
can import with a single line:

    from ml.src.predict import predict_risk
"""

__version__ = "1.0.0"
__author__ = "SIH 2026 Team — Member 3 (AI/ML)"

# Public re-export for clean FastAPI backend imports
try:
    from ml.src.predict import ModelNotLoadedError, predict_risk
except ImportError:
    pass
