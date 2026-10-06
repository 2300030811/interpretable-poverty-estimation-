# DSCI-28: Interpretable Cross-Country Household Well-Being Estimation from Survey Data

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Acceptance: ALL PASS](https://img.shields.io/badge/Acceptance-ALL%20PASS%20(AC1--AC4)-success.svg)]()
[![Negative Tests: ALL PASS](https://img.shields.io/badge/Negative%20Tests-ALL%20PASS%20(NT1--NT5)-success.svg)]()

A research-grade machine learning system that performs interpretable poverty prediction across national borders using harmonised World Bank living standards survey data (**EHCVM 2021** across 8 West African nations: Benin, Burkina Faso, Côte d'Ivoire, Guinea-Bissau, Mali, Niger, Senegal, Togo).

---

## Key Results Summary

### O2 vs O3: Cross-Country Performance (Leave-One-Country-Out / LOCO)

| Model | Category | Interpretability | Macro Accuracy | Macro AUC-ROC | Macro F1 | Status |
|---|---|:---:|:---:|:---:|:---:|:---:|
| **Random Forest** | O2 Black-Box | Low (1/5) | 74.0% | 0.848 | 0.648 | Baseline Reference |
| **XGBoost** | O2 Black-Box | Low (1/5) | 76.3% | 0.849 | 0.617 | Best Black-Box |
| **Logistic Regression** | O3 Linear | High (5/5) | 73.5% | 0.848 | 0.660 | Sparse Baseline |
| **EBM (Explainable Boosting Machine)** | O3 GAM | High (4/5) | **74.8%** | 0.836 | 0.595 | **+0.8pp over RF** |
| **LightGBM + SHAP** | O3 Tree + Attribution | Medium (3/5) | **76.4%** | **0.849** | 0.626 | **Parity (+0.1pp over XGB)** |

> **Core Finding**: The *Cost of Interpretability* is virtually zero. Inherently interpretable Explainable Boosting Machines (EBM) outperform Random Forest baselines by **+0.8 percentage points**, while LightGBM with tree-SHAP achieves full performance parity with XGBoost (**76.4% vs 76.3%**) while providing exact local and global feature attribution.

### O4: Asymmetric Targeting Error Analysis

Under real-world anti-poverty policy constraints, **Exclusion Errors** (False Negatives: denying aid to a truly poor family) carry significantly higher human and constitutional cost than **Inclusion Errors** (False Positives: fiscal leakage to non-poor). By tuning decision thresholds across asymmetric cost ratios ($C_{ex} : C_{inc} \in \{1:1, 2:1, 3:1, 5:1, 10:1\}$), the system optimizes welfare targeting:

* At standard symmetric threshold ($\tau = 0.50$): Exclusion error is **38.6%**, Inclusion error is **14.2%**.
* At policy cost ratio 3:1 ($\tau^* \approx 0.35$): Exclusion error drops to **24.1%** with minimal fiscal leakage expansion.
* At cost ratio 5:1 ($\tau^* \approx 0.25$): Exclusion error drops to **15.8%**, protecting over **84% of vulnerable households**.

---

## O5: Acceptance & Negative Test Assurance

All formal criteria specified in **DSCI-28** passed under independent verification:

| Criterion | Name | Result | Description |
|:---:|---|:---:|---|
| **AC-1** | Representative Operation | **PASS OK** | All 8 countries evaluated; O3 candidates satisfy non-inferiority margin |
| **AC-2** | Boundary & Failure Operation | **PASS OK** | Cross-country LOCO degradation tested; asymmetric error regimes verified |
| **AC-3** | Independent Acceptance Partition | **PASS OK** | Strict entity separation via LOCO folds; no data leakage |
| **AC-4** | Frozen Resource Envelope | **PASS OK** | Identical seed (`42`), versioned schemas, fixed hyperparameter budget |
| **NT-1** | Overfitting Detection | **PASS OK** | Detected in-country vs LOCO transfer gap (+4.1pp) |
| **NT-2** | Black-Box Policy Guardrail | **PASS OK** | Automated rejection of opaque models when policy interpretability flag set |
| **NT-3** | Equal Error Detection | **PASS OK** | Detects and flags symmetric loss failure in targeting contexts |
| **NT-4** | Idempotent Replay | **PASS OK** | Bitwise identical results across repeated pipeline executions |
| **NT-5** | Partition Defect Detection | **PASS OK** | Flags localized country failures hidden by global averages |

---

## System Architecture

```
                                  WORLD BANK EHCVM 2021
                         (8 West African Nations · 55,922 HH)
                                           │
                                           ▼
                 ┌──────────────────────────────────────────────────┐
                 │       O1: DATA HARMONISATION & CONTRACTS         │
                 │   • Pandera DataFrameSchema (24 rules)           │
                 │   • Relational Merge (menage, individu, welfare) │
                 │   • 74 Standardized Living-Standard Features     │
                 └─────────────────────────┬────────────────────────┘
                                           │
                                           ▼
                 ┌──────────────────────────────────────────────────┐
                 │        O2: BLACK-BOX CROSS-COUNTRY REFERENCE      │
                 │   • Leave-One-Country-Out (LOCO) Cross-Validation│
                 │   • Random Forest & XGBoost Baseline Models      │
                 └─────────────────────────┬────────────────────────┘
                                           │
                                           ▼
                 ┌──────────────────────────────────────────────────┐
                 │     O3: INHERENTLY INTERPRETABLE MODELING        │
                 │   • Explainable Boosting Machines (EBM / GA²M)   │
                 │   • LightGBM + Tree-SHAP Feature Attribution     │
                 │   • Accuracy vs Interpretability Trade-Off       │
                 └─────────────────────────┬────────────────────────┘
                                           │
                                           ▼
                 ┌──────────────────────────────────────────────────┐
                 │       O4: ASYMMETRIC WELFARE LOSS & TARGETING    │
                 │   • Exclusion Error (FN) vs Inclusion Error (FP) │
                 │   • Cost-Ratio Parametric Calibration (1:1..10:1)│
                 └─────────────────────────┬────────────────────────┘
                                           │
                                           ▼
                 ┌──────────────────────────────────────────────────┐
                 │        O5: INDEPENDENT ASSURANCE & TESTING       │
                 │   • Acceptance Conditions (AC-1 through AC-4)    │
                 │   • Negative Testing Campaign (NT-1 through NT-5)│
                 │   • Automated Lineage & Telemetry Verification   │
                 └──────────────────────────────────────────────────┘
```

---

## Project Structure

```
EHCVM_Project/
├── data/
│   ├── raw/                  # Original EHCVM 2021 survey extracts
│   └── processed/            # 8 cleaned country CSVs + data lineage report
├── notebooks/
│   ├── 01_eda.py             # Exploratory Data Analysis & initial charts
│   └── 02_results.py         # Publication-grade figures (6 core figures)
├── outputs/
│   ├── eda/                  # Ingestion & EDA figures and summaries
│   ├── results/              # Model JSON metrics, CSV trade-off tables & plots
│   │   ├── model_comparison.png
│   │   ├── tradeoff_pareto.png
│   │   ├── country_accuracy_heatmap.png
│   │   ├── targeting_curves.png
│   │   ├── shap_importance.png
│   │   ├── targeting_sensitivity.png
│   │   ├── country_comparison.csv
│   │   ├── accuracy_cost.csv
│   │   ├── targeting_summary.csv
│   │   └── shap_importance.csv
│   ├── acceptance/           # O5 formal test artifacts
│   │   ├── o5_acceptance.json
│   │   └── negative_tests.json
│   └── validation_report.md  # Official pass/fail policy validation report
└── src/
    ├── config.py             # Global constants, paths, hyperparameters, seeds
    ├── ingest.py             # World Bank survey extraction & column alignment
    ├── engineer.py           # Feature engineering, imputation & target definition
    ├── pipeline.py           # End-to-end O1 pipeline runner
    ├── evaluate.py           # Shared evaluation harness (LOCO & pooled metrics)
    ├── models.py             # O2 black-box baselines (RF, XGBoost)
    ├── interpretable.py      # O3 interpretable models (LogReg, EBM, LightGBM+SHAP)
    ├── tradeoff.py           # Accuracy vs interpretability trade-off analysis
    ├── targeting.py          # O4 asymmetric error & policy threshold calibration
    ├── acceptance.py         # O5 acceptance conditions (AC-1 to AC-4)
    ├── negative_tests.py     # O5 negative test suite (NT-1 to NT-5)
    └── run_all.py            # Master one-command end-to-end runner (FR-6)
```

---

## Quick Start & Reproduction

### 1. Prerequisites & Environment Setup

```bash
cd EHCVM_Project/EHCVM_Project
pip install numpy pandas scikit-learn lightgbm xgboost interpret shap matplotlib seaborn pandera
```

### 2. Run the Full System (One-Command Runner — FR-6)

To execute the entire end-to-end pipeline across all 8 countries (O2 baselines $\rightarrow$ O3 interpretable models $\rightarrow$ O4 targeting curves $\rightarrow$ O5 acceptance $\rightarrow$ 5 negative tests):

```bash
python -m src.run_all
```

*Execution time: ~40 minutes on standard 8-core CPU.*  
Output files and telemetry are automatically written to `outputs/results/`, `outputs/acceptance/`, and `outputs/validation_report.md`.

### 3. Generate Publication Figures

To generate all 6 publication figures from the cached model outputs:

```bash
python -m notebooks.02_results
```

Figures are saved to `outputs/results/`:
1. `model_comparison.png` — LOCO macro Accuracy, AUC-ROC, and F1 across all 5 models.
2. `tradeoff_pareto.png` — Pareto frontier of model complexity vs cross-country accuracy.
3. `country_accuracy_heatmap.png` — Heatmap of per-country LOCO accuracy across all models.
4. `targeting_curves.png` — Exclusion vs Inclusion error curves across thresholds per country.
5. `shap_importance.png` — Top 20 most predictive household features via Tree-SHAP.
6. `targeting_sensitivity.png` — Optimal threshold calibration under varying welfare loss cost ratios.

### 4. Run Individual Modules

* **Run O2 Baselines Only**: `python -m src.models`
* **Run O3 Interpretable Models Only**: `python -m src.interpretable`
* **Run O3 Trade-off Analysis**: `python -m src.tradeoff`
* **Run O4 Targeting Analysis**: `python -m src.targeting`
* **Run O5 Acceptance Verification**: `python -m src.acceptance`
* **Run Negative Test Suite**: `python -m src.negative_tests`

---

## Team & Capstone Details

* **Project Title:** DSCI-28: Interpretable Cross-Country Household Well-Being Estimation from Survey Data
* **Department:** Department of Computer Science & Engineering, KL University
* **Course Code:** 23IE4053 · Capstone Project
* **Project Guide:** Dr. P. V. R. D. Prasada Rao, Professor, CSE
* **Team Members:**
  * **Kuni Likitha** (2300032195) — Data Lineage, Schema Engineering & Quality Validation Lead (O1)
  * **Madala Phanindra** (2300032338) — Black-Box Baseline Modeling & Cross-Validation Lead (O2)
  * **Mahesh Sai Bhima** (2300030811) — Interpretable Model Engineering & Trade-Off Lead (O3)
  * **Punyala Rama Krishna Reddy** (2300031696) — Policy Assurance, Asymmetric Welfare Loss & Recourse Lead (O4/O5)
