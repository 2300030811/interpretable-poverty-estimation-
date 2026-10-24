"""
interpretable.py — O3: Interpretable models + accuracy cost measurement.

Implements Logistic Regression, EBM (GAM), and LightGBM+SHAP.
Same LOCO evaluation as O2 (AC-4: frozen resource envelope).
"""
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
import lightgbm as lgb

from . import config
from .evaluate import evaluate_loco, evaluate_pooled, save_results


def _make_logreg(X_train, y_train):
    """Logistic Regression with scaling — fully interpretable baseline."""
    pipe = Pipeline([
        ("scaler", StandardScaler()),
        ("lr", LogisticRegression(
            random_state=config.RANDOM_SEED,
            **config.MODEL_PARAMS["logistic_regression"]
        )),
    ])
    pipe.fit(X_train, y_train)
    return pipe


def _make_ebm(X_train, y_train):
    """Explainable Boosting Machine — state-of-the-art GAM (FR-5)."""
    from interpret.glassbox import ExplainableBoostingClassifier

    ebm = ExplainableBoostingClassifier(
        random_state=config.RANDOM_SEED,
        **config.MODEL_PARAMS["ebm"]
    )
    ebm.fit(X_train, y_train)
    return ebm


def _make_lgbm(X_train, y_train):
    """LightGBM — boosted trees with post-hoc SHAP attribution (FR-5)."""
    clf = lgb.LGBMClassifier(
        random_state=config.RANDOM_SEED,
        **config.MODEL_PARAMS["lightgbm"]
    )
    clf.fit(X_train, y_train)
    return clf


def run_interpretable(data: dict[str, pd.DataFrame] = None) -> dict:
    """
    Run O3 interpretable models: LogReg, EBM, LightGBM under LOCO.
    Returns dict of all results.
    """
    if data is None:
        from .models import load_clean_data
        data = load_clean_data()

    print("\n" + "=" * 70)
    print("O3 — INTERPRETABLE MODELS + ACCURACY COST")
    print("=" * 70)

    all_results = {}

    # -- Logistic Regression ----------------------------------------------
    print("\n-- Logistic Regression (LOCO) ------------------------------")
    lr_loco = evaluate_loco(_make_logreg, data, "logistic_regression")
    save_results(lr_loco, "o3_logreg_loco.json")
    all_results["logreg_loco"] = lr_loco

    # -- EBM / GAM --------------------------------------------------------
    print("\n-- Explainable Boosting Machine (LOCO) --------------------")
    ebm_loco = evaluate_loco(_make_ebm, data, "ebm")
    save_results(ebm_loco, "o3_ebm_loco.json")
    all_results["ebm_loco"] = ebm_loco

    # -- LightGBM ---------------------------------------------------------
    print("\n-- LightGBM (LOCO) ----------------------------------------")
    lgbm_loco = evaluate_loco(_make_lgbm, data, "lightgbm")
    save_results(lgbm_loco, "o3_lgbm_loco.json")
    all_results["lgbm_loco"] = lgbm_loco

    # Summary
    print("\n-- O3 Interpretable Model Summary -------------------------")
    for key, res in all_results.items():
        m = res.get("macro", res.get("overall", {}))
        print(f"  {key:20s}  acc={m['accuracy']:.3f}  "
              f"auc={m.get('auc_roc', float('nan')):.3f}  "
              f"f1={m['f1']:.3f}")

    return all_results


def compute_shap_importance(data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Compute SHAP feature importance for LightGBM on pooled data.
    Returns DataFrame with feature names and mean |SHAP| values.
    """
    import shap

    from .evaluate import _get_feature_cols
    feature_cols = _get_feature_cols(data)
    pooled = pd.concat(data.values(), ignore_index=True).fillna(0)

    X = pooled[feature_cols].values
    y = pooled[config.TARGET_COL].values

    clf = lgb.LGBMClassifier(
        random_state=config.RANDOM_SEED, **config.MODEL_PARAMS["lightgbm"]
    )
    clf.fit(X, y)

    explainer = shap.TreeExplainer(clf)
    shap_values = explainer.shap_values(X)

    # For binary classification, shap_values may be a list [class0, class1]
    if isinstance(shap_values, list):
        shap_values = shap_values[1]

    importance = pd.DataFrame({
        "feature": feature_cols,
        "mean_abs_shap": np.abs(shap_values).mean(axis=0),
    }).sort_values("mean_abs_shap", ascending=False).reset_index(drop=True)

    out_path = config.OUTPUT_RESULTS / "shap_importance.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    importance.to_csv(out_path, index=False)
    print(f"  -> SHAP importance: {out_path.name}")
    return importance


if __name__ == "__main__":
    run_interpretable()
