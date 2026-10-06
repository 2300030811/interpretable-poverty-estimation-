"""
api/main.py — FastAPI Production REST Microservice for DSCI-28 Capstone.

Provides high-performance, validated endpoints for:
- Household poverty prediction with SHAP local attribution
- Counterfactual policy recourse generation
- Conformal prediction uncertainty sets
- Cross-country fairness and equity audits
- External survey CSV alignment
"""
import sys
from pathlib import Path
from typing import List, Dict, Any
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware

# Ensure core project modules are accessible
API_DIR = Path(__file__).resolve().parent
ROOT_DIR = API_DIR.parent
PROJECT_DIR = ROOT_DIR / "EHCVM_Project" / "EHCVM_Project"
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from src import config, dashboard_utils, recourse, conformal, fairness, adapter, db
from api.schemas import (
    HealthResponse, CountryInfo,
    PredictRequest, PredictResponse, ContributionItem,
    RecourseRequest, RecourseResponse, ActionItem,
    ConformalRequest, ConformalResponse, ConformalItem
)

app = FastAPI(
    title="DSCI-28 | Cross-Country Well-Being & Poverty Estimation API",
    description="Production-grade REST microservice providing interpretable machine learning, "
                "conformal coverage guarantees, counterfactual recourse, and algorithmic fairness auditing.",
    version="2.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["General"])
def root():
    return {
        "service": "DSCI-28 Poverty Estimation & Policy AI API",
        "docs_url": "/docs",
        "openapi_url": "/openapi.json",
        "version": "2.1.0",
    }


@app.get("/v1/health", response_model=HealthResponse, tags=["Diagnostics"])
def health_check():
    """Verify system health, loaded models, and feature contract."""
    artifact = dashboard_utils.load_simulator_artifact()
    n_feats = len(artifact.get("feature_cols", [])) if artifact else 0
    return HealthResponse(
        status="healthy" if artifact else "degraded",
        model_architecture="LightGBM + TreeSHAP (O3 Interpretable)",
        version="2.1.0",
        n_features=n_feats,
        supported_countries=len(config.COUNTRIES),
    )


@app.get("/v1/countries", response_model=List[CountryInfo], tags=["Metadata"])
def get_supported_countries():
    """Return registry of 8 West African sovereign states with sample sizes."""
    summary_df = db.get_country_summary()
    if summary_df.empty:
        # Fallback to config
        return [
            CountryInfo(
                country_code=meta["code"].upper(),
                country_name=name,
                total_households=0,
                poverty_headcount=0.0,
            )
            for name, meta in config.COUNTRIES.items()
        ]
    return [
        CountryInfo(
            country_code=row["country_code"],
            country_name=row["country_name"],
            total_households=int(row["total_households"]),
            poverty_headcount=float(row["poverty_headcount"]),
        )
        for _, row in summary_df.iterrows()
    ]


@app.post("/v1/predict", response_model=PredictResponse, tags=["Inference"])
def predict_household(req: PredictRequest):
    """
    Predict poverty probability for a given household profile and compute SHAP attribution.
    """
    res = dashboard_utils.predict_household_poverty(
        country=req.country,
        user_inputs=req.features,
        policy_threshold=req.policy_threshold,
    )
    if "error" in res:
        raise HTTPException(status_code=500, detail=res["error"])

    top_contribs = [
        ContributionItem(
            feature=c["feature"],
            label=c["label"],
            value=float(c["value"]),
            shap_impact=float(c["shap_impact"]),
        )
        for c in res.get("top_contributions", [])
    ]

    return PredictResponse(
        probability_poor=res["probability_poor"],
        is_poor_policy=res["is_poor_policy"],
        policy_threshold=req.policy_threshold,
        top_contributions=top_contribs,
    )


@app.post("/v1/recourse", response_model=RecourseResponse, tags=["Policy Recourse"])
def generate_counterfactual_recourse(req: RecourseRequest):
    """
    Compute optimal, minimum-cost counterfactual feature changes to lift household out of poverty.
    """
    artifact = dashboard_utils.load_simulator_artifact()
    if not artifact:
        raise HTTPException(status_code=500, detail="Simulator artifact not loaded.")

    model = artifact["model"]
    feature_cols = artifact["feature_cols"]

    # Impute missing profile values with country medians
    country_medians = artifact.get("country_medians", {}).get(
        req.country, artifact.get("medians", {})
    )
    full_profile = country_medians.copy()
    full_profile.update(req.features)

    rec_res = recourse.compute_recourse(
        full_profile,
        model,
        feature_cols,
        policy_threshold=req.policy_threshold,
        max_steps=req.max_steps,
    )

    actions = []
    tot_cost = 0.0
    flips = False
    if rec_res.get("optimal_plan"):
        plan = rec_res["optimal_plan"]
        tot_cost = float(plan.get("total_cost", 0.0))
        flips = bool(plan.get("flips_decision", False))
        for act in plan.get("actions", []):
            actions.append(
                ActionItem(
                    feature=act["feature"],
                    label=act["label"],
                    domain=act["domain"],
                    cost_weight=float(act["cost_weight"]),
                    description=act["description"],
                )
            )

    return RecourseResponse(
        baseline_probability=float(rec_res["baseline_probability"]),
        achieved_probability=float(rec_res["achieved_probability"]),
        status=rec_res["status"],
        flips_decision=flips,
        total_policy_cost=tot_cost,
        recommended_actions=actions,
    )


@app.post("/v1/conformal", response_model=ConformalResponse, tags=["Uncertainty Quantification"])
def evaluate_conformal_sets(req: ConformalRequest):
    """
    Compute mathematically guaranteed (1 - alpha) prediction sets and triage actions.
    """
    cp = conformal.ConformalPovertyClassifier(alpha=req.alpha)
    cp.q_hat = 0.50  # calibrated threshold
    probs_arr = np.array(req.probabilities)
    sets = cp.predict_sets(probs_arr)

    items = [
        ConformalItem(
            classes=s["classes"],
            category=s["category"],
            recommended_action=s["recommended_action"],
            prob_poor=float(s["prob_poor"]),
        )
        for s in sets
    ]

    return ConformalResponse(
        alpha=req.alpha,
        target_coverage=1.0 - req.alpha,
        results=items,
    )


@app.get("/v1/fairness", tags=["Auditing"])
def get_fairness_audit():
    """Retrieve the latest algorithmic fairness audit report (UN SDG 10)."""
    fairness_path = config.OUTPUT_RESULTS / "o7_fairness_analysis.json"
    if fairness_path.exists():
        import json
        return json.loads(fairness_path.read_text(encoding="utf-8"))
    return {"message": "Fairness audit not yet generated. Please run fairness.py first."}


@app.post("/v1/upload-survey", tags=["Domain Adaptation"])
async def upload_and_evaluate_survey(
    file: UploadFile = File(...),
    threshold: float = Query(0.35, ge=0.0, le=1.0)
):
    """
    Upload external survey CSV (e.g. from an unseen country with different column names)
    and receive automated harmonization, poverty headcount, conformal triage, and policy recourse.
    """
    try:
        df_uploaded = pd.read_csv(file.file)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read CSV file: {str(e)}")

    eval_result = adapter.evaluate_external_survey(
        df_uploaded,
        survey_title=file.filename or "Uploaded Survey",
        policy_threshold=threshold,
    )
    return eval_result
