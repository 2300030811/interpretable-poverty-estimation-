"""
evaluate.py — Shared evaluation harness for all models.

Computes accuracy, AUC-ROC, F1, precision, recall, confusion matrix.
Saves results as versioned JSON for lineage (NFR-3).
"""
import json
import datetime
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.metrics import (
    accuracy_score, roc_auc_score, f1_score,
    precision_score, recall_score, confusion_matrix,
)

from . import config


def compute_metrics(y_true, y_pred, y_prob=None) -> dict:
    """Compute standard classification metrics."""
    cm = confusion_matrix(y_true, y_pred)
    tn, fp, fn, tp = cm.ravel()

    metrics = {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp),
        "n": len(y_true),
        "prevalence": float(y_true.mean()),
        # Targeting errors (O4)
        "exclusion_error": float(fn / (fn + tp)) if (fn + tp) > 0 else 0.0,
        "inclusion_error": float(fp / (fp + tn)) if (fp + tn) > 0 else 0.0,
    }
    if y_prob is not None:
        try:
            metrics["auc_roc"] = float(roc_auc_score(y_true, y_prob))
        except ValueError:
            metrics["auc_roc"] = float("nan")
    return metrics


def evaluate_loco(model_fn, data: dict[str, pd.DataFrame], model_name: str) -> dict:
    """
    Leave-One-Country-Out evaluation.

    model_fn(X_train, y_train) -> fitted model with .predict() and .predict_proba()
    data: {country_name: DataFrame with features + 'poor'}
    Returns per-country and macro-averaged metrics.
    """
    countries = list(data.keys())
    feature_cols = _get_feature_cols(data)
    results = {"model": model_name, "method": "LOCO", "countries": {}}

    for test_country in countries:
        # Train on all except test_country
        train_dfs = [data[c] for c in countries if c != test_country]
        train = pd.concat(train_dfs, ignore_index=True)

        X_train = train[feature_cols].values
        y_train = train[config.TARGET_COL].values
        X_test = data[test_country][feature_cols].values
        y_test = data[test_country][config.TARGET_COL].values

        model = model_fn(X_train, y_train)
        y_pred = model.predict(X_test)
        y_prob = _safe_predict_proba(model, X_test)

        metrics = compute_metrics(y_test, y_pred, y_prob)
        results["countries"][test_country] = metrics
        print(f"    {test_country:20s}  acc={metrics['accuracy']:.3f}  "
              f"auc={metrics.get('auc_roc', float('nan')):.3f}  "
              f"f1={metrics['f1']:.3f}")

    # Macro averages
    results["macro"] = _macro_average(results["countries"])
    print(f"    {'MACRO':20s}  acc={results['macro']['accuracy']:.3f}  "
          f"auc={results['macro'].get('auc_roc', float('nan')):.3f}  "
          f"f1={results['macro']['f1']:.3f}")

    return results


def evaluate_pooled(model_fn, data: dict[str, pd.DataFrame],
                    model_name: str, test_frac: float = 0.2) -> dict:
    """
    Pooled train/test evaluation (stratified by country).
    """
    from sklearn.model_selection import train_test_split

    feature_cols = _get_feature_cols(data)
    pooled = pd.concat(data.values(), ignore_index=True)

    X = pooled[feature_cols].values
    y = pooled[config.TARGET_COL].values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_frac, random_state=config.RANDOM_SEED, stratify=y
    )

    model = model_fn(X_train, y_train)
    y_pred = model.predict(X_test)
    y_prob = _safe_predict_proba(model, X_test)

    metrics = compute_metrics(y_test, y_pred, y_prob)
    results = {"model": model_name, "method": "pooled", "overall": metrics}
    print(f"    Pooled  acc={metrics['accuracy']:.3f}  "
          f"auc={metrics.get('auc_roc', float('nan')):.3f}  "
          f"f1={metrics['f1']:.3f}")
    return results


def save_results(results: dict, filename: str, out_dir: Path = None):
    """Save results dict as JSON with timestamp for lineage."""
    out_dir = out_dir or config.OUTPUT_RESULTS
    out_dir.mkdir(parents=True, exist_ok=True)
    results["saved_at"] = datetime.datetime.now().isoformat()
    results["seed"] = config.RANDOM_SEED
    path = out_dir / filename
    path.write_text(json.dumps(results, indent=2, default=str))
    print(f"  -> Saved: {path.name}")
    return path


def _get_feature_cols(data: dict[str, pd.DataFrame]) -> list[str]:
    """Get feature columns from any DataFrame in the dict, sorted for canonical order."""
    sample = next(iter(data.values()))
    return sorted([c for c in sample.columns if c not in config.EXCLUDE_FROM_FEATURES])


def _safe_predict_proba(model, X):
    """Get probability of positive class, None if not available."""
    if hasattr(model, "predict_proba"):
        return model.predict_proba(X)[:, 1]
    return None


def _macro_average(country_metrics: dict) -> dict:
    """Average metrics across countries."""
    keys = ["accuracy", "f1", "precision", "recall", "auc_roc",
            "exclusion_error", "inclusion_error"]
    macro = {}
    for k in keys:
        vals = [m[k] for m in country_metrics.values()
                if k in m and not (isinstance(m[k], float) and np.isnan(m[k]))]
        macro[k] = float(np.mean(vals)) if vals else float("nan")
    macro["n_countries"] = len(country_metrics)
    return macro
