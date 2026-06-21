"""
CrowdFlow — Model Training Module
====================================
Trains XGBoost, LightGBM, and CatBoost models for each of the 3 targets.
Uses time-based train/test split + Stratified K-Fold cross-validation.
Light hyperparameter tuning via Optuna (20 trials per model).

Saves: best model per target, model_metadata.json, comparison results.
"""

import pandas as pd
import numpy as np
import os
import json
import joblib
import warnings
from datetime import datetime

warnings.filterwarnings("ignore")

# ML imports
from sklearn.model_selection import (
    StratifiedKFold, KFold, cross_val_score
)
from sklearn.metrics import (
    accuracy_score, f1_score, precision_score, recall_score,
    confusion_matrix, mean_absolute_error, mean_squared_error, r2_score,
    make_scorer
)
from sklearn.preprocessing import LabelEncoder

import xgboost as xgb
import lightgbm as lgb
import catboost as cb

try:
    import optuna
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    HAS_OPTUNA = True
except ImportError:
    HAS_OPTUNA = False
    print("[train] Optuna not installed — using default hyperparameters")

# Local imports
from data_prep import clean_data
from feature_engineering import build_features, get_feature_columns
from targets import derive_all_targets

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")
os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
N_FOLDS = 5
N_OPTUNA_TRIALS = 20
RANDOM_STATE = 42


def prepare_data():
    """Run full pipeline: clean → features → targets → train/test split."""
    print("=" * 70)
    print("PREPARING DATA")
    print("=" * 70)

    df = clean_data(save=True)
    df = derive_all_targets(df)
    df, feat_cols, encoders = build_features(df)

    # Save encoders for inference
    joblib.dump(encoders, os.path.join(MODELS_DIR, "label_encoders.joblib"))

    # Time-based split: train on earlier events, test on later ones
    for col in ["created_date", "start_datetime"]:
        if not pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = pd.to_datetime(df[col], format="mixed", utc=True, errors="coerce")

    sort_col = "created_date"
    df = df.sort_values(sort_col).reset_index(drop=True)
    split_idx = int(len(df) * 0.8)
    train_df = df.iloc[:split_idx].copy()
    test_df = df.iloc[split_idx:].copy()

    print(f"\n[train] Time-based split:")
    print(f"  Train: {len(train_df)} rows (up to {train_df[sort_col].max()})")
    print(f"  Test:  {len(test_df)} rows (from {test_df[sort_col].min()})")

    return train_df, test_df, feat_cols, encoders


# ---------------------------------------------------------------------------
# Optuna objective factories
# ---------------------------------------------------------------------------

def expm1_mae(y_true, y_pred):
    return mean_absolute_error(np.expm1(y_true), np.expm1(y_pred))

expm1_mae_scorer = make_scorer(expm1_mae, greater_is_better=False)

def xgb_objective(trial, X, y, task_type, target_name="time_to_resolution", n_folds=N_FOLDS):
    """Optuna objective for XGBoost."""
    params = {
        "n_estimators": trial.suggest_int("n_estimators", 100, 500),
        "max_depth": trial.suggest_int("max_depth", 3, 8),
        "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
        "subsample": trial.suggest_float("subsample", 0.6, 1.0),
        "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 1.0),
        "reg_alpha": trial.suggest_float("reg_alpha", 1e-3, 10.0, log=True),
        "reg_lambda": trial.suggest_float("reg_lambda", 1e-3, 10.0, log=True),
        "random_state": RANDOM_STATE,
        "verbosity": 0,
    }

    if task_type == "classification":
        model = xgb.XGBClassifier(**params, eval_metric="mlogloss")
        cv = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=RANDOM_STATE)
        scoring = "f1_macro"
    else:
        model = xgb.XGBRegressor(**params, eval_metric="rmse")
        cv = KFold(n_splits=n_folds, shuffle=True, random_state=RANDOM_STATE)
        scoring = expm1_mae_scorer if target_name == "time_to_resolution" else "neg_mean_absolute_error"

    scores = cross_val_score(model, X, y, cv=cv, scoring=scoring, n_jobs=-1)
    return scores.mean()


def lgb_objective(trial, X, y, task_type, target_name="time_to_resolution", n_folds=N_FOLDS):
    """Optuna objective for LightGBM."""
    params = {
        "n_estimators": trial.suggest_int("n_estimators", 100, 500),
        "max_depth": trial.suggest_int("max_depth", 3, 8),
        "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
        "subsample": trial.suggest_float("subsample", 0.6, 1.0),
        "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 1.0),
        "reg_alpha": trial.suggest_float("reg_alpha", 1e-3, 10.0, log=True),
        "reg_lambda": trial.suggest_float("reg_lambda", 1e-3, 10.0, log=True),
        "random_state": RANDOM_STATE,
        "verbosity": -1,
    }

    if task_type == "classification":
        model = lgb.LGBMClassifier(**params)
        cv = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=RANDOM_STATE)
        scoring = "f1_macro"
    else:
        model = lgb.LGBMRegressor(**params)
        cv = KFold(n_splits=n_folds, shuffle=True, random_state=RANDOM_STATE)
        scoring = expm1_mae_scorer if target_name == "time_to_resolution" else "neg_mean_absolute_error"

    scores = cross_val_score(model, X, y, cv=cv, scoring=scoring, n_jobs=-1)
    return scores.mean()


def cb_objective(trial, X, y, task_type, target_name="time_to_resolution", n_folds=N_FOLDS):
    """Optuna objective for CatBoost."""
    params = {
        "iterations": trial.suggest_int("iterations", 100, 500),
        "depth": trial.suggest_int("depth", 3, 8),
        "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
        "l2_leaf_reg": trial.suggest_float("l2_leaf_reg", 1e-3, 10.0, log=True),
        "random_seed": RANDOM_STATE,
        "verbose": 0,
    }

    if task_type == "classification":
        model = cb.CatBoostClassifier(**params)
        cv = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=RANDOM_STATE)
        scoring = "f1_macro"
    else:
        model = cb.CatBoostRegressor(**params)
        cv = KFold(n_splits=n_folds, shuffle=True, random_state=RANDOM_STATE)
        scoring = expm1_mae_scorer if target_name == "time_to_resolution" else "neg_mean_absolute_error"

    scores = cross_val_score(model, X, y, cv=cv, scoring=scoring, n_jobs=-1)
    return scores.mean()


# ---------------------------------------------------------------------------
# Training pipeline for one target
# ---------------------------------------------------------------------------

def train_target(target_name: str, task_type: str,
                 train_df: pd.DataFrame, test_df: pd.DataFrame,
                 feat_cols: list) -> dict:
    """
    Train XGBoost, LightGBM, CatBoost for one target.
    Returns comparison results dict.
    """
    print(f"\n{'='*70}")
    print(f"TRAINING TARGET: {target_name} ({task_type})")
    print(f"{'='*70}")

    # Prepare X, y — drop rows where target is null
    train_valid = train_df[train_df[target_name].notna()].copy()
    test_valid = test_df[test_df[target_name].notna()].copy()

    if len(train_valid) < 50:
        print(f"[train] SKIP {target_name}: only {len(train_valid)} training samples")
        return None

    X_train = train_valid[feat_cols].copy()
    X_test = test_valid[feat_cols].copy()

    # Handle any remaining NaN in features
    X_train = X_train.fillna(0)
    X_test = X_test.fillna(0)

    if task_type == "classification":
        # Label encode target
        target_le = LabelEncoder()
        y_train = target_le.fit_transform(train_valid[target_name])
        y_test = target_le.transform(test_valid[target_name]) if len(test_valid) > 0 else np.array([])
        joblib.dump(target_le, os.path.join(MODELS_DIR, f"{target_name}_label_encoder.joblib"))
    else:
        y_train = train_valid[target_name].values.astype(float)
        y_test = test_valid[target_name].values.astype(float) if len(test_valid) > 0 else np.array([])
        # Log-transform for time_to_resolution (right-skewed)
        if target_name == "time_to_resolution":
            y_train = np.log1p(y_train)
            y_test = np.log1p(y_test) if len(y_test) > 0 else y_test

    print(f"  Train samples: {len(X_train)}, Test samples: {len(X_test)}")
    print(f"  Features: {len(feat_cols)}")

    # --- Train 3 algorithms ---
    results = {}
    models = {}

    algorithms = {
        "XGBoost": (xgb_objective, xgb.XGBClassifier if task_type == "classification" else xgb.XGBRegressor),
        "LightGBM": (lgb_objective, lgb.LGBMClassifier if task_type == "classification" else lgb.LGBMRegressor),
        "CatBoost": (cb_objective, cb.CatBoostClassifier if task_type == "classification" else cb.CatBoostRegressor),
    }

    for algo_name, (objective_fn, ModelClass) in algorithms.items():
        print(f"\n  --- {algo_name} ---")

        # Hyperparameter tuning with Optuna
        best_params = {}
        if HAS_OPTUNA:
            study = optuna.create_study(direction="maximize")
            study.optimize(
                lambda trial: objective_fn(trial, X_train, y_train, task_type, target_name),
                n_trials=N_OPTUNA_TRIALS,
                show_progress_bar=False,
            )
            best_params = study.best_params
            print(f"  Best CV score: {study.best_value:.4f}")
        else:
            best_params = {"n_estimators": 200, "max_depth": 5, "learning_rate": 0.1}

        # Train final model with best params
        if algo_name == "CatBoost":
            final_params = {
                "iterations": best_params.get("iterations", 200),
                "depth": best_params.get("depth", 5),
                "learning_rate": best_params.get("learning_rate", 0.1),
                "l2_leaf_reg": best_params.get("l2_leaf_reg", 1.0),
                "random_seed": RANDOM_STATE,
                "verbose": 0,
            }
        else:
            final_params = {
                "n_estimators": best_params.get("n_estimators", 200),
                "max_depth": best_params.get("max_depth", 5),
                "learning_rate": best_params.get("learning_rate", 0.1),
                "subsample": best_params.get("subsample", 0.8),
                "colsample_bytree": best_params.get("colsample_bytree", 0.8),
                "random_state": RANDOM_STATE,
            }
            if algo_name == "XGBoost":
                final_params["verbosity"] = 0
                if task_type == "classification":
                    final_params["eval_metric"] = "mlogloss"
            else:
                final_params["verbosity"] = -1
                final_params["reg_alpha"] = best_params.get("reg_alpha", 0.1)
                final_params["reg_lambda"] = best_params.get("reg_lambda", 0.1)

        model = ModelClass(**final_params)
        model.fit(X_train, y_train)
        models[algo_name] = model

        # Cross-validation scores
        if task_type == "classification":
            cv = StratifiedKFold(n_splits=N_FOLDS, shuffle=True, random_state=RANDOM_STATE)
            cv_scores = cross_val_score(model, X_train, y_train, cv=cv,
                                        scoring="f1_macro", n_jobs=-1)
        else:
            cv = KFold(n_splits=N_FOLDS, shuffle=True, random_state=RANDOM_STATE)
            scoring = expm1_mae_scorer if target_name == "time_to_resolution" else "neg_mean_absolute_error"
            cv_scores = cross_val_score(model, X_train, y_train, cv=cv,
                                        scoring=scoring, n_jobs=-1)

        # Test set evaluation
        if len(y_test) > 0:
            y_pred = model.predict(X_test)

            if task_type == "classification":
                acc = accuracy_score(y_test, y_pred)
                f1_mac = f1_score(y_test, y_pred, average="macro", zero_division=0)
                f1_wt = f1_score(y_test, y_pred, average="weighted", zero_division=0)
                cm = confusion_matrix(y_test, y_pred).tolist()

                results[algo_name] = {
                    "cv_mean": float(cv_scores.mean()),
                    "cv_std": float(cv_scores.std()),
                    "test_accuracy": float(acc),
                    "test_f1_macro": float(f1_mac),
                    "test_f1_weighted": float(f1_wt),
                    "confusion_matrix": cm,
                    "params": {k: (int(v) if isinstance(v, (np.integer,)) else
                                   float(v) if isinstance(v, (np.floating, float)) else v)
                               for k, v in best_params.items()},
                }
                print(f"  Test — Acc: {acc:.4f}, F1-macro: {f1_mac:.4f}, F1-weighted: {f1_wt:.4f}")
            else:
                if target_name == "time_to_resolution":
                    y_pred_actual = np.expm1(y_pred)
                    y_test_actual = np.expm1(y_test)
                else:
                    y_pred_actual = y_pred
                    y_test_actual = y_test

                mae = mean_absolute_error(y_test_actual, y_pred_actual)
                rmse = np.sqrt(mean_squared_error(y_test_actual, y_pred_actual))
                r2 = r2_score(y_test_actual, y_pred_actual)

                results[algo_name] = {
                    "cv_mean": float(cv_scores.mean()),
                    "cv_std": float(cv_scores.std()),
                    "test_mae": float(mae),
                    "test_rmse": float(rmse),
                    "test_r2": float(r2),
                    "params": {k: (int(v) if isinstance(v, (np.integer,)) else
                                   float(v) if isinstance(v, (np.floating, float)) else v)
                               for k, v in best_params.items()},
                }
                print(f"  Test — MAE: {mae:.2f}, RMSE: {rmse:.2f}, R²: {r2:.4f}")

        print(f"  CV — {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")

    # --- Select best model ---
    if task_type == "classification":
        best_algo = max(results, key=lambda k: results[k].get("test_f1_macro", results[k]["cv_mean"]))
    else:
        best_algo = max(results, key=lambda k: results[k].get("test_r2", results[k]["cv_mean"]))

    print(f"\n  *** Best algorithm for {target_name}: {best_algo} ***")

    # Save best model
    best_model = models[best_algo]
    model_path = os.path.join(MODELS_DIR, f"{target_name}_model.joblib")
    joblib.dump(best_model, model_path)
    print(f"  Saved to {model_path}")

    return {
        "target": target_name,
        "task_type": task_type,
        "best_algorithm": best_algo,
        "results": results,
        "feature_columns": feat_cols,
        "train_samples": len(X_train),
        "test_samples": len(X_test),
    }


def train_all():
    """Train models for all 3 targets."""
    train_df, test_df, feat_cols, encoders = prepare_data()

    all_results = {}

    # Target 1: time_to_resolution (regression — ground truth)
    res1 = train_target("time_to_resolution", "regression",
                        train_df, test_df, feat_cols)
    if res1:
        all_results["time_to_resolution"] = res1

    # Target 2: congestion_severity (classification — heuristic)
    res2 = train_target("congestion_severity", "classification",
                        train_df, test_df, feat_cols)
    if res2:
        all_results["congestion_severity"] = res2

    # Target 3: required_manpower (classification — heuristic)
    res3 = train_target("required_manpower", "classification",
                        train_df, test_df, feat_cols)
    if res3:
        all_results["required_manpower"] = res3

    # Save model metadata
    metadata = {
        "training_date": datetime.now().isoformat(),
        "feature_columns": feat_cols,
        "targets": {},
    }
    for name, res in all_results.items():
        metadata["targets"][name] = {
            "task_type": res["task_type"],
            "best_algorithm": res["best_algorithm"],
            "train_samples": res["train_samples"],
            "test_samples": res["test_samples"],
            "cv_mean": res["results"][res["best_algorithm"]]["cv_mean"],
            "cv_std": res["results"][res["best_algorithm"]]["cv_std"],
            "ground_truth": name == "time_to_resolution",
            "heuristic": name != "time_to_resolution",
        }
        # Add test metrics
        best_res = res["results"][res["best_algorithm"]]
        for k, v in best_res.items():
            if k.startswith("test_"):
                metadata["targets"][name][k] = v

    with open(os.path.join(MODELS_DIR, "model_metadata.json"), "w") as f:
        json.dump(metadata, f, indent=2)

    # Save full comparison results
    with open(os.path.join(RESULTS_DIR, "model_comparison.json"), "w") as f:
        json.dump(all_results, f, indent=2, default=str)

    # Print summary table
    print("\n" + "=" * 70)
    print("MODEL COMPARISON SUMMARY")
    print("=" * 70)
    for target_name, res in all_results.items():
        print(f"\n  {target_name} ({res['task_type']}):")
        for algo, metrics in res["results"].items():
            marker = "***" if algo == res["best_algorithm"] else "   "
            if res["task_type"] == "classification":
                test_acc = f"{metrics['test_accuracy']:.4f}" if isinstance(metrics.get('test_accuracy'), float) else "N/A"
                test_f1 = f"{metrics['test_f1_macro']:.4f}" if isinstance(metrics.get('test_f1_macro'), float) else "N/A"
                print(f"    {marker} {algo:12s} | CV F1: {metrics['cv_mean']:.4f}±{metrics['cv_std']:.4f} | "
                      f"Test Acc: {test_acc} | Test F1: {test_f1}")
            else:
                test_mae = f"{metrics['test_mae']:.2f}" if isinstance(metrics.get('test_mae'), float) else "N/A"
                test_r2 = f"{metrics['test_r2']:.4f}" if isinstance(metrics.get('test_r2'), float) else "N/A"
                print(f"    {marker} {algo:12s} | CV MAE: {abs(metrics['cv_mean']):.2f}±{metrics['cv_std']:.2f} | "
                      f"Test MAE: {test_mae} | Test R²: {test_r2}")

    return all_results


if __name__ == "__main__":
    train_all()
