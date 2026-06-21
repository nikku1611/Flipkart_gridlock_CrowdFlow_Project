"""
CrowdFlow — Prediction Router
================================
FastAPI endpoints for ML predictions and model transparency.
"""

from fastapi import APIRouter, HTTPException
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "services"))

from schemas import (
    EventInput, DiversionInput,
    EventImpactResponse, DiversionPlanResponse,
    FeatureImportanceResponse, ModelMetricsResponse,
)
from services.prediction_service import (
    predict_event_impact, get_prediction_explanation, get_model_metrics
)
from services.diversion_service import generate_diversion_plan

router = APIRouter(prefix="/predict", tags=["predictions"])
model_router = APIRouter(prefix="/model", tags=["model"])


@router.post("/event-impact", response_model=EventImpactResponse)
async def predict_event(event: EventInput):
    """
    Predict the impact of a traffic event.
    Returns congestion severity, required manpower, and time to resolution.
    """
    try:
        event_dict = event.model_dump()
        # Set defaults
        if not event_dict.get("start_datetime"):
            event_dict["start_datetime"] = datetime.now().isoformat()
        if event_dict.get("endlatitude") is None:
            event_dict["endlatitude"] = event_dict["latitude"]
        if event_dict.get("endlongitude") is None:
            event_dict["endlongitude"] = event_dict["longitude"]

        results = predict_event_impact(event_dict)

        return EventImpactResponse(
            prediction_id=results.get("prediction_id", "unknown"),
            congestion_severity=results.get("congestion_severity"),
            required_manpower=results.get("required_manpower"),
            time_to_resolution=results.get("time_to_resolution"),
            event_input=event_dict,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")


@router.post("/diversion-plan", response_model=DiversionPlanResponse)
async def get_diversion_plan(input_data: DiversionInput):
    """
    Generate a rule-based response plan (barricades, diversions, deployment).
    This combines the ML predictions with operational business logic.
    """
    try:
        plan = generate_diversion_plan(
            severity=input_data.severity.value,
            latitude=input_data.latitude,
            longitude=input_data.longitude,
            requires_road_closure=input_data.requires_road_closure,
            event_cause=input_data.event_cause.value,
            corridor=input_data.corridor or "Non-corridor",
            zone=input_data.zone or "Unknown",
            manpower_needed=input_data.manpower_needed or "3-5",
            police_station=input_data.police_station,
        )
        return DiversionPlanResponse(**plan)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Diversion plan failed: {str(e)}")


@model_router.get("/explain/{prediction_id}")
async def explain_prediction(prediction_id: str):
    """
    Return SHAP/feature-importance explanation for a given prediction.
    """
    try:
        explanation = get_prediction_explanation(prediction_id)
        if "error" in explanation:
            raise HTTPException(status_code=404, detail=explanation["error"])
        return explanation
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@model_router.get("/metrics")
async def model_metrics():
    """
    Return the model comparison metrics (XGBoost vs LightGBM vs CatBoost).
    """
    try:
        metrics = get_model_metrics()
        if not metrics:
            raise HTTPException(status_code=404, detail="No metrics available. Train models first.")
        return metrics
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
