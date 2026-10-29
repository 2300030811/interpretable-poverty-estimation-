"""
domain_diagnostics.py — Distributional Shift & Compatibility Diagnostics for Survey Uploads.

Evaluates empirical distribution divergence between uploaded destination-country survey microdata
and the reference EHCVM baseline training distribution across 73 features.

Core Principles:
1. Input Compatibility != Distributional Similarity != Predictive Accuracy.
2. A low domain-shift score does NOT guarantee high predictive accuracy.
3. A high domain-shift score indicates substantial distributional shift, which may degrade
   model calibration and increase transfer error.
"""
from typing import Dict, List, Any, Optional
import numpy as np
import pandas as pd

from . import feature_contract

SHIFT_LOW_THRESHOLD = 0.15
SHIFT_MODERATE_THRESHOLD = 0.35


def compute_feature_shift(
    uploaded_vals: pd.Series,
    baseline_stats: Dict[str, float],
    feat_meta: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Compute domain shift metrics for a single feature between upload and baseline reference.
    """
    clean_vals = pd.to_numeric(uploaded_vals, errors="coerce").dropna()
    n_total = len(uploaded_vals)
    n_valid = len(clean_vals)
    missing_pct = float((n_total - n_valid) / n_total * 100) if n_total > 0 else 100.0

    if n_valid == 0:
        return {
            "status": "COMPLETELY_MISSING",
            "drift_score": 1.0,
            "shift_category": "SEVERE_SHIFT",
            "missing_pct": missing_pct,
            "range_violation_pct": 0.0,
            "median_diff": None,
            "alert": "No valid numeric observations in uploaded column.",
        }

    # 1. Range Violations
    min_allowed, max_allowed = feat_meta["range"]
    n_out_of_bounds = int(np.sum((clean_vals < min_allowed) | (clean_vals > max_allowed)))
    range_violation_pct = float(n_out_of_bounds / n_valid * 100)

    # 2. Distributional shift
    ref_median = baseline_stats.get("median", 0.0)
    ref_q25 = baseline_stats.get("q25", 0.0)
    ref_q75 = baseline_stats.get("q75", 1.0)
    ref_iqr = max(0.01, ref_q75 - ref_q25)

    up_median = float(clean_vals.median())
    up_q25 = float(clean_vals.quantile(0.25))
    up_q75 = float(clean_vals.quantile(0.75))

    # Normalized median shift
    norm_median_shift = abs(up_median - ref_median) / ref_iqr

    # For binary / categorical features, compare mean proportion difference
    feat_type = feat_meta.get("type", "continuous")
    if feat_type == "binary":
        ref_mean = baseline_stats.get("mean", 0.5)
        up_mean = float(clean_vals.mean())
        drift = min(1.0, abs(up_mean - ref_mean))
    else:
        # Bounded normalized median shift + IQR ratio divergence
        up_iqr = max(0.001, up_q75 - up_q25)
        iqr_ratio = max(up_iqr / ref_iqr, ref_iqr / up_iqr)
        drift = min(1.0, (norm_median_shift * 0.7) + (min(2.0, iqr_ratio - 1.0) * 0.15))

    if drift < SHIFT_LOW_THRESHOLD:
        category = "LOW_SHIFT"
        alert = None
    elif drift < SHIFT_MODERATE_THRESHOLD:
        category = "MODERATE_SHIFT"
        alert = f"Moderate distribution divergence (drift score: {drift:.2f})."
    else:
        category = "SEVERE_SHIFT"
        alert = f"Severe distribution shift: uploaded median {up_median:.1f} vs baseline {ref_median:.1f}."

    if range_violation_pct > 5.0:
        category = "SEVERE_SHIFT"
        alert = (alert or "") + f" {range_violation_pct:.1f}% values outside plausible bounds [{min_allowed}, {max_allowed}]."

    return {
        "status": "OBSERVED",
        "drift_score": float(drift),
        "shift_category": category,
        "missing_pct": missing_pct,
        "range_violation_pct": range_violation_pct,
        "uploaded_median": up_median,
        "baseline_median": ref_median,
        "alert": alert,
    }


def evaluate_domain_shift(
    df_raw: pd.DataFrame,
    matched_mapping: Dict[str, str],
    reference_stats: Optional[Dict[str, Dict[str, float]]] = None,
) -> Dict[str, Any]:
    """
    Run domain shift diagnostics on all matched features in the uploaded survey.
    Distinguishes input compatibility from distribution shift and actual predictive accuracy.
    """
    if reference_stats is None:
        reference_stats = feature_contract.load_baseline_reference_stats()

    feature_shifts = {}
    drift_scores = []
    severe_alerts = []
    moderate_alerts = []

    for raw_col, canonical in matched_mapping.items():
        if canonical not in feature_contract.CANONICAL_FEATURE_CONTRACT:
            continue

        base_s = reference_stats.get(canonical, {})
        feat_m = feature_contract.CANONICAL_FEATURE_CONTRACT[canonical]
        res = compute_feature_shift(df_raw[raw_col], base_s, feat_m)
        feature_shifts[canonical] = res
        drift_scores.append(res["drift_score"])

        if res["shift_category"] == "SEVERE_SHIFT":
            severe_alerts.append(f"**{canonical}** (`{raw_col}`): {res['alert']}")
        elif res["shift_category"] == "MODERATE_SHIFT" and res["alert"]:
            moderate_alerts.append(f"**{canonical}** (`{raw_col}`): {res['alert']}")

    mean_drift = float(np.mean(drift_scores)) if drift_scores else 0.0
    shift_index_pct = round(mean_drift * 100, 1)

    if mean_drift < SHIFT_LOW_THRESHOLD:
        overall_level = "LOW"
        risk_summary = "Uploaded survey feature distributions closely track the EHCVM baseline."
    elif mean_drift < SHIFT_MODERATE_THRESHOLD:
        overall_level = "MODERATE"
        risk_summary = "Noticeable distribution shift detected in several features. Model transfer may experience moderate calibration drift."
    else:
        overall_level = "HIGH"
        risk_summary = "Substantial distribution shift detected across key survey indicators. Model accuracy may degrade significantly."

    return {
        "overall_shift_index": shift_index_pct,
        "overall_shift_level": overall_level,
        "risk_summary": risk_summary,
        "evaluated_features_count": len(drift_scores),
        "severe_alerts": severe_alerts,
        "moderate_alerts": moderate_alerts,
        "feature_shifts": feature_shifts,
        "scientific_disclaimer": (
            "Distributional similarity (low shift) is necessary but NOT sufficient for predictive accuracy. "
            "A low domain-shift score does NOT prove model accuracy, and a high domain-shift score indicates "
            "distributional divergence where calibration validity must not be presumed without local evaluation."
        ),
    }
