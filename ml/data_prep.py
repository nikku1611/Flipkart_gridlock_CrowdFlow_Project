"""
CrowdFlow — Data Preparation Module
====================================
Loads the raw CSV, cleans data, handles missing values, and outputs
a cleaned DataFrame ready for feature engineering.

Extends the partial pipeline from problem_statement_2.ipynb, but preserves
columns needed for target derivation and spatial features that the notebook
dropped prematurely.
"""

import pandas as pd
import numpy as np
import os
import warnings

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
RAW_CSV = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "data.csv",
)
CLEAN_CSV = os.path.join(os.path.dirname(__file__), "data", "cleaned_data.csv")


def load_raw_data(path: str = RAW_CSV) -> pd.DataFrame:
    """Load the raw CSV and return a DataFrame."""
    df = pd.read_csv(path)
    print(f"[data_prep] Loaded raw data: {df.shape[0]} rows × {df.shape[1]} cols")
    return df


def drop_empty_and_leakage_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Drop columns that are:
      - 100% null (map_file, comment, meta_data)
      - >98% null and not useful (direction, route_path, citizen_accident_id,
        assigned_to_police_id)
      - Post-outcome leakage (resolved_at_*, resolved_by_id, closed_by_id)
      - ID columns with no predictive value (id, veh_no, kgid, created_by_id,
        last_modified_by_id, client_id)

    IMPORTANT: We RETAIN closed_datetime, resolved_datetime, zone, junction,
    description, cargo_material, reason_breakdown, age_of_truck — these are
    needed for target derivation and features.
    """
    drop_cols = [
        # 100% null
        "map_file", "comment", "meta_data",
        # >98% null / not useful
        "direction", "route_path", "citizen_accident_id", "assigned_to_police_id",
        # Post-outcome leakage
        "resolved_at_address", "resolved_at_latitude", "resolved_at_longitude",
        "resolved_by_id", "closed_by_id",
        # ID columns — no predictive value
        "id", "veh_no", "kgid", "created_by_id", "last_modified_by_id", "client_id",
        # end_address — 91.6% null
        "end_address",
        # end_datetime — 94% null
        "end_datetime",
    ]
    existing = [c for c in drop_cols if c in df.columns]
    df = df.drop(columns=existing)
    print(f"[data_prep] Dropped {len(existing)} columns -> {df.shape[1]} cols remaining")
    return df


def normalize_event_cause(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize event_cause values: merge duplicates, map rare to 'others'."""
    cause_map = {
        "Debris": "debris",
        "test_demo": "others",
        "Fog / Low Visibility": "fog_low_visibility",
    }
    df["event_cause"] = df["event_cause"].replace(cause_map)
    print(f"[data_prep] Normalized event_cause: {df['event_cause'].nunique()} unique values")
    return df


def parse_datetimes(df: pd.DataFrame) -> pd.DataFrame:
    """Parse all datetime columns with mixed formats."""
    dt_cols = ["start_datetime", "modified_datetime", "created_date",
               "closed_datetime", "resolved_datetime"]
    for col in dt_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], format="mixed", utc=True, errors="coerce")
    print("[data_prep] Parsed datetime columns")
    return df


def fill_missing_values(df: pd.DataFrame) -> pd.DataFrame:
    """
    Handle missing values with domain-appropriate strategies.
    Unlike the notebook's naive mode-fill, we use contextual fills.
    """
    # Coordinates: fill end coords with start coords where missing
    mask_end_lat = df["endlatitude"].isna() | (df["endlatitude"] == 0)
    mask_end_lon = df["endlongitude"].isna() | (df["endlongitude"] == 0)
    df.loc[mask_end_lat, "endlatitude"] = df.loc[mask_end_lat, "latitude"]
    df.loc[mask_end_lon, "endlongitude"] = df.loc[mask_end_lon, "longitude"]

    # Zone / junction / corridor: fill with "Unknown"
    for col in ["zone", "junction", "corridor", "gba_identifier"]:
        if col in df.columns:
            df[col] = df[col].fillna("Unknown")

    # Vehicle type: "not_applicable" for non-breakdown events
    df["veh_type"] = df["veh_type"].fillna("not_applicable")

    # Priority: fill with mode (High, the majority class)
    df["priority"] = df["priority"].fillna(df["priority"].mode()[0])

    # Description: fill with empty string
    df["description"] = df["description"].fillna("")

    # Address: fill with "Unknown"
    df["address"] = df["address"].fillna("Unknown")

    # Cargo material / reason_breakdown / age_of_truck: leave as NaN
    # (only relevant for breakdown events; we'll handle in feature engineering)

    # Authenticated: fill with "no"
    df["authenticated"] = df["authenticated"].fillna("no")

    print("[data_prep] Filled missing values")
    return df


def clean_data(save: bool = True) -> pd.DataFrame:
    """Full cleaning pipeline."""
    df = load_raw_data()
    df = drop_empty_and_leakage_columns(df)
    df = normalize_event_cause(df)
    df = parse_datetimes(df)
    df = fill_missing_values(df)

    # Final null check
    null_counts = df.isnull().sum()
    non_zero_nulls = null_counts[null_counts > 0]
    if len(non_zero_nulls) > 0:
        print(f"[data_prep] Remaining nulls:\n{non_zero_nulls}")
    else:
        print("[data_prep] No remaining nulls in core columns")

    print(f"[data_prep] Final shape: {df.shape}")

    if save:
        os.makedirs(os.path.dirname(CLEAN_CSV), exist_ok=True)
        df.to_csv(CLEAN_CSV, index=False)
        print(f"[data_prep] Saved cleaned data to {CLEAN_CSV}")

    return df


if __name__ == "__main__":
    df = clean_data()
    print("\n=== Column dtypes ===")
    print(df.dtypes)
    print(f"\n=== Shape: {df.shape} ===")
