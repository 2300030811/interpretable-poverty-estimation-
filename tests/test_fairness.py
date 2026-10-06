"""
tests/test_fairness.py — Unit tests for Algorithmic Fairness auditing engine.
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

from src.fairness import compute_group_metrics, audit_binary_attribute

def test_compute_group_metrics_exact():
    """Verify exact calculation of precision, TPR, FPR, and selection rate."""
    y_true = np.array([1, 1, 0, 0])
    y_pred = np.array([1, 0, 0, 1])

    m = compute_group_metrics(y_true, y_pred)
    assert m["tp"] == 1
    assert m["fn"] == 1
    assert m["tn"] == 1
    assert m["fp"] == 1
    assert m["tpr"] == 0.5
    assert m["fpr"] == 0.5
    assert m["selection_rate"] == 0.5
    assert m["precision"] == 0.5

def test_audit_binary_attribute_balanced():
    """Verify disparate impact ratio = 1.0 on perfectly symmetric groups."""
    df = pd.DataFrame({
        "gender": [1, 1, 2, 2],
        "pred": [1, 0, 1, 0],
        "true": [1, 0, 1, 0]
    })

    audit = audit_binary_attribute(
        df, "pred", "true", "Gender",
        "Male", df["gender"] == 1,
        "Female", df["gender"] == 2
    )

    assert audit["disparate_impact_ratio"] == 1.0
    assert audit["demographic_parity_diff"] == 0.0
    assert audit["passes_80_percent_rule"] is True
    assert audit["status"] == "PASS OK"

def test_fairness_violation_detection():
    """Verify that severe bias triggers FAIRNESS_ALERT."""
    df = pd.DataFrame({
        "group": [1]*100 + [2]*100,
        "pred": [1]*90 + [0]*10 + [1]*20 + [0]*80, # Group 1: 90% positive, Group 2: 20% positive
        "true": [1]*50 + [0]*50 + [1]*50 + [0]*50,
    })

    audit = audit_binary_attribute(
        df, "pred", "true", "Group",
        "Group 1", df["group"] == 1,
        "Group 2", df["group"] == 2
    )

    # Disparate impact = 0.20 / 0.90 = ~0.22 < 0.80
    assert audit["disparate_impact_ratio"] < 0.30
    assert audit["passes_80_percent_rule"] is False
    assert audit["status"] == "FAIRNESS_ALERT"
