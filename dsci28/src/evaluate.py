"""
evaluate.py — Shared evaluation harness for cross-country models and external validation.

Computes accuracy, AUC-ROC, PR-AUC, F1, precision, recall, Brier score, log loss,
targeting errors (exclusion/inclusion), and headcount estimation error.
Preserves LOCO protocol while adding reproducible external destination-country evaluation.
"""
import json
import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score, roc_auc_score, f1_score,
    precision_score, recall_score, confusion_matrix,
    average_precision_score, brier_score_loss, log_loss,
)

from . import config


def compute_metrics(y_true, y_pred, y_prob=None, sample_weight=None) -> dict:
    """Compute standard and extended classification metrics with optional survey weights."""
    y_true = np.asarray(y_true).astype(int)
    y_pred = np.asarray(y_pred).astype(int)
    sw = np.asarray(sample_weight, dtype=float) if sample_weight is not None else None
    
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1], sample_weight=sw)
    tn, fp, fn, tp = cm.ravel()

    headcount_pred = float(np.average(y_pred, weights=sw)) if sw is not None else float(np.mean(y_pred))
    headcount_true = float(np.average(y_true, weights=sw)) if sw is not None else float(np.mean(y_true))

    metrics = {
        "accuracy": float(accuracy_score(y_true, y_pred, sample_weight=sw)),
        "f1": float(f1_score(y_true, y_pred, sample_weight=sw, zero_division=0)),
        "precision": float(precision_score(y_true, y_pred, sample_weight=sw, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, sample_weight=sw, zero_division=0)),
        "tn": int(round(tn)), "fp": int(round(fp)), "fn": int(round(fn)), "tp": int(round(tp)),
        "n": len(y_true),
        "is_weighted": sw is not None,
        "prevalence": headcount_true,
        "headcount_pred": headcount_pred,
        "headcount_true": headcount_true,
        "headcount_error": float(abs(headcount_pred - headcount_true)),
        # Targeting errors (O4)
        "exclusion_error": float(fn / (fn + tp)) if (fn + tp) > 0 else 0.0,
        "inclusion_error": float(fp / (fp + tn)) if (fp + tn) > 0 else 0.0,
    }
    if y_prob is not None:
        y_prob = np.asarray(y_prob, dtype=float)
        try:
            metrics["auc_roc"] = float(roc_auc_score(y_true, y_prob, sample_weight=sw))
        except ValueError:
            metrics["auc_roc"] = float("nan")

        try:
            metrics["pr_auc"] = float(average_precision_score(y_true, y_prob, sample_weight=sw))
        except ValueError:
            metrics["pr_auc"] = float("nan")

        try:
            metrics["brier"] = float(brier_score_loss(y_true, y_prob, sample_weight=sw))
        except ValueError:
            metrics["brier"] = float("nan")

        try:
            # Clip probabilities to avoid log loss infinity
            eps = 1e-15
            p_clipped = np.clip(y_prob, eps, 1.0 - eps)
            metrics["log_loss"] = float(log_loss(y_true, p_clipped, sample_weight=sw))
        except ValueError:
            metrics["log_loss"] = float("nan")

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


def bootstrap_metric_ci(y_true, y_prob, policy_threshold: float = 0.35, n_resamples: int = 100, seed: int = 42) -> dict:
    """Compute 95% bootstrap confidence intervals for key metrics."""
    rng = np.random.default_rng(seed)
    n = len(y_true)
    auc_list, f1_list, brier_list, err_list = [], [], [], []

    for _ in range(n_resamples):
        idx = rng.integers(0, n, size=n)
        yt = y_true[idx]
        yp = y_prob[idx]
        y_pred = (yp >= policy_threshold).astype(int)

        try:
            auc_list.append(float(roc_auc_score(yt, yp)))
        except ValueError:
            pass
        f1_list.append(float(f1_score(yt, y_pred, zero_division=0)))
        brier_list.append(float(brier_score_loss(yt, yp)))
        err_list.append(float(abs(np.mean(y_pred) - np.mean(yt))))

    def _ci(vals):
        if not vals:
            return {"mean": float("nan"), "ci_lower": float("nan"), "ci_upper": float("nan")}
        return {
            "mean": float(np.mean(vals)),
            "ci_lower": float(np.percentile(vals, 2.5)),
            "ci_upper": float(np.percentile(vals, 97.5)),
        }

    return {
        "auc_roc_95ci": _ci(auc_list),
        "f1_95ci": _ci(f1_list),
        "brier_95ci": _ci(brier_list),
        "headcount_error_95ci": _ci(err_list),
    }


def evaluate_external_dataset(
    model,
    feature_cols: list[str],
    df_external: pd.DataFrame,
    target_col: str = "poor",
    weight_col: Optional[str] = None,
    policy_threshold: float = 0.35,
    is_synthetic_fixture: bool = False,
    destination_name: str = "External Destination Survey",
    n_bootstrap: int = 100,
) -> dict:
    """
    Reproducible external evaluation harness for an unseen destination survey.
    
    1. Quarantines ground-truth labels and target leakage from inference.
    2. Runs the production harmonization and inference pipeline.
    3. Evaluates predictions against destination ground truth ONLY after scoring.
    4. Computes ROC-AUC, PR-AUC, F1, Brier, calibration, targeting errors, headcount error, and bootstrap CIs.
    5. Evaluates both unweighted sample and survey-weighted population metrics when weights are supplied.
    6. Explicitly marks whether validation is against real external microdata or software synthetic fixture.
    """
    from .adapter import validate_and_harmonize_survey

    if target_col not in df_external.columns:
        raise ValueError(f"Ground truth target column '{target_col}' not found in external dataset.")

    # 1. Quarantine ground-truth labels and weights
    y_true = pd.to_numeric(df_external[target_col], errors="coerce").fillna(0).astype(int).values
    sample_weights = None
    if weight_col and weight_col in df_external.columns:
        sample_weights = pd.to_numeric(df_external[weight_col], errors="coerce").fillna(1.0).values

    drop_cols = [target_col]
    if weight_col and weight_col in df_external.columns:
        drop_cols.append(weight_col)
    df_features_only = df_external.drop(columns=drop_cols).copy()

    # 2. Production harmonization (no label exposure)
    df_harmonized, meta = validate_and_harmonize_survey(
        df_features_only, canonical_features=feature_cols
    )

    if meta["status"] == "INSUFFICIENT":
        return {
            "destination_name": destination_name,
            "status": "INSUFFICIENT_COMPATIBILITY",
            "message": "Input compatibility is insufficient (<30% coverage or missing critical domains). Evaluation blocked.",
            "metadata": meta,
            "metrics": None,
        }

    # 3. Model Scoring
    probs = model.predict_proba(df_harmonized)[:, 1]
    y_pred = (probs >= policy_threshold).astype(int)

    # 4. Metric Computation (unweighted + optional survey-weighted)
    metrics = compute_metrics(y_true, y_pred, probs)
    weighted_metrics = None
    if sample_weights is not None:
        weighted_metrics = compute_metrics(y_true, y_pred, probs, sample_weight=sample_weights)

    # 5. Uncertainty quantification
    ci_res = bootstrap_metric_ci(y_true, probs, policy_threshold=policy_threshold, n_resamples=n_bootstrap)

    scientific_verification = (
        "GENUINE_EXTERNAL_VERIFIED" if not is_synthetic_fixture
        else "SYNTHETIC_FIXTURE_ONLY_UNVERIFIED_IN_WILD"
    )

    results = {
        "destination_name": destination_name,
        "is_synthetic_fixture": is_synthetic_fixture,
        "verification_status": scientific_verification,
        "evaluation_timestamp": datetime.datetime.now().isoformat(),
        "policy_threshold": policy_threshold,
        "n_households": len(y_true),
        "prevalence": float(np.mean(y_true)),
        "predicted_headcount": float(np.mean(y_pred)),
        "headcount_error_pp": float(abs(np.mean(y_pred) - np.mean(y_true)) * 100),
        "metrics": metrics,
        "weighted_metrics": weighted_metrics,
        "uncertainty_intervals": ci_res,
        "schema_metadata": {
            "feature_coverage_pct": meta["feature_coverage_pct"],
            "critical_coverage_pct": meta["critical_coverage_pct"],
            "observed_count": meta["observed_count"],
            "derived_count": meta["derived_count"],
            "imputed_count": meta["imputed_count"],
        },
        "disclaimer": (
            "Genuine external microdata evaluated." if not is_synthetic_fixture
            else "Real external-country generalization has not yet been verified with genuine external labeled microdata. Results are from a software-testing synthetic fixture."
        ),
    }

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
