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
from typing import List, Dict, Any, Optional
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware

# Ensure core project modules are accessible
API_DIR = Path(__file__).resolve().parent
ROOT_DIR = API_DIR.parent
PROJECT_DIR = ROOT_DIR / "dsci28"
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
    allow_credentials=False,
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

    is_supported = req.country in config.COUNTRIES
    val_status = "VALIDATED_EHCVM_INTERNAL" if is_supported else "UNVALIDATED_EXTERNAL_DOMAIN"

    return PredictResponse(
        probability_poor=res["probability_poor"],
        is_poor_policy=res["is_poor_policy"],
        policy_threshold=req.policy_threshold,
        top_contributions=top_contribs,
        scientific_validation_status=val_status,
        is_supported_country=is_supported,
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

    is_supported = req.country in config.COUNTRIES
    val_status = "VALIDATED_EHCVM_INTERNAL" if is_supported else "UNVALIDATED_EXTERNAL_DOMAIN"

    return RecourseResponse(
        baseline_probability=float(rec_res["baseline_probability"]),
        achieved_probability=float(rec_res["achieved_probability"]),
        status=rec_res["status"],
        flips_decision=flips,
        total_policy_cost=tot_cost,
        recommended_actions=actions,
        causal_disclaimer=rec_res.get("causal_disclaimer"),
        scientific_validation_status=val_status,
        is_supported_country=is_supported,
    )


@app.post("/v1/conformal", response_model=ConformalResponse, tags=["Uncertainty Quantification"])
def evaluate_conformal_sets(req: ConformalRequest):
    """
    Compute mathematically guaranteed (1 - alpha) prediction sets and triage actions.
    Calibrates on pooled split calibration set dynamically for requested alpha.
    """
    cp = conformal.load_calibrated_classifier(alpha=req.alpha)
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
        q_hat=float(cp.q_hat) if cp.q_hat is not None else None,
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
    threshold: float = Query(0.35, ge=0.0, le=1.0),
    allow_exploratory: bool = Query(True),
):
    """
    Upload external survey CSV (e.g. from an unseen country with different column names)
    and receive automated harmonization, compatibility check, domain shift diagnostics,
    calibrated poverty predictions, conformal triage, and policy recourse.
    """
    try:
        content = await file.read()
        if not content or len(content.strip()) == 0:
            raise HTTPException(
                status_code=400,
                detail="Uploaded CSV file is empty. Please provide a valid CSV file with household survey data."
            )
        import io
        df_uploaded = pd.read_csv(io.BytesIO(content))
        if len(df_uploaded) == 0:
            raise HTTPException(
                status_code=400,
                detail="Uploaded CSV file has zero data rows. Please provide at least one household record."
            )
    except HTTPException:
        raise
    except Exception:
        # Sanitized error message without leaking internal stack traces or system paths
        raise HTTPException(
            status_code=400,
            detail="Failed to parse CSV file: invalid format, delimiter, or encoding."
        )

    try:
        eval_result = adapter.evaluate_external_survey(
            df_uploaded,
            survey_title=file.filename or "Uploaded Survey",
            policy_threshold=threshold,
            allow_exploratory=allow_exploratory,
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=f"Survey evaluation error: {str(ve)}")
    return eval_result


@app.post("/v1/upload-multi-module", tags=["Domain Adaptation"])
async def upload_multi_module_survey(
    menage_file: UploadFile = File(..., description="Household housing & assets CSV"),
    welfare_file: Optional[UploadFile] = File(None, description="Household head & demographics CSV"),
    individu_file: Optional[UploadFile] = File(None, description="Individual roster CSV"),
    threshold: float = Query(0.35, ge=0.0, le=1.0),
):
    """
    Join multiple survey modules (menage, welfare, individu) with verified join cardinality,
    roster aggregation, and target-leakage quarantine, then run evaluation pipeline.
    """
    import io
    try:
        m_bytes = await menage_file.read()
        if not m_bytes or len(m_bytes.strip()) == 0:
            raise HTTPException(status_code=400, detail="Ménage module file is empty.")
        df_menage = pd.read_csv(io.BytesIO(m_bytes))

        df_welfare = None
        if welfare_file is not None:
            w_bytes = await welfare_file.read()
            if w_bytes and len(w_bytes.strip()) > 0:
                df_welfare = pd.read_csv(io.BytesIO(w_bytes))

        df_indiv = None
        if individu_file is not None:
            i_bytes = await individu_file.read()
            if i_bytes and len(i_bytes.strip()) > 0:
                df_indiv = pd.read_csv(io.BytesIO(i_bytes))

        df_merged, merge_audit = adapter.merge_survey_modules(df_menage, df_welfare, df_indiv)
    except HTTPException:
        raise
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=f"Module merge error: {str(ve)}")
    except Exception:
        raise HTTPException(status_code=400, detail="Failed to parse or join multi-module survey files.")

    eval_result = adapter.evaluate_external_survey(
        df_merged,
        survey_title=f"Multi-Module: {menage_file.filename}",
        policy_threshold=threshold,
    )
    eval_result["merge_audit"] = merge_audit
    return eval_result
