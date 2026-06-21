"""
CrowdFlow — Pydantic Schemas
================================
Request/response models for the FastAPI backend.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, List
from datetime import datetime
from enum import Enum


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class EventType(str, Enum):
    planned = "planned"
    unplanned = "unplanned"


class EventCause(str, Enum):
    vehicle_breakdown = "vehicle_breakdown"
    accident = "accident"
    construction = "construction"
    pot_holes = "pot_holes"
    water_logging = "water_logging"
    tree_fall = "tree_fall"
    road_conditions = "road_conditions"
    congestion = "congestion"
    public_event = "public_event"
    procession = "procession"
    vip_movement = "vip_movement"
    protest = "protest"
    debris = "debris"
    fog_low_visibility = "fog_low_visibility"
    others = "others"


class Priority(str, Enum):
    high = "High"
    low = "Low"


class SeverityLevel(str, Enum):
    low = "Low"
    medium = "Medium"
    high = "High"
    critical = "Critical"


class ManpowerLevel(str, Enum):
    minimal = "1-2"
    moderate = "3-5"
    significant = "6-10"
    full_deployment = "10+"


# ---------------------------------------------------------------------------
# Request Models
# ---------------------------------------------------------------------------
class EventInput(BaseModel):
    """Input schema for event impact prediction."""
    event_type: EventType = Field(default=EventType.unplanned, description="Type of event")
    event_cause: EventCause = Field(..., description="Cause of the event")
    latitude: float = Field(..., ge=10.0, le=15.0, description="Event latitude (Bengaluru range)")
    longitude: float = Field(..., ge=75.0, le=80.0, description="Event longitude (Bengaluru range)")
    endlatitude: Optional[float] = Field(None, description="End latitude")
    endlongitude: Optional[float] = Field(None, description="End longitude")
    requires_road_closure: bool = Field(default=False, description="Whether road closure is required")
    start_datetime: Optional[str] = Field(None, description="Event start time (ISO 8601)")
    priority: Priority = Field(default=Priority.high, description="Event priority")
    corridor: Optional[str] = Field(default="Non-corridor", description="Traffic corridor")
    zone: Optional[str] = Field(default="Unknown", description="City zone")
    police_station: Optional[str] = Field(default="No Police Station", description="Nearest police station")
    veh_type: Optional[str] = Field(default="not_applicable", description="Vehicle type involved")
    description: Optional[str] = Field(default="", description="Event description text")
    cargo_material: Optional[str] = Field(None, description="Cargo material if vehicle breakdown")
    address: Optional[str] = Field(None, description="Event address")


class DiversionInput(BaseModel):
    """Input for diversion plan generation."""
    severity: SeverityLevel = Field(..., description="Predicted congestion severity")
    latitude: float = Field(...)
    longitude: float = Field(...)
    requires_road_closure: bool = Field(default=False)
    event_cause: EventCause = Field(...)
    corridor: Optional[str] = Field(default="Non-corridor")
    zone: Optional[str] = Field(default="Unknown")
    police_station: Optional[str] = Field(None)
    manpower_needed: Optional[str] = Field(None)


class HistoricalQuery(BaseModel):
    """Query parameters for historical events."""
    zone: Optional[str] = None
    event_type: Optional[str] = None
    event_cause: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


# ---------------------------------------------------------------------------
# Response Models
# ---------------------------------------------------------------------------
class TimeToResolutionPrediction(BaseModel):
    value_minutes: float
    value_hours: float
    display: str
    is_ground_truth: bool = True


class SeverityPrediction(BaseModel):
    value: str
    probabilities: Dict[str, float] = {}
    is_heuristic: bool = True
    disclaimer: str = "Estimated via rule-based heuristic"


class ManpowerPrediction(BaseModel):
    value: str
    is_heuristic: bool = True
    disclaimer: str = "Estimated via rule-based heuristic"


class EventImpactResponse(BaseModel):
    """Combined prediction response for all 3 targets."""
    prediction_id: str
    congestion_severity: Optional[SeverityPrediction] = None
    required_manpower: Optional[ManpowerPrediction] = None
    time_to_resolution: Optional[TimeToResolutionPrediction] = None
    event_input: dict = {}


class DiversionPlanResponse(BaseModel):
    """Response plan with barricades, diversions, and deployment."""
    severity: str
    recommended_barricades: int
    recommended_officers: str
    road_closure_needed: bool
    diversion_routes: List[str]
    nearest_police_stations: List[dict]
    action_summary: str
    alert_level: str


class FeatureImportanceResponse(BaseModel):
    """Feature importance for explainability."""
    target: str
    method: str
    features: Dict[str, float]


class ModelMetricsResponse(BaseModel):
    """Model comparison metrics."""
    training_date: str
    targets: dict


class HeatmapPoint(BaseModel):
    """Single point for heatmap visualization."""
    latitude: float
    longitude: float
    intensity: float
    zone: Optional[str] = None
    event_count: int = 0


class EventHistoricalItem(BaseModel):
    """Single historical event for the dashboard."""
    event_type: str
    event_cause: str
    latitude: float
    longitude: float
    address: Optional[str] = None
    requires_road_closure: bool = False
    priority: str = "High"
    status: str = "closed"
    corridor: str = "Non-corridor"
    zone: str = "Unknown"
    police_station: str = "Unknown"
    start_datetime: Optional[str] = None
    created_date: Optional[str] = None


class DashboardStats(BaseModel):
    """Dashboard KPI stats."""
    total_events: int
    active_events: int
    avg_resolution_minutes: float
    events_by_type: Dict[str, int]
    events_by_cause: Dict[str, int]
    events_by_zone: Dict[str, int]
    events_by_priority: Dict[str, int]
    high_priority_percentage: float
    road_closure_percentage: float
