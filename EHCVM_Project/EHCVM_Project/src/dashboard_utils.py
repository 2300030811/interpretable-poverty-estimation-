"""
dashboard_utils.py — Data loading, model inference, and visualization utilities
for the DSCI-28 Streamlit Capstone application.
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import joblib
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from . import config

PROJECT_ROOT = config.PROJECT_ROOT
OUTPUT_RESULTS = config.OUTPUT_RESULTS
OUTPUT_ACCEPTANCE = config.OUTPUT_ACCEPTANCE
OUTPUT_EDA = config.OUTPUT_EDA
OUTPUT_MODELS = config.OUTPUT_MODELS

# Human-readable labels for prominent survey features
FEATURE_LABELS = {
    "hhsize": "Household Size",
    "eqadu1": "Adult Equivalent Units (Scale 1)",
    "eqadu2": "Adult Equivalent Units (Scale 2)",
    "indiv_count": "Roster Individuals Count",
    "ind_telpor": "Mobile Phone Owners in Household",
    "ind_internet": "Members with Internet Access",
    "ind_bank": "Members with Bank Accounts",
    "ind_salaire": "Formal Wage Earners",
    "ind_mal30j": "Sick Members in Past 30 Days",
    "ind_activ12m": "Economically Active Members (12m)",
    "ind_activ7j": "Active Workers (Past 7 Days)",
    "ind_educ_hi": "Highest Education Attained",
    "ind_diplome": "Members with Certified Diploma",
    "tv": "Television Ownership",
    "frigo": "Refrigerator Ownership",
    "car": "Motor Vehicle Ownership",
    "decod": "TV Satellite / Decoder",
    "elec_ac": "Electric Grid Connection",
    "elec_ur": "Solar / Off-grid Electricity",
    "superf": "Agricultural Land Area (ha)",
    "grosrum": "Large Livestock / Cattle Head",
    "petitrum": "Small Ruminants (Goats/Sheep)",
    "sol": "Floor Material Quality (1-5)",
    "mur": "Wall Construction Quality (1-5)",
    "toit": "Roof Material Quality (1-5)",
    "toilet": "Sanitation / Latrine Type (1-5)",
    "eauboi_ss": "Dry Season Drinking Water Source",
    "eauboi_sp": "Rainy Season Drinking Water Source",
    "hnation": "Household Head Nationality",
    "hethnie": "Household Head Ethnicity Code",
    "hreligion": "Household Head Religion",
    "hbranch": "Head Sector / Industry of Activity",
    "zae": "Agro-Ecological Zone",
    "sh_co_eco": "Macroeconomic Shock Incurred",
    "sh_id_demo": "Demographic Shock (Death/Illness)",
}

COLUMN_GROUPS = {
    "All Columns (75)": None,
    "Housing & Sanitation (10)": ["logem", "mur", "toit", "sol", "eauboi_ss", "eauboi_sp", "toilet", "eva_toi", "eva_eau", "ordure"],
    "Assets & Electricity (10)": ["elec_ac", "elec_ur", "elec_ua", "tv", "fer", "frigo", "cuisin", "ordin", "decod", "car"],
    "Connectivity & Labor (8)": ["ind_telpor", "ind_internet", "ind_bank", "ind_salaire", "ind_mal30j", "ind_activ7j", "ind_activ12m", "ind_diplome"],
    "Land & Livestock (6)": ["superf", "grosrum", "petitrum", "porc", "lapin", "volail"],
    "Demographics & Shocks (7)": ["hhsize", "eqadu1", "eqadu2", "hgender", "hage", "heduc", "sh_co_eco", "poor"],
}

HOUSEHOLD_ARCHETYPES = {
    "Custom Configuration": None,
    "🏚️ Impoverished Rural Household (Large, No Assets)": {
        "hhsize": 11, "ind_telpor": 0, "ind_internet": 0, "ind_bank": 0, "ind_salaire": 0,
        "ind_mal30j": 2, "ind_educ_hi": 1, "tv": 0, "frigo": 0, "car": 0, "decod": 0,
        "elec_ac": 0, "sol": 1, "superf": 1.0, "grosrum": 0, "petitrum": 1, "sh_co_eco": 1
    },
    "🌾 Vulnerable Agro-Pastoralist (Livestock Dependent)": {
        "hhsize": 7, "ind_telpor": 1, "ind_internet": 0, "ind_bank": 0, "ind_salaire": 0,
        "ind_mal30j": 1, "ind_educ_hi": 1, "tv": 0, "frigo": 0, "car": 0, "decod": 0,
        "elec_ac": 0, "sol": 2, "superf": 3.5, "grosrum": 3, "petitrum": 8, "sh_co_eco": 1
    },
    "🏙️ Emerging Urban Household (Connected, Wage Earner)": {
        "hhsize": 4, "ind_telpor": 3, "ind_internet": 2, "ind_bank": 2, "ind_salaire": 2,
        "ind_mal30j": 0, "ind_educ_hi": 3, "tv": 1, "frigo": 1, "car": 0, "decod": 1,
        "elec_ac": 1, "sol": 4, "superf": 0.0, "grosrum": 0, "petitrum": 0, "sh_co_eco": 0
    },
    "🚗 Affluent Urban Household (Protected)": {
        "hhsize": 3, "ind_telpor": 3, "ind_internet": 3, "ind_bank": 3, "ind_salaire": 2,
        "ind_mal30j": 0, "ind_educ_hi": 4, "tv": 1, "frigo": 1, "car": 1, "decod": 1,
        "elec_ac": 1, "sol": 5, "superf": 0.0, "grosrum": 0, "petitrum": 0, "sh_co_eco": 0
    }
}


@st.cache_data
def load_csv_summaries() -> dict[str, pd.DataFrame]:
    """Load pre-computed CSV summaries."""
    summaries = {}
    csv_files = {
        "country_comparison": OUTPUT_RESULTS / "country_comparison.csv",
        "tradeoff_table": OUTPUT_RESULTS / "tradeoff_table.csv",
        "targeting_summary": OUTPUT_RESULTS / "targeting_summary.csv",
        "shap_importance": OUTPUT_RESULTS / "shap_importance.csv",
        "accuracy_cost": OUTPUT_RESULTS / "accuracy_cost.csv",
        "overview_table": OUTPUT_EDA / "overview_table.csv",
        "feature_summary": OUTPUT_EDA / "feature_summary.csv",
        "poverty_urban_rural": OUTPUT_EDA / "poverty_urban_rural.csv",
    }
    for key, path in csv_files.items():
        if path.exists():
            summaries[key] = pd.read_csv(path)
        else:
            summaries[key] = pd.DataFrame()
    return summaries


@st.cache_data
def load_json_records() -> dict[str, dict]:
    """Load JSON test, telemetry, and evaluation results."""
    records = {}
    json_files = {
        "acceptance": OUTPUT_ACCEPTANCE / "o5_acceptance.json",
        "negative_tests": OUTPUT_ACCEPTANCE / "negative_tests.json",
        "telemetry": OUTPUT_RESULTS / "telemetry.json",
        "o2_rf_loco": OUTPUT_RESULTS / "o2_rf_loco.json",
        "o2_xgb_loco": OUTPUT_RESULTS / "o2_xgb_loco.json",
        "o3_ebm_loco": OUTPUT_RESULTS / "o3_ebm_loco.json",
        "o3_lgbm_loco": OUTPUT_RESULTS / "o3_lgbm_loco.json",
        "o3_logreg_loco": OUTPUT_RESULTS / "o3_logreg_loco.json",
        "targeting_analysis": OUTPUT_RESULTS / "o4_targeting_analysis.json",
    }
    for key, path in json_files.items():
        if path.exists():
            try:
                records[key] = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                records[key] = {}
        else:
            records[key] = {}
    return records


@st.cache_data
def load_sample_microdata(country_name: str, n_rows: int = 200, col_group: str = "All Columns (75)") -> pd.DataFrame:
    """Load sample microdata from processed CSVs with optional column grouping."""
    meta = config.COUNTRIES.get(country_name)
    if not meta:
        return pd.DataFrame()
    path = config.DATA_PROCESSED / f"{meta['code']}_clean.csv"
    if path.exists():
        df = pd.read_csv(path, nrows=n_rows).fillna(0)
        selected_cols = COLUMN_GROUPS.get(col_group)
        if selected_cols:
            present_cols = [c for c in selected_cols if c in df.columns]
            if "hhid" in df.columns and "hhid" not in present_cols:
                present_cols = ["hhid"] + present_cols
            return df[present_cols]
        return df
    return pd.DataFrame()


@st.cache_resource
def load_simulator_artifact() -> dict:
    """Load the pre-trained LightGBM model, TreeSHAP explainer, and feature medians."""
    model_path = OUTPUT_MODELS / "dashboard_model.joblib"
    if model_path.exists():
        return joblib.load(model_path)
    return {}


def predict_household_poverty(
    country: str,
    user_inputs: dict,
    policy_threshold: float = 0.35,
    symmetric_threshold: float = 0.50,
) -> dict:
    """
    Given interactive user input values for key survey features,
    imputes missing features from country-specific medians, predicts poverty probability,
    and calculates local SHAP feature contributions.
    """
    artifact = load_simulator_artifact()
    if not artifact:
        return {
            "error": "Simulator model artifact not found. Please verify dashboard_model.joblib."
        }

    model = artifact["model"]
    explainer = artifact["explainer"]
    feature_cols = artifact["feature_cols"]
    country_medians = artifact.get("country_medians", {})
    fallback_medians = artifact.get("medians", {})

    # Start with country median profile or pooled fallback
    base_profile = country_medians.get(country, fallback_medians).copy()

    # Override user-specified values
    for k, v in user_inputs.items():
        if k in base_profile:
            base_profile[k] = float(v)

    # If hhsize was set, scale adult equivalent scales accordingly
    if "hhsize" in user_inputs:
        size = float(user_inputs["hhsize"])
        base_profile["eqadu1"] = round(1.0 + 0.7 * max(0.0, size - 1), 2)
        base_profile["eqadu2"] = round(size ** 0.5, 2)
        base_profile["indiv_count"] = size

    # Build 1-row DataFrame with identical column order
    df_sample = pd.DataFrame([[base_profile[col] for col in feature_cols]], columns=feature_cols)

    # Predict probability
    probs = model.predict_proba(df_sample)[0]
    prob_poor = float(probs[1])

    # SHAP local attribution
    shap_explanation = explainer(df_sample)
    shap_values = shap_explanation.values[0]

    # Collect top contributors
    contributions = []
    for col, sv, val in zip(feature_cols, shap_values, df_sample.iloc[0]):
        contributions.append({
            "feature": col,
            "label": FEATURE_LABELS.get(col, col),
            "value": val,
            "shap_impact": float(sv),
            "abs_impact": abs(float(sv)),
        })

    # Sort by absolute SHAP impact
    contributions.sort(key=lambda x: x["abs_impact"], reverse=True)

    return {
        "probability_poor": prob_poor,
        "is_poor_symmetric": bool(prob_poor >= symmetric_threshold),
        "is_poor_policy": bool(prob_poor >= policy_threshold),
        "top_contributions": contributions[:12],
        "all_contributions": contributions,
        "base_value": float(explainer.expected_value),
        "base_profile": base_profile,
    }


def get_targeting_point(targeting_analysis: dict, country: str, threshold: float) -> dict:
    """Find the closest threshold evaluation point in precomputed curves."""
    curves = targeting_analysis.get("curves", {})
    country_curve = curves.get(country, [])
    if not country_curve:
        return {}
    return min(country_curve, key=lambda x: abs(x["threshold"] - threshold))


def create_poverty_risk_meter(prob: float, threshold: float = 0.35) -> go.Figure:
    """
    Creates a clean, intuitive horizontal risk meter bar chart
    showing the household risk position against policy (tau*) and standard (0.50) cutoffs.
    Guarantees no overlapping text or cluttered annotations.
    """
    prob_pct = prob * 100
    tau_pct = threshold * 100

    fig = go.Figure()

    # 1. Background Zone: Resilient (0 to tau*)
    fig.add_trace(go.Bar(
        y=["Poverty Risk"],
        x=[tau_pct],
        orientation="h",
        name="Resilient Zone (0% - Cutoff)",
        marker=dict(color="rgba(16, 185, 129, 0.45)", line=dict(color="#10b981", width=1.5)),
        hoverinfo="text",
        hovertext=f"Resilient Zone (0% to {tau_pct:.0f}%): Self-Sufficient / No Aid Needed",
    ))

    # 2. Background Zone: Vulnerable Buffer (tau* to 50%)
    buffer_width = max(0.0, 50.0 - tau_pct)
    if buffer_width > 0:
        fig.add_trace(go.Bar(
            y=["Poverty Risk"],
            x=[buffer_width],
            orientation="h",
            name="Vulnerable Buffer (Policy Protected)",
            marker=dict(color="rgba(245, 158, 11, 0.50)", line=dict(color="#f59e0b", width=1.5)),
            hoverinfo="text",
            hovertext=f"Vulnerable Buffer ({tau_pct:.0f}% to 50%): Protected by DSCI-28 Policy",
        ))

    # 3. Background Zone: Severe Poverty (50% to 100%)
    fig.add_trace(go.Bar(
        y=["Poverty Risk"],
        x=[50.0 if buffer_width > 0 else 100.0 - tau_pct],
        orientation="h",
        name="Severe Subsistence Need",
        marker=dict(color="rgba(239, 68, 68, 0.50)", line=dict(color="#ef4444", width=1.5)),
        hoverinfo="text",
        hovertext="Severe Need (50% to 100%): High Poverty Across All Standards",
    ))

    # 4. Household Score Pin Marker
    marker_color = "#ef4444" if prob >= threshold else "#10b981"
    fig.add_trace(go.Scatter(
        x=[prob_pct],
        y=["Poverty Risk"],
        mode="markers+text",
        name="Household Score",
        marker=dict(
            symbol="diamond",
            size=22,
            color=marker_color,
            line=dict(color="#ffffff", width=2.5),
        ),
        text=[f"<b>{prob_pct:.1f}%</b>"],
        textposition="top center",
        textfont=dict(size=14, color="#ffffff"),
        hoverinfo="text",
        hovertext=f"Current Household: {prob_pct:.1f}% Poverty Likelihood",
    ))

    # Vertical reference lines without conflicting text annotations
    fig.add_vline(x=tau_pct, line_width=2.5, line_dash="dash", line_color="#f59e0b")
    if abs(threshold - 0.50) > 0.04:
        fig.add_vline(x=50.0, line_width=2, line_dash="dot", line_color="#cbd5e1")

    # Custom Axis values with clear human labels
    axis_vals = [0, round(tau_pct, 1), 50, 100]
    axis_labels = ["0%", f"Our Policy ({tau_pct:.0f}%)", "Old Standard (50%)", "100%"]

    fig.update_layout(
        barmode="stack",
        height=130,
        margin=dict(l=15, r=25, t=35, b=25),
        xaxis=dict(
            title="",
            range=[0, 100],
            tickmode="array",
            tickvals=axis_vals,
            ticktext=axis_labels,
            tickfont=dict(size=12, color="#cbd5e1"),
            gridcolor="rgba(255, 255, 255, 0.08)",
        ),
        yaxis=dict(visible=False),
        showlegend=False,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def create_poverty_gauge(prob: float, threshold: float = 0.35) -> go.Figure:
    """Modern horizontal risk meter replacing the clunky semi-circular speedometer."""
    return create_poverty_risk_meter(prob, threshold)


def generate_shap_narrative(contributions: list[dict], prob: float, threshold: float = 0.35) -> dict:
    """
    Translates raw SHAP log-odds and feature values into intuitive plain-English explanations.
    """
    risk_drivers = [c for c in contributions if c.get("shap_impact", 0) > 0]
    protective_buffers = [c for c in contributions if c.get("shap_impact", 0) < 0]

    risk_drivers.sort(key=lambda x: x["abs_impact"], reverse=True)
    protective_buffers.sort(key=lambda x: x["abs_impact"], reverse=True)

    is_poor = prob >= threshold
    prob_pct = prob * 100

    if prob >= 0.70:
        urgency = "Severe Subsistence Poverty"
        summary_tone = "substantially exceeds"
    elif is_poor:
        urgency = "Vulnerable / Assistance Eligible"
        summary_tone = "exceeds"
    else:
        urgency = "Economically Resilient"
        summary_tone = "remains safely below"

    headline = f"Household evaluated at **{prob_pct:.1f}% Poverty Likelihood** ({urgency})."
    narrative_body = (
        f"Under humanitarian policy targeting, this household {summary_tone} the policy eligibility "
        f"threshold of $\\tau^* = {threshold:.2f}$."
    )

    return {
        "headline": headline,
        "narrative_body": narrative_body,
        "urgency": urgency,
        "is_poor": is_poor,
        "top_risks": risk_drivers[:3],
        "top_buffers": protective_buffers[:3],
    }


def create_loco_comparison_chart(tradeoff_df: pd.DataFrame) -> go.Figure:
    """Create interactive Plotly grouped bar chart for model LOCO performance."""
    if tradeoff_df.empty:
        return go.Figure()

    df = tradeoff_df.copy()
    df = df.sort_values(by="Accuracy", ascending=True)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=df["Model"],
        x=df["Accuracy"] * 100,
        name="Macro Accuracy (%)",
        orientation="h",
        marker=dict(color="#3b82f6"),
        text=[f"{x*100:.1f}%" for x in df["Accuracy"]],
        textposition="auto",
    ))
    fig.add_trace(go.Bar(
        y=df["Model"],
        x=df["AUC-ROC"] * 100,
        name="Macro AUC-ROC (%)",
        orientation="h",
        marker=dict(color="#10b981"),
        text=[f"{x*100:.1f}%" for x in df["AUC-ROC"]],
        textposition="auto",
    ))
    fig.add_trace(go.Bar(
        y=df["Model"],
        x=df["F1"] * 100,
        name="Macro F1-Score (%)",
        orientation="h",
        marker=dict(color="#f59e0b"),
        text=[f"{x*100:.1f}%" for x in df["F1"]],
        textposition="auto",
    ))

    fig.update_layout(
        title="<b>Cross-Country Generalisation (LOCO Evaluation Across 8 Nations)</b>",
        barmode="group",
        xaxis=dict(title="Score (%)", range=[50, 100]),
        yaxis=dict(title=""),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=20, r=20, t=50, b=20),
        height=380,
    )
    return fig


def create_country_breakdown_chart(comparison_df: pd.DataFrame, metric: str = "Accuracy") -> go.Figure:
    """Grouped chart comparing all 5 models across all 8 countries."""
    if comparison_df.empty:
        return go.Figure()

    fig = px.bar(
        comparison_df,
        x="Country",
        y=metric,
        color="Model",
        barmode="group",
        title=f"<b>Cross-Country Transfer: {metric} per Nation</b>",
        color_discrete_sequence=["#2563eb", "#dc2626", "#16a34a", "#9333ea", "#d97706"],
    )
    fig.update_layout(
        yaxis=dict(title=metric, tickformat=".1%"),
        xaxis=dict(title="Evaluated Hold-Out Nation (LOCO Fold)"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
        margin=dict(l=20, r=20, t=60, b=20),
        height=420,
    )
    return fig


def create_targeting_tradeoff_chart(targeting_df: pd.DataFrame, selected_country: str, current_tau: float = None) -> go.Figure:
    """Plot exclusion vs inclusion errors across decision thresholds with active threshold marker."""
    if targeting_df.empty:
        return go.Figure()

    sub = targeting_df[targeting_df["Country"] == selected_country].copy()
    if sub.empty:
        sub = targeting_df.copy()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=sub["Threshold"],
        y=sub["Exclusion Error"] * 100,
        mode="lines+markers",
        name="Exclusion Error (False Negatives %)",
        line=dict(color="#ef4444", width=3),
    ))
    fig.add_trace(go.Scatter(
        x=sub["Threshold"],
        y=sub["Inclusion Error"] * 100,
        mode="lines+markers",
        name="Inclusion Error (Fiscal Leakage %)",
        line=dict(color="#3b82f6", width=3, dash="dash"),
    ))

    if current_tau is not None:
        fig.add_vline(
            x=current_tau,
            line_dash="dot",
            line_color="#10b981",
            annotation_text=f"Active τ = {current_tau:.2f}",
            annotation_position="top left",
        )

    fig.update_layout(
        title=f"<b>Policy Targeting Trade-Off Curve ({selected_country})</b>",
        xaxis=dict(title="Decision Threshold (τ)", range=[0, 1]),
        yaxis=dict(title="Error Rate (%)", range=[0, 100]),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
        margin=dict(l=20, r=20, t=60, b=20),
        height=380,
    )
    return fig


def create_local_shap_waterfall_chart(contributions: list[dict], prob: float) -> go.Figure:
    """Horizontal bar chart illustrating local feature forces."""
    if not contributions:
        return go.Figure()

    sorted_items = sorted(contributions, key=lambda x: x["shap_impact"])
    labels = [x["label"] for x in sorted_items]
    impacts = [x["shap_impact"] for x in sorted_items]
    colors = ["#ef4444" if val > 0 else "#10b981" for val in impacts]

    fig = go.Figure(go.Bar(
        x=impacts,
        y=labels,
        orientation="h",
        marker=dict(color=colors),
        text=[f"{val:+.3f}" for val in impacts],
        textposition="outside",
    ))

    fig.update_layout(
        title=f"<b>Local SHAP Feature Attribution (Poverty Risk: {prob:.1%})</b><br>"
              f"<span style='font-size:12px; color:gray'>Red = Increases Poverty Likelihood | Green = Decreases Poverty Likelihood</span>",
        xaxis=dict(title="SHAP Value (Log-Odds Impact)"),
        yaxis=dict(title=""),
        margin=dict(l=20, r=40, t=60, b=20),
        height=430,
    )
    return fig
