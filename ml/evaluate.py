"""
CrowdFlow — Evaluation Module
================================
Generates model comparison reports, SHAP explanations, and confusion matrices.
"""

import pandas as pd
import numpy as np
import os
import json
import joblib
import warnings

warnings.filterwarnings("ignore")

from sklearn.metrics import (
    classification_report, confusion_matrix,
    mean_absolute_error, mean_squared_error, r2_score
)

MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")


def generate_shap_importance(model, X, feature_names, target_name, top_n=15):
    """
    Generate SHAP-based feature importance for the winning model.
    Falls back to native feature_importances_ if SHAP fails.
    Returns dict of {feature: importance}.
    """
    try:
        import shap
        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(X.head(min(500, len(X))))

        if isinstance(shap_values, list):
            # Multi-class: average absolute SHAP values across classes
            shap_abs = np.mean([np.abs(sv) for sv in shap_values], axis=0)
        else:
            shap_abs = np.abs(shap_values)

        mean_shap = np.mean(shap_abs, axis=0)
        if len(mean_shap.shape) > 1:
            mean_shap = np.mean(mean_shap, axis=tuple(range(1, len(mean_shap.shape))))
        importance = dict(zip(feature_names, mean_shap.tolist()))
        method = "shap"
    except Exception as e:
        print(f"  [evaluate] SHAP failed ({e}), using native importance")
        try:
            imp = model.feature_importances_
            importance = dict(zip(feature_names, imp.tolist()))
            method = "native"
        except:
            importance = {}
            method = "none"

    # Sort and take top_n
    sorted_imp = dict(sorted(importance.items(), key=lambda x: x[1], reverse=True)[:top_n])

    # Save
    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(os.path.join(RESULTS_DIR, f"{target_name}_feature_importance.json"), "w") as f:
        json.dump({"method": method, "features": sorted_imp}, f, indent=2)

    print(f"  [evaluate] Feature importance ({method}) — top {top_n}:")
    for feat, val in list(sorted_imp.items())[:10]:
        print(f"    {feat}: {val:.4f}")

    return sorted_imp


def evaluate_all():
    """Load results and generate evaluation reports."""
    results_path = os.path.join(RESULTS_DIR, "model_comparison.json")
    if not os.path.exists(results_path):
        print("[evaluate] No model_comparison.json found. Run train.py first.")
        return

    with open(results_path) as f:
        all_results = json.load(f)

    # Generate SHAP for each target's best model
    metadata_path = os.path.join(MODELS_DIR, "model_metadata.json")
    if os.path.exists(metadata_path):
        with open(metadata_path) as f:
            metadata = json.load(f)

        feat_cols = metadata.get("feature_columns", [])

        # Load cleaned data for SHAP computation
        from data_prep import clean_data
        from feature_engineering import build_features
        from targets import derive_all_targets

        df = clean_data(save=False)
        df = derive_all_targets(df)

        # Load saved encoders
        encoders_path = os.path.join(MODELS_DIR, "label_encoders.joblib")
        if os.path.exists(encoders_path):
            encoders = joblib.load(encoders_path)
            df, feat_cols_actual, _ = build_features(df, fit=False, encoders=encoders)
        else:
            df, feat_cols_actual, _ = build_features(df)

        X = df[feat_cols].fillna(0)

        for target_name, info in metadata.get("targets", {}).items():
            model_path = os.path.join(MODELS_DIR, f"{target_name}_model.joblib")
            if os.path.exists(model_path):
                print(f"\n[evaluate] Generating importance for {target_name}...")
                model = joblib.load(model_path)
                generate_shap_importance(model, X, feat_cols, target_name)

    # Create summary report
    report = {
        "generated_at": pd.Timestamp.now().isoformat(),
        "targets": {}
    }
    for target_name, res in all_results.items():
        target_report = {
            "task_type": res["task_type"],
            "best_algorithm": res["best_algorithm"],
            "algorithms": {}
        }
        for algo, metrics in res["results"].items():
            target_report["algorithms"][algo] = {
                k: v for k, v in metrics.items()
                if k != "confusion_matrix" and k != "params"
            }
        report["targets"][target_name] = target_report

    with open(os.path.join(RESULTS_DIR, "evaluation_report.json"), "w") as f:
        json.dump(report, f, indent=2)

    print("\n[evaluate] Evaluation complete. Results saved to", RESULTS_DIR)


if __name__ == "__main__":
    evaluate_all()
