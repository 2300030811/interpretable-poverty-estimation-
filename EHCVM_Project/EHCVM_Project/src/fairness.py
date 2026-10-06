"""
fairness.py — Algorithmic Fairness Auditing & SDG 10 Compliance.

Evaluates predictive equity across protected demographic attributes:
1. Gender: Male-headed (hgender=1) vs Female-headed (hgender=2)
2. Geography: Urban (milieu=1) vs Rural (milieu=2)
3. Age: Working-age head (<60) vs Elderly-headed (>=60)

Computes standard statistical parity and equalized odds metrics:
- Disparate Impact Ratio (80% / four-fifths rule threshold)
- Demographic Parity Difference
- Equal Opportunity Difference (|TPR_a - TPR_b|)
- Equalized Odds Difference (max(|TPR_a - TPR_b|, |FPR_a - FPR_b|))
"""
from typing import Dict, List, Any, Optional
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import confusion_matrix

from . import config

def compute_group_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    """Calculate basic classification rates for a single demographic subgroup."""
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    n = len(y_true)
    tpr = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0
    fpr = float(fp / (fp + tn)) if (fp + tn) > 0 else 0.0
    selection_rate = float((tp + fp) / n) if n > 0 else 0.0
    precision = float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0

    return {
        "n": int(n),
        "tp": int(tp), "fp": int(fp), "tn": int(tn), "fn": int(fn),
        "tpr": tpr,
        "fpr": fpr,
        "selection_rate": selection_rate,
        "precision": precision,
    }


def audit_binary_attribute(
    df: pd.DataFrame,
    pred_col: str,
    target_col: str,
    attr_col: str,
    group_a_name: str,
    group_a_mask: pd.Series,
    group_b_name: str,
    group_b_mask: pd.Series,
    min_disparate_impact: float = 0.80,
) -> Dict[str, Any]:
    """
    Audit fairness metrics between two subgroups A and B.
    """
    df_a = df[group_a_mask]
    df_b = df[group_b_mask]

    m_a = compute_group_metrics(df_a[target_col].values, df_a[pred_col].values)
    m_b = compute_group_metrics(df_b[target_col].values, df_b[pred_col].values)

    # Disparate Impact Ratio = min(SR_a, SR_b) / max(SR_a, SR_b)
    sr_a, sr_b = m_a["selection_rate"], m_b["selection_rate"]
    if max(sr_a, sr_b) > 0:
        di_ratio = min(sr_a, sr_b) / max(sr_a, sr_b)
    else:
        di_ratio = 1.0

    # Differences
    dp_diff = abs(sr_a - sr_b)
    eq_opp_diff = abs(m_a["tpr"] - m_b["tpr"])
    fpr_diff = abs(m_a["fpr"] - m_b["fpr"])
    eq_odds_diff = max(eq_opp_diff, fpr_diff)

    passes_di = bool(di_ratio >= min_disparate_impact)

    return {
        "attribute": attr_col,
        "group_a": {"name": group_a_name, **m_a},
        "group_b": {"name": group_b_name, **m_b},
        "disparate_impact_ratio": di_ratio,
        "demographic_parity_diff": dp_diff,
        "equal_opportunity_diff": eq_opp_diff,
        "equalized_odds_diff": eq_odds_diff,
        "passes_80_percent_rule": passes_di,
        "status": "PASS OK" if passes_di else "FAIRNESS_ALERT",
    }


def run_fairness_audit(data: dict = None, threshold: float = 0.35) -> dict:
    """
    Run comprehensive fairness audit on all countries and pooled dataset.
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
    print("ALGORITHMIC FAIRNESS AUDIT (UN SDG 10 Equity & Non-Discrimination)")
    print("=" * 70)

    # Combine all countries for pooled analysis
    pooled_dfs = []
    country_audits = {}

    for name, df in data.items():
        df_eval = df.copy()
        probs = model.predict_proba(df_eval[feature_cols])[:, 1]
        df_eval["pred_poor"] = (probs >= threshold).astype(int)
        df_eval["country_name"] = name
        pooled_dfs.append(df_eval)

        # Gender audit
        g_res = audit_binary_attribute(
            df_eval, "pred_poor", config.TARGET_COL, "Gender",
            "Male-Headed", df_eval["hgender"] == 1,
            "Female-Headed", df_eval["hgender"] == 2
        )
        # Geography audit
        m_res = audit_binary_attribute(
            df_eval, "pred_poor", config.TARGET_COL, "Geography",
            "Urban", df_eval["milieu"] == 1,
            "Rural", df_eval["milieu"] == 2
        )
        # Age audit
        a_res = audit_binary_attribute(
            df_eval, "pred_poor", config.TARGET_COL, "Age",
            "Working-Age (<60)", df_eval["hage"] < 60,
            "Elderly (>=60)", df_eval["hage"] >= 60
        )

        country_audits[name] = {
            "gender": g_res,
            "geography": m_res,
            "age": a_res,
            "overall_passed": g_res["passes_80_percent_rule"] and a_res["passes_80_percent_rule"],
        }
        print(f"  {name:20s}: Gender DI={g_res['disparate_impact_ratio']:.2f} [{g_res['status']}]  "
              f"Age DI={a_res['disparate_impact_ratio']:.2f} [{a_res['status']}]  "
              f"Geo DI={m_res['disparate_impact_ratio']:.2f}")

    pooled_df = pd.concat(pooled_dfs, ignore_index=True)
    pooled_gender = audit_binary_attribute(
        pooled_df, "pred_poor", config.TARGET_COL, "Gender",
        "Male-Headed", pooled_df["hgender"] == 1,
        "Female-Headed", pooled_df["hgender"] == 2
    )
    pooled_geography = audit_binary_attribute(
        pooled_df, "pred_poor", config.TARGET_COL, "Geography",
        "Urban", pooled_df["milieu"] == 1,
        "Rural", pooled_df["milieu"] == 2
    )
    pooled_age = audit_binary_attribute(
        pooled_df, "pred_poor", config.TARGET_COL, "Age",
        "Working-Age (<60)", pooled_df["hage"] < 60,
        "Elderly (>=60)", pooled_df["hage"] >= 60
    )

    print("\n-- Pooled Cross-Country Equity Audit ----------------------------")
    print(f"  Gender Equity (Male vs Female Heads):")
    print(f"    - Disparate Impact Ratio: {pooled_gender['disparate_impact_ratio']:.3f} (threshold >= 0.80)")
    print(f"    - Equal Opportunity Diff: {pooled_gender['equal_opportunity_diff']:.3f}")
    print(f"    - Status:                 {pooled_gender['status']}")
    print(f"  Age Equity (Working-Age vs Elderly Heads):")
    print(f"    - Disparate Impact Ratio: {pooled_age['disparate_impact_ratio']:.3f} (threshold >= 0.80)")
    print(f"    - Equal Opportunity Diff: {pooled_age['equal_opportunity_diff']:.3f}")
    print(f"    - Status:                 {pooled_age['status']}")
    print(f"  Geographic Rural/Urban Dispersion:")
    print(f"    - Urban Selection Rate:   {pooled_geography['group_a']['selection_rate']:.1%}")
    print(f"    - Rural Selection Rate:   {pooled_geography['group_b']['selection_rate']:.1%}")

    report = {
        "threshold": threshold,
        "pooled": {
            "gender": pooled_gender,
            "geography": pooled_geography,
            "age": pooled_age,
        },
        "countries": country_audits,
        "passed": pooled_gender["passes_80_percent_rule"] and pooled_age["passes_80_percent_rule"],
    }

    out_path = config.OUTPUT_RESULTS / "o7_fairness_analysis.json"
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\n  -> Saved: {out_path.name}")

    # Generate summary CSV table
    summary_rows = []
    for c_name, c_res in country_audits.items():
        summary_rows.append({
            "Country": c_name,
            "Gender_DI_Ratio": round(c_res["gender"]["disparate_impact_ratio"], 3),
            "Gender_EqOpp_Diff": round(c_res["gender"]["equal_opportunity_diff"], 3),
            "Gender_Status": c_res["gender"]["status"],
            "Age_DI_Ratio": round(c_res["age"]["disparate_impact_ratio"], 3),
            "Age_EqOpp_Diff": round(c_res["age"]["equal_opportunity_diff"], 3),
            "Age_Status": c_res["age"]["status"],
            "Rural_Selection_Rate": round(c_res["geography"]["group_b"]["selection_rate"], 3),
            "Urban_Selection_Rate": round(c_res["geography"]["group_a"]["selection_rate"], 3),
        })
    summary_df = pd.DataFrame(summary_rows)
    csv_path = config.OUTPUT_RESULTS / "fairness_summary.csv"
    summary_df.to_csv(csv_path, index=False)
    print(f"  -> Summary: {csv_path.name}")

    return report


if __name__ == "__main__":
    run_fairness_audit()
