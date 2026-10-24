# DSCI-28 — Validation Report

Generated: 2026-09-21T08:34:22.667016

## O2 Reference Results (Black-Box Baselines)

| Model | Method | Accuracy | AUC-ROC | F1 |
|-------|--------|----------|---------|-----|
| random_forest | LOCO | 0.740 | 0.848 | 0.648 |
| random_forest | pooled | 0.769 | 0.857 | 0.696 |
| xgboost | LOCO | 0.763 | 0.849 | 0.617 |
| xgboost | pooled | 0.802 | 0.876 | 0.695 |

## O3 Interpretable Model Results

| Model | Accuracy | AUC-ROC | F1 |
|-------|----------|---------|-----|
| logistic_regression | 0.735 | 0.848 | 0.660 |
| ebm | 0.748 | 0.836 | 0.595 |
| lightgbm | 0.764 | 0.849 | 0.626 |

## O5 Acceptance Conditions

| AC | Description | Status |
|----|-------------|--------|
| AC-1 | Representative operation | PASS OK |
| AC-2 | Boundary and failure operation | PASS OK |
| AC-3 | Independent acceptance evidence | PASS OK |
| AC-4 | Frozen resource envelope | PASS OK |

## Negative Tests

| NT | Description | Status |
|----|-------------|--------|
| NT-1 | Country-specific overfitting | PASS OK |
| NT-2 | Black-box unusable for policy | PASS OK |
| NT-3 | Equal error type treatment detection | PASS OK |
| NT-4 | Idempotent replay | PASS OK |
| NT-5 | Partition defect detection | PASS OK |

## Limitations and Residual Risks

- Models trained on EHCVM 2021 data; temporal generalisation not tested
- EBM interpretability is at feature level; individual predictions need local explanations
- Cost ratios for targeting are illustrative; real-world ratios need policy input
- Sample sizes vary across countries (affects confidence in smaller countries)
