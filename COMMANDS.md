# DSCI-28: Complete Execution Runbook & Quick Start Guide

**Project**: Interpretable Cross-Country Household Well-Being Estimation  
**Data**: World Bank EHCVM 2021 Survey Microdata · 8 West African Nations (55,922 Households)  
**Institution**: KL University (KLEF) · Academic Year 2026–27  

---

## ⚡ Quick Start: How to Run the Project

You can run the entire platform with **1 command** (recommended) or **2 commands** in separate terminals:

### Option 1: The 1-Command All-in-One Launcher (Recommended)
From the project root:
```powershell
python run_all.py
```
*(Or in Windows File Explorer, simply double-click **`start.bat`**)*

This launches both services simultaneously:
* **Interactive Streamlit Dashboard**: [http://localhost:8501](http://localhost:8501)
* **Production FastAPI REST Microservice**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

### Option 2: Running Services Separately (2 Terminals)

If you prefer dedicated terminal tabs to monitor real-time logs:

#### Terminal 1 — Streamlit Interactive Web Application
```powershell
streamlit run app.py
```
* **URL**: [http://localhost:8501](http://localhost:8501)  
* **Features Included**:
  * **Tab 1: Data & Schema (O1)**: National Survey microdata inspector, urban/rural divide (58.4% vs 24.1%), Pandera schema validation.
  * **Tab 2: LOCO Benchmark (O2)**: Leave-One-Country-Out evaluation matrix, EBM (+0.8 pp over Random Forest) zero cost of interpretability.
  * **Tab 3: Interpretable AI (O3)**: Tree-SHAP local explanations, plain-English decision narrative, and **Counterfactual Policy Recourse Plan**.
  * **Tab 4: Policy Targeting (O4)**: Asymmetric humanitarian loss ($\tau^* = 0.35$ reduces exclusion error from 38.6% to 24.1%) & **Conformal 90% Triage**.
  * **Tab 5: QA & DuckDB (O5)**: AC-1 to AC-4, NT-1 to NT-5, **UN SDG 10 Algorithmic Fairness Audit**, and **DuckDB Live SQL Console**.
  * **Tab 6: Universal Upload (O6)**: Zero-shot microdata ingestion for unseen countries (e.g., Ghana GLSS, India survey) with instant scored CSV download.

#### Terminal 2 — FastAPI Production REST Microservice
```powershell
uvicorn api.main:app --reload --port 8000
```
* **Interactive Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
* **ReDoc Documentation**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
* **Health Check**: `GET http://localhost:8000/v1/health`
* **Single Household Inference**: `POST http://localhost:8000/v1/predict`
* **Counterfactual Recourse**: `POST http://localhost:8000/v1/recourse`
* **Conformal Prediction**: `POST http://localhost:8000/v1/conformal`
* **External Survey Ingestion**: `POST http://localhost:8000/v1/upload-survey`

---

## 🧪 Verification & Assurance Commands (For Viva Defense)

| Action | Command | Purpose / Expected Output |
|---|---|---|
| **Run Pytest Suite** | `python -m pytest tests/` | Runs all **21 automated unit & integration tests** in ~6s (100% pass). |
| **Inspect DuckDB Database** | `python run_db.py` | Queries `ehcvm.duckdb` and prints table row counts (55,922 households, 40 calibration tuples). |
| **Build Defense Presentation** | `node generate_deck_final.js` | Generates 17-slide widescreen presentation deck: `DSCI28_Final_Capstone_Presentation.pptx`. |
| **Generate Publication Figures** | `cd EHCVM_Project/EHCVM_Project; python -m notebooks.02_results` | Generates all 6 high-resolution PNG charts in `outputs/results/`. |

---

## 📦 System Requirements & Dependency Setup

### 1. Requirements
* **Python**: `3.10` or `3.11` (64-bit)
* **Node.js**: `v18.0.0` or higher (only needed for slide generation)
* **RAM**: 8 GB minimum
* **OS**: Windows 10/11, macOS, Linux

### 2. Dependency Installation
```bash
pip install -r requirements.txt
```
*Key packages installed*: `streamlit`, `fastapi`, `uvicorn`, `duckdb`, `lightgbm`, `xgboost`, `interpret`, `shap`, `pandera`, `plotly`, `scikit-learn`, `pytest`.

### 3. Windows Encoding Configuration
To ensure UTF-8 encoding across all Windows PowerShell terminals:
```powershell
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONPATH = "EHCVM_Project/EHCVM_Project"
```

---

## 🔬 Individual Analytical Modules (Modular Execution)

If examiners ask to execute individual scientific modules from the terminal:

Execute from `EHCVM_Project/EHCVM_Project`:
```powershell
cd EHCVM_Project/EHCVM_Project

# 1. Embedded DuckDB Analytics & SQL Tables (55,922 households)
python -m src.db

# 2. Counterfactual Policy Recourse Optimization (Greedy Action Search)
python -m src.recourse

# 3. Distribution-Free Split Conformal Prediction (90% coverage guarantees)
python -m src.conformal

# 4. UN SDG 10 Algorithmic Fairness Audit (Four-Fifths 80% Rule)
python -m src.fairness

# 5. Universal Survey Adapter (Multilingual Column Synonym Harmonization)
python -m src.adapter

# 6. Formal Acceptance Criteria (AC-1 to AC-4)
python -m src.acceptance

# 7. Adversarial Negative Test Suite (NT-1 to NT-5)
python -m src.negative_tests
```

---

## 🐳 Docker Deployment (Optional Production Container)

To build and run the production container with Docker:

```bash
# Build and launch using Docker Compose
docker-compose up --build

# Or build standalone image
docker build -t dsci28-capstone .
docker run -p 8000:8000 -p 8501:8501 dsci28-capstone
```

---

## 🛠️ Troubleshooting & Common Fixes

| Issue | Root Cause | Solution |
|---|---|---|
| `ModuleNotFoundError: No module named 'src'` | Python run from root without module path. | Run with `$env:PYTHONPATH = "EHCVM_Project/EHCVM_Project"` or use root helper scripts (`run_all.py`, `run_db.py`). |
| `UnicodeEncodeError: 'charmap'` | Windows default code page cp1252. | All files now enforce `encoding="utf-8"`. Run `$env:PYTHONIOENCODING = "utf-8"`. |
| Port 8000 or 8501 already in use | Previous process still running in background. | Kill previous process via task manager or run on an alternate port (`--port 8001`). |
