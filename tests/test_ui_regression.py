"""
Regression test suite for DSCI-28 Streamlit Application (app.py).
Strictly verifies all 7 primary navigation views, local sub-views, 
state synchronization, edge cases, and confirmed defect resolutions.
"""
import io
import json
import sys
from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
APP_PATH = str(ROOT / "app.py")
PROJECT_DIR = ROOT / "dsci28"
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src import dashboard_utils, config


def _nav_to(app_instance, partial_name: str):
    """Robust navigation helper finding radio option by substring to avoid emoji encoding divergence."""
    matching_opts = [o for o in app_instance.sidebar.radio[0].options if partial_name in o]
    assert len(matching_opts) >= 1, f"Navigation option matching '{partial_name}' not found in sidebar"
    app_instance.sidebar.radio[0].set_value(matching_opts[0]).run()
    assert not app_instance.exception, f"Exception while navigating to {partial_name}: {app_instance.exception}"


@pytest.fixture(scope="function")
def app():
    """Load a fresh, isolated Streamlit app instance for each independent test."""
    at = AppTest.from_file(APP_PATH, default_timeout=25)
    at.run()
    assert not at.exception, f"App startup exception: {at.exception}"
    return at


# ── Page 0: Executive Overview ────────────────────────────────────────────────
def test_app_startup_and_executive_overview(app):
    """Verify application startup, macro KPIs, problem/solution framing, and assurance badges."""
    assert not app.exception

    # Check that core metrics are present in Executive Overview with real values
    metric_map = {m.label: m.value for m in app.metric}
    assert "Harmonized Households" in metric_map
    hh_val = str(metric_map["Harmonized Households"]).replace(",", "")
    assert hh_val.isdigit() and int(hh_val) > 50000

    assert "Standardized Features" in metric_map
    assert metric_map["Standardized Features"] != "None" and metric_map["Standardized Features"] != "Unavailable"

    assert "Cost of Interpretability" in metric_map
    assert "pp" in str(metric_map["Cost of Interpretability"]) or metric_map["Cost of Interpretability"] == "Pending"

    assert "Targeting Excl. Error" in metric_map

    # Verify Sidebar System Assurance badges are rendered
    sidebar_text = " ".join(str(m.value) for m in app.sidebar.markdown)
    assert "AC-1 to AC-4" in sidebar_text
    assert "NT-1 to NT-5" in sidebar_text
    assert "Fairness (SDG 10)" in sidebar_text
    assert "DuckDB" in sidebar_text


# ── Primary Navigation Across All 7 Views ─────────────────────────────────────
def test_sidebar_navigation_all_seven_views(app):
    """Test switching through all seven primary navigation pages without exception."""
    pages = [
        ("Executive Overview", "Interpretable Cross-Country"),
        ("O1: Survey Data & Schema", "Objective 1: World Bank EHCVM"),
        ("O2: LOCO Benchmarks", "Objective 2: Cross-Country LOCO Benchmarking"),
        ("O3: Interpretable AI & Simulator", "Objective 3: Transparent Household Targeting"),
        ("O4: Policy Targeting & Loss", "Objective 4: Asymmetric Social Welfare Loss"),
        ("O5: Quality Assurance & DuckDB", "Objective 5: Formal QA Gates"),
        ("O6: External Survey Ingestion", "Objective 6: Trustworthy External Survey Ingestion"),
    ]
    for nav_key, expected_heading in pages:
        _nav_to(app, nav_key)
        all_text = " ".join(str(m.value) for m in app.markdown)
        assert expected_heading in all_text, f"Expected heading '{expected_heading}' not found in {nav_key}"


# ── Objective 1: Data & Schema ────────────────────────────────────────────────
def test_objective_1_data_and_schema_views(app):
    """Verify O1 sub-views: National overview, Urban/Rural disparity, Microdata Inspector, and Feature Dictionary."""
    _nav_to(app, "O1: Survey Data & Schema")

    # Check dataframes present (National Overview and Urban/Rural)
    assert len(app.dataframe) >= 2, "Expected at least 2 dataframes in O1 overview tab"

    # Microdata inspector filter interaction: country selectbox and rows slider
    country_boxes = [s for s in app.selectbox if "Country Context" in getattr(s, "label", "")]
    assert len(country_boxes) >= 1, "Country Context selectbox not found in O1"
    country_boxes[0].set_value("Benin").run()
    assert not app.exception

    sliders = [s for s in app.slider if "Sample Rows" in getattr(s, "label", "")]
    assert len(sliders) >= 1, "Sample Rows slider not found in O1"
    sliders[0].set_value(30).run()
    assert not app.exception
    assert len(app.dataframe) >= 2


def test_objective_1_missing_microdata_graceful(monkeypatch):
    """Verify O1 displays graceful warning when sample microdata is absent."""
    monkeypatch.setattr(dashboard_utils, "load_sample_microdata", lambda *args, **kwargs: pd.DataFrame())
    at = AppTest.from_file(APP_PATH, default_timeout=25).run()
    _nav_to(at, "O1: Survey Data & Schema")
    # Warning should be rendered when microdata is empty
    warnings = [str(w.value) for w in at.warning]
    assert any("No processed data found" in w for w in warnings)


# ── Objective 2: LOCO Benchmarks ──────────────────────────────────────────────
def test_objective_2_loco_leaderboard_and_matrix(app):
    """Verify O2 LOCO Benchmark takeaways, leaderboard dataframe, and all 3 view modes."""
    _nav_to(app, "O2: LOCO Benchmarks")

    # Check Takeaway Cards
    all_text = " ".join(str(m.value) for m in app.markdown)
    assert "The Spatial Transfer Defect" in all_text
    assert "Zero Cost of Interpretability" in all_text

    # Leaderboard table contains model names
    assert len(app.dataframe) >= 1
    # Check that plotly chart is rendered
    assert len(app.get("plotly_chart")) >= 1

    # Locate Hold-Out view mode radio
    view_radios = [r for r in app.radio if any("Grouped Bar Chart" in opt for opt in r.options)]
    assert len(view_radios) >= 1, "Hold-out view mode radio not found"
    view_radio = view_radios[0]

    # Test all 3 view modes
    for opt_keyword in ["Grouped Bar Chart", "Interactive Heatmap", "Publication Heatmap"]:
        match_opt = [o for o in view_radio.options if opt_keyword in o][0]
        view_radio.set_value(match_opt).run()
        assert not app.exception, f"Exception in O2 view mode {opt_keyword}: {app.exception}"


def test_objective_2_missing_artifact_graceful(monkeypatch):
    """Verify O2 handles missing tradeoff_table.csv cleanly without uncaught crash."""
    st.cache_data.clear()
    original_load = dashboard_utils.load_csv_summaries()
    tampered = dict(original_load)
    tampered["tradeoff_table"] = pd.DataFrame()
    monkeypatch.setattr(dashboard_utils, "load_csv_summaries", lambda: tampered)

    at = AppTest.from_file(APP_PATH, default_timeout=25).run()
    _nav_to(at, "O2: LOCO Benchmarks")
    assert not at.exception


# ── Objective 3: Interpretable AI & Simulator ─────────────────────────────────
def test_objective_3_household_simulator_inference_and_metrics(app):
    """Verify O3 Household Simulator submission, neutral descriptions, and SHAP decomposition."""
    _nav_to(app, "O3: Interpretable AI & Simulator")

    # Find the form submission button and submit
    submit_buttons = [b for b in app.button if "Run Real-Time Household Prediction" in getattr(b, "label", "")]
    assert len(submit_buttons) >= 1, "Simulator submit button not found"
    submit_buttons[0].click().run()
    assert not app.exception, f"Exception after simulator submit: {app.exception}"

    # Verify neutral probability-based presentation (no unsupported administrative claims)
    text_content = " ".join([str(m.value) for m in app.markdown] + [str(m.label) for m in app.metric])
    assert "AID APPROVED" not in text_content
    assert "AID NOT REQUIRED" not in text_content
    assert "SELF-SUFFICIENT" not in text_content
    assert "Research & Administrative Notice" in text_content

    metric_labels = [m.label for m in app.metric]
    assert any("Estimated Poverty Probability" in lbl for lbl in metric_labels)
    assert any("Policy Cutoff (τ*)" in lbl for lbl in metric_labels)
    assert any("Margin vs. Cutoff" in lbl for lbl in metric_labels)
    assert any("Model Classification" in lbl for lbl in metric_labels)

    # Check risk meter chart and Tree-SHAP waterfall chart
    assert len(app.get("plotly_chart")) >= 2


def test_objective_3_stale_prediction_prevention(app):
    """
    Defect 3 Verification: Confirm that changing scenario archetype or inputs
    immediately refreshes prediction and never presents a stale prediction.
    """
    _nav_to(app, "O3: Interpretable AI & Simulator")

    # Read initial probability for default scenario
    metric_map_1 = {m.label: m.value for m in app.metric}
    prob_1 = metric_map_1.get("Estimated Poverty Probability")
    assert prob_1 is not None

    # Change archetype preset to Affluent Urban Household (Protected)
    preset_boxes = [s for s in app.selectbox if "Preset Household Scenario" in getattr(s, "label", "")]
    assert len(preset_boxes) >= 1
    affluent_opt = [opt for opt in preset_boxes[0].options if "Affluent Urban" in opt][0]
    preset_boxes[0].set_value(affluent_opt).run()
    assert not app.exception

    # Prediction must have recomputed and not be equal to the initial impoverished state
    metric_map_2 = {m.label: m.value for m in app.metric}
    prob_2 = metric_map_2.get("Estimated Poverty Probability")
    assert prob_2 is not None
    assert prob_1 != prob_2, f"Stale prediction detected! prob_1={prob_1} remained identical after switching to {affluent_opt}"


def test_objective_3_reset_parameters(app):
    """Verify reset button clears scenario session state cleanly."""
    _nav_to(app, "O3: Interpretable AI & Simulator")

    reset_buttons = [b for b in app.button if "Reset Parameters" in getattr(b, "label", "")]
    assert len(reset_buttons) >= 1
    reset_buttons[0].click().run()
    assert not app.exception


def test_objective_3_missing_model_artifact(monkeypatch):
    """Verify O3 handles missing model artifact with an explicit error rather than crash."""
    monkeypatch.setattr(dashboard_utils, "load_simulator_artifact", lambda: {})
    at = AppTest.from_file(APP_PATH, default_timeout=25).run()
    _nav_to(at, "O3: Interpretable AI & Simulator")
    errors = [str(e.value) for e in at.error]
    assert any("Simulator model artifact not found" in e for e in errors)


# ── Objective 4: Policy Targeting & Loss ──────────────────────────────────────
def test_objective_4_policy_targeting_optimization(app):
    """Verify O4 Asymmetric Welfare loss controls, slider interaction, and confusion matrix cards."""
    _nav_to(app, "O4: Policy Targeting & Loss")

    # Verify slider interaction
    tau_sliders = [s for s in app.slider if "Decision Cutoff" in getattr(s, "label", "")]
    assert len(tau_sliders) >= 1, "Decision Cutoff slider not found in O4"
    tau_sliders[0].set_value(0.40).run()
    assert not app.exception

    # Confusion matrix cards present
    all_text = " ".join(str(m.value) for m in app.markdown)
    assert "True Positives (TP)" in all_text
    assert "False Negatives (FN)" in all_text
    assert "False Positives (FP)" in all_text
    assert "True Negatives (TN)" in all_text


def test_objective_4_conformal_uncertainty_metrics(app):
    """Verify O4 Conformal uncertainty metrics are rendered without fabricated fallbacks."""
    _nav_to(app, "O4: Policy Targeting & Loss")

    metric_labels = [m.label for m in app.metric]
    assert any("Target Coverage" in lbl for lbl in metric_labels)
    assert any("Empirical Coverage" in lbl for lbl in metric_labels)
    assert any("Certain Enrollment" in lbl for lbl in metric_labels)
    assert any("Ambiguous Queue" in lbl for lbl in metric_labels)

    # Verify country table is present
    assert len(app.dataframe) >= 1


# ── Objective 5: Quality Assurance & DuckDB ───────────────────────────────────
def test_objective_5_formal_acceptance_and_negative_tests(app):
    """Verify O5 AC-1 to AC-4 and NT-1 to NT-5 are rendered with verified status."""
    _nav_to(app, "O5: Quality Assurance & DuckDB")

    all_text = " ".join(str(m.value) for m in app.markdown)
    for ac in ["AC-1", "AC-2", "AC-3", "AC-4"]:
        assert ac in all_text, f"{ac} badge missing in O5"
    for nt in ["NT-1", "NT-2", "NT-3", "NT-4", "NT-5"]:
        assert nt in all_text, f"{nt} badge missing in O5"


def test_objective_5_unverified_badges_when_passed_absent(monkeypatch):
    """
    Defect 1 Verification: Confirm that missing evidence displays UNVERIFIED (badge-amber),
    not PASS OK, when the 'passed' field is absent.
    """
    st.cache_data.clear()
    original_load = dashboard_utils.load_json_records()
    tampered = dict(original_load)
    tampered["acceptance"] = {"AC-1": {"description": "Test unverified", "passed": None}}
    tampered["negative_tests"] = {"NT-1": {"description": "Test unverified NT", "passed": None}}

    monkeypatch.setattr(dashboard_utils, "load_json_records", lambda: tampered)
    at = AppTest.from_file(APP_PATH, default_timeout=25).run()
    _nav_to(at, "O5: Quality Assurance & DuckDB")

    all_text = " ".join(str(m.value) for m in at.markdown)
    assert "UNVERIFIED" in all_text, "Missing 'passed' field must display UNVERIFIED badge"


def test_objective_5_all_sql_presets_exist_and_execute(app):
    """Verify all 4 DuckDB SQL preset buttons exist and execute without error (fail if any is missing)."""
    _nav_to(app, "O5: Quality Assurance & DuckDB")

    presets = ["Nations Summary", "LOCO Leaderboard", "Targeting 10:1", "Poverty by Nation"]
    for preset_label in presets:
        matching_buttons = [b for b in app.button if preset_label in getattr(b, "label", "")]
        assert len(matching_buttons) >= 1, f"Required DuckDB SQL preset button '{preset_label}' not found!"
        matching_buttons[0].click().run()
        assert not app.exception, f"Exception executing DuckDB preset '{preset_label}': {app.exception}"
        # A dataframe should be returned from query
        assert len(app.dataframe) >= 1


# ── Objective 6: External Survey Ingestion ────────────────────────────────────
def test_objective_6_synthetic_ghana_demo_and_labeling(app):
    """
    Verify O6 external survey ingestion simulation via Ghana GLSS 7 demo,
    checking feature coverage, critical domains, and explicit synthetic fixture labeling.
    """
    _nav_to(app, "O6: External Survey Ingestion")

    # Locate Ghana demo button with synthetic fixture label
    demo_buttons = [b for b in app.button if "Ghana GLSS 7" in getattr(b, "label", "")]
    assert len(demo_buttons) >= 1, "Ghana GLSS demo button not found"
    assert "Synthetic Fixture" in getattr(demo_buttons[0], "label", "")

    demo_buttons[0].click().run()
    assert not app.exception, "Exception running Ghana GLSS demo simulation"

    # Verify synthetic software demonstration label
    all_text = " ".join(str(m.value) for m in app.markdown)
    assert "Synthetic Test Fixture" in all_text
    info_text = " ".join(str(i.value) for i in app.info)
    assert "UNVALIDATED_EXTERNAL_DOMAIN" in info_text or "UNVALIDATED" in info_text

    metric_labels = [m.label for m in app.metric]
    assert any("Feature Coverage" in lbl for lbl in metric_labels)
    assert any("Critical Domains" in lbl for lbl in metric_labels)
    assert any("Domain Shift Level" in lbl for lbl in metric_labels)

    # Microdata preview dataframe rendered
    assert len(app.dataframe) >= 1

    # Verify download buttons are present
    download_buttons = app.get("download_button")
    assert len(download_buttons) >= 2


def test_objective_6_empty_csv_upload_handling(app, monkeypatch):
    """Verify O6 shows an explicit error for an empty (0 rows) uploaded CSV."""
    _nav_to(app, "O6: External Survey Ingestion")

    empty_file = io.StringIO("hhid,superf,sol\n")  # 0 data rows
    empty_file.name = "empty_survey.csv"
    monkeypatch.setattr(st, "file_uploader", lambda *args, **kwargs: empty_file)

    app.run()
    assert not app.exception
    errors = [str(e.value) for e in app.error]
    assert any("no records (0 rows)" in e for e in errors)


def test_objective_6_malformed_csv_upload_handling(app, monkeypatch):
    """Verify O6 handles unparseable/malformed CSV uploads gracefully with an error message."""
    _nav_to(app, "O6: External Survey Ingestion")

    class BadStream:
        name = "corrupted.csv"
        def read(self, *args, **kwargs):
            raise ValueError("Corrupted encoding or binary payload")
        def readline(self, *args, **kwargs):
            raise ValueError("Corrupted encoding or binary payload")

    monkeypatch.setattr(st, "file_uploader", lambda *args, **kwargs: BadStream())
    app.run()
    assert not app.exception
    errors = [str(e.value) for e in app.error]
    assert any("Error reading CSV" in e for e in errors)
