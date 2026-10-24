"""
engineer.py — Merge tables, aggregate individuals, impute, create target.

Produces one clean DataFrame per country: household-level features + binary target.
"""
import pandas as pd
import numpy as np

from . import config


def _aggregate_individu(indiv_df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate individual-level data to household level.

    Strategy (ponytail: simplest that works):
      - Numeric columns → mean per household
      - Binary columns   → any (1 if any member has it)
      - Add member count
    """
    # Keep only columns we want to aggregate + join key
    num_cols = [c for c in config.INDIV_NUMERIC_AGG if c in indiv_df.columns]
    bin_cols = [c for c in config.INDIV_BINARY_AGG if c in indiv_df.columns]
    keep = ["hhid"] + num_cols + bin_cols

    df = indiv_df[keep].copy()

    # Numeric aggregations
    agg_dict = {c: "mean" for c in num_cols}
    # Binary aggregations (any member = 1)
    for c in bin_cols:
        agg_dict[c] = "max"

    grouped = df.groupby("hhid").agg(agg_dict)

    # Add member count
    grouped["indiv_count"] = indiv_df.groupby("hhid").size()

    # Prefix all columns to avoid collision with menage/welfare
    grouped.columns = [f"ind_{c}" if c != "indiv_count" else c for c in grouped.columns]

    return grouped.reset_index()


def _merge_tables(
    menage: pd.DataFrame,
    welfare: pd.DataFrame,
    indiv_agg: pd.DataFrame,
) -> pd.DataFrame:
    """Merge menage + welfare + aggregated-individu on hhid."""
    # Menage features
    menage_cols = ["hhid"] + [c for c in config.MENAGE_FEATURE_COLS if c in menage.columns]
    m = menage[menage_cols].copy()

    # Welfare features + target source
    welfare_cols = (
        ["hhid"]
        + [c for c in config.WELFARE_FEATURE_COLS if c in welfare.columns]
        + [c for c in config.EXPENDITURE_COLS if c in welfare.columns]
    )
    w = welfare[welfare_cols].copy()

    # Merge menage + welfare
    merged = m.merge(w, on="hhid", how="inner")

    # Merge aggregated individuals
    merged = merged.merge(indiv_agg, on="hhid", how="left")

    return merged


def _create_target(df: pd.DataFrame) -> pd.DataFrame:
    """Add binary poverty target: poor = 1 if pcexp < zref."""
    df[config.TARGET_COL] = (df["pcexp"] < df["zref"]).astype(int)
    return df


def _impute(df: pd.DataFrame) -> pd.DataFrame:
    """
    Impute missing values.
    
    Strategy (ponytail: median/mode, no fancy imputers):
      - Numeric columns → median
      - Categorical (int codes) → mode (most frequent)
    """
    for col in df.columns:
        if df[col].isna().sum() == 0:
            continue
        if df[col].dtype in ("float64", "float32"):
            df[col] = df[col].fillna(df[col].median())
        elif df[col].dtype in ("int64", "int32"):
            mode_val = df[col].mode()
            if len(mode_val) > 0:
                df[col] = df[col].fillna(mode_val.iloc[0])
        # ponytail: object cols shouldn't appear after merge, but safety net
        elif df[col].dtype == "object":
            df[col] = df[col].fillna("unknown")
    return df


def engineer_country(country_data: dict) -> pd.DataFrame:
    """
    Full feature engineering pipeline for one country.

    Returns a clean DataFrame: one row per household, all features + 'poor' target.
    """
    name = country_data["_country"]
    menage = country_data["menage"]
    welfare = country_data["welfare"]
    individu = country_data["individu"]

    # 1. Aggregate individuals to household level
    indiv_agg = _aggregate_individu(individu)

    # 2. Merge all three tables
    merged = _merge_tables(menage, welfare, indiv_agg)

    # 3. Create binary target
    merged = _create_target(merged)

    # 4. Impute missing values
    merged = _impute(merged)

    # 5. Drop target-source columns (prevent leakage)
    # ponytail: pcexp IS the expenditure we're predicting poverty from.
    # zref is the poverty line (constant per country). Both leak.
    # dali/dnal/dtot/def_* are expenditure components — also leak.
    leak_cols = [c for c in config.EXPENDITURE_COLS if c in merged.columns]
    merged = merged.drop(columns=leak_cols)

    poverty_rate = merged[config.TARGET_COL].mean() * 100
    print(f"  ✓ {name:20s} → {len(merged):>6,} households, "
          f"{len(merged.columns):>3} features, "
          f"poverty rate: {poverty_rate:.1f}%")

    return merged


def engineer_all(all_data: dict) -> dict[str, pd.DataFrame]:
    """Engineer features for all countries. Returns {country: clean_df}."""
    results = {}
    for name, data in all_data.items():
        print(f"Engineering {name}...")
        results[name] = engineer_country(data)
    return results
