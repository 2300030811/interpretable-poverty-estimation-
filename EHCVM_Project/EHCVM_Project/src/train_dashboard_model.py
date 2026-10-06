"""
train_dashboard_model.py — Standalone training and artifact generation script
for dashboard model and conformal calibration split.

Creates:
  - outputs/models/dashboard_model.joblib (LightGBM model, TreeSHAP explainer, feature medians)
  - outputs/models/conformal_calibration.npz (50% pooled split probabilities & ground truth for conformal calibration)
"""
import time
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
import lightgbm as lgb
import shap
from sklearn.model_selection import train_test_split

from . import config
from .models import load_clean_data
from .evaluate import _get_feature_cols


def train_and_export_dashboard_model(data: dict = None) -> dict:
    """Train LightGBM on pooled dataset and export joblib artifact + conformal calibration."""
    if data is None:
        data = load_clean_data()

    feature_cols = _get_feature_cols(data)
    pooled = pd.concat(data.values(), ignore_index=True).fillna(0)

    X = pooled[feature_cols]
    y = pooled[config.TARGET_COL].values

    print(f"Training LightGBM on {len(pooled):,} pooled households with {len(feature_cols)} features...")
    t0 = time.time()

    model = lgb.LGBMClassifier(
        random_state=config.RANDOM_SEED,
        **config.MODEL_PARAMS["lightgbm"]
    )
    model.fit(X, y)
    print(f"  Model trained in {time.time() - t0:.2f}s")

    print("Fitting TreeSHAP explainer...")
    t0 = time.time()
    explainer = shap.TreeExplainer(model)
    print(f"  TreeSHAP fitted in {time.time() - t0:.2f}s")

    # Feature medians for interactive dashboard simulation
    medians = {col: float(pooled[col].median()) for col in feature_cols}
    country_medians = {
        c: {col: float(df[col].median()) for col in feature_cols if col in df.columns}
        for c, df in data.items()
    }

    artifact = {
        "model": model,
        "explainer": explainer,
        "feature_cols": feature_cols,
        "medians": medians,
        "country_medians": country_medians,
    }

    config.OUTPUT_MODELS.mkdir(parents=True, exist_ok=True)
    out_model_path = config.OUTPUT_MODELS / "dashboard_model.joblib"
    joblib.dump(artifact, out_model_path, compress=3)
    print(f"  -> Exported model artifact: {out_model_path} ({out_model_path.stat().st_size / 1e6:.2f} MB)")

    # Generate and export conformal calibration split (50% cal / 50% test)
    print("Generating conformal calibration split...")
    probs = model.predict_proba(X)
    _, _, y_cal, _, p_cal, _ = train_test_split(
        X, y, probs, test_size=0.5, random_state=config.RANDOM_SEED, stratify=y
    )

    out_cal_path = config.OUTPUT_MODELS / "conformal_calibration.npz"
    np.savez_compressed(out_cal_path, probs_cal=p_cal, y_cal=y_cal)
    print(f"  -> Exported conformal calibration: {out_cal_path} ({len(y_cal):,} samples, {out_cal_path.stat().st_size / 1e3:.1f} KB)")

    return artifact


if __name__ == "__main__":
    train_and_export_dashboard_model()
