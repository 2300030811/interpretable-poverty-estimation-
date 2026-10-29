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
    scientific_validation_status: Optional[str] = "VALIDATED_EHCVM_INTERNAL"
    is_supported_country: Optional[bool] = True


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
    provenance: Optional[str] = "OBSERVED"
    is_imputed: Optional[bool] = False


class RecourseResponse(BaseModel):
    baseline_probability: float
    achieved_probability: float
    status: str
    flips_decision: bool
    total_policy_cost: float
    recommended_actions: List[ActionItem]
    causal_disclaimer: Optional[str] = None
    scientific_validation_status: Optional[str] = "VALIDATED_EHCVM_INTERNAL"
    is_supported_country: Optional[bool] = True


class ConformalRequest(BaseModel):
    probabilities: List[float]
    alpha: float = Field(default=0.10, gt=0.0, lt=1.0)


class ConformalItem(BaseModel):
    classes: List[int]
    category: str
    recommended_action: str
    prob_poor: float
    is_external_unvalidated: Optional[bool] = False
    coverage_guaranteed: Optional[bool] = True


class ConformalResponse(BaseModel):
    alpha: float
    target_coverage: float
    q_hat: Optional[float] = None
    results: List[ConformalItem]


class SurveyValidationReport(BaseModel):
    status: str
    schema_compatibility: Optional[str] = None
    scientific_validation_status: Optional[str] = "UNVALIDATED_EXTERNAL_DOMAIN"
    eligibility_determination_permitted: Optional[bool] = False
    decision_boundary_notice: Optional[str] = None
    status_message: str
    uploaded_rows: int
    uploaded_columns: int
    matched_count: int
    observed_count: int
    derived_count: int
    imputed_count: int
    invalid_count: int
    feature_coverage_pct: float
    critical_coverage_pct: float
    critical_domains_present: List[str]
    critical_domains_missing: List[str]
    matched_features: List[str]
    observed_features: List[str]
    derived_features: List[str]
    imputed_features: List[str]
    invalid_features: List[str]
    unmatched_columns: List[str]
    warnings: List[str]
    errors: List[str]


class DomainShiftSummary(BaseModel):
    overall_shift_index: float
    overall_shift_level: str
    risk_summary: str
    severe_alerts: List[str]
    moderate_alerts: List[str]
    scientific_disclaimer: Optional[str] = None


class SurveyUploadResponse(BaseModel):
    status: str
    schema_compatibility: Optional[str] = None
    scientific_validation_status: Optional[str] = "UNVALIDATED_EXTERNAL_DOMAIN"
    eligibility_determination_permitted: Optional[bool] = False
    decision_boundary_notice: Optional[str] = None
    survey_title: str
    n_households: int
    validation_report: SurveyValidationReport
    domain_shift: DomainShiftSummary
    policy_headcount_rate: Optional[float] = None
    policy_threshold: float = 0.35
    mean_poverty_probability: Optional[float] = None
    ground_truth_poverty_rate: Optional[float] = None
    conformal_status: Optional[str] = None
    conformal_notice: Optional[str] = None
    audit_report_markdown: Optional[str] = None
    message: Optional[str] = None
