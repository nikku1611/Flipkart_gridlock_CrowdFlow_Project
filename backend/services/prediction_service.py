"""
CrowdFlow — Prediction Service
================================
Wraps the ML prediction module for use by FastAPI endpoints.
Handles model loading, feature transformation, and SHAP explanations.
"""

import sys
import os
import json
import uuid
from typing import Dict, Optional

# Add ML directory to path
ML_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "ml")
sys.path.insert(0, ML_DIR)

from predict import CrowdFlowPredictor

# Cache for predictions (for SHAP lookup by prediction_id)
_prediction_cache: Dict[str, dict] = {}
_predictor: Optional[CrowdFlowPredictor] = None


def get_predictor() -> CrowdFlowPredictor:
    """Get or initialize the predictor singleton."""
    global _predictor
    if _predictor is None:
        _predictor = CrowdFlowPredictor(
            models_dir=os.path.join(ML_DIR, "models")
        )
    return _predictor


def predict_event_impact(event_dict: dict) -> dict:
    """
    Make predictions for an event and cache the result.
    Returns prediction results with a prediction_id.
    """
    predictor = get_predictor()
    results = predictor.predict(event_dict)

    # Generate unique prediction ID
    prediction_id = str(uuid.uuid4())[:8]
    results["prediction_id"] = prediction_id

    # Cache for later SHAP lookup
    _prediction_cache[prediction_id] = {
        "event": event_dict,
        "results": results,
    }

    # Keep cache small
    if len(_prediction_cache) > 1000:
        oldest_keys = list(_prediction_cache.keys())[:500]
        for k in oldest_keys:
            del _prediction_cache[k]

    return results


def get_prediction_explanation(prediction_id: str) -> dict:
    """
    Get feature importance explanation for a cached prediction.
    """
    predictor = get_predictor()

    cached = _prediction_cache.get(prediction_id)
    if not cached:
        return {"error": "Prediction not found. Predictions are cached temporarily."}

    # Return precomputed feature importances for each target
    explanations = {}
    for target in ["congestion_severity", "required_manpower", "time_to_resolution"]:
        importance = predictor.get_feature_importance(target)
        if importance:
            explanations[target] = importance

    return {
        "prediction_id": prediction_id,
        "explanations": explanations,
    }


def get_model_metrics() -> dict:
    """Load and return model comparison metrics."""
    results_path = os.path.join(ML_DIR, "results", "model_comparison.json")
    metadata_path = os.path.join(ML_DIR, "models", "model_metadata.json")

    metrics = {}
    if os.path.exists(metadata_path):
        with open(metadata_path) as f:
            metrics["metadata"] = json.load(f)

    if os.path.exists(results_path):
        with open(results_path) as f:
            metrics["comparison"] = json.load(f)

    return metrics
