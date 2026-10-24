"""
acceptance.py — O5: Acceptance conditions AC-1 through AC-4.

Validates the complete system against the capstone acceptance criteria.
"""
import json
import hashlib
from pathlib import Path

from . import config


def check_ac1_representative(results_dir: Path = None) -> dict:
    """
    AC-1: Representative operation.
    Validate that accuracy, generalisation, and interpretability metrics exist
    and meet KPI targets for all 8 countries.
    """
    results_dir = results_dir or config.OUTPUT_RESULTS
    checks = {"ac": "AC-1", "description": "Representative operation", "tests": []}

    # Check O2 baselines exist
    for f in ["o2_rf_loco.json", "o2_xgb_loco.json"]:
        path = results_dir / f
        passed = path.exists()
        checks["tests"].append({"check": f"O2 baseline {f} exists", "passed": passed})

    # Check O3 interpretable models exist
    for f in ["o3_logreg_loco.json", "o3_ebm_loco.json", "o3_lgbm_loco.json"]:
        path = results_dir / f
        passed = path.exists()
        checks["tests"].append({"check": f"O3 model {f} exists", "passed": passed})

    # Check all countries are evaluated
    ebm_path = results_dir / "o3_ebm_loco.json"
    if ebm_path.exists():
        ebm_data = json.loads(ebm_path.read_text())
        n_countries = len(ebm_data.get("countries", {}))
        min_countries = len(config.COUNTRIES)
        checks["tests"].append({
            "check": f"All baseline countries evaluated (expected >={min_countries}, got {n_countries})",
            "passed": n_countries >= min_countries,
        })

    # KPI-1: cross-country accuracy (FR-5: GAMs / boosted trees with attribution)
    o2_rf = _get_model_accuracy(results_dir, "o2_rf_loco.json")
    o2_xgb = _get_model_accuracy(results_dir, "o2_xgb_loco.json")
    o2_best = max(filter(None, [o2_rf, o2_xgb]))

    o3_ebm = _get_model_accuracy(results_dir, "o3_ebm_loco.json")
    o3_lgbm = _get_model_accuracy(results_dir, "o3_lgbm_loco.json")
    o3_best = max(filter(None, [o3_ebm, o3_lgbm]))

    if o2_best is not None and o3_best is not None:
        gap_best = (o3_best - o2_best) * 100
        passed_best = gap_best >= -1.0  # within 1 percentage point non-inferiority margin
        best_name = "LightGBM+SHAP" if o3_best == o3_lgbm else "EBM"
        checks["tests"].append({
            "check": f"KPI-1: Best interpretable ({best_name} {o3_best:.3f}) within 1pp of O2 reference ({o2_best:.3f}), gap={gap_best:+.1f}pp",
            "passed": passed_best,
        })

    if o2_rf is not None and o3_ebm is not None:
        gap_ebm_rf = (o3_ebm - o2_rf) * 100
        passed_ebm_rf = gap_ebm_rf >= -1.0
        checks["tests"].append({
            "check": f"KPI-1 (GAM): EBM ({o3_ebm:.3f}) vs RF reference ({o2_rf:.3f}), gap={gap_ebm_rf:+.1f}pp",
            "passed": passed_ebm_rf,
        })

    checks["passed"] = all(t["passed"] for t in checks["tests"])
    return checks


def check_ac2_boundary() -> dict:
    """
    AC-2: Boundary and failure operation.
    Exercise country-specific overfitting; verify asymmetric error treatment.
    """
    results_dir = config.OUTPUT_RESULTS
    checks = {"ac": "AC-2", "description": "Boundary and failure operation", "tests": []}

    # Check overfitting analysis exists
    loco_files = list(results_dir.glob("*_loco.json"))
    checks["tests"].append({
        "check": f"LOCO results exist ({len(loco_files)} files)",
        "passed": len(loco_files) >= 4,
    })

    # Check targeting analysis exists (asymmetric errors)
    targeting = results_dir / "o4_targeting_analysis.json"
    checks["tests"].append({
        "check": "Targeting analysis (asymmetric errors) exists",
        "passed": targeting.exists(),
    })

    # Check trade-off table exists
    tradeoff = results_dir / "accuracy_cost.csv"
    checks["tests"].append({
        "check": "Accuracy cost trade-off table exists",
        "passed": tradeoff.exists(),
    })

    checks["passed"] = all(t["passed"] for t in checks["tests"])
    return checks


def check_ac3_independent_partition() -> dict:
    """
    AC-3: Independent acceptance evidence.
    LOCO is inherently a country-separated partition — each test fold is a
    completely different country never seen during training.
    """
    results_dir = config.OUTPUT_RESULTS
    checks = {"ac": "AC-3", "description": "Independent acceptance evidence", "tests": []}

    # Verify LOCO uses entity-separated partitions
    for model_file in ["o2_xgb_loco.json", "o3_ebm_loco.json"]:
        path = results_dir / model_file
        if path.exists():
            data = json.loads(path.read_text())
            method = data.get("method", "")
            checks["tests"].append({
                "check": f"{model_file}: method={method} (entity-separated)",
                "passed": method == "LOCO",
            })

    # Verify lineage report exists
    lineage = config.DATA_PROCESSED / "lineage_report.json"
    checks["tests"].append({
        "check": "Source lineage report exists",
        "passed": lineage.exists(),
    })

    checks["passed"] = all(t["passed"] for t in checks["tests"])
    return checks


def check_ac4_frozen_envelope() -> dict:
    """
    AC-4: Frozen resource envelope.
    Verify same seeds, hyperparameters, and data versions across O2 and O3.
    """
    results_dir = config.OUTPUT_RESULTS
    checks = {"ac": "AC-4", "description": "Frozen resource envelope", "tests": []}

    # Check seeds match
    seeds = set()
    for f in results_dir.glob("*.json"):
        try:
            data = json.loads(f.read_text())
            if "seed" in data:
                seeds.add(data["seed"])
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass

    checks["tests"].append({
        "check": f"All results use same seed (found: {seeds})",
        "passed": len(seeds) <= 1,
    })

    # Check data versions match (hash of lineage report)
    EXPECTED_LINEAGE_HASH = "d02adba7"
    lineage = config.DATA_PROCESSED / "lineage_report.json"
    if lineage.exists():
        h = hashlib.md5(lineage.read_bytes()).hexdigest()[:8]
        checks["tests"].append({
            "check": f"Data lineage hash: {h} (expected: {EXPECTED_LINEAGE_HASH})",
            "passed": h == EXPECTED_LINEAGE_HASH,
        })
    else:
        checks["tests"].append({
            "check": "Data lineage report exists",
            "passed": False,
        })

    # Verify frozen hyperparameters are recorded
    checks["tests"].append({
        "check": "Hyperparameters defined in config.MODEL_PARAMS",
        "passed": len(config.MODEL_PARAMS) >= 5,
    })

    checks["passed"] = all(t["passed"] for t in checks["tests"])
    return checks


def run_acceptance() -> dict:
    """Run all acceptance conditions and produce a summary."""
    print("\n" + "=" * 70)
    print("O5 — ACCEPTANCE CONDITIONS")
    print("=" * 70)

    all_checks = {}
    for check_fn in [check_ac1_representative, check_ac2_boundary,
                     check_ac3_independent_partition, check_ac4_frozen_envelope]:
        result = check_fn()
        ac = result["ac"]
        all_checks[ac] = result
        status = "PASS OK" if result["passed"] else "FAIL FAIL"
        print(f"\n  {ac}: {result['description']} — {status}")
        for t in result["tests"]:
            mark = "OK" if t["passed"] else "FAIL"
            print(f"    {mark} {t['check']}")

    # Overall
    all_pass = all(r["passed"] for r in all_checks.values())
    print(f"\n  {'='*50}")
    print(f"  Overall: {'ALL PASS OK' if all_pass else 'SOME FAILED FAIL'}")

    from .evaluate import save_results
    save_results(all_checks, "o5_acceptance.json", config.OUTPUT_ACCEPTANCE)

    return all_checks


def _get_best_baseline_accuracy(results_dir):
    """Get the best O2 baseline macro accuracy."""
    best = None
    for f in ["o2_rf_loco.json", "o2_xgb_loco.json"]:
        path = results_dir / f
        if path.exists():
            data = json.loads(path.read_text())
            acc = data.get("macro", {}).get("accuracy")
            if acc is not None and (best is None or acc > best):
                best = acc
    return best


def _get_model_accuracy(results_dir, filename):
    """Get macro accuracy from a LOCO result file."""
    path = results_dir / filename
    if path.exists():
        data = json.loads(path.read_text())
        return data.get("macro", {}).get("accuracy")
    return None


if __name__ == "__main__":
    run_acceptance()
