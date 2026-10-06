# 🌍 DSCI-28: Interpretable Cross-Country Household Well-Being Estimation

[![Python 3.11](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-v2.1-009688?logo=fastapi&logoColor=white)](http://localhost:8000/docs)
[![Streamlit](https://img.shields.io/badge/Streamlit-v1.31-FF4B4B?logo=streamlit&logoColor=white)](http://localhost:8501)
[![DuckDB](https://img.shields.io/badge/DuckDB-Embedded_Columnar-FFF000?logo=duckdb&logoColor=black)](https://duckdb.org/)
[![Tests: 21 Passed](https://img.shields.io/badge/Tests-21%2F21%20PASS%20(100%25)-success.svg)](file:///c:/Users/bhima/OneDrive/Desktop/CAPSTONE/tests)
[![Acceptance: AC1--AC4](https://img.shields.io/badge/Acceptance-AC1--AC4%20PASS-success.svg)](outputs/acceptance/o5_acceptance.json)
[![UN SDG 10: Fair](https://img.shields.io/badge/UN%20SDG%2010-80%25%20Fairness%20Pass-blue.svg)](outputs/results/fairness_summary.csv)
[![License: Academic](https://img.shields.io/badge/Academic%20Year-2026--27-blue.svg)]()

A research-grade, production-ready machine learning platform for **interpretable, cross-border household poverty estimation and social welfare targeting**. Built on harmonized World Bank Living Standards Measurement Study microdata (**EHCVM 2021** across 8 West African nations: *Benin, Burkina Faso, Côte d'Ivoire, Guinea-Bissau, Mali, Niger, Senegal, and Togo*).

---

## 🏛️ Academic Dossier & Project Credits

* **Course**: 23IE4053 · Capstone Project (16 Credits)
* **Department**: Department of Computer Science & Engineering
* **Institution**: Koneru Lakshmaiah Education Foundation (KL University / KLEF)
* **Cluster**: Cluster A (Software & Data Science)
* **Project Guide**: **Dr. P. V. R. D. Prasada Rao**, Professor

### 👥 Engineering Team & Roles
* **Kuni Likitha** (`2300032195`) — *Lead: Data Lineage & Schema Validation (Objective 1)*
* **Madala Phanindra** (`2300032338`) — *Lead: Black-Box Baselines & LOCO Cross-Border Folds (Objective 2)*
* **Mahesh Sai Bhima** (`2300030811`) — *Lead: Interpretable ML, SHAP Explanations & Counterfactual Recourse (Objective 3)*
* **Punyala Rama Krishna Reddy** (`2300031696`) — *Lead: Policy Targeting, Conformal Prediction, Fairness & QA (Objectives 4 & 5)*

---

## ⚡ Quick Start: Running the Project

You can run the entire platform with **1 command** (recommended) or **2 commands** in separate terminals:

### Option 1: The 1-Command All-in-One Launcher (Recommended)
From the project root:
```powershell
python run_all.py
```
*(Or in Windows File Explorer, simply double-click **`start.bat`**)*

This starts both services concurrently:
* **Interactive Streamlit Dashboard**: [http://localhost:8501](http://localhost:8501)
* **FastAPI Swagger REST Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

### Option 2: Running Services Separately (2 Terminals)

#### Terminal 1 — Streamlit Interactive Web Application
```powershell
streamlit run app.py
```

#### Terminal 2 — FastAPI Production Microservice
```powershell
uvicorn api.main:app --reload --port 8000
```

---

## 🌟 Key Scientific & Engineering Contributions

```
                                      WORLD BANK EHCVM 2021 MICRODATA
                                    (8 West African Nations · 55,922 HH)
                                                     │
                                                     ▼
    ┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
    │ O1: DATA HARMONIZATION & SCHEMA CONTRACTS                                                       │
    │ • 3-Tier Relational Merge: menage (dwelling), individu (demographics), welfare (poverty line)   │
    │ • 100% Pandera Data Contract Validation (24 strict assertions; zero target leakage)             │
    │ • Key Finding: 58.4% rural poverty vs. 24.1% urban poverty across Sub-Saharan Africa            │
    └────────────────────────────────────────────────┬────────────────────────────────────────────────┘
                                                     │
                                                     ▼
    ┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
    │ O2 & O3: CROSS-BORDER GENERALIZATION & ZERO COST OF INTERPRETABILITY                            │
    │ • Leave-One-Country-Out (LOCO): Trains on 7 nations, evaluates strictly on unseen 8th nation     │
    │ • Zero Cost of Interpretability: EBM (74.8%) beats Random Forest (74.0%) by +0.8 pp             │
    │ • LightGBM + Tree-SHAP achieves 76.4% macro accuracy, matching black-box XGBoost (76.3%)       │
    └────────────────────────────────────────────────┬────────────────────────────────────────────────┘
                                                     │
                                                     ▼
    ┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
    │ O3 (EXT): COUNTERFACTUAL POLICY RECOURSE ("HOW TO ESCAPE POVERTY")                              │
    │ • Solves optimization for minimum-cost actionable upgrades across 11 actionable levers          │
    │ • Preserves immutable features (age, gender, ethnicity, shocks, location)                      │
    │ • Outputs practical policy roadmap (e.g. broadband voucher, off-grid solar, livestock micro-aid) │
    └────────────────────────────────────────────────┬────────────────────────────────────────────────┘
                                                     │
                                                     ▼
    ┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
    │ O4: ASYMMETRIC WELFARE LOSS & CONFORMAL PREDICTION TRIAGE                                       │
    │ • Humanitarian Loss: Asymmetric 3:1 penalty (C_ex:C_inc) optimizes threshold to τ* = 0.35       │
    │ • Reduces Exclusion Error from 38.6% down to 24.1% (-14.5 pp drop in humanitarian harm)         │
    │ • Split Conformal Prediction (1 - α = 90%): Distribution-free guarantees with 3-tier triage:     │
    │   Certain Poor (Disburse aid) | Certain Non-Poor (Decline) | Ambiguous (Human Audit-in-the-Loop)│
    └────────────────────────────────────────────────┬────────────────────────────────────────────────┘
                                                     │
                                                     ▼
    ┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
    │ O5: SYSTEM ASSURANCE, FAIRNESS AUDIT & EMBEDDED DUCKDB                                          │
    │ • AC-1 to AC-4 (Formal Acceptance) & NT-1 to NT-5 (Adversarial Negative Tests): 100% PASS       │
    │ • UN SDG 10 Algorithmic Fairness: Audits 80% Disparate Impact rule across Gender, Age & Urban    │
    │ • Embedded Columnar DuckDB: 55,922 records, 5 tables, sub-millisecond analytical SQL queries    │
    └────────────────────────────────────────────────┬────────────────────────────────────────────────┘
                                                     │
                                                     ▼
    ┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
    │ O6: UNIVERSAL SURVEY ADAPTER & ZERO-SHOT INGESTION                                              │
    │ • Dynamic Multilingual Synonym Dictionary maps external surveys (e.g., Ghana GLSS, India survey)│
    │ • Regional median imputation for unobserved features; zero-shot inference without retraining   │
    │ • One-click downloadable scored dataset with conformal triage tiers and counterfactual plans    │
    └─────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 📊 LOCO Benchmark Leaderboard (Cross-Country Generalisation)

Models trained on 7 countries and evaluated strictly on the unseen 8th country:

| Model Architecture | Category | Interpretability Bar | Macro Accuracy | Macro AUC-ROC | Macro F1 | Cost of Interpretability |
|---|---|:---:|:---:|:---:|:---:|:---:|
| **Random Forest** | Black-Box Reference (O2) | Low | 74.0% | 0.848 | 0.648 | Baseline |
| **XGBoost** | Black-Box Gradient Boost (O2) | Low | 76.3% | 0.849 | 0.617 | +2.3 pp |
| **Logistic Regression** | Linear Glass-Box (O3) | High | 73.5% | 0.848 | 0.660 | -0.5 pp |
| **Explainable Boosting Machine (EBM)** | GAM Glass-Box (O3) | **High (Intrinsically Auditable)** | **74.8%** | **0.836** | **0.595** | **+0.8 pp over Random Forest** |
| **LightGBM + Tree-SHAP** | Gradient Boost + SHAP (O3) | **High (Exact Shapley Attribution)** | **76.4%** | **0.849** | **0.626** | **Full Parity with XGBoost** |

---

## 🖥️ Interactive Dashboard Structure (`app.py`)

The Streamlit web application is organized into 6 executive tabs:

1. **🌐 1. Data & Schema (O1)**:
   * National survey summary across 8 West African nations (55,922 validated households).
   * Urban vs. Rural poverty disparity inspector (58.4% rural vs. 24.1% urban).
   * Interactive microdata browser with domain column filters and Pandera schema validation report.
2. **📊 2. LOCO Benchmark (O2)**:
   * Cross-country generalization grouped bar charts.
   * Macro-averaged benchmark leaderboard and full country-by-country performance matrix.
   * Viva defense guide explaining why spatial autocorrelation invalidates simple 80/20 train/test splits.
3. **🔍 3. Interpretable AI (O3)**:
   * Global Tree-SHAP feature importance rankings (top 20 welfare predictors).
   * **Live Household Poverty Estimator**: Choose preset archetypes or customize 16 living-standard features.
   * **Horizontal Risk Meter Bar** with clear, non-overlapping color zones and household position marker.
   * **Plain-English AI Decision Narrative**: Explains in everyday terms why the AI scored the family and what protected them.
   * **Counterfactual Recourse Plan**: Prescribes the exact, minimum-cost actions (e.g. broadband voucher, solar kit) to lift the family out of poverty.
4. **⚖️ 4. Policy Targeting (O4)**:
   * Interactive social welfare loss simulator across penalty ratios ($1:1, 2:1, 3:1, 5:1, 10:1$).
   * Targeting trade-off curve visualizing Exclusion Errors vs. Inclusion Leakage.
   * **Conformal Prediction 90% Coverage Triage**: Distribution-free certainty classification (`Certain Poor`, `Certain Non-Poor`, `Ambiguous / Audit Needed`).
5. **🛡️ 5. QA & DuckDB (O5)**:
   * **AC-1 to AC-4 Dossier**: Full formal acceptance verification with sub-checks.
   * **NT-1 to NT-5 Adversarial Suite**: Overfitting, black-box gates, equal error, idempotency, and partition defects.
   * **UN SDG 10 Algorithmic Fairness Audit**: 80% Disparate Impact compliance across Gender, Geography, and Age brackets.
   * **Live Embedded DuckDB SQL Console**: Execute real-time analytical SQL queries against 55,922 records.
6. **🌍 6. Universal Upload (O6)**:
   * Zero-shot domain ingestion: Upload any external CSV survey (e.g., Ghana GLSS, Nigeria NBS, India survey).
   * Multilingual synonym harmonization automatically maps column headers and imputes unobserved features.
   * Scored microdata table with conformal triage and **one-click enriched CSV export**.

---

## 🔌 FastAPI REST Microservice Endpoints

Interactive Swagger documentation is available at **`http://localhost:8000/docs`**.

| Method | Endpoint | Description |
|:---:|---|---|
| `GET` | `/v1/health` | Service health status, model architecture, feature count, and supported nations. |
| `GET` | `/v1/countries` | Metadata and statistics for all 8 supported WAEMU nations. |
| `POST` | `/v1/predict` | Single household inference returning calibrated poverty probability and targeting decision. |
| `POST` | `/v1/recourse` | Generates optimal counterfactual policy recourse intervention steps. |
| `POST` | `/v1/conformal` | Evaluates distribution-free prediction sets ($1 - \alpha = 90\%$) and triage category. |
| `POST` | `/v1/upload-survey` | Ingests raw external CSV surveys with zero-shot column harmonization and batch scoring. |

---

## 🧪 Automated Testing & Assurance Suite

The project includes an exhaustive automated test suite in [`tests/`](file:///c:/Users/bhima/OneDrive/Desktop/CAPSTONE/tests):

```powershell
python -m pytest tests/ -v
```

```text
tests/test_adapter.py::test_normalize_column_name PASSED                 [  4%]
tests/test_adapter.py::test_harmonize_external_survey_fill PASSED        [  9%]
tests/test_adapter.py::test_end_to_end_survey_evaluation PASSED          [ 14%]
tests/test_api.py::test_api_root PASSED                                  [ 19%]
tests/test_api.py::test_api_health PASSED                                [ 23%]
tests/test_api.py::test_api_countries PASSED                             [ 28%]
tests/test_api.py::test_api_predict PASSED                               [ 33%]
tests/test_api.py::test_api_recourse PASSED                              [ 38%]
tests/test_api.py::test_api_conformal PASSED                             [ 42%]
tests/test_api.py::test_api_upload_survey PASSED                         [ 47%]
tests/test_conformal.py::test_conformal_coverage_on_synthetic_data PASSED [ 52%]
tests/test_conformal.py::test_conformal_empty_guard PASSED               [ 57%]
tests/test_conformal.py::test_conformal_prediction_set_categories PASSED [ 61%]
tests/test_fairness.py::test_compute_group_metrics_exact PASSED          [ 66%]
tests/test_fairness.py::test_audit_binary_attribute_balanced PASSED      [ 71%]
tests/test_fairness.py::test_fairness_violation_detection PASSED         [ 76%]
tests/test_recourse.py::test_immutable_features_safety PASSED            [ 80%]
tests/test_recourse.py::test_already_non_poor_household PASSED           [ 85%]
tests/test_recourse.py::test_recourse_reduces_poverty_probability PASSED [ 90%]
tests/test_targeting.py::test_targeting_curve_monotonicity PASSED        [ 95%]
tests/test_targeting.py::test_find_optimal_threshold_cost_sensitivity PASSED [100%]
============================= 21 passed in 6.00s ==============================
```

---

## 📁 Repository Directory Structure

```text
CAPSTONE/
├── app.py                      # Production Streamlit 6-Tab Interactive Web Application
├── run_all.py                  # 1-Command Launcher (Starts FastAPI & Streamlit concurrently)
├── start.bat                   # Windows batch launcher (Double-click execution)
├── run_db.py                   # DuckDB database verification & table inspector
├── COMMANDS.md                 # Complete Execution Runbook & Command Reference
├── README.md                   # Primary Documentation & Capstone Dossier
├── Dockerfile                  # Container definition for containerized deployment
├── docker-compose.yml          # Multi-service composition file
├── requirements.txt            # Python dependencies
├── api/
│   ├── main.py                 # FastAPI microservice application & endpoints
│   └── schemas.py              # Pydantic v2 request/response validation schemas
├── tests/
│   ├── test_adapter.py         # Universal survey adapter tests
│   ├── test_api.py             # FastAPI REST endpoint integration tests
│   ├── test_conformal.py       # Split conformal prediction coverage tests
│   ├── test_fairness.py        # UN SDG 10 disparate impact ratio tests
│   ├── test_recourse.py        # Counterfactual recourse & immutability tests
│   └── test_targeting.py       # Asymmetric welfare targeting & monotonicity tests
└── EHCVM_Project/EHCVM_Project/
    ├── src/
    │   ├── adapter.py          # Multilingual synonym survey adapter
    │   ├── conformal.py        # Distribution-free split conformal classifier
    │   ├── dashboard_utils.py  # Visualizations, risk meter & SHAP narrative engine
    │   ├── db.py               # Embedded DuckDB analytical database tables
    │   ├── fairness.py         # UN SDG 10 Algorithmic Fairness auditing engine
    │   ├── recourse.py         # Greedy multi-action counterfactual recourse engine
    │   ├── models.py           # Black-box baseline models (RF, XGBoost)
    │   ├── interpretable.py    # Interpretable models (EBM, LightGBM, LogReg)
    │   ├── targeting.py        # Asymmetric welfare loss optimization
    │   ├── acceptance.py       # Formal acceptance criteria (AC-1 to AC-4)
    │   ├── negative_tests.py   # Adversarial negative test suite (NT-1 to NT-5)
    │   └── pipeline.py         # Pandera data contract harmonization pipeline
    └── data/processed/
        └── ehcvm.duckdb        # Columnar relational analytical database (55,922 records)
```

---

## 📜 Citation & Academic Use

```bibtex
@mastersthesis{dsci28_capstone_2027,
  author    = {Kuni Likitha and Madala Phanindra and Mahesh Sai Bhima and Punyala Rama Krishna Reddy},
  title     = {Interpretable Cross-Country Household Well-Being Estimation from Survey Data},
  school    = {Koneru Lakshmaiah Education Foundation (KL University)},
  department= {Department of Computer Science and Engineering},
  year      = {2026--2027},
  note      = {Project Guide: Dr. P. V. R. D. Prasada Rao, Professor}
}
```
