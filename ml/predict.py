"""
CrowdFlow — Prediction Module
================================
Loads trained models and provides inference for all 3 targets.
Transforms raw event input into the feature vector expected by the models.
"""

import pandas as pd
import numpy as np
import os
import json
import joblib
import warnings

warnings.filterwarnings("ignore")

from feature_engineering import (
    haversine_km, FESTIVAL_WINDOWS, PEAK_HOURS_MORNING, PEAK_HOURS_EVENING,
    get_feature_columns
)

MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")


class CrowdFlowPredictor:
    """Load trained models and make predictions for new events."""

    def __init__(self, models_dir: str = MODELS_DIR):
        self.models_dir = models_dir
        self.models = {}
        self.encoders = None
        self.target_encoders = {}
        self.metadata = None
        self.feature_cols = None
        self._load_models()

    def _load_models(self):
        """Load all trained models, encoders, and metadata."""
        # Load metadata
        meta_path = os.path.join(self.models_dir, "model_metadata.json")
        if os.path.exists(meta_path):
            with open(meta_path) as f:
                self.metadata = json.load(f)
            self.feature_cols = self.metadata.get("feature_columns", get_feature_columns())

        # Load label encoders
        enc_path = os.path.join(self.models_dir, "label_encoders.joblib")
        if os.path.exists(enc_path):
            self.encoders = joblib.load(enc_path)

        # Load models for each target
        for target in ["time_to_resolution", "congestion_severity", "required_manpower"]:
            model_path = os.path.join(self.models_dir, f"{target}_model.joblib")
            if os.path.exists(model_path):
                self.models[target] = joblib.load(model_path)

            # Load target label encoders (for classification targets)
            le_path = os.path.join(self.models_dir, f"{target}_label_encoder.joblib")
            if os.path.exists(le_path):
                self.target_encoders[target] = joblib.load(le_path)

        print(f"[predict] Loaded {len(self.models)} models: {list(self.models.keys())}")

    def _build_feature_vector(self, event: dict) -> pd.DataFrame:
        """
        Transform a raw event dict into a feature vector matching training pipeline.
        This mirrors feature_engineering.py but for a single event at inference time.
        """
        row = pd.DataFrame([event])

        # Parse datetime
        ref_time = pd.to_datetime(event.get("start_datetime", event.get("created_date")),
                                   utc=True)

        # Temporal features
        row["hour_of_day"] = ref_time.hour
        row["day_of_week"] = ref_time.dayofweek
        row["is_weekend"] = 1 if ref_time.dayofweek >= 5 else 0
        row["month"] = ref_time.month
        row["day_of_month"] = ref_time.day

        season_map = {12: 1, 1: 1, 2: 1, 3: 2, 4: 2, 5: 2,
                      6: 3, 7: 3, 8: 3, 9: 3, 10: 4, 11: 4}
        row["season"] = season_map.get(ref_time.month, 1)

        row["is_peak_hour"] = 1 if (ref_time.hour in PEAK_HOURS_MORNING or
                                     ref_time.hour in PEAK_HOURS_EVENING) else 0

        is_fest = 0
        for m, d_start, d_end, _ in FESTIVAL_WINDOWS:
            if ref_time.month == m and d_start <= ref_time.day <= d_end:
                is_fest = 1
                break
        row["is_festival_season"] = is_fest

        # Spatial features
        lat = event.get("latitude", 0)
        lon = event.get("longitude", 0)
        endlat = event.get("endlatitude", lat)
        endlon = event.get("endlongitude", lon)
        row["latitude"] = lat
        row["longitude"] = lon
        row["endlatitude"] = endlat
        row["endlongitude"] = endlon
        row["start_end_distance_km"] = haversine_km(lat, lon, endlat, endlon)

        # Frequency features (use defaults if not available)
        for col in ["zone_freq", "corridor_freq", "junction_freq", "police_station_freq"]:
            row[col] = event.get(col, 50)  # Default to median-ish value

        # Event features
        row["event_type"] = event.get("event_type", "unplanned")
        row["event_cause"] = event.get("event_cause", "others")
        row["road_closure"] = int(event.get("requires_road_closure", False))
        row["corridor"] = event.get("corridor", "Non-corridor")
        row["priority"] = event.get("priority", "High")
        row["zone"] = event.get("zone", "Unknown")
        row["police_station"] = event.get("police_station", "No Police Station")
        row["veh_type"] = event.get("veh_type", "not_applicable")
        row["event_type_x_cause"] = f"{row['event_type'].iloc[0]}_{row['event_cause'].iloc[0]}"
        row["is_authenticated"] = int(event.get("authenticated", "yes") == "yes")
        row["has_cargo"] = int(bool(event.get("cargo_material")))
        row["is_hazmat"] = 0
        row["truck_age_bucket"] = -1
        row["breakdown_category"] = "not_applicable"

        # Rolling features (defaults for new events)
        for col in ["zone_events_7d", "corridor_events_7d",
                     "zone_events_30d", "corridor_events_30d"]:
            row[col] = event.get(col, 5)

        # Text features
        desc = str(event.get("description", "")).lower()
        keywords = {
            "desc_has_rally": ["rally", "dharni", "dharna"],
            "desc_has_vip": ["vip", "minister"],
            "desc_has_festival": ["festival", "celebration", "puja"],
            "desc_has_accident": ["accident", "collision", "crash"],
            "desc_has_fire": ["fire", "blaze", "burn"],
            "desc_has_protest": ["protest", "strike", "bandh"],
            "desc_has_waterlog": ["flood", "water log", "waterlog"],
        }
        for feat, kws in keywords.items():
            row[feat] = 1 if any(kw in desc for kw in kws) else 0

        # Encode categoricals
        if self.encoders:
            for col, le in self.encoders.items():
                if col in row.columns:
                    val = row[col].iloc[0]
                    if val not in le.classes_:
                        val = "__UNKNOWN__"
                    row[col] = le.transform([val])[0]

        # Select only feature columns
        if self.feature_cols:
            for col in self.feature_cols:
                if col not in row.columns:
                    row[col] = 0
            row = row[self.feature_cols]

        return row.fillna(0)

    def predict(self, event: dict) -> dict:
        """
        Make all 3 predictions for an event.
        Returns dict with severity, manpower, resolution_time, and confidence info.
        """
        X = self._build_feature_vector(event)
        results = {}

        # Time to resolution (regression)
        if "time_to_resolution" in self.models:
            pred = self.models["time_to_resolution"].predict(X)[0]
            # Reverse log transform
            ttr_minutes = float(np.expm1(pred))
            ttr_minutes = max(1.0, ttr_minutes)  # Minimum 1 minute
            results["time_to_resolution"] = {
                "value_minutes": round(ttr_minutes, 1),
                "value_hours": round(ttr_minutes / 60, 2),
                "display": self._format_duration(ttr_minutes),
                "is_ground_truth": True,
            }

        # Congestion severity (classification)
        if "congestion_severity" in self.models:
            pred = self.models["congestion_severity"].predict(X)[0]
            le = self.target_encoders.get("congestion_severity")
            label = le.inverse_transform([pred])[0] if le else str(pred)
            # Get probabilities if available
            proba = {}
            try:
                probs = self.models["congestion_severity"].predict_proba(X)[0]
                if le:
                    for i, cls in enumerate(le.classes_):
                        proba[cls] = float(probs[i])
            except:
                pass
            results["congestion_severity"] = {
                "value": label,
                "probabilities": proba,
                "is_heuristic": True,
                "disclaimer": "Estimated via rule-based heuristic, validated against historical patterns",
            }

        # Required manpower (classification)
        if "required_manpower" in self.models:
            pred = self.models["required_manpower"].predict(X)[0]
            le = self.target_encoders.get("required_manpower")
            label = le.inverse_transform([pred])[0] if le else str(pred)
            results["required_manpower"] = {
                "value": label,
                "is_heuristic": True,
                "disclaimer": "Estimated via rule-based heuristic, validated against historical patterns",
            }

        return results

    def get_feature_importance(self, target_name: str) -> dict:
        """Load precomputed feature importance for a target."""
        path = os.path.join(
            os.path.dirname(self.models_dir), "results",
            f"{target_name}_feature_importance.json"
        )
        if os.path.exists(path):
            with open(path) as f:
                return json.load(f)
        return {}

    @staticmethod
    def _format_duration(minutes: float) -> str:
        """Format minutes into human-readable duration."""
        if minutes < 60:
            return f"{int(minutes)} min"
        hours = minutes / 60
        if hours < 24:
            return f"{hours:.1f} hours"
        days = hours / 24
        return f"{days:.1f} days"


if __name__ == "__main__":
    predictor = CrowdFlowPredictor()

    # Test prediction
    test_event = {
        "event_type": "unplanned",
        "event_cause": "accident",
        "latitude": 12.9716,
        "longitude": 77.5946,
        "requires_road_closure": True,
        "start_datetime": "2024-03-15T14:30:00+05:30",
        "priority": "High",
        "corridor": "Bellary Road 1",
        "zone": "Central Zone 2",
        "police_station": "Cubbon Park",
        "veh_type": "heavy_vehicle",
        "description": "Major accident involving heavy vehicle near junction",
    }

    results = predictor.predict(test_event)
    print("\n=== Prediction Results ===")
    for target, pred in results.items():
        print(f"\n{target}:")
        for k, v in pred.items():
            print(f"  {k}: {v}")
