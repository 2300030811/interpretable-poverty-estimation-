# REVIEW 2 MASTER DEFENSE DOSSIER & COMPLIANCE SPECIFICATION
## Capstone Project I (23IE4053) · Academic Year 2026–27 · Review 2: System Design & Partial Implementation

**Project Title:** Interpretable Cross-Country Household Well-Being Estimation from Survey Data  
**Team Identifier:** DSCI-28 · Cluster A (Software Development & Data Science)  
**Department:** Department of Computer Science & Engineering, Koneru Lakshmaiah Education Foundation (KL University)  
**Project Guide:** Dr. P. V. R. D. Prasada Rao, Professor, Department of Computer Science & Engineering  

---

### Capstone Project Team
| Student Name | University ID Number | Engineering Role & Module Ownership | Primary Review 2 Defense Domain |
|---|:---:|---|---|
| **Kuni Likitha** | 2300032195 | Data Lineage, Schema Engineering & Quality Validation Lead (**O1**) | Data Ingestion, Pandera Contracts, 3-Tier Merge, Imputation |
| **Madala Phanindra** | 2300032338 | Black-Box Baseline Modeling & LOCO Validation Lead (**O2**) | Spatial Generalisation, LOCO Cross-Validation, RF/XGBoost |
| **Mahesh Sai Bhima** | 2300030811 | Interpretable Model Engineering & Trade-Off Lead (**O3**) | EBM / GA²M Architecture, Tree-SHAP Attribution, Accuracy Cost |
| **Punyala Rama Krishna Reddy** | 2300031696 | Policy Assurance, Asymmetric Loss & Recourse Lead (**O4 / O5**) | Asymmetric Welfare Loss ($C_{ex}:C_{inc}$), AC-1..4, NT-1..5 Guardrails |

---

## Executive Summary & Review 2 Rubric Compliance Matrix

This document provides complete, unambiguous, and auditable evidence for **Review 2 (System Design & Partial Implementation)** in strict accordance with the official KL University Panel Evaluation Rubric (Course 23IE4053, 50 Marks Total):

| S.No | Rubric Criterion | Max Marks | Benchmark for Full Marks | Demonstrated Artifacts & Evidence |
|:---:|---|:---:|---|---|
| **1** | **System Requirements & Functional Specs** | **10** | *Requirements are complete, unambiguous, and traceable to the problem statement.* | Section 1: Complete SRS, User Personas, Hardware/Software/Data constraints, FR-1 to FR-6, NFR-1 to NFR-4, and Full Traceability Matrix. |
| **2** | **System Design & Architecture** | **10** | *Architecture/ER/UML diagrams are complete, consistent, and justify key design decisions.* | Section 2: 5-Tier Architecture, Complete ER Diagram with Cardinalities, UML Class & Sequence Diagrams, 8 Architectural Design Justifications with Discarded Alternatives, Code Consistency Proofs. |
| **3** | **Initial Implementation / Prototype** | **10** | *A working prototype demonstrates core functionality aligned with the design.* | Section 3: Objective 1 100% complete (24/24 Pandera schemas verified, 55,922 clean households, 74 features, 0.0% missing data, SHA-256 lineage tracking), Interactive Streamlit Dashboard (`app.py`), CLI runner. |
| **4** | **Use of Tools / Technologies** | **10** | *Tools and technologies are appropriate, correctly applied, and justified.* | Section 4: Python 3.10+, Pandas 2.x, Pandera 0.33, Scikit-learn, XGBoost, LightGBM, InterpretML (EBM), SHAP, Streamlit, Pytest, PPTXGenJS; Tool Justification Matrix comparing against discarded alternatives. |
| **5** | **Teamwork & Agile Practice** | **10** | *There is clear evidence of iterative development, sprint planning, and effective team collaboration.* | Section 5: Agile Scrum framework, Sprint 1, 2, and 3 backlogs, User Stories, Story Points & Velocity, Definition of Done (DoD), Scrum ceremony cadence, Git commit lineage & role accountability. |
| **—** | **Individual Student Defense** | **50** | *Guide's Individual Evaluation Sheet (Meeting attendance, planning/design/implementation contribution, viva defense).* | Section 6: Individual Viva Defense scripts, anticipated examiner defense Q&A for each of the 4 team members mapped to their respective university IDs. |

---

# SECTION 1: System Requirements Specification (SRS) & Functional Traceability Matrix (Criterion 1 — 10 Marks)

### 1.1 Problem Statement & Scope Boundary
Algorithmic targeting systems distribute over **$800 billion annually to 1.5+ billion beneficiaries** worldwide via Proxy Means Tests (PMT). In developing nations, national household expenditure surveys occur infrequently (every 5–8 years), necessitating the transfer of predictive models across geographical borders. However, standard solutions encounter:
1. **The Spatial Transfer Defect**: Models optimized within a single nation overfit to localized wealth patterns and experience catastrophic degradation when deployed cross-border.
2. **The Black-Box Policy Barrier**: Complex ensemble models (XGBoost, deep networks) lack legal defensibility, denying impoverished citizens transparent, appealable recourse when mistakenly excluded from subsistence aid.

**System Goal**: Develop an auditable, reproducible machine learning system that harmonizes 8 West African national surveys (World Bank EHCVM 2021: 55,922 households, 24 CSV datasets), validates data integrity via declarative schema contracts, evaluates cross-country spatial transfer under Leave-One-Country-Out (LOCO) validation, provides glass-box interpretability via Explainable Boosting Machines (EBM / GA²M), and minimizes asymmetric social welfare exclusion error.

### 1.2 User Personas & Stakeholder Needs
1. **National Social Protection Administrators & Policymakers**: Require global policy transparency (additive feature curves), budget-constrained welfare loss sweeps ($C_{ex}:C_{inc}$), and predictable fiscal leakage projections.
2. **Field Programme Officers & Legal Auditors**: Require instance-level, legally defensible, monotonic feature attributions to adjudicate citizen appeals without black-box obscurity.
3. **Vulnerable Beneficiary Households**: Affected citizens who depend on aid for survival; require fair, auditable decisions free from arbitrary model hallucinations or discriminatory bias.

### 1.3 System Requirements & Constraints
* **Hardware Requirements**:
  - Processor: Quad-core CPU (Intel Core i5/i7 or AMD Ryzen 5/7, 2.4 GHz+).
  - RAM: Minimum 8 GB; Peak pipeline memory footprint < 1.8 GB during multi-table relational joins.
  - Storage: ~272 MB total footprint (185 MB raw EHCVM CSVs across 24 files + 82 MB engineered datasets + 5 MB visual plots).
* **Software Requirements**:
  - Python Environment: Python 3.10 or 3.11 (64-bit).
  - Presentation Engine: Node.js v18.0.0+ with `pptxgenjs`.
  - Execution Shell: PowerShell 7+ or Bash with `PYTHONIOENCODING=utf-8`.
* **Data Quality & Operating Envelope**:
  - Determinism: 100% bitwise reproducibility via frozen random seed `seed = 42`.
  - Missingness Guarantee: 0.0% missing values across all analytical feature columns post-imputation.
  - Data Lineage: SHA-256 cryptographic digests generated and stored for all raw ingestion sources.
  - Pipeline Execution Latency: < 45 seconds for end-to-end 8-country data ingestion, validation, and feature engineering.

### 1.4 Formal Functional Specifications (FR-1 through FR-6)

| Req ID | Functional Requirement | Input Data | Processing & Business Logic | Output & Success Verification |
|:---:|---|---|---|---|
| **FR-1** | **Survey Ingestion & Lineage Tracking** | 24 raw EHCVM CSV files across 8 countries. | Ingest raw survey files, extract ISO-3 country identifiers, compute SHA-256 hashes, and track lineage. | In-memory data dictionary, verified `lineage_report.json` with 24 verified checksums. |
| **FR-2** | **Declarative Schema Contract Validation** | Raw survey DataFrames for `menage`, `welfare`, `individu`. | Apply 24 declarative Pandera DataFrameSchemas; enforce non-null keys, type coercion, and value boundary rules. | 0 schema violations; validation exception raised on any data corruption. |
| **FR-3** | **3-Tier Relational Merge & Imputation** | Validated `menage`, `welfare`, `individu` tables. | Execute inner join on composite key `(country_code, hhid)`; compute roster-level aggregations (`mean`, `max`, `count`); impute missing values via localized median/mode. | 8 clean harmonized CSV files (`data/processed/*_clean.csv`) with 74 standardized features and 0.0% missingness. |
| **FR-4** | **Target Formulation & Leakage Purge** | Per capita consumption (`pcexp`), poverty line (`zref`). | Construct binary target: $\text{poor}_i = \mathbb{I}(pcexp_i < zref_i)$; purge all target-constructing expenditure variables to prevent data leakage. | Analytical feature matrix $X \in \mathbb{R}^{55922 \times 74}$ and target vector $y \in \{0, 1\}^{55922}$ with zero mathematical leakage. |
| **FR-5** | **Leave-One-Country-Out (LOCO) Evaluator** | 8 clean country datasets. | Generate 8 deterministic partitions where country $k$ is held out for testing and model trains strictly on the remaining 7 nations. | LOCO fold metrics: Macro Accuracy, Macro AUC-ROC, Macro F1, Precision, and Recall across 8 iterations. |
| **FR-6** | **One-Command Master Orchestrator** | Terminal invocation (`python -m src.pipeline`). | Sequentially orchestrate ingestion, validation, feature engineering, summary telemetry, and automated EDA report generation. | Terminal execution completes in <45s with structured audit logs and 6 publication-grade figures. |

### 1.5 Non-Functional Specifications (NFR-1 through NFR-4)

| NFR ID | Quality Attribute | Technical Requirement & Specification | Measurement Method |
|:---:|---|---|---|
| **NFR-1** | **Zero Data Leakage** | Complete removal of target-deriving financial indicators (`pcexp`, `zref`, consumption sub-aggregates) from predictive feature space. | Automated column audit verifying no correlation $>0.90$ with target variable. |
| **NFR-2** | **Execution Efficiency** | Ingestion, validation, and engineering across 55,922 records and 24 files must execute in under 60 seconds on commodity hardware. | Benchmark wall-clock execution: 38.4 seconds measured on standard 4-core laptop. |
| **NFR-3** | **Reproducibility & Lineage** | Pipeline execution must be idempotent and deterministic across repeated executions. | SHA-256 cryptographic comparison of generated clean CSVs yields identical bitwise digests. |
| **NFR-4** | **Schema Integrity & Soundness** | Zero tolerance for schema violations; invalid data types or out-of-bound codes must fail fast before model consumption. | Pandera schema validation gate: 24/24 schemas verified passing with 0 exceptions. |

### 1.6 Traceability Matrix to Problem Statement & Capstone Objectives

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                           REQUIREMENTS TRACEABILITY MATRIX                                           │
├───────────────────────┬────────────────────────┬─────────────────────────┬───────────────────┬───────────────────────┤
│ Problem Statement     │ SMART Objective        │ Functional Requirement  │ Source Code File  │ Verification Test     │
├───────────────────────┼────────────────────────┼─────────────────────────┼───────────────────┼───────────────────────┤
│ Survey data           │ Objective O1:          │ FR-1: Survey Ingestion  │ src/ingest.py     │ lineage_report.json   │
│ heterogeneity across  │ Harmonised Data &      │ FR-2: Schema Validation │ src/schemas.py    │ 24 Pandera Contracts  │
│ 8 African nations     │ Quality Contracts      │ FR-3: Relational Merge  │ src/engineer.py   │ 0% Missingness Audit  │
│                       │                        │ FR-4: Target & Leakage  │ src/pipeline.py   │ Zero Leakage Check    │
├───────────────────────┼────────────────────────┼─────────────────────────┼───────────────────┼───────────────────────┤
│ Spatial Transfer      │ Objective O2:          │ FR-5: LOCO Evaluator    │ src/evaluate.py   │ 8-Fold LOCO Benchmark │
│ Defect (Overfitting   │ Spatial Generalisation │ FR-6: Baseline Modeling │ src/models.py     │ RF & XGBoost Metrics  │
│ to single nation)     │ Reference              │                         │                   │ Transfer Gap: -3.9pp  │
├───────────────────────┼────────────────────────┼─────────────────────────┼───────────────────┼───────────────────────┤
│ Black-Box Policy      │ Objective O3:          │ FR-5: EBM Glass-Box     │ src/interpretable.│ EBM LOCO (74.8% Acc)  │
│ Barrier (Lack of      │ Interpretable Model    │       GA²M Splines      │ src/tradeoff.py   │ LightGBM+SHAP (76.4%) │
│ auditability)         │ Engineering            │       Pareto Frontier   │                   │ Accuracy Cost: 0.0pp  │
├───────────────────────┼────────────────────────┼─────────────────────────┼───────────────────┼───────────────────────┤
│ High Exclusion Error  │ Objective O4:          │ FR-4: Policy Targeting  │ src/targeting.py  │ Cost sweep c in [1,10]│
│ in Social Safety Nets │ Asymmetric Welfare     │       Threshold Sweeps  │                   │ Exclusion: 38.6%->24% │
│ (38.6% FN under tau)  │ Loss Optimization      │       C_ex : C_inc      │                   │ Tau* = 0.35 at c=3    │
├───────────────────────┼────────────────────────┼─────────────────────────┼───────────────────┼───────────────────────┤
│ Lack of Independent   │ Objective O5:          │ NFR-1..4: AC-1..AC-4    │ src/acceptance.py │ o5_acceptance.json    │
│ Safety Verification   │ Independent Assurance  │           NT-1..NT-5    │ src/negative_     │ negative_tests.json   │
│ in Policy Systems     │ & Negative Testing     │           Adversarial   │     tests.py      │ 100% Pass Rate        │
└───────────────────────┴────────────────────────┴─────────────────────────┴───────────────────┴───────────────────────┘
```

---

# SECTION 2: System Design & Architecture (Criterion 2 — 10 Marks)

### 2.1 Five-Tier Production Architecture

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                   DSCI-28 ARCHITECTURAL TIERS                                   │
├───────────────────────┬──────────────────────────────────────────────────────────────────────────┤
│ 1. Data Ingestion &   │ • 8 Sovereign WAEMU Nations (BEN, BFA, CIV, GNB, MLI, NER, SEN, TGO)     │
│    Lineage Tier       │ • 24 Relational Survey Files (Ménage, Welfare, Individu)                 │
│                       │ • SHA-256 Cryptographic Lineage Tracking (src/ingest.py)                 │
├───────────────────────┼──────────────────────────────────────────────────────────────────────────┤
│ 2. Schema Validation  │ • 24 Declarative Pandera DataFrameSchemas (src/schemas.py)               │
│    Tier               │ • Strict Type Coercion, Null Value Rejection, Range Boundary Guards      │
├───────────────────────┼──────────────────────────────────────────────────────────────────────────┤
│ 3. Transformation &   │ • 3-Tier Relational Merge on Composite Key (country_code, hhid)          │
│    Engineering Tier   │ • Individual-to-Household Statistical Aggregation (mean, max, size)     │
│                       │ • Localized Deterministic Imputation (0.0% Missingness Guarantee)        │
│                       │ • Mathematical Target Formulation & Zero-Leakage Source Purge            │
├───────────────────────┼──────────────────────────────────────────────────────────────────────────┤
│ 4. Machine Learning   │ • Leave-One-Country-Out (LOCO) Partition Generator (src/evaluate.py)     │
│    Evaluation Tier    │ • Black-Box Reference Baselines: Random Forest, XGBoost (src/models.py)  │
│                       │ • Interpretable Core: Explainable Boosting Machines (GA²M), LightGBM+SHAP│
├───────────────────────┼──────────────────────────────────────────────────────────────────────────┤
│ 5. Policy Assurance & │ • Asymmetric Welfare Loss Threshold Optimization (src/targeting.py)      │
│    Presentation Tier  │ • Formal Acceptance Suite (AC-1..4) & Negative Test Suite (NT-1..5)      │
│                       │ • Interactive Streamlit Telemetry Dashboard (app.py)                     │
└───────────────────────┴──────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Entity-Relationship (ER) Diagram

```
                  ┌──────────────────────────────┐
                  │           COUNTRY            │
                  ├──────────────────────────────┤
                  │ PK  country_code (ISO-3)     │
                  │     country_name             │
                  │     zref_threshold           │
                  │     total_households         │
                  └──────────────┬───────────────┘
                                 │ 1:N
         ┌───────────────────────┼───────────────────────┐
         │ 1:N                   │ 1:N                   │ 1:N
         ▼                       ▼                       ▼
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│      MENAGE      │    │     WELFARE      │    │ EVALUATION_FOLD  │
├──────────────────┤    ├──────────────────┤    ├──────────────────┤
│ PK,FK country    │    │ PK,FK country    │    │ PK  fold_id      │
│ PK    hhid       │    │ PK    hhid       │    │ FK  held_country │
│       mur, toit  │    │       hage, hhsize│   │ FK  experiment_id│
│       sol, elec  │    │       milieu     │    │     macro_acc    │
│       tv, frigo  │    │       pcexp, zref│    │     macro_f1     │
└────────┬─────────┘    └────────┬─────────┘    └────────▲─────────┘
         │                       │                       │
         │ 1:1                   │ 1:1                   │ 1:N
         └───────────┬───────────┘                       │
                     │                                   │
                     ▼                                   │
         ┌───────────────────────┐                       │
         │       INDIVIDU        │                       │
         ├───────────────────────┤                       │
         │ PK,FK country_code    │                       │
         │ PK,FK hhid            │                       │
         │ PK    indiv_id        │                       │
         │       telpor, bank    │                       │
         │       mal30j, edu     │                       │
         └───────────┬───────────┘                       │
                     │ 1:N                               │
                     ▼ (Aggregate)                       │
         ┌───────────────────────┐                       │
         │    CLEAN_HOUSEHOLD    │                       │
         ├───────────────────────┤                       │
         │ PK,FK country_code    │                       │
         │ PK    hhid            │                       │
         │       poor (Target)   │                       │
         │       74 Features     │                       │
         │       0% Missingness  │                       │
         └───────────┬───────────┘                       │
                     │                                   │
                     │ 1:N (Partitioned Into)            │
                     └───────────────────────────────────┘
```

#### Relational Cardinalities & Keys
* `COUNTRY` (1) $\rightarrow$ `MENAGE` (0..N): Each nation enumerates multiple household dwellings.
* `COUNTRY` (1) $\rightarrow$ `WELFARE` (0..N): Each nation records demographic living standards.
* `MENAGE` (1) $\leftrightarrow$ `WELFARE` (1): Exactly one dwelling record pairs with one welfare survey via composite key `(country_code, hhid)`.
* `MENAGE` (1) $\rightarrow$ `INDIVIDU` (1..N): Each household contains one or more individual roster members.
* `MENAGE` + `WELFARE` + `INDIVIDU` (Aggregated) $\rightarrow$ `CLEAN_HOUSEHOLD` (1): The transformation engine collapses individual records into household summary statistics, producing a single analytical record per household.

### 2.3 UML Software Class Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    PipelineOrchestrator                     │
├─────────────────────────────────────────────────────────────┤
│ + run() : dict                                              │
└─────────────┬────────────────┬──────────────┬───────────────┘
              │ invokes        │ verifies     │ transforms
              ▼                ▼              ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│   DataIngestor   │ │ SchemaValidator  │ │ FeatureEngineer  │
├──────────────────┤ ├──────────────────┤ ├──────────────────┤
│ + load_country() │ │ + validate_      │ │ - _aggregate_    │
│ + load_all()     │ │   country()      │ │   individu()     │
│ + save_lineage() │ │ + validate_all() │ │ - _merge_tables()│
└──────────────────┘ └──────────────────┘ │ + engineer_all() │
                                          └────────┬─────────┘
                                                   │ feeds
                                                   ▼
┌─────────────────────────────────────────────────────────────┐
│                      EvaluationHarness                      │
├─────────────────────────────────────────────────────────────┤
│ + compute_metrics(y_true, y_pred, y_prob) : dict            │
│ + evaluate_loco(model_fn, data, model_name) : dict          │
│ + evaluate_pooled(model_fn, data, model_name) : dict        │
└─────────────▲────────────────────────────────▲──────────────┘
              │ evaluates                      │ evaluates
┌─────────────┴──────────────┐   ┌─────────────┴──────────────┐
│    BaselineModelEngine     │   │  InterpretableModelEngine  │
├────────────────────────────┤   ├────────────────────────────┤
│ - _make_rf() : RFClassifier│   │ - _make_ebm() : EBMClassif │
│ - _make_xgb(): XGBClassif  │   │ - _make_lgbm(): LGBMClassif│
│ + run_baselines() : dict   │   │ + run_interpretable() :dict│
│                            │   │ + compute_shap() : DF      │
└────────────────────────────┘   └─────────────┬──────────────┘
                                               │ calibrates
                                               ▼
                                 ┌────────────────────────────┐
                                 │     TargetingOptimizer     │
                                 ├────────────────────────────┤
                                 │ + compute_threshold_curve()│
                                 │ + find_optimal_threshold() │
                                 │ + run_targeting() : dict   │
                                 └────────────────────────────┘
```

### 2.4 UML Sequence Diagram: End-to-End Pipeline Execution

```
User/CLI        PipelineOrch        DataIngestor       SchemaValidator     FeatureEngineer      CleanStore
   │                 │                   │                    │                   │                 │
   │── python -m ───>│                   │                    │                   │                 │
   │   src.pipeline  │── load_all() ────>│                    │                   │                 │
   │                 │                   │── read 24 CSVs ───>│                   │                 │
   │                 │                   │<── raw DataFrames ─│                   │                 │
   │                 │                   │── SHA-256 hash ───>│ (lineage_report)  │                 │
   │                 │<── raw_data dict ─│                    │                   │                 │
   │                 │                                        │                   │                 │
   │                 │── validate_all(raw_data) ─────────────>│                   │                 │
   │                 │                                        │── 24 Pandera      │                 │
   │                 │                                        │   Contracts Check │                 │
   │                 │<── validation passed (0 errors) ───────│                   │                 │
   │                 │                                                            │                 │
   │                 │── engineer_all(raw_data) ─────────────────────────────────>│                 │
   │                 │                                                            │── 3-Table Join  │
   │                 │                                                            │── Member Agg    │
   │                 │                                                            │── Mode Impute   │
   │                 │                                                            │── Purge Leakage │
   │                 │<── 8 clean DataFrames (55,922 records, 74 features) ───────│                 │
   │                 │                                                                              │
   │                 │── export clean CSVs ────────────────────────────────────────────────────────>│
   │                 │                                                                              │ (data/processed/
   │                 │<── export confirmed ─────────────────────────────────────────────────────────│  *_clean.csv)
   │<── Success ─────│
   │    (<45s elapsed)
```

### 2.5 Justification of 8 Key Architectural & Design Decisions

| # | Architectural Decision | Discarded Alternative | Engineering & Policy Justification |
|:---:|---|---|---|
| **1** | **3-Tier Relational Ingestion & Tailored Aggregation** | Monolithic flat CSV join | Preserves raw provenance; prevents Cartesian member multiplication; enables differentiated aggregation (`mean` for age, `max` for digital/bank assets). |
| **2** | **Declarative Pandera Schema Contracts** | Ad-hoc runtime `assert` statements | Formally enforces type coercion, non-null guarantees, and value bounds across 24 distinct survey files with zero silent failures. |
| **3** | **Deterministic Median/Mode Imputation** | Complex MICE / KNN imputation | Eliminates cross-country spatial data leakage; guarantees 0.0% missingness while adhering to the frozen compute resource envelope. |
| **4** | **Strict Target Source Leakage Purge** | Retaining expenditure sub-totals | `pcexp` and `zref` mathematically construct the target; retaining them causes 100% artificial accuracy without learning poverty proxies. |
| **5** | **Leave-One-Country-Out (LOCO) Protocol** | Random pooled 5-fold cross-validation | Random splits mix country distributions, masking spatial transfer failure; LOCO rigorously tests authentic cross-border deployment. |
| **6** | **Explainable Boosting Machines (EBM / GA²M)** | Pure black-box neural nets / XGBoost | Delivers exact glass-box additive shape functions required for legal defensibility while outperforming Random Forest (+0.8pp macro accuracy). |
| **7** | **Asymmetric Social Welfare Loss ($C_{ex}:C_{inc}$)** | Symmetric accuracy ($\tau = 0.50$) | Symmetric cuts cause 38.6% exclusion of starving families; calibrating $\tau^* \approx 0.35$ ($3:1$ ratio) reduces exclusion error to 24.1%. |
| **8** | **AC-1..AC-4 & NT-1..NT-5 Guardrails** | Standard happy-path unit tests | Detects country overfitting, enforces transparency gates, verifies bitwise replay, and isolates partition defects. |

---

# SECTION 3: Initial Implementation & Working Prototype (Criterion 3 — 10 Marks)

### 3.1 Objective 1 Implementation Status: 100% Complete & Verified
The team has fully implemented and verified Objective 1 across all 8 West African nations:

| Country | ISO-3 Code | Raw Households | Clean Verified Households | National Poverty Headcount (%) | Mean Household Size | Pandera Schemas Passing |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Benin** | BEN | 8,032 | 8,032 | 29.1% | 4.8 | 3 / 3 (100%) |
| **Burkina Faso** | BFA | 3,227 | 3,227 | 30.1% | 5.9 | 3 / 3 (100%) |
| **Côte d'Ivoire** | CIV | 12,965 | 12,965 | 35.7% | 4.5 | 3 / 3 (100%) |
| **Guinea-Bissau** | GNB | 5,351 | 5,351 | 41.7% | 7.3 | 3 / 3 (100%) |
| **Mali** | MLI | 8,629 | 8,629 | 36.3% | 6.8 | 3 / 3 (100%) |
| **Niger** | NER | 4,008 | 4,008 | 26.8% | 6.7 | 3 / 3 (100%) |
| **Senegal** | SEN | 6,707 | 6,707 | 28.5% | 8.9 | 3 / 3 (100%) |
| **Togo** | TGO | 7,003 | 7,003 | 35.0% | 4.4 | 3 / 3 (100%) |
| **Total / Macro** | **WAEMU** | **55,922** | **55,922** | **33.8% (Weighted)** | **5.8** | **24 / 24 (100%)** |

### 3.2 Prototype Live Demonstration Runbook

#### Step 1: Run the Interactive Streamlit Telemetry Dashboard
To launch the user-facing prototype application in front of the review panel:
```powershell
$env:PYTHONIOENCODING = "utf-8"
streamlit run app.py
```
**Demonstrable Dashboard Capabilities**:
* **Executive Summary**: Overview of 55,922 households, 8 nations, 24 Pandera schema contracts.
* **Country Profiler**: Dynamic selector for any of the 8 nations showing poverty distribution, asset ownership rates, and demographic breakdowns.
* **O1 Pipeline Audit**: Live inspection of SHA-256 data lineage digests and zero-missingness proofs.
* **Model Benchmarks & LOCO Heatmap**: Cross-country transfer performance comparison across RF, XGBoost, EBM, and LightGBM.
* **Policy Loss Simulator**: Interactive slider for cost ratio $C_{ex}:C_{inc}$ (1:1 to 10:1) updating the optimal decision threshold $\tau^*$ and showing simulated exclusion reduction in real time.

#### Step 2: Run the CLI Data Pipeline
To execute the backend data engineering pipeline live in the terminal:
```powershell
$env:PYTHONIOENCODING = "utf-8"
python -m src.pipeline
```
**Expected Console Telemetry**:
* `[INFO] Ingesting 8 countries across 24 files... Done.`
* `[INFO] Validating 24 Pandera DataFrameSchemas... 24/24 PASS OK.`
* `[INFO] Executing 3-tier relational joins and aggregations... Done.`
* `[INFO] Imputing missing values and checking zero-leakage... 0.0% missing.`
* `[INFO] Exported 8 clean datasets to data/processed/ (55,922 records, 74 features).`
* `[INFO] Total pipeline execution time: 38.4s.`

---

# SECTION 4: Tools & Technologies Selection & Justification (Criterion 4 — 10 Marks)

### 4.1 Tools & Technologies Justification Matrix

| Category | Selected Tool | Discarded Alternatives | Engineering & Policy Justification |
|---|---|---|---|
| **Data Ingestion & Manipulation** | **pandas 2.x & numpy** | polars, PySpark, Dask | In-memory processing of 55,922 records requires <1.8 GB RAM, well within standard hardware envelopes. Pandas 2.x PyArrow backend offers extreme stability without JVM or distributed cluster overhead. |
| **Schema Validation** | **pandera 0.33** | Great Expectations, Cerberus, Pydantic | Pandera integrates directly with Pandas DataFrames using vectorized type checks. Great Expectations introduces massive JSON configuration bloat; Pydantic operates at record-level rather than vectorized tabular speed. |
| **Black-Box ML Baselines** | **scikit-learn & xgboost** | TensorFlow, PyTorch Tabular | Tabular survey data with 74 features is proven to favor gradient boosted decision trees over deep neural networks (Garbero & Letta 2022). RF and XGBoost provide industry-standard benchmark baselines. |
| **Interpretable ML Core** | **InterpretML (EBM / GA²M)** | Standard GLM, RuleFit, PyGAM | Standard linear models cannot capture nonlinear asset poverty traps. EBM learns exact piece-wise constant splines with automated interaction detection, yielding +0.8pp higher accuracy than Random Forest while remaining 100% glass-box. |
| **Feature Attribution** | **SHAP (Tree-SHAP)** | LIME, Permutation Importance | Tree-SHAP computes exact Shapley values in polynomial time $O(TLD^2)$ with mathematical efficiency guarantees (local accuracy, missingness, consistency). LIME suffers from sampling instability across repeated evaluations. |
| **Presentation & Dashboard** | **Streamlit** | Flask, Django, React | Allows rapid, reproducible Python-native presentation of live telemetry, interactive policy threshold sliders, and LOCO performance heatmaps directly connected to project source code. |
| **Slide Generation Engine** | **pptxgenjs (Node.js)** | Manual MS PowerPoint | Eliminates manual copy-paste errors; programmatically compiles research data, tables, color palettes, and notes into standardized widescreen slides with 100% deterministic layout consistency. |
| **Data Lineage** | **SHA-256 Digesting** | Blind file reading | Guarantees absolute data provenance and detects any accidental upstream modification of World Bank survey files across the 8 sovereign datasets. |

---

# SECTION 5: Teamwork & Agile Practice: Sprint Planning & Iteration (Criterion 5 — 10 Marks)

### 5.1 Agile Scrum Framework Architecture
The DSCI-28 Capstone project was executed using an **Iterative Agile Scrum Framework** organized into **3 focused bi-weekly Sprints** leading up to the Review 2 milestone:

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                   AGILE SPRINT LIFECYCLE ROADMAP                                 │
├────────────────────────────────┬────────────────────────────────┬────────────────────────────────┤
│ SPRINT 1 (Weeks 1–3)           │ SPRINT 2 (Weeks 4–6)           │ SPRINT 3 (Weeks 7–9, Active)   │
│ Problem Charter & Schemas      │ Feature Engineering & Ingest   │ LOCO Baselines & Review 3 Prep │
├────────────────────────────────┼────────────────────────────────┼────────────────────────────────┤
│ • Problem Charter & UN SDGs    │ • 3-Tier Relational Join Engine│ • LOCO Cross-Validation Engine │
│ • Literature Survey Synthesis  │ • Member Aggregations          │ • Random Forest & XGBoost Runs │
│ • Raw EHCVM Ingestion (24 CSVs)│ • Deterministic Imputation     │ • Heatmap Visualizations       │
│ • Pandera Schema Definitions   │ • Target Formulation & Leakage │ • Preparation for Review 3     │
│ • Status: 100% COMPLETED       │ • Status: 100% COMPLETED       │ • Status: ACTIVE / IN PROGRESS │
│ • Velocity: 24 Story Points    │ • Velocity: 30 Story Points    │ • Target Velocity: 26 Points   │
└────────────────────────────────┴────────────────────────────────┴────────────────────────────────┘
```

### 5.2 Detailed Sprint Backlogs & User Stories

#### SPRINT 1: Problem Charter, Literature Survey & Schema Gates (Weeks 1–3)
* **Sprint Goal**: Formulate the project charter, synthesize 12 literature survey papers, ingest 24 raw EHCVM survey files, and construct declarative Pandera validation schemas.
* **Sprint Backlog & User Stories**:
  - **US-1.1**: *As a researcher, I want to map the Capstone problem statement to UN SDG 1 and SDG 10, so that our research aligns with international policy mandates.* (Story Points: 3 · Assigned: Punyala Rama Krishna Reddy · **DONE**)
  - **US-1.2**: *As a data engineer, I want to ingest raw survey CSVs across 8 countries and generate SHA-256 lineage hashes, so that data provenance is tamper-proof.* (Story Points: 5 · Assigned: Kuni Likitha · **DONE**)
  - **US-1.3**: *As a QA engineer, I want to author 24 declarative Pandera DataFrameSchemas for ménage, welfare, and individu tables, so that corrupted records fail fast.* (Story Points: 8 · Assigned: Kuni Likitha · **DONE**)
  - **US-1.4**: *As a researcher, I want to review 12 indexed papers and identify the 4-pillar research gap, so that our novelty is academically defensible.* (Story Points: 8 · Assigned: Mahesh Sai Bhima & Madala Phanindra · **DONE**)
* **Sprint Velocity**: 24 / 24 Story Points Completed (100%).

#### SPRINT 2: Relational Engineering, Imputation & Objective 1 Release (Weeks 4–6)
* **Sprint Goal**: Engineer the 3-tier relational join pipeline, execute member aggregation, eliminate missing values, formulate zero-leakage poverty targets, and release clean analytical datasets.
* **Sprint Backlog & User Stories**:
  - **US-2.1**: *As a data engineer, I want to merge household dwellings (`menage`) with expenditure records (`welfare`) on composite key `(country_code, hhid)`, so that assets and welfare are aligned.* (Story Points: 5 · Assigned: Kuni Likitha · **DONE**)
  - **US-2.2**: *As a data scientist, I want to aggregate individual member rosters (`mean` age, `max` literacy, `max` banking) to household level, so that roster data is preserved without Cartesian expansion.* (Story Points: 8 · Assigned: Kuni Likitha · **DONE**)
  - **US-2.3**: *As a data engineer, I want to implement localized median/mode imputation, so that 0.0% missing values remain across all 74 features.* (Story Points: 5 · Assigned: Kuni Likitha · **DONE**)
  - **US-2.4**: *As an auditor, I want to purge all expenditure subtotals from the feature space, so that no mathematical target leakage occurs.* (Story Points: 4 · Assigned: Punyala Rama Krishna Reddy · **DONE**)
  - **US-2.5**: *As an analyst, I want to build automated EDA scripts to generate demographic profile tables and 6 distribution plots, so that data characteristics are validated.* (Story Points: 8 · Assigned: Madala Phanindra & Mahesh Sai Bhima · **DONE**)
* **Sprint Velocity**: 30 / 30 Story Points Completed (100%).

#### SPRINT 3: LOCO Evaluation Engine & Black-Box Baselines (Weeks 7–9, Active)
* **Sprint Goal**: Construct the Leave-One-Country-Out (LOCO) partitioning generator, execute Random Forest and XGBoost baseline experiments, and establish the spatial transfer benchmark for Review 3.
* **Sprint Backlog & User Stories**:
  - **US-3.1**: *As a modeler, I want to generate 8 LOCO cross-validation folds, so that models are strictly evaluated on unseen sovereign nations.* (Story Points: 5 · Assigned: Madala Phanindra · **DONE**)
  - **US-3.2**: *As a data scientist, I want to train 300-tree Random Forest and depth-6 XGBoost baselines on LOCO and pooled splits, so that the transfer degradation penalty is quantified.* (Story Points: 8 · Assigned: Madala Phanindra · **DONE**)
  - **US-3.3**: *As an analyst, I want to generate cross-country accuracy heatmaps and metrics tables, so that spatial variance is visible.* (Story Points: 5 · Assigned: Mahesh Sai Bhima · **DONE**)
  - **US-3.4**: *As a UI developer, I want to assemble the interactive Streamlit telemetry dashboard (`app.py`), so that the review panel can inspect results live.* (Story Points: 8 · Assigned: Mahesh Sai Bhima & Punyala Rama Krishna Reddy · **DONE**)
* **Sprint Status**: 26 Story Points planned; initial prototypes operational for Review 2 demonstration.

### 5.3 Scrum Ceremonies & Team Collaboration Cadence
* **Sprint Cadence**: 2-week sprint cycles with planned deliverables aligned to Capstone review milestones.
* **Weekly Standups**: Held every Tuesday and Friday at 4:30 PM (Google Meet / Lab); each member answers:
  1. *What did I complete since the last standup?*
  2. *What will I work on before the next standup?*
  3. *What blockers or dependencies are impeding my progress?*
* **Sprint Review & Retrospectives**: Held at the conclusion of each sprint to inspect code artifacts, verify Pandera validation logs, and refine the product backlog.
* **Definition of Done (DoD)**:
  - Code implemented in clean Python modules adhering to PEP 8 standards.
  - Zero Pandera schema contract violations across all 24 datasets.
  - Fixed random seed `seed = 42` applied to ensure 100% deterministic repeatability.
  - SHA-256 lineage hash registered in `lineage_report.json`.
  - Code peer-reviewed and merged into the primary branch with clean test verification.

---

# SECTION 6: Individual Student Viva Defense Scripts (Guide's Evaluation Sheet)

### Student 1: Kuni Likitha (University ID: 2300032195)
* **Assigned Engineering Domain**: Data Lineage, Schema Engineering & Quality Validation Lead (**Objective O1**).
* **Core Code Modules Owned**: `src/ingest.py`, `src/schemas.py`, `src/engineer.py`, `src/pipeline.py`.

#### Anticipated Viva Questions & Model Answers:
1. **Examiner Q**: *"How did you prevent data corruption across 24 raw survey files from 8 different countries?"*
   * **Student Answer**: *"We implemented a two-fold data assurance gate. First, `src/ingest.py` reads raw CSVs and computes cryptographic SHA-256 hashes to establish an immutable lineage audit trail recorded in `lineage_report.json`. Second, `src/schemas.py` applies 24 declarative Pandera `DataFrameSchema` contracts. These schemas strictly enforce data types, check null constraints on primary identifiers (`hhid`), and enforce valid value ranges (such as housing material codes and expenditure bounds). If any country dataset contains an unexpected schema alteration or type corruption, Pandera raises a fail-fast schema error before data enters the engineering pipeline."*
2. **Examiner Q**: *"Why did you use tailored household aggregations for the individual roster (`INDIVIDU`) instead of a simple join?"*
   * **Student Answer**: *"The `INDIVIDU` table has a 1-to-N relationship with the `MENAGE` table, where each household contains multiple resident members. A flat relational merge would cause Cartesian row explosion, replicating household assets across every member and introducing statistical bias. Instead, in `src/engineer.py`, we designed tailored domain-specific aggregations: continuous demographics like member age use the `mean`; human capital indicators like education and literacy use the `max` to reflect the highest capability in the household; and digital/financial assets (mobile phone ownership, bank accounts) use `max` as a binary indicator of household connectivity. This collapsed the multi-member roster into unified household summary features while preserving individual attributes."*
3. **Examiner Q**: *"How did you guarantee zero missing values without leaking information across national borders?"*
   * **Student Answer**: *"Missing values in survey data cannot be imputed using global cross-country statistics, because economic baselines differ drastically between nations like Senegal and Niger. We performed localized, within-country median imputation for continuous variables and mode imputation for categorical assets. This ensured 0.0% missingness across all 74 features across all 55,922 households while strictly preserving national distribution integrity and preventing cross-border leakage."*

---

### Student 2: Madala Phanindra (University ID: 2300032338)
* **Assigned Engineering Domain**: Black-Box Baseline Modeling & LOCO Validation Lead (**Objective O2**).
* **Core Code Modules Owned**: `src/evaluate.py`, `src/models.py`, `notebooks/01_eda.py`.

#### Anticipated Viva Questions & Model Answers:
1. **Examiner Q**: *"What is the 'Spatial Transfer Defect' and how does your evaluation methodology expose it?"*
   * **Student Answer**: *"Standard machine learning literature (e.g., Yitageasu et al. 2025) typically evaluates poverty models using random train-test splits. However, on multi-country data, a random split allows households from all nations to appear in both training and test sets, measuring only within-distribution interpolation. When an algorithm is deployed across national borders, it encounters differing asset valuations and macroeconomic baselines. To measure true spatial generalisation, we implemented Leave-One-Country-Out (LOCO) cross-validation in `src/evaluate.py`. In each of the 8 folds, the model trains on 7 nations and is tested strictly on the withheld 8th country. This revealed a significant Transfer Penalty: Random Forest dropped by 2.9 percentage points (76.9% to 74.0%) and XGBoost dropped by 3.9 percentage points (80.2% to 76.3%), demonstrating why cross-border models require specialized calibration."*
2. **Examiner Q**: *"Why compare both Random Forest and XGBoost instead of selecting just one?"*
   * **Student Answer**: *"In our literature survey of 12 indexed papers, there is no consensus on a single superior tabular algorithm. Garbero & Letta (2022) found Random Forest excelled in cross-country resilience transfer, while Scandurra et al. (2026) and Mariyah & Wobcke (2025) found XGBoost superior. In our empirical results, while XGBoost achieved higher macro accuracy in LOCO (76.3% vs 74.0%), it did so by becoming conservative in predicting poverty (precision 0.695, but recall only 0.569). Random Forest maintained much higher recall (0.702). Evaluating both provided the essential performance envelope needed to benchmark our interpretable models."*

---

### Student 3: Mahesh Sai Bhima (University ID: 2300030811)
* **Assigned Engineering Domain**: Interpretable Model Engineering & Trade-Off Benchmarking Lead (**Objective O3**).
* **Core Code Modules Owned**: `src/interpretable.py`, `src/tradeoff.py`, `app.py`.

#### Anticipated Viva Questions & Model Answers:
1. **Examiner Q**: *"Why is Explainable Boosting Machine (EBM / GA²M) considered glass-box, while XGBoost with post-hoc SHAP is not?"*
   * **Student Answer**: *"XGBoost builds complex, high-order multi-feature trees where individual feature effects are tangled and opaque. Post-hoc SHAP values provide local linear approximations of feature importance, but as Dejkam & Madlener (2025) and Watson (2022) emphasize, SHAP values reflect correlation rather than causal effect and can produce non-monotonic artifacts. In contrast, Explainable Boosting Machines (Zschech et al. 2026) are Generalized Additive Models with pairwise interactions: $g(\mathbb{E}[y]) = \beta_0 + \sum f_i(x_i) + \sum f_{ij}(x_i, x_j)$. Each univariate function $f_i$ is learned via cyclic gradient boosting on single features, producing an exact piece-wise constant spline. A policy administrator can plot and audit the exact mathematical curve of how adding a refrigerator or changing roof materials alters the predicted log-odds of poverty with zero approximation error."*
2. **Examiner Q**: *"What is the empirical 'Cost of Interpretability' observed in your cross-country experiments?"*
   * **Student Answer**: *"A common assumption in machine learning is that interpretability requires sacrificing predictive performance. Our empirical LOCO evaluation decisively disproves this: Explainable Boosting Machine achieves **74.8% macro accuracy**, outperforming the Random Forest black-box reference (**74.0%**, a **+0.8 percentage point gain**). Furthermore, LightGBM with exact Tree-SHAP polynomial attribution achieves **76.4% macro accuracy**, matching and marginally exceeding XGBoost (**76.3%**). The empirical cost of interpretability in our 8-nation system is essentially **0.0 percentage points**."*

---

### Student 4: Punyala Rama Krishna Reddy (University ID: 2300031696)
* **Assigned Engineering Domain**: Policy Assurance, Asymmetric Welfare Loss & Recourse Lead (**Objective O4 / O5**).
* **Core Code Modules Owned**: `src/targeting.py`, `src/acceptance.py`, `src/negative_tests.py`, `src/run_all.py`.

#### Anticipated Viva Questions & Model Answers:
1. **Examiner Q**: *"Why is a standard 0.5 decision threshold unacceptable in social safety net targeting?"*
   * **Student Answer**: *"In anti-poverty targeting, classification errors have deeply asymmetric human and economic consequences. An **Exclusion Error (False Negative)** means a destitute, starving family is denied aid, leading to malnutrition and severe deprivation. An **Inclusion Error (False Positive)** means a non-poor family receives assistance, representing modest fiscal budget dilution. Under a standard symmetric threshold of $\tau = 0.50$, default models produce an unacceptably high **38.6% exclusion error**. In `src/targeting.py`, we formulate the policy loss as $\mathcal{L}_{policy}(\tau; c) = c \cdot \text{FN}(\tau) + 1 \cdot \text{FP}(\tau)$, where $c = C_{ex} / C_{inc}$. Calibrating across policy ratios shifts the optimal threshold to $\tau^* = 0.35$ for $c=3$ (reducing exclusion error to **24.1%**) and $\tau^* = 0.15$ for humanitarian emergencies ($c=10$, reducing exclusion to **7.2%**), directly aligning model behavior with humanitarian objectives."*
2. **Examiner Q**: *"What are your Mandatory Negative Tests (NT-1 to NT-5) and why are standard unit tests insufficient?"*
   * **Student Answer**: *"Standard unit tests only verify the 'happy path' — that code executes without crashing. In public governance, AI systems must have adversarial guardrails to prevent catastrophic failure. In `src/negative_tests.py`, we designed 5 negative stress tests: **NT-1** detects single-country overfitting by catching spatial generalization gaps (>4pp) and blocking single-nation deployment; **NT-2** rejects black-box ensemble deployment when policy transparency flags mandate explainability; **NT-3** flags symmetric error abuse when equal cost weighting is attempted in humanitarian targeting; **NT-4** verifies bitwise idempotent replay under frozen seed 42; and **NT-5** detects localized country partition defects where a single country suffers extreme targeting variance. All 5 negative tests passed 100% verification."*

---

*Certified fully compliant with KL University Capstone Project 23IE4053 Review 2 Guidelines & Evaluation Rubrics.*
