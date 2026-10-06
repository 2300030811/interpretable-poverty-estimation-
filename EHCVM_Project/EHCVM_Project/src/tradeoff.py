"""
tradeoff.py — Accuracy vs interpretability trade-off analysis (FR-3).

Compares O2 baselines with O3 interpretable models,
generates Pareto chart and per-country failure analysis.
"""
import json
import numpy as np
import pandas as pd
from pathlib import Path

from . import config


# ponytail: interpretability score is a qualitative ordinal ranking,
# not a computed metric. This is standard in the literature.
INTERPRETABILITY_SCORES = {
    "logistic_regression": 5,  # fully transparent, coefficient-based
    "ebm": 4,                  # GAM — additive, feature-level explanations
    "lightgbm": 3,             # post-hoc SHAP, but model is a black box
    "random_forest": 2,        # feature importance available, but opaque
    "xgboost": 1,              # most complex, least interpretable
}

MODEL_DISPLAY = {
    "logistic_regression": "Logistic Regression",
    "ebm": "EBM (GAM)",
    "lightgbm": "LightGBM",
    "random_forest": "Random Forest",
    "xgboost": "XGBoost",
}


def load_loco_results() -> dict:
    """Load all LOCO JSON results from outputs/results/."""
    results = {}
    results_dir = config.OUTPUT_RESULTS
    for f in sorted(results_dir.glob("*_loco.json")):
        data = json.loads(f.read_text())
        key = data["model"]
        results[key] = data
    return results


def build_tradeoff_table() -> pd.DataFrame:
    """
    Build a table comparing all models on accuracy, AUC, F1 vs interpretability.
    """
    results = load_loco_results()
    rows = []
    for model_name, res in results.items():
        macro = res.get("macro", {})
        rows.append({
            "Model": MODEL_DISPLAY.get(model_name, model_name),
            "Interpretability": INTERPRETABILITY_SCORES.get(model_name, 0),
            "Accuracy": macro.get("accuracy", float("nan")),
            "AUC-ROC": macro.get("auc_roc", float("nan")),
            "F1": macro.get("f1", float("nan")),
            "Exclusion Error": macro.get("exclusion_error", float("nan")),
            "Inclusion Error": macro.get("inclusion_error", float("nan")),
        })

    df = pd.DataFrame(rows).sort_values("Interpretability", ascending=False)

    out_path = config.OUTPUT_RESULTS / "tradeoff_table.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)
    print(f"  -> Trade-off table: {out_path.name}")
    return df


def build_country_comparison() -> pd.DataFrame:
    """
    Per-country accuracy for each model — shows which countries
    degrade most with interpretable models.
    """
    results = load_loco_results()
    rows = []
    for model_name, res in results.items():
        for country, metrics in res.get("countries", {}).items():
            rows.append({
                "Model": MODEL_DISPLAY.get(model_name, model_name),
                "Country": country,
                "Accuracy": metrics.get("accuracy", float("nan")),
                "AUC-ROC": metrics.get("auc_roc", float("nan")),
                "F1": metrics.get("f1", float("nan")),
            })

    df = pd.DataFrame(rows)
    out_path = config.OUTPUT_RESULTS / "country_comparison.csv"
    df.to_csv(out_path, index=False)
    print(f"  -> Country comparison: {out_path.name}")
    return df


def compute_accuracy_cost() -> pd.DataFrame:
    """
    Compute the accuracy cost of interpretability relative to best black-box.
    """
    tradeoff = build_tradeoff_table()

    # Best black-box = lowest interpretability score with highest accuracy
    blackbox = tradeoff[tradeoff["Interpretability"] <= 2]
    if blackbox.empty:
        print("  ⚠ No black-box baselines found")
        return tradeoff

    best_bb_acc = blackbox["Accuracy"].max()
    best_bb_auc = blackbox["AUC-ROC"].max()

    tradeoff["Accuracy Cost (pp)"] = (best_bb_acc - tradeoff["Accuracy"]) * 100
    tradeoff["AUC Cost (pp)"] = (best_bb_auc - tradeoff["AUC-ROC"]) * 100

    out_path = config.OUTPUT_RESULTS / "accuracy_cost.csv"
    tradeoff.to_csv(out_path, index=False)

    print("\n-- Accuracy Cost of Interpretability ----------------------")
    print(f"  Best black-box accuracy: {best_bb_acc:.3f}")
    for _, row in tradeoff.iterrows():
        print(f"  {row['Model']:25s}  acc={row['Accuracy']:.3f}  "
              f"cost={row['Accuracy Cost (pp)']:+.1f}pp  "
              f"interpretability={row['Interpretability']}")

    return tradeoff


def run_tradeoff():
    """Run complete trade-off analysis."""
    print("\n" + "=" * 70)
    print("O3 — ACCURACY vs INTERPRETABILITY TRADE-OFF")
    print("=" * 70)

    compute_accuracy_cost()
    build_country_comparison()
    print("\n  Trade-off analysis complete.")


if __name__ == "__main__":
    run_tradeoff()
