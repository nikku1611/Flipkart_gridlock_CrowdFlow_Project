"""
CrowdFlow — Feature Engineering Module
========================================
Builds the feature matrix from cleaned data. Features are strictly partitioned
into those available at prediction time (when an event is first reported) vs.
post-outcome fields (used only for target derivation, never as features).

LEAKAGE PREVENTION:
  - NEVER use: status, closed_datetime, resolved_datetime, modified_datetime,
    closed_by_id, resolved_by_id, assigned_to_police_id as features
  - These fields are only known AFTER the event is resolved
  - The deployed model must only use pre-resolution features

Extends the partial pipeline's temporal features (year/month/day/hour/dayofweek)
with: is_weekend, is_peak_hour, is_festival_season, spatial frequency encoding,
rolling event counts, text keyword flags, and interaction features.
"""

import pandas as pd
import numpy as np
import os
import json
import warnings
from math import radians, sin, cos, sqrt, atan2

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------------
# Karnataka Festival Calendar (approximate dates for 2023-2024)
# ---------------------------------------------------------------------------
FESTIVAL_WINDOWS = [
    # (month, day_start, day_end, name)
    (1, 26, 26, "Republic Day"),
    (3, 22, 22, "Ugadi"),         # Mar-Apr varies
    (4, 11, 11, "Ugadi 2024"),
    (8, 15, 15, "Independence Day"),
    (9, 18, 19, "Ganesh Chaturthi"),
    (10, 15, 24, "Dasara/Navaratri"),
    (10, 24, 24, "Vijaya Dashami"),
    (11, 1, 1, "Kannada Rajyotsava"),
    (11, 12, 13, "Diwali"),
    (12, 25, 25, "Christmas"),
]

# Peak hours in Bengaluru (morning + evening rush)
PEAK_HOURS_MORNING = range(8, 11)  # 8 AM - 10 AM
PEAK_HOURS_EVENING = range(17, 21)  # 5 PM - 8 PM


def haversine_km(lat1, lon1, lat2, lon2):
    """Calculate haversine distance between two coordinate pairs in km."""
    R = 6371.0  # Earth's radius in km
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    return R * c


def add_temporal_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Extract temporal features from start_datetime and created_date.
    These are all available at prediction time (when event is first reported).
    """
    # Parse if not already datetime
    for col in ["start_datetime", "created_date"]:
        if col in df.columns and not pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = pd.to_datetime(df[col], format="mixed", utc=True, errors="coerce")

    ref = df["start_datetime"].fillna(df["created_date"])

    df["hour_of_day"] = ref.dt.hour
    df["day_of_week"] = ref.dt.dayofweek  # 0=Mon, 6=Sun
    df["is_weekend"] = (df["day_of_week"] >= 5).astype(int)
    df["month"] = ref.dt.month
    df["day_of_month"] = ref.dt.day

    # Season: 1=Winter(Dec-Feb), 2=Summer(Mar-May), 3=Monsoon(Jun-Sep), 4=Post-Monsoon(Oct-Nov)
    season_map = {12: 1, 1: 1, 2: 1, 3: 2, 4: 2, 5: 2,
                  6: 3, 7: 3, 8: 3, 9: 3, 10: 4, 11: 4}
    df["season"] = df["month"].map(season_map)

    # Peak hour flag
    df["is_peak_hour"] = df["hour_of_day"].apply(
        lambda h: 1 if h in PEAK_HOURS_MORNING or h in PEAK_HOURS_EVENING else 0
    )

    # Festival season flag
    def is_festival(row_month, row_day):
        for m, d_start, d_end, _ in FESTIVAL_WINDOWS:
            if row_month == m and d_start <= row_day <= d_end:
                return 1
        return 0

    df["is_festival_season"] = df.apply(
        lambda r: is_festival(ref.loc[r.name].month, ref.loc[r.name].day), axis=1
    )

    print(f"[features] Added temporal features")
    return df


def add_spatial_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Spatial features: frequency encoding of zone/corridor/junction/police_station,
    and start-end distance.
    """
    # Frequency encoding: count of events per category (historical density)
    for col in ["zone", "corridor", "junction", "police_station"]:
        if col in df.columns:
            freq = df[col].value_counts().to_dict()
            df[f"{col}_freq"] = df[col].map(freq).fillna(0).astype(int)

    # Distance between start and end coordinates (haversine)
    df["start_end_distance_km"] = haversine_km(
        df["latitude"], df["longitude"],
        df["endlatitude"], df["endlongitude"]
    )
    # Cap unrealistic distances (>100km likely data errors)
    df["start_end_distance_km"] = df["start_end_distance_km"].clip(upper=100)

    print(f"[features] Added spatial features")
    return df


def add_event_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Event characteristic features available at prediction time.
    """
    # Interaction: event_type × event_cause
    df["event_type_x_cause"] = df["event_type"] + "_" + df["event_cause"]

    # Road closure binary (already bool, ensure int)
    df["road_closure"] = df["requires_road_closure"].astype(int)

    # Cargo material flags
    df["has_cargo"] = df["cargo_material"].notna().astype(int)

    # Hazmat flag: keywords suggesting hazardous materials
    hazmat_keywords = ["gas", "fuel", "oil", "chemical", "petrol", "diesel",
                       "lpg", "acid", "inflammable", "explosive", "toxic"]
    df["is_hazmat"] = 0
    mask_cargo = df["cargo_material"].notna()
    if mask_cargo.any():
        df.loc[mask_cargo, "is_hazmat"] = df.loc[mask_cargo, "cargo_material"].str.lower().apply(
            lambda x: 1 if any(kw in str(x) for kw in hazmat_keywords) else 0
        )

    # Age of truck bucketed
    df["truck_age_bucket"] = pd.cut(
        df["age_of_truck"],
        bins=[-1, 5, 10, 100, 3000],
        labels=[0, 1, 2, 3],  # 0-5, 5-10, 10+, very old
        right=True
    ).astype("Int64").fillna(-1)  # -1 = not applicable

    # Authenticated binary
    df["is_authenticated"] = (df["authenticated"] == "yes").astype(int)

    print(f"[features] Added event characteristic features")
    return df


def add_rolling_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Historical/rolling features: count of events in the same zone/corridor
    in the last 7/30 days. This is a first-class feature group as specified.

    IMPORTANT: These are computed using only PAST events (before the current
    event's created_date) to avoid future leakage.
    """
    for col in ["start_datetime", "created_date"]:
        if col in df.columns and not pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = pd.to_datetime(df[col], format="mixed", utc=True, errors="coerce")

    ref_time = df["created_date"].fillna(df["start_datetime"])
    df = df.sort_values("created_date").reset_index(drop=True)

    # Pre-compute for efficiency: group by zone/corridor, then count events
    # within rolling windows using vectorized approach
    for group_col in ["zone", "corridor"]:
        col_7d = f"{group_col}_events_7d"
        col_30d = f"{group_col}_events_30d"
        df[col_7d] = 0
        df[col_30d] = 0

        for grp_name, grp_idx in df.groupby(group_col).groups.items():
            grp = df.loc[grp_idx].sort_values("created_date")
            times = grp["created_date"].values

            counts_7d = []
            counts_30d = []
            for i, t in enumerate(times):
                if pd.isna(t):
                    counts_7d.append(0)
                    counts_30d.append(0)
                    continue
                t_7d = t - pd.Timedelta(days=7)
                t_30d = t - pd.Timedelta(days=30)
                c7 = ((times[:i] >= t_7d) & (times[:i] < t)).sum()
                c30 = ((times[:i] >= t_30d) & (times[:i] < t)).sum()
                counts_7d.append(int(c7))
                counts_30d.append(int(c30))

            df.loc[grp.index, col_7d] = counts_7d
            df.loc[grp.index, col_30d] = counts_30d

    print(f"[features] Added rolling event count features")
    return df


def add_text_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Lightweight keyword extraction from description and reason_breakdown.
    No NLP — just flag words for interpretability and speed.
    """
    # Description keyword flags
    keywords = {
        "desc_has_rally": ["rally", "dharni", "dharna"],
        "desc_has_vip": ["vip", "minister", "cm ", "governor", "dignitary"],
        "desc_has_festival": ["festival", "celebration", "puja", "ganesh", "dasara",
                              "diwali", "procession", "jatha"],
        "desc_has_accident": ["accident", "collision", "hit", "crash", "injured",
                              "fatal", "death"],
        "desc_has_fire": ["fire", "blaze", "burn", "smoke"],
        "desc_has_protest": ["protest", "strike", "bandh", "agitation", "demonstration"],
        "desc_has_waterlog": ["flood", "water log", "waterlog", "rain", "inundat"],
    }

    desc_lower = df["description"].str.lower().fillna("")
    for feat_name, kw_list in keywords.items():
        pattern = "|".join(kw_list)
        df[feat_name] = desc_lower.str.contains(pattern, na=False).astype(int)

    # Reason breakdown simplified categories
    df["breakdown_category"] = "not_applicable"
    mask_rb = df["reason_breakdown"].notna()
    if mask_rb.any():
        rb_lower = df.loc[mask_rb, "reason_breakdown"].str.lower()
        df.loc[mask_rb, "breakdown_category"] = "other_mechanical"
        df.loc[mask_rb & rb_lower.str.contains("tyre|tire|puncture", na=False),
               "breakdown_category"] = "tyre_issue"
        df.loc[mask_rb & rb_lower.str.contains("engine|start|overheat", na=False),
               "breakdown_category"] = "engine_issue"
        df.loc[mask_rb & rb_lower.str.contains("electric|battery|wir", na=False),
               "breakdown_category"] = "electrical_issue"
        df.loc[mask_rb & rb_lower.str.contains("brake|break", na=False),
               "breakdown_category"] = "brake_issue"

    print(f"[features] Added text keyword features")
    return df


def encode_categoricals(df: pd.DataFrame, fit: bool = True,
                        encoders: dict = None) -> tuple:
    """
    Encode categorical features using label encoding (not one-hot) to avoid
    feature explosion. CatBoost handles categoricals natively; for XGBoost/
    LightGBM, label encoding works better than one-hot for high-cardinality cols.

    Returns (df, encoders_dict) — save encoders for inference.
    """
    from sklearn.preprocessing import LabelEncoder

    cat_cols = [
        "event_type", "event_cause", "corridor", "priority", "zone",
        "police_station", "veh_type", "event_type_x_cause",
        "breakdown_category",
    ]

    if encoders is None:
        encoders = {}

    for col in cat_cols:
        if col not in df.columns:
            continue
        if fit:
            le = LabelEncoder()
            # Add "UNKNOWN" to handle unseen categories at inference
            unique_vals = list(df[col].unique()) + ["__UNKNOWN__"]
            le.fit(unique_vals)
            encoders[col] = le
        else:
            le = encoders.get(col)
            if le is None:
                continue
            # Map unseen categories to __UNKNOWN__
            df[col] = df[col].apply(
                lambda x: x if x in le.classes_ else "__UNKNOWN__"
            )
        df[col] = le.transform(df[col])

    print(f"[features] Label-encoded {len(cat_cols)} categorical columns")
    return df, encoders


def get_feature_columns() -> list:
    """
    Return the list of feature columns used for model training.
    This explicitly excludes all post-outcome and target columns.
    """
    return [
        # Spatial
        "latitude", "longitude", "endlatitude", "endlongitude",
        "start_end_distance_km",
        "zone_freq", "corridor_freq", "junction_freq", "police_station_freq",
        # Temporal
        "hour_of_day", "day_of_week", "is_weekend", "month", "day_of_month",
        "season", "is_peak_hour", "is_festival_season",
        # Event characteristics (encoded)
        "event_type", "event_cause", "road_closure", "corridor", "priority",
        "zone", "police_station", "veh_type", "event_type_x_cause",
        "is_authenticated", "has_cargo", "is_hazmat", "truck_age_bucket",
        "breakdown_category",
        # Rolling / historical
        "zone_events_7d", "corridor_events_7d",
        "zone_events_30d", "corridor_events_30d",
        # Text keyword flags
        "desc_has_rally", "desc_has_vip", "desc_has_festival",
        "desc_has_accident", "desc_has_fire", "desc_has_protest",
        "desc_has_waterlog",
    ]


def build_features(df: pd.DataFrame, fit: bool = True,
                   encoders: dict = None) -> tuple:
    """
    Full feature engineering pipeline.
    Returns (df_with_features, feature_columns, encoders).
    """
    df = add_temporal_features(df)
    df = add_spatial_features(df)
    df = add_event_features(df)
    df = add_rolling_features(df)
    df = add_text_features(df)
    df, encoders = encode_categoricals(df, fit=fit, encoders=encoders)

    feature_cols = get_feature_columns()
    # Only keep columns that exist
    feature_cols = [c for c in feature_cols if c in df.columns]

    print(f"[features] Feature matrix: {len(feature_cols)} features")
    return df, feature_cols, encoders


if __name__ == "__main__":
    from data_prep import clean_data

    df = clean_data(save=False)
    df, feat_cols, encoders = build_features(df)
    print(f"\nFeature columns ({len(feat_cols)}):")
    for c in feat_cols:
        print(f"  {c}: {df[c].dtype}, nulls={df[c].isnull().sum()}")
