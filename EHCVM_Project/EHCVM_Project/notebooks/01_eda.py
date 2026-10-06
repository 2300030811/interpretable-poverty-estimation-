"""
01_eda.py — Exploratory Data Analysis for EHCVM 2021 household data.

Generates summary tables and plots saved to outputs/eda/.
Run after the pipeline has produced clean CSVs in data/processed/.

Usage:
    cd EHCVM_Project/EHCVM_Project
    python -m notebooks.01_eda
"""
import sys
from pathlib import Path

# Ensure project root is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")  # non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns

from src import config

# ── Setup ─────────────────────────────────────────────────────────────────────
sns.set_theme(style="whitegrid", palette="muted", font_scale=1.1)
OUT = config.OUTPUT_EDA
OUT.mkdir(parents=True, exist_ok=True)


def load_clean_data() -> dict[str, pd.DataFrame]:
    """Load all clean CSVs from data/processed/."""
    data = {}
    for name, meta in config.COUNTRIES.items():
        path = config.DATA_PROCESSED / f"{meta['code']}_clean.csv"
        if path.exists():
            data[name] = pd.read_csv(path)
        else:
            print(f"  ⚠ Missing: {path}")
    return data


def eda_01_overview(data: dict):
    """Dataset overview table."""
    rows = []
    for name, df in data.items():
        pov_rate = df[config.TARGET_COL].mean() * 100
        rows.append({
            "Country": name,
            "Households": len(df),
            "Features": len(df.columns) - 1,  # minus target
            "Poverty Rate (%)": round(pov_rate, 1),
            "Missing (%)": round(df.isna().mean().mean() * 100, 2),
        })
    overview = pd.DataFrame(rows)
    overview.to_csv(OUT / "overview_table.csv", index=False)
    print("\n── Dataset Overview ─────────────────────────────────")
    print(overview.to_string(index=False))
    return overview


def eda_02_poverty_rates(data: dict):
    """Bar chart: poverty rates across countries."""
    names, rates = [], []
    for name, df in data.items():
        names.append(name)
        rates.append(df[config.TARGET_COL].mean() * 100)

    fig, ax = plt.subplots(figsize=(10, 5))
    colors = sns.color_palette("YlOrRd", len(names))
    # Sort by poverty rate
    order = np.argsort(rates)[::-1]
    bars = ax.barh(
        [names[i] for i in order],
        [rates[i] for i in order],
        color=[colors[i] for i in range(len(order))],
        edgecolor="white",
    )
    ax.set_xlabel("Poverty Rate (%)")
    ax.set_title("Household Poverty Rates by Country (EHCVM 2021)")
    for bar, idx in zip(bars, order):
        ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height() / 2,
                f"{rates[idx]:.1f}%", va="center", fontsize=10)
    plt.tight_layout()
    fig.savefig(OUT / "poverty_rates.png", dpi=150)
    plt.close()
    print("  ✓ poverty_rates.png")


def eda_03_household_size_dist(data: dict):
    """Household size distribution per country."""
    fig, axes = plt.subplots(2, 4, figsize=(16, 8), sharey=True)
    axes = axes.flatten()
    for i, (name, df) in enumerate(data.items()):
        ax = axes[i]
        if "hhsize" in df.columns:
            df["hhsize"].clip(upper=20).hist(bins=20, ax=ax, color=sns.color_palette()[i % 8], edgecolor="white")
        ax.set_title(name, fontsize=10)
        ax.set_xlabel("Household Size")
    fig.suptitle("Household Size Distribution by Country", fontsize=14, y=1.02)
    plt.tight_layout()
    fig.savefig(OUT / "household_size_dist.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("  ✓ household_size_dist.png")


def eda_04_missing_values(data: dict):
    """Missing value heatmap per country (top 20 columns with most missing)."""
    fig, axes = plt.subplots(2, 4, figsize=(20, 10))
    axes = axes.flatten()
    for i, (name, df) in enumerate(data.items()):
        ax = axes[i]
        missing = df.isna().mean().sort_values(ascending=False).head(20)
        if missing.sum() > 0:
            missing.plot.barh(ax=ax, color="coral")
        else:
            ax.text(0.5, 0.5, "No missing\nvalues", ha="center", va="center", transform=ax.transAxes)
        ax.set_title(name, fontsize=10)
        ax.set_xlabel("Missing %")
    fig.suptitle("Top 20 Columns with Missing Values (post-imputation)", fontsize=14, y=1.02)
    plt.tight_layout()
    fig.savefig(OUT / "missing_values.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("  ✓ missing_values.png")


def eda_05_asset_ownership(data: dict):
    """Asset ownership rates across countries."""
    assets = [c for c in config.ASSET_COLS if c != "car"]  # car is rare, keep it
    assets.append("car")

    rows = []
    for name, df in data.items():
        for asset in assets:
            if asset in df.columns:
                # Assets are coded as counts or binary; >0 means ownership
                rate = (df[asset] > 0).mean() * 100
                rows.append({"Country": name, "Asset": asset, "Ownership (%)": rate})

    asset_df = pd.DataFrame(rows)
    pivot = asset_df.pivot(index="Country", columns="Asset", values="Ownership (%)")

    fig, ax = plt.subplots(figsize=(12, 6))
    sns.heatmap(pivot, annot=True, fmt=".0f", cmap="YlGn", ax=ax, linewidths=0.5)
    ax.set_title("Asset Ownership Rates (%) by Country")
    plt.tight_layout()
    fig.savefig(OUT / "asset_ownership.png", dpi=150)
    plt.close()
    print("  ✓ asset_ownership.png")


def eda_06_correlation_with_poverty(data: dict):
    """Top feature correlations with poverty target (pooled data)."""
    pooled = pd.concat(data.values(), ignore_index=True)
    # Only numeric columns
    numeric = pooled.select_dtypes(include=[np.number])
    if config.TARGET_COL not in numeric.columns:
        print("  ⚠ No target column found in pooled data")
        return

    corr = numeric.corr()[config.TARGET_COL].drop(config.TARGET_COL).sort_values()
    top = pd.concat([corr.head(15), corr.tail(15)])

    fig, ax = plt.subplots(figsize=(10, 8))
    colors = ["#e74c3c" if v < 0 else "#2ecc71" for v in top.values]
    top.plot.barh(ax=ax, color=colors)
    ax.set_title("Top Features Correlated with Poverty (Pooled, 8 Countries)")
    ax.set_xlabel("Pearson Correlation")
    ax.axvline(0, color="black", linewidth=0.8)
    plt.tight_layout()
    fig.savefig(OUT / "correlation_with_poverty.png", dpi=150)
    plt.close()
    print("  ✓ correlation_with_poverty.png")


def eda_07_cross_country_feature_summary(data: dict):
    """Summary statistics per country for key features."""
    key_features = ["hhsize", "hage", "hgender", "milieu", "halfa", "heduc"]
    rows = []
    for name, df in data.items():
        for feat in key_features:
            if feat in df.columns:
                rows.append({
                    "Country": name, "Feature": feat,
                    "Mean": round(df[feat].mean(), 2),
                    "Std": round(df[feat].std(), 2),
                    "Min": df[feat].min(),
                    "Max": df[feat].max(),
                })
    summary = pd.DataFrame(rows)
    summary.to_csv(OUT / "feature_summary.csv", index=False)
    print("  ✓ feature_summary.csv")


def eda_08_poverty_by_urban_rural(data: dict):
    """Poverty rate split by urban/rural (milieu: 1=urban, 2=rural)."""
    rows = []
    for name, df in data.items():
        if "milieu" not in df.columns:
            continue
        for mil, label in [(1, "Urban"), (2, "Rural")]:
            sub = df[df["milieu"] == mil]
            if len(sub) > 0:
                rows.append({
                    "Country": name,
                    "Area": label,
                    "Poverty Rate (%)": round(sub[config.TARGET_COL].mean() * 100, 1),
                    "N": len(sub),
                })
    ur_df = pd.DataFrame(rows)
    ur_df.to_csv(OUT / "poverty_urban_rural.csv", index=False)

    fig, ax = plt.subplots(figsize=(10, 5))
    pivot = ur_df.pivot(index="Country", columns="Area", values="Poverty Rate (%)")
    pivot.plot.bar(ax=ax, color=["#3498db", "#e67e22"], edgecolor="white")
    ax.set_title("Poverty Rate: Urban vs. Rural")
    ax.set_ylabel("Poverty Rate (%)")
    ax.legend(title="Area")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    fig.savefig(OUT / "poverty_urban_rural.png", dpi=150)
    plt.close()
    print("  ✓ poverty_urban_rural.png")


def main():
    print("=" * 60)
    print("EDA — EHCVM 2021 Household Well-Being")
    print("=" * 60)

    data = load_clean_data()
    if not data:
        print("ERROR: No clean data found. Run the pipeline first:")
        print("  python -m src.pipeline")
        sys.exit(1)

    print(f"\nLoaded {len(data)} countries. Generating EDA...\n")

    eda_01_overview(data)
    eda_02_poverty_rates(data)
    eda_03_household_size_dist(data)
    eda_04_missing_values(data)
    eda_05_asset_ownership(data)
    eda_06_correlation_with_poverty(data)
    eda_07_cross_country_feature_summary(data)
    eda_08_poverty_by_urban_rural(data)

    print(f"\n{'='*60}")
    print(f"EDA complete! All outputs in: {OUT}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
