"""
pipeline.py — End-to-end O1 orchestrator.

Usage:
    python -m src.pipeline
"""
import sys
from pathlib import Path

from . import config
from .ingest import load_all_countries, save_lineage_report
from .schemas import validate_all
from .engineer import engineer_all


def run():
    print("=" * 70)
    print("OBJECTIVE 1 — Data Foundation Pipeline")
    print("Interpretable Cross-Country Household Well-Being Estimation")
    print("=" * 70)

    # ── Step 1: Ingest ────────────────────────────────────────────────────
    print("\n[1/4] INGESTING raw EHCVM 2021 data...")
    all_data = load_all_countries()

    # ── Step 2: Validate ──────────────────────────────────────────────────
    print("\n[2/4] VALIDATING schemas (Pandera)...")
    validation = validate_all(all_data)

    total_pass = sum(1 for r in validation.values() for v in r.values() if v)
    total_checks = sum(len(r) for r in validation.values())
    print(f"\n  Schema validation: {total_pass}/{total_checks} tables passed")

    if total_pass < total_checks:
        print("  ⚠ Some validations failed — proceeding anyway (coercion may fix).")

    # ── Step 3: Engineer ──────────────────────────────────────────────────
    print("\n[3/4] ENGINEERING features (merge + aggregate + impute + target)...")
    clean_data = engineer_all(all_data)

    # ── Step 4: Export ────────────────────────────────────────────────────
    print("\n[4/4] EXPORTING clean datasets...")
    out_dir = config.DATA_PROCESSED
    out_dir.mkdir(parents=True, exist_ok=True)

    for name, df in clean_data.items():
        code = config.COUNTRIES[name]["code"]
        out_path = out_dir / f"{code}_clean.csv"
        df.to_csv(out_path, index=False)
        print(f"  → {out_path.name:20s} ({len(df):>6,} rows × {len(df.columns):>3} cols)")

    # Lineage report
    save_lineage_report(all_data)

    # ── Summary ───────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("PIPELINE COMPLETE")
    print("=" * 70)
    print(f"  Countries processed : {len(clean_data)}")
    print(f"  Output directory    : {out_dir}")
    print(f"  Files generated     : {len(clean_data)} clean CSVs + lineage_report.json")
    print()
    for name, df in clean_data.items():
        pov = df[config.TARGET_COL].mean() * 100
        print(f"  {name:20s}: {len(df):>6,} households, poverty rate = {pov:.1f}%")
    print()

    return clean_data


if __name__ == "__main__":
    run()
