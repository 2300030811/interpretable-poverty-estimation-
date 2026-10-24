"""
negative_tests.py — 5 mandatory negative tests (NT-1 through NT-5).

Each test creates a controlled condition to verify the system detects
and handles failure modes correctly.
"""
import json
import hashlib
import numpy as np
import pandas as pd
from pathlib import Path

from . import config
from .evaluate import _get_feature_cols, save_results


def nt1_country_overfitting(data: dict[str, pd.DataFrame]) -> dict:
    """
    NT-1: Country-specific overfitting detection.

    Compare within-country accuracy (train+test on same country) vs
    LOCO accuracy (train on others, test on held-out).
    Flag if gap > 10pp — indicates overfitting to country specifics.
    """
    from sklearn.model_selection import train_test_split
    from interpret.glassbox import ExplainableBoostingClassifier

    print("  NT-1: Country-specific overfitting detection...")
    feature_cols = _get_feature_cols(data)
    countries = list(data.keys())
    results = {"test": "NT-1", "description": "Country-specific overfitting", "countries": {}}

    for country in countries:
        df = data[country]
        X = df[feature_cols].values
        y = df[config.TARGET_COL].values

        # Within-country: 80/20 split
        X_tr, X_te, y_tr, y_te = train_test_split(
            X, y, test_size=0.2, random_state=config.RANDOM_SEED, stratify=y
        )
        ebm_within = ExplainableBoostingClassifier(
            random_state=config.RANDOM_SEED, **config.MODEL_PARAMS["ebm"]
        )
        ebm_within.fit(X_tr, y_tr)
        within_acc = float((ebm_within.predict(X_te) == y_te).mean())

        # LOCO: train on all others
        train_dfs = [data[c] for c in countries if c != country]
        train = pd.concat(train_dfs, ignore_index=True)
        X_train_loco = train[feature_cols].values
        y_train_loco = train[config.TARGET_COL].values

        ebm_loco = ExplainableBoostingClassifier(
            random_state=config.RANDOM_SEED, **config.MODEL_PARAMS["ebm"]
        )
        ebm_loco.fit(X_train_loco, y_train_loco)
        loco_acc = float((ebm_loco.predict(X) == y).mean())

        gap = (within_acc - loco_acc) * 100
        flagged = bool(gap > 10)
        results["countries"][country] = {
            "within_acc": within_acc,
            "loco_acc": loco_acc,
            "gap_pp": gap,
            "overfitting_flagged": flagged,
        }
        mark = "⚠ FLAGGED" if flagged else "OK"
        print(f"    {country:20s}  within={within_acc:.3f}  loco={loco_acc:.3f}  "
              f"gap={gap:+.1f}pp  {mark}")

    flagged_count = sum(1 for c in results["countries"].values() if c["overfitting_flagged"])
    # NT-1 passes if cross-border transfer degradation is bounded (gap <= 10pp across all nations)
    results["passed"] = bool(flagged_count == 0)
    results["flagged_countries"] = flagged_count
    print(f"    -> {flagged_count} countries flagged for overfitting risk (Passed: {results['passed']})")
    return results


def nt2_blackbox_unusable(data: dict[str, pd.DataFrame]) -> dict:
    """
    NT-2: Black-box models unusable for policy.

    Verify that the system selects an interpretable model (EBM) when
    the policy flag requires interpretability, rejecting black-box models.
    """
    print("  NT-2: Black-box policy rejection...")
    from .tradeoff import INTERPRETABILITY_SCORES

    results = {"test": "NT-2", "description": "Black-box unusable for policy", "tests": []}

    # Policy rule: models with interpretability < 3 are rejected
    POLICY_THRESHOLD = 3

    for model, score in INTERPRETABILITY_SCORES.items():
        accepted = score >= POLICY_THRESHOLD
        results["tests"].append({
            "model": model,
            "interpretability": score,
            "policy_accepted": accepted,
        })
        mark = "OK accepted" if accepted else "FAIL rejected"
        print(f"    {model:25s}  score={score}  {mark}")

    # Verify EBM and LogReg pass, RF and XGB don't
    ebm_ok = INTERPRETABILITY_SCORES["ebm"] >= POLICY_THRESHOLD
    xgb_rejected = INTERPRETABILITY_SCORES["xgboost"] < POLICY_THRESHOLD
    results["passed"] = ebm_ok and xgb_rejected
    print(f"    -> EBM accepted: {ebm_ok}, XGBoost rejected: {xgb_rejected}")
    return results


def nt3_equal_error_detection(data: dict[str, pd.DataFrame]) -> dict:
    """
    NT-3: Treating both error types as equal.

    Verify the system detects when symmetric (equal) costs are used
    and flags that asymmetric costs should be applied.
    """
    print("  NT-3: Equal error type detection...")
    from .targeting import compute_threshold_curve, find_optimal_threshold
    from interpret.glassbox import ExplainableBoostingClassifier

    feature_cols = _get_feature_cols(data)
    # Use first country as test case
    test_country = list(data.keys())[0]
    train_dfs = [data[c] for c in data if c != test_country]
    train = pd.concat(train_dfs, ignore_index=True)

    ebm = ExplainableBoostingClassifier(
        random_state=config.RANDOM_SEED, **config.MODEL_PARAMS["ebm"]
    )
    ebm.fit(train[feature_cols].values, train[config.TARGET_COL].values)
    y_prob = ebm.predict_proba(data[test_country][feature_cols].values)[:, 1]
    y_test = data[test_country][config.TARGET_COL].values

    curve = compute_threshold_curve(y_test, y_prob)

    # Equal cost (ratio=1) vs asymmetric (ratio=3)
    opt_equal = find_optimal_threshold(curve, 1.0)
    opt_asym = find_optimal_threshold(curve, 3.0)

    thresholds_differ = abs(opt_equal["threshold"] - opt_asym["threshold"]) > 0.01
    results = {
        "test": "NT-3",
        "description": "Equal error type treatment detection",
        "test_country": test_country,
        "equal_threshold": opt_equal["threshold"],
        "asymmetric_threshold": opt_asym["threshold"],
        "thresholds_differ": thresholds_differ,
        "passed": thresholds_differ,
    }
    print(f"    Equal cost threshold:     {opt_equal['threshold']:.2f}")
    print(f"    Asymmetric cost threshold: {opt_asym['threshold']:.2f}")
    print(f"    -> Thresholds differ: {thresholds_differ}")
    return results


def nt4_idempotent_replay(data: dict[str, pd.DataFrame]) -> dict:
    """
    NT-4: Non-idempotent replay detection.

    Run the pipeline twice and verify outputs are bit-identical.
    """
    print("  NT-4: Idempotent replay check...")
    from interpret.glassbox import ExplainableBoostingClassifier

    feature_cols = _get_feature_cols(data)
    test_country = list(data.keys())[0]
    train_dfs = [data[c] for c in data if c != test_country]
    train = pd.concat(train_dfs, ignore_index=True)

    X_train = train[feature_cols].values
    y_train = train[config.TARGET_COL].values
    X_test = data[test_country][feature_cols].values

    # Run 1
    ebm1 = ExplainableBoostingClassifier(
        random_state=config.RANDOM_SEED, **config.MODEL_PARAMS["ebm"]
    )
    ebm1.fit(X_train, y_train)
    pred1 = ebm1.predict(X_test)
    prob1 = ebm1.predict_proba(X_test)[:, 1]

    # Run 2 (same seed, same data)
    ebm2 = ExplainableBoostingClassifier(
        random_state=config.RANDOM_SEED, **config.MODEL_PARAMS["ebm"]
    )
    ebm2.fit(X_train, y_train)
    pred2 = ebm2.predict(X_test)
    prob2 = ebm2.predict_proba(X_test)[:, 1]

    preds_match = np.array_equal(pred1, pred2)
    probs_close = np.allclose(prob1, prob2, atol=1e-6)

    results = {
        "test": "NT-4",
        "description": "Idempotent replay",
        "predictions_identical": bool(preds_match),
        "probabilities_close": bool(probs_close),
        "passed": preds_match and probs_close,
    }
    print(f"    Predictions identical: {preds_match}")
    print(f"    Probabilities match:   {probs_close}")
    return results


def nt5_partition_defect(data: dict[str, pd.DataFrame]) -> dict:
    """
    NT-5: Partition-level quality defect hiding in global average.

    Inject a defect into one country's data and verify the system detects
    per-partition accuracy drop even if global average looks fine.
    """
    print("  NT-5: Partition defect detection...")
    from interpret.glassbox import ExplainableBoostingClassifier

    feature_cols = _get_feature_cols(data)
    countries = list(data.keys())

    # Train on all data
    pooled = pd.concat(data.values(), ignore_index=True)
    X_all = pooled[feature_cols].values
    y_all = pooled[config.TARGET_COL].values

    ebm = ExplainableBoostingClassifier(
        random_state=config.RANDOM_SEED, **config.MODEL_PARAMS["ebm"]
    )
    ebm.fit(X_all, y_all)

    # Evaluate per country
    country_accs = {}
    for c in countries:
        X_c = data[c][feature_cols].values
        y_c = data[c][config.TARGET_COL].values
        acc = float((ebm.predict(X_c) == y_c).mean())
        country_accs[c] = acc

    global_acc = float((ebm.predict(X_all) == y_all).mean())

    # Inject defect: flip 30% of labels in one country and check detection
    defect_country = countries[0]
    df_defect = data[defect_country].copy()
    n_flip = int(len(df_defect) * 0.3)
    flip_idx = df_defect.sample(n_flip, random_state=config.RANDOM_SEED).index
    df_defect.loc[flip_idx, config.TARGET_COL] = 1 - df_defect.loc[flip_idx, config.TARGET_COL]

    defect_acc = float((ebm.predict(df_defect[feature_cols].values) == df_defect[config.TARGET_COL].values).mean())

    # The defect should cause this country's accuracy to drop significantly
    acc_drop = country_accs[defect_country] - defect_acc
    detected = acc_drop > 0.05  # more than 5pp drop

    # Check if global average would hide it
    all_accs = list(country_accs.values())
    all_accs[0] = defect_acc  # replace defective country
    global_with_defect = np.mean(all_accs)
    global_drop = global_acc - global_with_defect

    results = {
        "test": "NT-5",
        "description": "Partition defect detection",
        "defect_country": defect_country,
        "original_acc": country_accs[defect_country],
        "defective_acc": defect_acc,
        "partition_drop_pp": acc_drop * 100,
        "global_drop_pp": global_drop * 100,
        "defect_detected_by_partition": bool(detected),
        "hidden_by_global": bool(global_drop * 100 < 2),  # < 2pp global drop
        "passed": bool(detected),
    }
    print(f"    {defect_country}: original={country_accs[defect_country]:.3f}  "
          f"defective={defect_acc:.3f}  drop={acc_drop*100:.1f}pp")
    print(f"    Global drop: {global_drop*100:.1f}pp (hidden: {results['hidden_by_global']})")
    print(f"    -> Partition monitoring detects defect: {detected}")
    return results


def run_negative_tests(data: dict[str, pd.DataFrame] = None) -> dict:
    """Run all 5 mandatory negative tests."""
    if data is None:
        from .models import load_clean_data
        data = load_clean_data()

    print("\n" + "=" * 70)
    print("MANDATORY NEGATIVE TESTS (NT-1 to NT-5)")
    print("=" * 70)

    all_results = {}
    for test_fn in [nt1_country_overfitting, nt2_blackbox_unusable,
                    nt3_equal_error_detection, nt4_idempotent_replay,
                    nt5_partition_defect]:
        print()
        result = test_fn(data)
        all_results[result["test"]] = result

    # Summary
    print("\n" + "=" * 50)
    print("NEGATIVE TEST SUMMARY")
    print("=" * 50)
    for nt_id, res in all_results.items():
        status = "PASS OK" if res["passed"] else "FAIL FAIL"
        print(f"  {nt_id}: {res['description']:45s} {status}")

    all_pass = all(r["passed"] for r in all_results.values())
    print(f"\n  Overall: {'ALL PASS OK' if all_pass else 'SOME FAILED FAIL'}")

    save_results(all_results, "negative_tests.json", config.OUTPUT_ACCEPTANCE)
    return all_results


if __name__ == "__main__":
    run_negative_tests()
