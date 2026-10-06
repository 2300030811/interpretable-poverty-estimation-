"""
tests/test_adapter.py — Unit tests for Universal Survey Adapter.
"""
import pytest
import pandas as pd
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROJECT_DIR = ROOT / "EHCVM_Project" / "EHCVM_Project"
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from src.adapter import normalize_column_name, harmonize_external_survey, evaluate_external_survey

def test_normalize_column_name():
    """Verify synonym matching across multiple languages and formats."""
    assert normalize_column_name("roof_material") == "toit"
    assert normalize_column_name("TYPE_TOITURE") == "toit"
    assert normalize_column_name("grid_electricity") == "elec_ac"
    assert normalize_column_name("mobile_phone") == "ind_telpor"
    assert normalize_column_name("bank_account") == "ind_bank"
    assert normalize_column_name("completely_unknown_xyz") is None

def test_harmonize_external_survey_fill():
    """Verify that external dataframe with only 3 features is harmonized to canonical schema."""
    raw_df = pd.DataFrame({
        "household_id": [1, 2],
        "roof_type": [2, 3],
        "electricity": [0, 1],
    })

    harmonized, meta = harmonize_external_survey(
        raw_df,
        fallback_medians={"sol": 1.0, "toit": 2.0, "elec_ac": 0.0},
        canonical_features=["toit", "elec_ac", "sol"]
    )

    assert list(harmonized.columns) == ["toit", "elec_ac", "sol"]
    assert len(harmonized) == 2
    assert "toit" in meta["matched_features"]
    assert "elec_ac" in meta["matched_features"]
    assert "sol" in meta["imputed_features"]
    assert harmonized["sol"].iloc[0] == 1.0

def test_end_to_end_survey_evaluation():
    """Verify end-to-end evaluation pipeline runs without errors."""
    raw_df = pd.DataFrame({
        "family_size": [5, 4],
        "cellphone": [1, 2],
        "bank_account": [0, 1],
        "floor_material": [1, 3],
    })

    result = evaluate_external_survey(raw_df, survey_title="Sample Survey")
    assert result["n_households"] == 2
    assert "policy_headcount_rate" in result
    assert "conformal_triage" in result
    assert result["metadata"]["matched_count"] >= 3
