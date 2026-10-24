"""
targeting.py — O4: Exclusion vs inclusion error analysis (FR-4).

Analyses asymmetric targeting costs:
  - Exclusion error: truly poor classified as non-poor (FN) — denied benefits
  - Inclusion error: non-poor classified as poor (FP) — wasted resources
"""
import json
import numpy as np
import pandas as pd
from sklearn.metrics import confusion_matrix

from . import config
from .evaluate import _get_feature_cols, save_results


def compute_threshold_curve(y_true, y_prob, thresholds=None):
    """
    Compute exclusion/inclusion errors at varying decision thresholds.
    Returns DataFrame with columns: threshold, exclusion_error, inclusion_error,
    accuracy, f1, precision, recall.
    """
    if thresholds is None:
        thresholds = np.arange(0.05, 0.96, 0.05)

    rows = []
    for t in thresholds:
        y_pred = (y_prob >= t).astype(int)
        cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
        tn, fp, fn, tp = cm.ravel()

        exc = fn / (fn + tp) if (fn + tp) > 0 else 0
        inc = fp / (fp + tn) if (fp + tn) > 0 else 0

        rows.append({
            "threshold": float(t),
            "exclusion_error": float(exc),
            "inclusion_error": float(inc),
            "accuracy": float((tp + tn) / (tp + tn + fp + fn)),
            "tp": int(tp), "fp": int(fp), "fn": int(fn), "tn": int(tn),
        })
    return pd.DataFrame(rows)


def find_optimal_threshold(curve_df, cost_ratio: float) -> dict:
    """
    Find threshold that minimises weighted cost:
    cost = exclusion_error * cost_ratio + inclusion_error
    """
    costs = curve_df["exclusion_error"] * cost_ratio + curve_df["inclusion_error"]
    best_idx = costs.idxmin()
    best = curve_df.loc[best_idx].to_dict()
    best["cost_ratio"] = cost_ratio
    best["weighted_cost"] = float(costs.iloc[best_idx])
    return best


def run_targeting(data: dict[str, pd.DataFrame] = None) -> dict:
    """
    Run O4 targeting error analysis using EBM (best interpretable model)
    under LOCO protocol.
    """
    if data is None:
        from .models import load_clean_data
        data = load_clean_data()

    print("\n" + "=" * 70)
    print("O4 — EXCLUSION vs INCLUSION ERROR ANALYSIS")
    print("=" * 70)

    from interpret.glassbox import ExplainableBoostingClassifier

    countries = list(data.keys())
    feature_cols = _get_feature_cols(data)
    all_results = {"curves": {}, "optimal_thresholds": {}}

    for test_country in countries:
        print(f"\n  Analysing {test_country}...")
        train_dfs = [data[c] for c in countries if c != test_country]
        train = pd.concat(train_dfs, ignore_index=True)

        X_train = train[feature_cols].values
        y_train = train[config.TARGET_COL].values
        X_test = data[test_country][feature_cols].values
        y_test = data[test_country][config.TARGET_COL].values

        ebm = ExplainableBoostingClassifier(
            random_state=config.RANDOM_SEED, **config.MODEL_PARAMS["ebm"]
        )
        ebm.fit(X_train, y_train)
        y_prob = ebm.predict_proba(X_test)[:, 1]

        # Threshold curve
        curve = compute_threshold_curve(y_test, y_prob)
        all_results["curves"][test_country] = curve.to_dict(orient="records")

        # Optimal thresholds for each cost ratio
        for ratio in config.COST_RATIOS:
            opt = find_optimal_threshold(curve, ratio)
            key = f"{test_country}_ratio_{ratio}"
            all_results["optimal_thresholds"][key] = opt
            if ratio == 3.0:  # Print the "exclusion costs 3× inclusion" case
                print(f"    Cost ratio 3:1 -> threshold={opt['threshold']:.2f}  "
                      f"excl={opt['exclusion_error']:.3f}  "
                      f"incl={opt['inclusion_error']:.3f}")

    # Save curves and thresholds
    save_results(all_results, "o4_targeting_analysis.json")

    # Summary table
    summary_rows = []
    for key, opt in all_results["optimal_thresholds"].items():
        parts = key.rsplit("_ratio_", 1)
        summary_rows.append({
            "Country": parts[0],
            "Cost Ratio": opt["cost_ratio"],
            "Threshold": opt["threshold"],
            "Exclusion Error": opt["exclusion_error"],
            "Inclusion Error": opt["inclusion_error"],
            "Accuracy": opt["accuracy"],
            "Weighted Cost": opt["weighted_cost"],
        })
    summary = pd.DataFrame(summary_rows)
    out_path = config.OUTPUT_RESULTS / "targeting_summary.csv"
    summary.to_csv(out_path, index=False)
    print(f"\n  -> Summary: {out_path.name}")

    # Print cross-country summary at default policy ratio (3:1)
    print("\n-- Cross-Country Targeting Summary (Cost Ratio 3:1) -------")
    policy = summary[summary["Cost Ratio"] == 3.0]
    for _, row in policy.iterrows():
        print(f"  {row['Country']:20s}  threshold={row['Threshold']:.2f}  "
              f"excl={row['Exclusion Error']:.3f}  "
              f"incl={row['Inclusion Error']:.3f}  "
              f"acc={row['Accuracy']:.3f}")

    return all_results


if __name__ == "__main__":
    run_targeting()
