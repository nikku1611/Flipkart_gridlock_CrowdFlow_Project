"""
CrowdFlow — Events Router
================================
FastAPI endpoints for historical event data, heatmap, and dashboard stats.
"""

from fastapi import APIRouter, Query
from typing import Optional, List
import pandas as pd
import os
import sys

router = APIRouter(prefix="/events", tags=["events"])

# Path to raw CSV
CSV_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "data.csv"
)

_df_cache = None

def _load_data():
    """Load and cache historical data."""
    global _df_cache
    if _df_cache is None:
        _df_cache = pd.read_csv(CSV_PATH)
        for col in ["start_datetime", "created_date", "modified_datetime", "closed_datetime"]:
            if col in _df_cache.columns:
                _df_cache[col] = pd.to_datetime(_df_cache[col], format="mixed", utc=True, errors="coerce")
    return _df_cache


@router.get("/historical")
async def get_historical_events(
    zone: Optional[str] = Query(None),
    event_type: Optional[str] = Query(None),
    event_cause: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """Paginated historical event data for dashboard charts."""
    df = _load_data()

    # Apply filters
    if zone:
        df = df[df["zone"] == zone]
    if event_type:
        df = df[df["event_type"] == event_type]
    if event_cause:
        df = df[df["event_cause"] == event_cause]
    if start_date:
        sd = pd.to_datetime(start_date, utc=True)
        df = df[df["created_date"] >= sd]
    if end_date:
        ed = pd.to_datetime(end_date, utc=True)
        df = df[df["created_date"] <= ed]

    total = len(df)
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size

    cols = ["event_type", "event_cause", "latitude", "longitude", "address",
            "requires_road_closure", "priority", "status", "corridor", "zone",
            "police_station", "start_datetime", "created_date", "junction"]
    existing_cols = [c for c in cols if c in df.columns]
    subset = df[existing_cols].iloc[start_idx:end_idx]

    records = subset.fillna("").to_dict(orient="records")
    # Convert datetimes to strings
    for r in records:
        for k, v in r.items():
            if isinstance(v, pd.Timestamp):
                r[k] = v.isoformat()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
        "events": records,
    }


@router.get("/heatmap")
async def get_heatmap_data():
    """Aggregated event density by location for map visualization."""
    df = _load_data()

    # Round coordinates to ~500m precision for aggregation
    df["lat_round"] = (df["latitude"] * 100).round() / 100
    df["lon_round"] = (df["longitude"] * 100).round() / 100

    heatmap = df.groupby(["lat_round", "lon_round"]).agg(
        event_count=("event_type", "count"),
        zone=("zone", "first"),
    ).reset_index()

    # Normalize intensity 0-1
    max_count = heatmap["event_count"].max()
    heatmap["intensity"] = heatmap["event_count"] / max_count if max_count > 0 else 0

    points = heatmap.rename(columns={
        "lat_round": "latitude", "lon_round": "longitude"
    }).to_dict(orient="records")

    return {"points": points, "total_points": len(points)}


@router.get("/stats")
async def get_dashboard_stats():
    """Dashboard KPI statistics."""
    df = _load_data()

    total_events = len(df)
    active_events = int((df["status"] == "active").sum())

    # Avg resolution time
    created = df["created_date"]
    closed = df["closed_datetime"]
    mask = closed.notna()
    ttr = (closed[mask] - created[mask]).dt.total_seconds() / 60
    ttr = ttr[ttr > 0]
    avg_resolution = float(ttr.median()) if len(ttr) > 0 else 0

    events_by_type = df["event_type"].value_counts().to_dict()
    events_by_cause = df["event_cause"].value_counts().head(10).to_dict()
    events_by_zone = df["zone"].value_counts().head(10).to_dict() if "zone" in df.columns else {}
    events_by_priority = df["priority"].value_counts().to_dict() if "priority" in df.columns else {}

    high_prio_pct = float(events_by_priority.get("High", 0)) / total_events * 100 if total_events > 0 else 0
    closure_pct = float(df["requires_road_closure"].sum()) / total_events * 100 if total_events > 0 else 0

    # Events by month for trend chart
    df["month_year"] = df["created_date"].dt.strftime("%Y-%m")
    monthly = df.groupby("month_year").size().to_dict()

    # Events by hour for distribution chart
    df["hour"] = df["created_date"].dt.hour
    hourly = df.groupby("hour").size().to_dict()
    hourly = {str(k): int(v) for k, v in hourly.items()}

    # Top corridors
    top_corridors = df["corridor"].value_counts().head(10).to_dict() if "corridor" in df.columns else {}

    # Top police stations
    top_stations = df["police_station"].value_counts().head(10).to_dict() if "police_station" in df.columns else {}

    return {
        "total_events": total_events,
        "active_events": active_events,
        "avg_resolution_minutes": round(avg_resolution, 1),
        "events_by_type": {str(k): int(v) for k, v in events_by_type.items()},
        "events_by_cause": {str(k): int(v) for k, v in events_by_cause.items()},
        "events_by_zone": {str(k): int(v) for k, v in events_by_zone.items()},
        "events_by_priority": {str(k): int(v) for k, v in events_by_priority.items()},
        "high_priority_percentage": round(high_prio_pct, 1),
        "road_closure_percentage": round(closure_pct, 1),
        "events_by_month": {str(k): int(v) for k, v in monthly.items()},
        "events_by_hour": hourly,
        "top_corridors": {str(k): int(v) for k, v in top_corridors.items()},
        "top_police_stations": {str(k): int(v) for k, v in top_stations.items()},
    }


@router.get("/corridors")
async def get_corridors():
    """List available corridors."""
    df = _load_data()
    corridors = sorted(df["corridor"].dropna().unique().tolist())
    return {"corridors": corridors}


@router.get("/zones")
async def get_zones():
    """List available zones."""
    df = _load_data()
    zones = sorted(df["zone"].dropna().unique().tolist()) if "zone" in df.columns else []
    return {"zones": zones}


@router.get("/police-stations")
async def get_police_stations():
    """List available police stations."""
    df = _load_data()
    stations = sorted(df["police_station"].dropna().unique().tolist())
    return {"police_stations": stations}
