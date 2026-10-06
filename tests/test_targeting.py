"""
tests/test_targeting.py — Unit tests for Policy Targeting Error curves and cost optimization.
"""
import pytest
import numpy as np
import pandas as pd
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROJECT_DIR = ROOT / "EHCVM_Project" / "EHCVM_Project"
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from src.targeting import compute_threshold_curve, find_optimal_threshold

def test_targeting_curve_monotonicity():
    """Verify that exclusion error increases and inclusion error decreases as threshold rises."""
    np.random.seed(42)
    y_true = np.array([1]*50 + [0]*50)
    # Probabilities centered higher for poor
    y_prob = np.concatenate([np.random.uniform(0.3, 0.9, 50), np.random.uniform(0.1, 0.6, 50)])

    curve_df = compute_threshold_curve(y_true, y_prob)

    # Exclusion error should generally increase or stay flat
    exc_diffs = np.diff(curve_df["exclusion_error"].values)
    assert np.all(exc_diffs >= -1e-6), "Exclusion error must be monotonically non-decreasing with threshold"

    # Inclusion error should generally decrease or stay flat
    inc_diffs = np.diff(curve_df["inclusion_error"].values)
    assert np.all(inc_diffs <= 1e-6), "Inclusion error must be monotonically non-increasing with threshold"

def test_find_optimal_threshold_cost_sensitivity():
    """Verify that higher cost ratio (penalizing exclusion) shifts optimal threshold lower."""
    y_true = np.array([1]*50 + [0]*50)
    y_prob = np.concatenate([np.linspace(0.4, 0.95, 50), np.linspace(0.05, 0.6, 50)])
    curve_df = compute_threshold_curve(y_true, y_prob)

    opt_ratio_1 = find_optimal_threshold(curve_df, cost_ratio=1.0)
    opt_ratio_5 = find_optimal_threshold(curve_df, cost_ratio=5.0)

    # Higher penalty on exclusion should favor lower threshold to enroll more people
    assert opt_ratio_5["threshold"] <= opt_ratio_1["threshold"]
    assert opt_ratio_5["exclusion_error"] <= opt_ratio_1["exclusion_error"]
