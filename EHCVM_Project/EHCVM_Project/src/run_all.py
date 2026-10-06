"""
run_all.py — One-command end-to-end runner (FR-6).

Usage:
    cd EHCVM_Project/EHCVM_Project
    python -m src.run_all
"""
import sys
import time
import datetime
import json
from pathlib import Path

from . import config


def run():
    start = time.time()
    print("=" * 70)
    print("DSCI-28 — Interpretable Cross-Country Poverty Estimation")
    print("Complete System Run (O2 -> O3 -> O4 -> O5)")
    print(f"Started: {datetime.datetime.now().isoformat()}")
    print("=" * 70)

    telemetry = {"stages": {}, "start": datetime.datetime.now().isoformat()}

    # -- Load data --------------------------------------------------------
    from .models import load_clean_data
    data = load_clean_data()
    if len(data) < 8:
        print(f"WARNING: Only {len(data)} countries loaded (expected 8)")

    # -- O2: Baselines ----------------------------------------------------
    t0 = time.time()
    from .models import run_baselines
    o2_results = run_baselines(data)
    telemetry["stages"]["O2_baselines"] = {
        "duration_s": round(time.time() - t0, 1), "status": "DONE"
    }

    # -- O3: Interpretable models -----------------------------------------
    t0 = time.time()
    from .interpretable import run_interpretable, compute_shap_importance
    o3_results = run_interpretable(data)
    compute_shap_importance(data)
    telemetry["stages"]["O3_interpretable"] = {
        "duration_s": round(time.time() - t0, 1), "status": "DONE"
    }

    # -- O3 Trade-off -----------------------------------------------------
    t0 = time.time()
    from .tradeoff import run_tradeoff
    run_tradeoff()
    telemetry["stages"]["O3_tradeoff"] = {
        "duration_s": round(time.time() - t0, 1), "status": "DONE"
    }

    # -- O4: Targeting errors ---------------------------------------------
    t0 = time.time()
    from .targeting import run_targeting
    run_targeting(data)
    telemetry["stages"]["O4_targeting"] = {
        "duration_s": round(time.time() - t0, 1), "status": "DONE"
    }

    # -- O5: Acceptance ---------------------------------------------------
    t0 = time.time()
    from .acceptance import run_acceptance
    ac_results = run_acceptance()
    telemetry["stages"]["O5_acceptance"] = {
        "duration_s": round(time.time() - t0, 1), "status": "DONE"
    }

    # -- Negative tests ---------------------------------------------------
    t0 = time.time()
    from .negative_tests import run_negative_tests
    nt_results = run_negative_tests(data)
    telemetry["stages"]["negative_tests"] = {
        "duration_s": round(time.time() - t0, 1), "status": "DONE"
    }

    # -- Generate validation report ---------------------------------------
    _generate_validation_report(o2_results, o3_results, ac_results, nt_results)

    # -- DuckDB Database Sync ---------------------------------------------
    t0 = time.time()
    from .db import populate_db
    db_counts = populate_db()
    telemetry["stages"]["duckdb_sync"] = {
        "duration_s": round(time.time() - t0, 1), "status": "DONE", "counts": db_counts
    }

    # -- Telemetry --------------------------------------------------------
    total = time.time() - start
    telemetry["total_duration_s"] = round(total, 1)
    telemetry["end"] = datetime.datetime.now().isoformat()

    tel_path = config.OUTPUT_RESULTS / "telemetry.json"
    tel_path.parent.mkdir(parents=True, exist_ok=True)
    tel_path.write_text(json.dumps(telemetry, indent=2))

    print("\n" + "=" * 70)
    print("COMPLETE SYSTEM RUN FINISHED")
    print(f"Total time: {total:.0f}s ({total/60:.1f}min)")
    print(f"Results:    {config.OUTPUT_RESULTS}")
    print(f"Acceptance: {config.OUTPUT_ACCEPTANCE}")
    print("=" * 70)


def _generate_validation_report(o2, o3, ac, nt):
    """Generate the auto-generated policy validation report (D5, D7)."""
    lines = [
        "# DSCI-28 — Validation Report",
        "",
        f"Generated: {datetime.datetime.now().isoformat()}",
        "",
        "## O2 Reference Results (Black-Box Baselines)",
        "",
        "| Model | Method | Accuracy | AUC-ROC | F1 |",
        "|-------|--------|----------|---------|-----|",
    ]

    for key, res in o2.items():
        m = res.get("macro", res.get("overall", {}))
        lines.append(
            f"| {res['model']} | {res['method']} | "
            f"{m.get('accuracy', 0):.3f} | {m.get('auc_roc', 0):.3f} | "
            f"{m.get('f1', 0):.3f} |"
        )

    lines += [
        "",
        "## O3 Interpretable Model Results",
        "",
        "| Model | Accuracy | AUC-ROC | F1 |",
        "|-------|----------|---------|-----|",
    ]

    for key, res in o3.items():
        m = res.get("macro", res.get("overall", {}))
        lines.append(
            f"| {res['model']} | "
            f"{m.get('accuracy', 0):.3f} | {m.get('auc_roc', 0):.3f} | "
            f"{m.get('f1', 0):.3f} |"
        )

    lines += [
        "",
        "## O5 Acceptance Conditions",
        "",
        "| AC | Description | Status |",
        "|----|-------------|--------|",
    ]

    for ac_id, check in ac.items():
        if ac_id in ("saved_at", "seed"):
            continue
        status = "PASS OK" if check.get("passed") else "FAIL FAIL"
        lines.append(f"| {ac_id} | {check.get('description', '')} | {status} |")

    lines += [
        "",
        "## Negative Tests",
        "",
        "| NT | Description | Status |",
        "|----|-------------|--------|",
    ]

    for nt_id, result in nt.items():
        if nt_id in ("saved_at", "seed"):
            continue
        status = "PASS OK" if result.get("passed") else "FAIL FAIL"
        lines.append(f"| {nt_id} | {result.get('description', '')} | {status} |")

    lines += [
        "",
        "## Limitations and Residual Risks",
        "",
        "- Models trained on EHCVM 2021 data; temporal generalisation not tested",
        "- EBM interpretability is at feature level; individual predictions need local explanations",
        "- Cost ratios for targeting are illustrative; real-world ratios need policy input",
        "- Sample sizes vary across countries (affects confidence in smaller countries)",
        "",
    ]

    report_path = config.PROJECT_ROOT / "outputs" / "validation_report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n  -> Validation report: {report_path}")


if __name__ == "__main__":
    run()
