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

try:
    from backend.ml.src.api_stub import router as ml_router
except ImportError:
    try:
        from ml.src.api_stub import router as ml_router
    except ImportError:
        from api_stub import router as ml_router

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
        "http://localhost:8443",
        "http://127.0.0.1:8443",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "*",
    ],
    allow_origin_regex=r"^https?://.*\.vercel\.app$",
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


@app.get("/api/v1/health", tags=["Health"])
async def health_check() -> dict:
    """Standardized API health and telemetry endpoint."""
    return {
        "service": "Landguard AI/ML Predictive Analytics Engine",
        "status": "operational",
        "version": "1.0.0",
        "model": "Landslide-XGBoost/RF Pipeline",
        "gis_telemetry": "online",
        "coverage": "Northeast India (8 States)",
    }

