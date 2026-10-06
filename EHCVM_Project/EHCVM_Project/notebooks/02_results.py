"""
02_results.py — Publication-quality figures for DSCI-28.

Run after `python -m src.run_all` has generated all results.

Usage:
    cd EHCVM_Project/EHCVM_Project
    python -m notebooks.02_results
"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

from src import config

sns.set_theme(style="whitegrid", palette="muted", font_scale=1.1)
OUT = config.OUTPUT_RESULTS
OUT.mkdir(parents=True, exist_ok=True)


def fig_01_model_comparison():
    """Bar chart comparing all models on macro accuracy (LOCO)."""
    loco_files = sorted(OUT.glob("*_loco.json"))
    rows = []
    for f in loco_files:
        data = json.loads(f.read_text())
        macro = data.get("macro", {})
        rows.append({
            "Model": data["model"],
            "Accuracy": macro.get("accuracy", 0),
            "AUC-ROC": macro.get("auc_roc", 0),
            "F1": macro.get("f1", 0),
        })

    if not rows:
        print("  ⚠ No LOCO results found")
        return

    df = pd.DataFrame(rows)
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))

    for i, metric in enumerate(["Accuracy", "AUC-ROC", "F1"]):
        ax = axes[i]
        colors = ["#e74c3c" if m in ("random_forest", "xgboost") else "#2ecc71"
                  for m in df["Model"]]
        bars = ax.barh(df["Model"], df[metric], color=colors, edgecolor="white")
        ax.set_title(metric)
        for bar, val in zip(bars, df[metric]):
            ax.text(bar.get_width() + 0.005, bar.get_y() + bar.get_height() / 2,
                    f"{val:.3f}", va="center", fontsize=9)

    fig.suptitle("Model Comparison — LOCO Cross-Country (red=black-box, green=interpretable)",
                 fontsize=12)
    plt.tight_layout()
    fig.savefig(OUT / "model_comparison.png", dpi=150)
    plt.close()
    print("  OK model_comparison.png")


def fig_02_tradeoff_pareto():
    """Pareto chart: accuracy vs interpretability score."""
    tradeoff_path = OUT / "accuracy_cost.csv"
    if not tradeoff_path.exists():
        print("  ⚠ accuracy_cost.csv not found")
        return

    df = pd.read_csv(tradeoff_path)
    fig, ax = plt.subplots(figsize=(8, 6))

    scatter = ax.scatter(df["Interpretability"], df["Accuracy"],
                         s=200, c=df["Interpretability"],
                         cmap="RdYlGn", edgecolor="black", zorder=5)
    for _, row in df.iterrows():
        ax.annotate(row["Model"], (row["Interpretability"], row["Accuracy"]),
                    textcoords="offset points", xytext=(0, 12),
                    ha="center", fontsize=9, fontweight="bold")

    ax.set_xlabel("Interpretability Score (1=opaque -> 5=transparent)")
    ax.set_ylabel("Macro Accuracy (LOCO)")
    ax.set_title("Accuracy vs Interpretability Trade-off")
    ax.set_xlim(0, 6)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    fig.savefig(OUT / "tradeoff_pareto.png", dpi=150)
    plt.close()
    print("  OK tradeoff_pareto.png")


def fig_03_country_heatmap():
    """Heatmap of per-country accuracy for each model."""
    comp_path = OUT / "country_comparison.csv"
    if not comp_path.exists():
        print("  ⚠ country_comparison.csv not found")
        return

    df = pd.read_csv(comp_path)
    pivot = df.pivot(index="Country", columns="Model", values="Accuracy")

    fig, ax = plt.subplots(figsize=(12, 7))
    sns.heatmap(pivot, annot=True, fmt=".3f", cmap="RdYlGn",
                center=pivot.values.mean(), ax=ax, linewidths=0.5)
    ax.set_title("Per-Country Accuracy by Model (LOCO)")
    plt.tight_layout()
    fig.savefig(OUT / "country_accuracy_heatmap.png", dpi=150)
    plt.close()
    print("  OK country_accuracy_heatmap.png")


def fig_04_targeting_curves():
    """Exclusion vs inclusion error curves for each country."""
    targeting_path = OUT / "o4_targeting_analysis.json"
    if not targeting_path.exists():
        print("  ⚠ o4_targeting_analysis.json not found")
        return

    data = json.loads(targeting_path.read_text())
    curves = data.get("curves", {})

    n = len(curves)
    cols = 4
    rows_n = (n + cols - 1) // cols
    fig, axes = plt.subplots(rows_n, cols, figsize=(16, 4 * rows_n))
    axes = axes.flatten() if n > 1 else [axes]

    for i, (country, records) in enumerate(curves.items()):
        ax = axes[i]
        df = pd.DataFrame(records)
        ax.plot(df["threshold"], df["exclusion_error"], "r-o",
                markersize=3, label="Exclusion (FN/poor)")
        ax.plot(df["threshold"], df["inclusion_error"], "b-s",
                markersize=3, label="Inclusion (FP/non-poor)")
        ax.set_title(country, fontsize=10)
        ax.set_xlabel("Threshold")
        ax.set_ylabel("Error Rate")
        ax.legend(fontsize=7)
        ax.grid(True, alpha=0.3)

    for j in range(i + 1, len(axes)):
        axes[j].set_visible(False)

    fig.suptitle("Exclusion vs Inclusion Error Curves (per country)", fontsize=13)
    plt.tight_layout()
    fig.savefig(OUT / "targeting_curves.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("  OK targeting_curves.png")


def fig_05_shap_importance():
    """SHAP feature importance bar chart."""
    shap_path = OUT / "shap_importance.csv"
    if not shap_path.exists():
        print("  ⚠ shap_importance.csv not found")
        return

    df = pd.read_csv(shap_path).head(20)
    fig, ax = plt.subplots(figsize=(10, 8))
    ax.barh(df["feature"][::-1], df["mean_abs_shap"][::-1],
            color=sns.color_palette("viridis", len(df)), edgecolor="white")
    ax.set_xlabel("Mean |SHAP value|")
    ax.set_title("Top 20 Features — LightGBM SHAP Importance")
    plt.tight_layout()
    fig.savefig(OUT / "shap_importance.png", dpi=150)
    plt.close()
    print("  OK shap_importance.png")


def fig_06_targeting_sensitivity():
    """Sensitivity analysis: optimal threshold vs cost ratio."""
    summary_path = OUT / "targeting_summary.csv"
    if not summary_path.exists():
        print("  ⚠ targeting_summary.csv not found")
        return

    df = pd.read_csv(summary_path)
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # Threshold vs cost ratio
    for country in df["Country"].unique():
        sub = df[df["Country"] == country].sort_values("Cost Ratio")
        axes[0].plot(sub["Cost Ratio"], sub["Threshold"], "-o",
                     markersize=4, label=country)
    axes[0].set_xlabel("Cost Ratio (Exclusion / Inclusion)")
    axes[0].set_ylabel("Optimal Threshold")
    axes[0].set_title("Optimal Threshold vs Cost Ratio")
    axes[0].legend(fontsize=7, ncol=2)
    axes[0].grid(True, alpha=0.3)

    # Exclusion error at ratio=3
    policy = df[df["Cost Ratio"] == 3.0].sort_values("Exclusion Error")
    axes[1].barh(policy["Country"], policy["Exclusion Error"],
                 color="#e74c3c", label="Exclusion", edgecolor="white")
    axes[1].barh(policy["Country"], -policy["Inclusion Error"],
                 color="#3498db", label="Inclusion", edgecolor="white")
    axes[1].set_xlabel("Error Rate")
    axes[1].set_title("Targeting Errors at Cost Ratio 3:1")
    axes[1].legend()
    axes[1].axvline(0, color="black", linewidth=0.8)

    plt.tight_layout()
    fig.savefig(OUT / "targeting_sensitivity.png", dpi=150)
    plt.close()
    print("  OK targeting_sensitivity.png")


def main():
    print("=" * 60)
    print("PUBLICATION FIGURES — DSCI-28")
    print("=" * 60)

    fig_01_model_comparison()
    fig_02_tradeoff_pareto()
    fig_03_country_heatmap()
    fig_04_targeting_curves()
    fig_05_shap_importance()
    fig_06_targeting_sensitivity()

    print(f"\n{'='*60}")
    print(f"All figures saved to: {OUT}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
