"""
CrowdFlow — FastAPI Main Application
======================================
Event-Driven Traffic Congestion Intelligence System API.
Loads ML models at startup and serves predictions, historical data, and analytics.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sys
import os

# Add project directories to path
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "ml"))

from routers.predict import router as predict_router, model_router
from routers.events import router as events_router

# ---------------------------------------------------------------------------
# App initialization
# ---------------------------------------------------------------------------
app = FastAPI(
    title="CrowdFlow API",
    description="Event-Driven Traffic Congestion Intelligence System — "
                "Predicts severity, manpower needs, and resolution time for traffic events.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Include routers
# ---------------------------------------------------------------------------
app.include_router(predict_router)
app.include_router(model_router)
app.include_router(events_router)


# ---------------------------------------------------------------------------
# Startup / health
# ---------------------------------------------------------------------------
@app.on_event("startup")
async def startup_event():
    """Pre-load ML models at startup for fast inference."""
    try:
        from services.prediction_service import get_predictor
        predictor = get_predictor()
        print(f"[startup] Models loaded: {list(predictor.models.keys())}")
    except Exception as e:
        print(f"[startup] Warning: Could not load models — {e}")
        print("[startup] API will run but predictions may fail until models are trained")


@app.get("/", tags=["health"])
async def root():
    """Health check endpoint."""
    return {
        "name": "CrowdFlow API",
        "status": "healthy",
        "version": "1.0.0",
        "description": "Event-Driven Traffic Congestion Intelligence System",
    }


@app.get("/health", tags=["health"])
async def health_check():
    """Detailed health check."""
    model_status = {}
    try:
        from services.prediction_service import get_predictor
        predictor = get_predictor()
        for target in ["congestion_severity", "required_manpower", "time_to_resolution"]:
            model_status[target] = target in predictor.models
    except:
        model_status = {"error": "Models not loaded"}

    return {
        "status": "healthy",
        "models": model_status,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
