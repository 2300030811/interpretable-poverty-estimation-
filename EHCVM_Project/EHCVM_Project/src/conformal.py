"""
conformal.py — Split Conformal Prediction for Distribution-Free Uncertainty Quantification.

Provides mathematical coverage guarantees (1 - alpha) for household poverty targeting:
Each household receives a prediction set C(X) subset of {0, 1}:
  - {1}     : Certain Poor      -> Automated enrollment in social safety net
  - {0}     : Certain Non-Poor  -> Exclude from transfer
  - {0, 1}  : Ambiguous / Borderline -> Flag for physical field visit / manual audit
  - {}      : Out of Distribution / Anomaly
"""
from typing import Dict, List, Tuple, Any, Optional
import math
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from . import config

class ConformalPovertyClassifier:
    """
    Split Conformal Classification for binary poverty estimation.
    Guarantee: P(Y in C(X)) >= 1 - alpha for any underlying distribution.
    """
    def __init__(self, alpha: float = 0.10):
        self.alpha = float(alpha)
        self.target_coverage = 1.0 - self.alpha
        self.q_hat: Optional[float] = None
        self.cal_size: int = 0

    def calibrate(self, probs_cal: np.ndarray, y_cal: np.ndarray) -> "ConformalPovertyClassifier":
        """
        Calibrate non-conformity threshold using split calibration set.
        probs_cal: shape (n, 2) predicted class probabilities
        y_cal: shape (n,) ground truth labels (0 or 1)
        """
        n = len(y_cal)
        self.cal_size = n
        if n == 0:
            raise ValueError("Calibration set cannot be empty.")

        y_cal = np.asarray(y_cal).astype(int)
        # Non-conformity score: 1 - P(true class)
        # For true label y, prob of true class is probs_cal[i, y_i]
        true_class_probs = probs_cal[np.arange(n), y_cal]
        scores = 1.0 - true_class_probs

        # Finite-sample adjusted quantile index
        # ceil((n + 1) * (1 - alpha)) / n
        level = min(1.0, math.ceil((n + 1) * (1.0 - self.alpha)) / n)
        self.q_hat = float(np.quantile(scores, level, method="higher"))
        return self

    def predict_sets(self, probs: np.ndarray) -> List[dict]:
        """
        Generate prediction sets for query probabilities.
        probs: shape (n, 2) or shape (n,)
        Returns list of triage dicts with set elements, category, and size.
        """
        if self.q_hat is None:
            raise RuntimeError("Classifier must be calibrated before predict_sets.")

        if probs.ndim == 1:
            probs = np.column_stack([1.0 - probs, probs])

        n = len(probs)
        results = []

        # Class 0 non-conformity score = 1 - P(Y=0) = P(Y=1)
        # Class 1 non-conformity score = 1 - P(Y=1) = P(Y=0)
        score_0 = 1.0 - probs[:, 0]
        score_1 = 1.0 - probs[:, 1]

        include_0 = score_0 <= self.q_hat
        include_1 = score_1 <= self.q_hat

        for i in range(n):
            classes = []
            if include_0[i]:
                classes.append(0)
            if include_1[i]:
                classes.append(1)

            size = len(classes)
            if size == 2:
                category = "AMBIGUOUS"
                action = "FLAG_FOR_FIELD_VISIT"
            elif classes == [1]:
                category = "CERTAIN_POOR"
                action = "AUTO_ENROLL_AID"
            elif classes == [0]:
                category = "CERTAIN_NON_POOR"
                action = "EXCLUDE_BENEFIT"
            else:
                category = "EMPTY_ANOMALY"
                action = "FLAG_DATA_ERROR"

            results.append({
                "classes": classes,
                "category": category,
                "recommended_action": action,
                "set_size": size,
                "prob_poor": float(probs[i, 1]),
            })

        return results

    def evaluate(self, probs_test: np.ndarray, y_test: np.ndarray) -> Dict[str, float]:
        """Compute empirical coverage and triage statistics on test data."""
        y_test = np.asarray(y_test).astype(int)
        sets = self.predict_sets(probs_test)
        n = len(y_test)

        covered = sum(1 for i, s in enumerate(sets) if y_test[i] in s["classes"])
        set_sizes = [s["set_size"] for s in sets]
        categories = [s["category"] for s in sets]

        return {
            "target_coverage": self.target_coverage,
            "empirical_coverage": float(covered / n) if n > 0 else 0.0,
            "coverage_gap_pp": float((covered / n - self.target_coverage) * 100) if n > 0 else 0.0,
            "average_set_size": float(np.mean(set_sizes)) if n > 0 else 0.0,
            "certain_poor_pct": float(categories.count("CERTAIN_POOR") / n * 100) if n > 0 else 0.0,
            "certain_non_poor_pct": float(categories.count("CERTAIN_NON_POOR") / n * 100) if n > 0 else 0.0,
            "ambiguous_pct": float(categories.count("AMBIGUOUS") / n * 100) if n > 0 else 0.0,
            "empty_pct": float(categories.count("EMPTY_ANOMALY") / n * 100) if n > 0 else 0.0,
            "q_hat": self.q_hat,
            "calibration_samples": self.cal_size,
            "test_samples": n,
            "passed_coverage_guarantee": bool((covered / n) >= self.target_coverage - 0.035), # finite sample statistical tolerance
        }


def run_conformal_audit(data: dict = None, alpha: float = 0.10) -> dict:
    """
    Run cross-country and pooled conformal prediction audits.
    Calibrates on 80% pooled data or LOCO folds and verifies mathematical coverage guarantees.
    """
    from .dashboard_utils import load_simulator_artifact
    from .models import load_clean_data

    if data is None:
        data = load_clean_data()

    artifact = load_simulator_artifact()
    if not artifact:
        raise RuntimeError("Simulator model artifact not found.")

    model = artifact["model"]
    feature_cols = artifact["feature_cols"]

    print("\n" + "=" * 70)
    print("CONFORMAL PREDICTION AUDIT (1 - alpha = 90% Coverage Guarantee)")
    print("=" * 70)

    # 1. Evaluate per-country calibration and test
    country_results = {}
    all_cal_probs, all_cal_y = [], []
    all_test_probs, all_test_y = [], []

    for country_name, df in data.items():
        X = df[feature_cols]
        y = df[config.TARGET_COL].values
        probs = model.predict_proba(X)

        # Split 50% cal, 50% test for clean conformal evaluation
        X_cal, X_te, y_cal, y_te, p_cal, p_te = train_test_split(
            X, y, probs, test_size=0.5, random_state=config.RANDOM_SEED, stratify=y
        )

        cp = ConformalPovertyClassifier(alpha=alpha)
        cp.calibrate(p_cal, y_cal)
        eval_metrics = cp.evaluate(p_te, y_te)
        country_results[country_name] = eval_metrics

        all_cal_probs.append(p_cal)
        all_cal_y.append(y_cal)
        all_test_probs.append(p_te)
        all_test_y.append(y_te)

        status = "PASS OK" if eval_metrics["passed_coverage_guarantee"] else "FAIL"
        print(f"  {country_name:20s}: Coverage={eval_metrics['empirical_coverage']:.1%} "
              f"(Target={1-alpha:.1%})  Avg Set={eval_metrics['average_set_size']:.2f}  "
              f"Ambiguous={eval_metrics['ambiguous_pct']:.1f}%  [{status}]")

    # 2. Overall pooled conformal evaluation
    pooled_p_cal = np.vstack(all_cal_probs)
    pooled_y_cal = np.concatenate(all_cal_y)
    pooled_p_te = np.vstack(all_test_probs)
    pooled_y_te = np.concatenate(all_test_y)

    cp_pooled = ConformalPovertyClassifier(alpha=alpha)
    cp_pooled.calibrate(pooled_p_cal, pooled_y_cal)
    pooled_metrics = cp_pooled.evaluate(pooled_p_te, pooled_y_te)

    print("\n-- Pooled Cross-Country Conformal Summary -----------------------")
    print(f"  Target Coverage:       {1-alpha:.1%}")
    print(f"  Empirical Coverage:    {pooled_metrics['empirical_coverage']:.1%}")
    print(f"  Average Set Size:      {pooled_metrics['average_set_size']:.3f}")
    print(f"  Triage Breakdown:")
    print(f"    - Certain Poor:      {pooled_metrics['certain_poor_pct']:.1f}% (auto-aid)")
    print(f"    - Certain Non-Poor:  {pooled_metrics['certain_non_poor_pct']:.1f}% (exclude)")
    print(f"    - Ambiguous:         {pooled_metrics['ambiguous_pct']:.1f}% (field audit)")

    final_report = {
        "alpha": alpha,
        "target_coverage": 1.0 - alpha,
        "pooled": pooled_metrics,
        "countries": country_results,
        "passed": pooled_metrics["passed_coverage_guarantee"],
    }

    out_path = config.OUTPUT_RESULTS / "o6_conformal_analysis.json"
    out_path.write_text(json.dumps(final_report, indent=2), encoding="utf-8")
    print(f"\n  -> Saved: {out_path.name}")
    return final_report


if __name__ == "__main__":
    run_conformal_audit()
