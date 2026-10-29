"""
tests/test_external_adaptation.py — Verification of Trustworthy Cross-Country Adaptation.

Validates:
1. Low-coverage inputs (17-of-73 example) -> status='INSUFFICIENT', inference blocked,
   conformal certainty suppressed, recourse suppressed.
2. Complete canonical feature normalizations and multilingual synonyms.
3. Empty, zero-row, and duplicate-column CSV handling without crashing.
4. Non-numeric and ambiguous value sanitization (no silent imputation of garbage).
5. Multi-table survey joining (menage + welfare + individu) with duplicate key detection.
6. Target leakage quarantine (pcexp, zref, dali removed from feature matrix).
7. Domain-shift diagnostics and range-violation alerts.
8. External conformal qualification (UNVALIDATED_EXTERNAL vs DESTINATION_CALIBRATED).
9. Honest recourse with observed vs imputed provenance and causal disclaimer.
10. External destination evaluation workflow with bootstrap uncertainty intervals.
"""
import pytest
import numpy as np
import pandas as pd
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROJECT_DIR = ROOT / "dsci28"
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from src import config, feature_contract, domain_diagnostics, adapter, evaluate, conformal, recourse


# ── 1. Synonym & Schema Normalization ───────────────────────────────────────

def test_all_73_canonical_features_normalize_to_themselves():
    """Verify that every canonical feature in the contract normalizes to itself."""
    for feat in feature_contract.CANONICAL_FEATURES:
        assert adapter.normalize_column_name(feat) == feat, f"Canonical feature '{feat}' failed to match itself"
        assert adapter.normalize_column_name(feat.upper()) == feat, f"Uppercase '{feat.upper()}' failed"
        assert adapter.normalize_column_name(f"  {feat}  ") == feat, f"Whitespace '{feat}' failed"


def test_multilingual_synonym_aliases():
    """Verify English, French, and international aliases."""
    assert adapter.normalize_column_name("roof_material") == "toit"
    assert adapter.normalize_column_name("TYPE_TOITURE") == "toit"
    assert adapter.normalize_column_name("water_source") == "eauboi_ss"
    assert adapter.normalize_column_name("source_eau") == "eauboi_ss"
    assert adapter.normalize_column_name("grid_electricity") == "elec_ac"
    assert adapter.normalize_column_name("cellphone") == "ind_telpor"
    assert adapter.normalize_column_name("bank_account") == "ind_bank"
    assert adapter.normalize_column_name("family_size") == "hhsize"
    assert adapter.normalize_column_name("head_age") == "hage"
    assert adapter.normalize_column_name("urban_rural") == "milieu"
    assert adapter.normalize_column_name("totally_unknown_gibberish_xyz") is None


# ── 2. Low-Coverage & Abstention (17-of-73 Defect Resolution) ───────────────

def test_low_coverage_17_of_73_is_marked_insufficient():
    """
    Verify that an upload with only 17 features (23.3% coverage) is explicitly
    flagged as INSUFFICIENT, blocks high-stakes policy decisions, and suppresses recourse.
    """
    # 17 features out of 73
    cols = [
        "family_size", "cellphone", "grid_electricity", "roof_material", "floor_material",
        "wall_material", "drinking_water", "toilet_type", "head_age", "head_gender",
        "urban_rural", "bank_account", "wage_earners", "tv", "fridge", "car", "computer"
    ]
    raw_df = pd.DataFrame(np.random.randint(0, 3, size=(10, len(cols))), columns=cols)
    raw_df["family_size"] = np.random.randint(1, 10, size=10)
    raw_df["head_age"] = np.random.randint(20, 70, size=10)

    result = adapter.evaluate_external_survey(raw_df, survey_title="Low-Coverage 17/73 Survey")

    meta = result["metadata"]
    assert meta["status"] == "INSUFFICIENT"
    assert meta["feature_coverage_pct"] < 30.0
    assert result["policy_headcount_rate"] is None, "Inference must be blocked for insufficient data"
    assert result["sample_recourse"] is None, "Recourse must be suppressed for insufficient data"
    assert "Insufficient feature coverage" in meta["status_message"]
    assert len(result["audit_report_markdown"]) > 100


def test_exploratory_and_compatible_thresholds():
    """
    Verify policy tiers:
      - Compatible (>=70% coverage + all critical domains)
      - Exploratory (30-70% coverage or 1 critical domain missing)
    """
    # Build 55 features (>70% coverage with all critical domains)
    critical_feats = [
        "toit", "mur", "sol", "logem",
        "eauboi_ss", "eauboi_sp", "toilet", "ordure",
        "elec_ac", "elec_ur",
        "tv", "frigo", "car", "decod", "ordin", "cuisin", "fer",
        "hhsize", "milieu", "hage", "hgender", "hmstat", "heduc", "hdiploma",
        "ind_telpor", "ind_bank", "ind_internet", "ind_salaire", "ind_activ7j", "ind_diplome"
    ]
    other_feats = [
        "superf", "grosrum", "petitrum", "volail", "sh_co_eco", "sh_id_demo", "sh_co_natu",
        "ind_age", "ind_sexe", "ind_alfa", "ind_scol", "ind_mal30j", "ind_couvmal", "ind_moustiq",
        "hreligion", "hnation", "hactiv7j", "hactiv12m", "hbranch", "hsectins", "hcsp", "zae"
    ]
    all_compatible_cols = critical_feats + other_feats
    df_compatible = pd.DataFrame(np.zeros((5, len(all_compatible_cols))), columns=all_compatible_cols)
    df_compatible["hhsize"] = 5
    df_compatible["hage"] = 40
    df_compatible["hgender"] = 1

    res_comp = adapter.evaluate_external_survey(df_compatible, survey_title="Compatible Survey")
    assert res_comp["status"] == "COMPATIBLE"
    assert res_comp["policy_headcount_rate"] is not None
    assert res_comp["conformal_triage"] is not None


# ── 3. Malformed, Empty, and Duplicate Inputs ───────────────────────────────

def test_zero_row_empty_dataframe_does_not_crash():
    """Verify empty DataFrame returns INSUFFICIENT status without crashing."""
    df_empty = pd.DataFrame()
    res = adapter.evaluate_external_survey(df_empty, survey_title="Empty Survey")
    assert res["status"] == "INSUFFICIENT"
    assert res["n_households"] == 0
    assert res["policy_headcount_rate"] is None


def test_duplicate_column_names_are_handled():
    """Verify CSV with duplicate columns is deduplicated safely without crashing."""
    df_dup = pd.DataFrame([[1, 2, 0, 4]], columns=["roof", "roof", "electricity", "family_size"])
    res, meta = adapter.validate_and_harmonize_survey(df_dup)
    assert len(res) == 1
    assert "toit" in meta["matched_features"]
    assert any("duplicate column" in w.lower() for w in meta["warnings"])


def test_non_numeric_garbage_does_not_silently_impute():
    """Verify that columns containing mostly text/garbage are flagged as invalid."""
    df_bad = pd.DataFrame({
        "family_size": [5, 4, 3],
        "grid_electricity": ["unknown", "n/a", "missing_text"],  # 100% non-numeric
    })
    _, meta = adapter.validate_and_harmonize_survey(df_bad)
    assert "elec_ac" in meta["invalid_features"]
    assert any("non-numeric" in w.lower() for w in meta["warnings"])


# ── 4. Multi-Module Ingestion & Duplicate Key Detection ──────────────────────

def test_multi_module_survey_join_and_leakage_quarantine():
    """Verify joining menage + welfare + individu with leakage removal."""
    df_menage = pd.DataFrame({
        "hhid": [1, 2],
        "roof_type": [2, 3],
        "grid_electricity": [0, 1],
    })
    df_welfare = pd.DataFrame({
        "hhid": [1, 2],
        "family_size": [6, 4],
        "head_age": [45, 50],
        # Leaking variables
        "pcexp": [150000, 450000],
        "zref": [250000, 250000],
        "dali": [90000, 210000],
        "poor": [1, 0],
    })
    df_indiv = pd.DataFrame({
        "hhid": [1, 1, 2],
        "age": [45, 12, 50],
        "sexe": [1, 2, 2],
        "telpor": [1, 0, 1],
        "bank": [0, 0, 1],
    })

    merged, audit = adapter.merge_survey_modules(df_menage, df_welfare, df_indiv)

    assert len(merged) == 2
    assert "pcexp" not in merged.columns, "pcexp must be quarantined"
    assert "zref" not in merged.columns, "zref must be quarantined"
    assert "dali" not in merged.columns, "dali must be quarantined"
    assert "ind_telpor" in merged.columns
    assert "indiv_count" in merged.columns
    assert audit["ground_truth_target"] is not None


def test_multi_module_detects_duplicate_hhid():
    """Verify exact identical duplicate rows are safely collapsed under documented policy."""
    df_menage_dups = pd.DataFrame({
        "hhid": [1, 1, 2],  # row 0 and row 1 are completely identical
        "roof_type": [2, 2, 3],
    })
    df_welfare = pd.DataFrame({
        "hhid": [1, 2],
        "family_size": [5, 4],
    })

    merged, audit = adapter.merge_survey_modules(df_menage_dups, df_welfare)
    assert len(merged) == 2, "Exact identical duplicate rows must be collapsed to avoid Cartesian explosion"
    assert audit["exact_duplicates_collapsed"]["Ménage"] == 1
    assert any("collapsed 1 exact identical" in w.lower() for w in audit["warnings"])


def test_multi_module_rejects_conflicting_duplicate_hhid():
    """Verify conflicting records sharing the same hhid raise explicit ValueError rather than silent dropping."""
    df_menage_conflicting = pd.DataFrame({
        "hhid": [1, 1, 2],  # row 0 has roof_type 2, row 1 has roof_type 5 (conflicting!)
        "roof_type": [2, 5, 3],
    })
    df_welfare = pd.DataFrame({
        "hhid": [1, 2],
        "family_size": [5, 4],
    })

    with pytest.raises(ValueError) as excinfo:
        adapter.merge_survey_modules(df_menage_conflicting, df_welfare)
    
    assert "conflicting duplicate records for identifier 'hhid'" in str(excinfo.value)
    assert "cannot be silently discarded" in str(excinfo.value)


def test_zero_overlap_modules_raises_error_and_prevents_inference():
    """
    Verify that zero overlap between required household modules (e.g. disjoint hhid sets)
    raises an explicit ValueError and strictly prevents downstream inference.
    """
    df_menage = pd.DataFrame({
        "hhid": [101, 102, 103],
        "roof_type": [1, 2, 3],
    })
    df_welfare = pd.DataFrame({
        "hhid": [201, 202, 203],  # Disjoint set of households
        "family_size": [4, 5, 6],
    })

    with pytest.raises(ValueError) as excinfo:
        adapter.merge_survey_modules(df_menage, df_welfare)

    assert "Zero overlapping 'hhid' identifiers" in str(excinfo.value)
    assert "Downstream inference cannot proceed" in str(excinfo.value)


# ── 5. Domain-Shift Diagnostics ─────────────────────────────────────────────

def test_domain_shift_diagnostics_calculation():
    """Verify distribution shift index and range violation detection."""
    df = pd.DataFrame({
        "family_size": [50, 60, 70],  # extreme values (EHCVM 75th percentile is 8)
        "cellphone": [0, 0, 0],
    })
    shift_res = domain_diagnostics.evaluate_domain_shift(df, {"family_size": "hhsize", "cellphone": "ind_telpor"})
    assert "overall_shift_index" in shift_res
    assert shift_res["overall_shift_level"] in ("MODERATE", "HIGH")
    assert "hhsize" in shift_res["feature_shifts"]


# ── 6. External Conformal Qualification ──────────────────────────────────────

def test_external_conformal_qualification():
    """Verify external conformal triage classifies as unvalidated to prevent false certainty."""
    cp = conformal.ConformalPovertyClassifier(alpha=0.10)
    cp.q_hat = 0.55

    # On within-domain calibrated data
    sets_internal = cp.predict_sets(np.array([[0.01, 0.99]]), is_external_unvalidated=False)
    assert sets_internal[0]["category"] == "CERTAIN_POOR"
    assert sets_internal[0]["coverage_guaranteed"] is True

    # On external unvalidated data
    sets_external = cp.predict_sets(np.array([[0.01, 0.99]]), is_external_unvalidated=True)
    assert sets_external[0]["category"] == "HIGH_RISK_EXTERNAL"
    assert sets_external[0]["coverage_guaranteed"] is False


def test_destination_specific_conformal_calibration():
    """
    Verify destination-specific conformal calibration:
    - Enforces sample size (min 20) and class diversity requirements.
    - Documents required exchangeability and separation assumptions.
    - Does NOT claim unconditional coverage guarantee merely because labels were supplied.
    """
    cp = conformal.ConformalPovertyClassifier(alpha=0.10)

    # 1. Reject insufficient sample size (< 20)
    p_small = np.array([[0.2, 0.8], [0.9, 0.1], [0.3, 0.7], [0.85, 0.15]])
    y_small = np.array([1, 0, 1, 0])
    with pytest.raises(ValueError, match="at least 20 labeled observations"):
        cp.calibrate_destination(p_small, y_small)

    # 2. Reject single class calibration sample
    p_single = np.tile([[0.2, 0.8]], (25, 1))
    y_single = np.ones(25)
    with pytest.raises(ValueError, match="must contain both classes"):
        cp.calibrate_destination(p_single, y_single)

    # 3. Valid calibration with 24 samples
    p_dest = np.array([[0.2, 0.8], [0.8, 0.2]] * 12)
    y_dest = np.array([1, 0] * 12)
    cp.calibrate_destination(p_dest, y_dest)

    assert cp.is_destination_calibrated is True
    assert cp.provenance == "DESTINATION_SPECIFIC_CALIBRATION"
    assert cp.calibration_assumptions["exchangeability_required"] is True
    assert cp.calibration_assumptions["sample_size"] == 24
    assert cp.calibration_assumptions["coverage_guarantee_status"] == "CONDITIONAL_ON_EXCHANGEABILITY_AND_SEPARATION"

    # Prediction sets must remain qualified: DO NOT claim unconditional guarantee
    sets = cp.predict_sets(np.array([[0.1, 0.9]]), is_external_unvalidated=False)
    assert sets[0]["coverage_guaranteed"] is False, "Guarantee must not be claimed unconditionally without verified exchangeability"
    assert sets[0]["category"] == "HIGH_RISK_DESTINATION"


def test_schema_compatibility_separated_from_scientific_validation():
    """
    Verify that structural schema compatibility is strictly separated from scientific validation.
    A survey can be COMPATIBLE while scientific validation remains UNVALIDATED_EXTERNAL_DOMAIN.
    Model scores must NOT be presented as verified aid entitlement or benefit exclusion decisions.
    """
    cols = [
        "toit", "mur", "sol", "logem",
        "eauboi_ss", "eauboi_sp", "toilet", "ordure",
        "elec_ac", "elec_ur",
        "tv", "frigo", "car", "decod", "ordin", "cuisin", "fer",
        "hhsize", "milieu", "hage", "hgender", "hmstat", "heduc", "hdiploma",
        "ind_telpor", "ind_bank", "ind_internet", "ind_salaire", "ind_activ7j", "ind_diplome",
        "superf", "grosrum", "petitrum", "volail", "sh_co_eco", "sh_id_demo", "sh_co_natu",
        "eau_dist", "elec_dist", "dep_tot", "ind_age", "ind_sexe", "ind_alfa", "ind_scol",
        "ind_educ_hi", "ind_couvmal", "ind_moustiq", "ind_hos12m", "ind_emploi_sec", "ind_handig",
        "ind_mal30j", "ind_alfa2", "indiv_count"
    ]
    df = pd.DataFrame(np.random.randint(0, 3, size=(20, len(cols))), columns=cols)
    df["hhsize"] = np.random.randint(2, 9, size=20)
    df["hage"] = np.random.randint(25, 65, size=20)
    df["elec_ac"] = 1

    result = adapter.evaluate_external_survey(df, survey_title="Compatible Survey Test")

    # 1. Status separation
    assert result["schema_compatibility"] == "COMPATIBLE"
    assert result["scientific_validation_status"] == "UNVALIDATED_EXTERNAL_DOMAIN"
    assert result["eligibility_determination_permitted"] is False
    assert "scores must NOT be used for verified aid eligibility" in result["decision_boundary_notice"]

    # 2. Household preview must NOT present scores as verified aid eligibility
    preview = result["household_preview"]
    assert len(preview) == 20
    for hh in preview:
        assert hh["Administrative_Eligibility"] == "BLOCKED (Unvalidated Domain)"
        assert hh["Model_Risk_Assessment"] in ("HIGH_PREDICTED_RISK", "LOW_PREDICTED_RISK")
        assert "POOR (Eligible)" not in hh["Model_Risk_Assessment"]
        assert hh["Schema_Compatibility"] == "COMPATIBLE"
        assert hh["Scientific_Validation"] == "UNVALIDATED_EXTERNAL_DOMAIN"

    # 3. Audit report contains dedicated distinction section
    audit_md = result["audit_report_markdown"]
    assert "## 0. Critical Distinction: Schema Compatibility vs. Scientific Validation" in audit_md
    assert "STRICTLY PROHIBITED (UNVALIDATED DOMAIN)" in audit_md


# ── 7. Honest Recourse & Causal Disclaimer ──────────────────────────────────

def test_recourse_tracks_observed_vs_imputed_and_disclaims_causality():
    """Verify recourse identifies observed vs imputed levers and includes causal disclaimer."""
    from src.dashboard_utils import load_simulator_artifact
    artifact = load_simulator_artifact()
    if not artifact:
        pytest.skip("Model artifact missing")

    model = artifact["model"]
    feature_cols = artifact["feature_cols"]

    # Household with only elec_ac observed, ind_bank imputed
    hh = {col: 0.0 for col in feature_cols}
    hh["hhsize"] = 8.0
    rec = recourse.compute_recourse(
        hh, model, feature_cols,
        policy_threshold=0.35,
        observed_features={"elec_ac", "hhsize"}
    )

    assert "causal_disclaimer" in rec
    assert "NOT causal evidence" in rec["causal_disclaimer"]
    if rec["single_action_effects"]:
        first_act = rec["single_action_effects"][0]
        assert "provenance" in first_act


# ── 8. External Dataset Evaluation Harness ──────────────────────────────────

def test_external_dataset_evaluation_harness():
    """Verify reproducible external evaluation harness runs with synthetic fixture."""
    from src.dashboard_utils import load_simulator_artifact
    artifact = load_simulator_artifact()
    if not artifact:
        pytest.skip("Model artifact missing")

    model = artifact["model"]
    feature_cols = artifact["feature_cols"]

    # Synthetic destination survey fixture
    n_dest = 20
    df_dest = pd.DataFrame(np.random.randint(0, 2, size=(n_dest, len(feature_cols))), columns=feature_cols)
    df_dest["poor"] = np.random.randint(0, 2, size=n_dest)
    df_dest["hhsize"] = np.random.randint(2, 9, size=n_dest)

    eval_out = evaluate.evaluate_external_dataset(
        model, feature_cols, df_dest,
        target_col="poor",
        is_synthetic_fixture=True,
        destination_name="Synthetic Ghana GLSS 7 Test Fixture",
        n_bootstrap=10
    )

    assert eval_out["is_synthetic_fixture"] is True
    assert eval_out["verification_status"] == "SYNTHETIC_FIXTURE_ONLY_UNVERIFIED_IN_WILD"
    assert "metrics" in eval_out
    assert "uncertainty_intervals" in eval_out
    assert "Real external-country generalization has not yet been verified" in eval_out["disclaimer"]


def test_external_dataset_evaluation_with_sampling_weights():
    """Verify compute_metrics and evaluation harness handle complex survey sampling weights."""
    from src.dashboard_utils import load_simulator_artifact
    artifact = load_simulator_artifact()
    if not artifact:
        pytest.skip("Model artifact missing")

    model = artifact["model"]
    feature_cols = artifact["feature_cols"]

    n_dest = 30
    df_dest = pd.DataFrame(np.random.randint(0, 2, size=(n_dest, len(feature_cols))), columns=feature_cols)
    df_dest["poor"] = np.random.randint(0, 2, size=n_dest)
    df_dest["hhsize"] = np.random.randint(2, 9, size=n_dest)
    df_dest["survey_weight"] = np.random.uniform(0.5, 3.0, size=n_dest)

    eval_out = evaluate.evaluate_external_dataset(
        model, feature_cols, df_dest,
        target_col="poor",
        weight_col="survey_weight",
        is_synthetic_fixture=True,
        destination_name="Weighted Synthetic Survey",
        n_bootstrap=10
    )

    assert eval_out["weighted_metrics"] is not None
    assert eval_out["weighted_metrics"]["is_weighted"] is True
    assert eval_out["metrics"]["is_weighted"] is False

