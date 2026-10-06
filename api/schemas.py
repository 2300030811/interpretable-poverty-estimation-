"""
api/schemas.py — Pydantic request and response schemas for DSCI-28 REST Microservice.
"""
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field

class HealthResponse(BaseModel):
    status: str = "healthy"
    model_architecture: str = "LightGBM + TreeSHAP / EBM"
    version: str = "2.1.0"
    n_features: int = 73
    supported_countries: int = 8

class CountryInfo(BaseModel):
    country_code: str
    country_name: str
    total_households: int
    poverty_headcount: float

class PredictRequest(BaseModel):
    country: str = Field(default="Benin", description="Country name for baseline medians")
    features: Dict[str, float] = Field(
        default_factory=dict,
        description="Key-value mapping of survey features (e.g. hhsize, elec_ac, sol, ind_telpor)"
    )
    policy_threshold: float = Field(default=0.35, ge=0.0, le=1.0)

class ContributionItem(BaseModel):
    feature: str
    label: str
    value: float
    shap_impact: float

class PredictResponse(BaseModel):
    probability_poor: float
    is_poor_policy: bool
    policy_threshold: float
    top_contributions: List[ContributionItem]

class RecourseRequest(BaseModel):
    country: str = Field(default="Benin")
    features: Dict[str, float] = Field(default_factory=dict)
    policy_threshold: float = Field(default=0.35, ge=0.0, le=1.0)
    max_steps: int = Field(default=3, ge=1, le=5)

class ActionItem(BaseModel):
    feature: str
    label: str
    domain: str
    cost_weight: float
    description: str

class RecourseResponse(BaseModel):
    baseline_probability: float
    achieved_probability: float
    status: str
    flips_decision: bool
    total_policy_cost: float
    recommended_actions: List[ActionItem]

class ConformalRequest(BaseModel):
    probabilities: List[float]
    alpha: float = Field(default=0.10, gt=0.0, lt=1.0)

class ConformalItem(BaseModel):
    classes: List[int]
    category: str
    recommended_action: str
    prob_poor: float

class ConformalResponse(BaseModel):
    alpha: float
    target_coverage: float
    results: List[ConformalItem]
