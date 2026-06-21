"""
CrowdFlow — Target Derivation Module
======================================
Derives three prediction targets from the event dataset:

1. time_to_resolution (REGRESSION — GROUND TRUTH)
   - closed_datetime - created_date in minutes
   - Available for ~3,141 rows (38.4%)

2. congestion_severity (CLASSIFICATION — HEURISTIC)
   - Composite score 0-100 → binned into Low/Medium/High/Critical
   - Derived from event_cause, road_closure, priority, duration, corridor/zone freq

3. required_manpower (ORDINAL CLASSIFICATION — HEURISTIC)
   - Ordinal bins: 1-2 / 3-5 / 6-10 / 10+
   - Derived from severity + event characteristics

TRANSPARENCY: Targets 2 and 3 are clearly labeled as heuristic/estimated
throughout the codebase and UI. Only target 1 has real ground truth.
"""

import pandas as pd
import numpy as np
import os
import warnings

warnings.filterwarnings("ignore")


# ---------------------------------------------------------------------------
# Event cause severity scores (0-30 scale)
# Higher = more likely to cause congestion
# ---------------------------------------------------------------------------
EVENT_CAUSE_SEVERITY = {
    "accident": 30,
    "protest": 30,
    "vip_movement": 28,
    "public_event": 25,
    "procession": 25,
    "congestion": 22,
    "tree_fall": 20,
    "fog_low_visibility": 18,
    "construction": 15,
    "water_logging": 15,
    "debris": 12,
    "road_conditions": 10,
    "pot_holes": 8,
    "vehicle_breakdown": 5,
    "others": 8,
}


def derive_time_to_resolution(df: pd.DataFrame) -> pd.Series:
    """
    TARGET 1: time_to_resolution (minutes)
    GROUND TRUTH: closed_datetime - created_date

    Returns a Series with TTR in minutes (NaN where not available).
    Outlier handling: cap at 7 days (10,080 min); negative values → NaN.
    """
    for col in ["closed_datetime", "created_date"]:
        if not pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = pd.to_datetime(df[col], format="mixed", utc=True, errors="coerce")

    ttr = (df["closed_datetime"] - df["created_date"]).dt.total_seconds() / 60.0

    # Remove negative values (data errors)
    ttr[ttr < 0] = np.nan

    # Exclude extreme outliers > 48 hours (data entry delays / chronic construction)
    ttr[ttr > 2880] = np.nan

    valid = ttr.notna().sum()
    print(f"[targets] time_to_resolution: {valid} valid rows "
          f"(median={ttr.median():.1f} min, mean={ttr.mean():.1f} min)")
    return ttr


def derive_congestion_severity(df: pd.DataFrame, ttr: pd.Series = None) -> pd.Series:
    """
    TARGET 2: congestion_severity (Low / Medium / High / Critical)
    HEURISTIC — composite score from multiple factors.

    Scoring (0-100):
      - event_cause severity:       0-30 points
      - requires_road_closure:      0-25 points
      - priority:                   0-15 points
      - event duration (TTR):       0-15 points
      - corridor historical freq:   0-10 points
      - junction presence:          0-5  points
    Total possible: 100

    Binning:
      Low:      0-25
      Medium:   26-50
      High:     51-75
      Critical: 76-100
    """
    scores = pd.Series(0.0, index=df.index)

    # 1. Event cause severity (0-30)
    cause_col = df["event_cause"] if "event_cause" in df.columns else None
    if cause_col is not None:
        scores += df["event_cause"].map(EVENT_CAUSE_SEVERITY).fillna(8)

    # 2. Road closure (0-25)
    if "requires_road_closure" in df.columns:
        scores += df["requires_road_closure"].astype(int) * 25

    # 3. Priority (0-15)
    if "priority" in df.columns:
        scores += (df["priority"] == "High").astype(int) * 15

    # 4. Event duration / TTR (0-15)
    if ttr is not None:
        duration_score = pd.cut(
            ttr,
            bins=[-1, 30, 120, 360, float("inf")],
            labels=[0, 5, 10, 15],
        ).astype("Int64").fillna(0)
        scores += duration_score.astype(float)

    # 5. Corridor historical frequency (0-10)
    if "corridor" in df.columns:
        corridor_freq = df["corridor"].value_counts()
        top_10 = set(corridor_freq.head(10).index)
        top_20 = set(corridor_freq.head(20).index)
        scores += df["corridor"].apply(
            lambda x: 10 if x in top_10 else (5 if x in top_20 else 0)
        )

    # 6. Junction presence (0-5)
    if "junction" in df.columns:
        scores += (df["junction"] != "Unknown").astype(int) * 5

    # Clip to 0-100
    scores = scores.clip(0, 100)

    # Bin into severity categories
    severity = pd.cut(
        scores,
        bins=[-1, 25, 50, 75, 100],
        labels=["Low", "Medium", "High", "Critical"],
    )

    # Distribution summary
    dist = severity.value_counts()
    print(f"[targets] congestion_severity distribution:")
    for cat in ["Low", "Medium", "High", "Critical"]:
        if cat in dist.index:
            print(f"  {cat}: {dist[cat]} ({dist[cat]/len(df)*100:.1f}%)")

    return severity


def derive_required_manpower(df: pd.DataFrame,
                             severity: pd.Series) -> pd.Series:
    """
    TARGET 3: required_manpower (ordinal: 1-2 / 3-5 / 6-10 / 10+)
    HEURISTIC — derived from congestion_severity + event characteristics.

    Rules:
      - Critical + road_closure → 10+
      - Critical OR (road_closure + high-impact cause) → 6-10
      - High OR road_closure → 3-5
      - Everything else → 1-2

    Modifiers:
      - Hazmat cargo → bump up 1 tier
      - Accident + heavy_vehicle → bump up 1 tier
    """
    # Start with base assignment
    manpower = pd.Series("1-2", index=df.index)

    # Apply rules (from lowest to highest — highest wins)
    road_closure = df["requires_road_closure"].astype(bool) if "requires_road_closure" in df.columns else pd.Series(False, index=df.index)

    high_impact_causes = {"accident", "protest", "public_event", "vip_movement", "procession"}
    is_high_impact = df["event_cause"].isin(high_impact_causes) if "event_cause" in df.columns else pd.Series(False, index=df.index)

    # Rule 1: High severity OR road_closure → 3-5
    mask_35 = (severity == "High") | road_closure
    manpower[mask_35] = "3-5"

    # Rule 2: Critical OR (road_closure + high_impact) → 6-10
    mask_610 = (severity == "Critical") | (road_closure & is_high_impact)
    manpower[mask_610] = "6-10"

    # Rule 3: Critical + road_closure → 10+
    mask_10plus = (severity == "Critical") & road_closure
    manpower[mask_10plus] = "10+"

    # Modifier: hazmat cargo → bump up 1 tier
    if "cargo_material" in df.columns:
        hazmat_kw = ["gas", "fuel", "oil", "chemical", "petrol", "diesel", "lpg"]
        is_hazmat = df["cargo_material"].fillna("").str.lower().apply(
            lambda x: any(kw in x for kw in hazmat_kw)
        )
        bump_map = {"1-2": "3-5", "3-5": "6-10", "6-10": "10+", "10+": "10+"}
        manpower[is_hazmat] = manpower[is_hazmat].map(bump_map)

    # Modifier: accident + heavy_vehicle → bump up 1 tier
    if "veh_type" in df.columns and "event_cause" in df.columns:
        heavy_accident = (df["event_cause"] == "accident") & \
                         (df["veh_type"].isin(["heavy_vehicle", "truck"]))
        bump_map = {"1-2": "3-5", "3-5": "6-10", "6-10": "10+", "10+": "10+"}
        manpower[heavy_accident] = manpower[heavy_accident].map(bump_map)

    # Distribution summary
    dist = manpower.value_counts()
    print(f"[targets] required_manpower distribution:")
    for cat in ["1-2", "3-5", "6-10", "10+"]:
        if cat in dist.index:
            print(f"  {cat}: {dist[cat]} ({dist[cat]/len(df)*100:.1f}%)")

    return manpower


def derive_all_targets(df: pd.DataFrame) -> pd.DataFrame:
    """
    Derive all 3 targets and add them as columns.
    """
    print("=" * 60)
    print("DERIVING TARGETS")
    print("=" * 60)

    # Target 1: time_to_resolution (ground truth)
    df["time_to_resolution"] = derive_time_to_resolution(df)

    # Target 2: congestion_severity (heuristic)
    df["congestion_severity"] = derive_congestion_severity(
        df, ttr=df["time_to_resolution"]
    )

    # Target 3: required_manpower (heuristic)
    df["required_manpower"] = derive_required_manpower(
        df, severity=df["congestion_severity"]
    )

    print("=" * 60)
    return df


if __name__ == "__main__":
    from data_prep import clean_data

    df = clean_data(save=False)
    df = derive_all_targets(df)

    print(f"\nFinal shape: {df.shape}")
    print(f"\nTarget nulls:")
    for t in ["time_to_resolution", "congestion_severity", "required_manpower"]:
        print(f"  {t}: {df[t].isnull().sum()} nulls")
