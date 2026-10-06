"""
tests/test_recourse.py — Unit tests for Counterfactual Recourse engine.
"""
import pytest
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROJECT_DIR = ROOT / "EHCVM_Project" / "EHCVM_Project"
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from src.recourse import compute_recourse, IMMUTABLE_FEATURES, INTERVENTION_CATALOG
from src.dashboard_utils import load_simulator_artifact, HOUSEHOLD_ARCHETYPES

def test_immutable_features_safety():
    """Verify that no action in the intervention catalog touches immutable features."""
    for feat in INTERVENTION_CATALOG:
        assert feat not in IMMUTABLE_FEATURES, f"Intervention catalog contains immutable feature: {feat}"

def test_already_non_poor_household():
    """Verify recourse engine handles already non-poor household without generating actions."""
    artifact = load_simulator_artifact()
    if not artifact:
        pytest.skip("Model artifact not available")
    
    model = artifact["model"]
    feature_cols = artifact["feature_cols"]

    affluent = HOUSEHOLD_ARCHETYPES["🚗 Affluent Urban Household (Protected)"]
    res = compute_recourse(affluent, model, feature_cols, policy_threshold=0.35)

    assert res["status"] == "ALREADY_NON_POOR"
    assert res["recourse_needed"] is False
    assert res["baseline_probability"] < 0.35

def test_recourse_reduces_poverty_probability():
    """Verify that recourse search produces lower poverty probability on poor household."""
    artifact = load_simulator_artifact()
    if not artifact:
        pytest.skip("Model artifact not available")

    model = artifact["model"]
    feature_cols = artifact["feature_cols"]

    poor = HOUSEHOLD_ARCHETYPES["🏚️ Impoverished Rural Household (Large, No Assets)"]
    res = compute_recourse(poor, model, feature_cols, policy_threshold=0.35)

    assert res["recourse_needed"] is True
    assert res["achieved_probability"] < res["baseline_probability"]
    assert res["optimal_plan"] is not None
    assert len(res["optimal_plan"]["actions"]) > 0
