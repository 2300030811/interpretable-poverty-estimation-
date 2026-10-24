"""
models.py — O2: Cross-country generalisation reference (black-box baselines).

Establishes the reference accuracy using Random Forest and XGBoost
via Leave-One-Country-Out (LOCO) evaluation.
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
import xgboost as xgb

from . import config
from .evaluate import evaluate_loco, evaluate_pooled, save_results, _get_feature_cols


def _make_rf(X_train, y_train):
    """Train a Random Forest classifier."""
    clf = RandomForestClassifier(
        random_state=config.RANDOM_SEED, **config.MODEL_PARAMS["random_forest"]
    )
    clf.fit(X_train, y_train)
    return clf


def _make_xgb(X_train, y_train):
    """Train an XGBoost classifier."""
    clf = xgb.XGBClassifier(
        random_state=config.RANDOM_SEED, **config.MODEL_PARAMS["xgboost"]
    )
    clf.fit(X_train, y_train)
    return clf


def load_clean_data() -> dict[str, pd.DataFrame]:
    """Load all clean CSVs from data/processed/."""
    data = {}
    for name, meta in config.COUNTRIES.items():
        path = config.DATA_PROCESSED / f"{meta['code']}_clean.csv"
        if path.exists():
            df = pd.read_csv(path)
            # ponytail: fill any residual NaN with 0 — the pipeline already imputed,
            # but CSVs can re-introduce NaN for blank cells
            df = df.fillna(0)
            data[name] = df
        else:
            print(f"  ⚠ Missing: {path}")
    if not data:
        raise RuntimeError(
            f"No processed datasets found in {config.DATA_PROCESSED}. "
            "Please run the data engineering pipeline (engineer.py) first."
        )
    return data


def run_baselines(data: dict[str, pd.DataFrame] = None) -> dict:
    """
    Run O2 baselines: RF and XGBoost under LOCO and pooled protocols.
    Returns dict of all results keyed by model+method.
    """
    if data is None:
        data = load_clean_data()

    print("\n" + "=" * 70)
    print("O2 — CROSS-COUNTRY GENERALISATION REFERENCE")
    print("=" * 70)

    all_results = {}

    # -- Random Forest ----------------------------------------------------
    print("\n-- Random Forest (LOCO) ------------------------------------")
    rf_loco = evaluate_loco(_make_rf, data, "random_forest")
    save_results(rf_loco, "o2_rf_loco.json")
    all_results["rf_loco"] = rf_loco

    print("\n-- Random Forest (Pooled) ----------------------------------")
    rf_pooled = evaluate_pooled(_make_rf, data, "random_forest")
    save_results(rf_pooled, "o2_rf_pooled.json")
    all_results["rf_pooled"] = rf_pooled

    # -- XGBoost ----------------------------------------------------------
    print("\n-- XGBoost (LOCO) -----------------------------------------")
    xgb_loco = evaluate_loco(_make_xgb, data, "xgboost")
    save_results(xgb_loco, "o2_xgb_loco.json")
    all_results["xgb_loco"] = xgb_loco

    print("\n-- XGBoost (Pooled) ---------------------------------------")
    xgb_pooled = evaluate_pooled(_make_xgb, data, "xgboost")
    save_results(xgb_pooled, "o2_xgb_pooled.json")
    all_results["xgb_pooled"] = xgb_pooled

    # Summary
    print("\n-- O2 Reference Summary -----------------------------------")
    for key, res in all_results.items():
        if "macro" in res:
            m = res["macro"]
            print(f"  {key:20s}  acc={m['accuracy']:.3f}  auc={m.get('auc_roc', float('nan')):.3f}")
        elif "overall" in res:
            m = res["overall"]
            print(f"  {key:20s}  acc={m['accuracy']:.3f}  auc={m.get('auc_roc', float('nan')):.3f}")

    return all_results


if __name__ == "__main__":
    run_baselines()
