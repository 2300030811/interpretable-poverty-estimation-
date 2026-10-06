"""
tests/test_conformal.py — Unit tests for Split Conformal Prediction engine.
"""
import pytest
import numpy as np
import sys
from pathlib import Path

# Add project src to path
ROOT = Path(__file__).resolve().parent.parent
PROJECT_DIR = ROOT / "EHCVM_Project" / "EHCVM_Project"
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from src.conformal import ConformalPovertyClassifier

def test_conformal_coverage_on_synthetic_data():
    """Verify that empirical coverage meets (1 - alpha) guarantee within statistical bounds."""
    np.random.seed(42)
    n = 1000
    alpha = 0.10
    
    # Generate synthetic well-calibrated probabilities
    y = np.random.binomial(1, 0.4, size=n)
    probs_1 = np.where(y == 1, np.random.uniform(0.4, 0.9, size=n), np.random.uniform(0.1, 0.6, size=n))
    probs = np.column_stack([1.0 - probs_1, probs_1])

    # Split calibration and test
    cal_idx, test_idx = range(0, 500), range(500, 1000)
    probs_cal, y_cal = probs[cal_idx], y[cal_idx]
    probs_te, y_te = probs[test_idx], y[test_idx]

    cp = ConformalPovertyClassifier(alpha=alpha)
    cp.calibrate(probs_cal, y_cal)

    eval_res = cp.evaluate(probs_te, y_te)
    
    # Coverage must be near 90% (>= 85% allowing for finite-sample noise)
    assert eval_res["empirical_coverage"] >= 0.85
    assert eval_res["average_set_size"] >= 1.0
    assert eval_res["passed_coverage_guarantee"] is True

def test_conformal_empty_guard():
    """Verify ValueError is raised on empty calibration set."""
    cp = ConformalPovertyClassifier()
    with pytest.raises(ValueError):
        cp.calibrate(np.empty((0, 2)), np.empty(0))

def test_conformal_prediction_set_categories():
    """Verify triage categorization for extreme probabilities."""
    cp = ConformalPovertyClassifier(alpha=0.10)
    cp.q_hat = 0.55

    # Near-certain poor (p=0.99)
    res_poor = cp.predict_sets(np.array([[0.01, 0.99]]))[0]
    assert res_poor["classes"] == [1]
    assert res_poor["category"] == "CERTAIN_POOR"

    # Near-certain non-poor (p=0.01)
    res_non_poor = cp.predict_sets(np.array([[0.99, 0.01]]))[0]
    assert res_non_poor["classes"] == [0]
    assert res_non_poor["category"] == "CERTAIN_NON_POOR"

    # Ambiguous / uncertain (p=0.50)
    res_amb = cp.predict_sets(np.array([[0.50, 0.50]]))[0]
    assert res_amb["category"] == "AMBIGUOUS"
    assert res_amb["classes"] == [0, 1]
