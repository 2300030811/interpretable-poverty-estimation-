"""
adapter.py — Universal Survey Adapter, Multi-Module Ingestion & Domain Compatibility.

Enables verified, trustworthy ingestion and poverty prediction for new surveys and
unseen countries with arbitrary column names, multi-module tables, and variable subsets.

Core Pillars:
1. Formal input validation & compatibility policies (COMPATIBLE, EXPLORATORY, INSUFFICIENT).
2. Complete multilingual synonym normalization across all 73 canonical features.
3. Multi-module survey joining (menage + welfare + individu) with strict cardinality & leakage guards.
4. Separation of observed, deterministically derived, and statistically imputed features.
5. Domain-shift diagnostic integration.
6. Qualified external conformal prediction (suppressing false certainty claims on unseen domains).
7. Honest SHAP attribution and guarded counterfactual recourse with causal disclaimers.
"""
from typing import Dict, List, Tuple, Any, Optional, Set
import re
import datetime
import numpy as np
import pandas as pd

from . import config
from . import feature_contract
from . import domain_diagnostics

# ── Comprehensive Multilingual Synonym Dictionary ───────────────────────────
SYNONYM_DICTIONARY: Dict[str, List[str]] = {
    # Housing & Shelter
    "toit": ["roof", "roof_type", "roof_material", "roofing", "toiture", "type_toit", "type_toiture", "materiau_toit", "h_roof"],
    "mur": ["wall", "wall_type", "wall_material", "walls", "type_mur", "materiau_mur", "h_wall"],
    "sol": ["floor", "floor_type", "floor_material", "flooring", "type_sol", "materiau_sol", "h_floor"],
    "logem": ["dwelling", "dwelling_type", "housing_type", "type_logement", "housing", "tenure_status", "statut_occupation"],
    "toilet": ["toilet", "latrine", "sanitation", "sanitation_type", "type_toilette", "wc", "toilet_facility"],
    "eauboi_ss": ["drinking_water", "water_source", "dry_season_water", "water", "eau_boisson", "source_eau", "water_dry"],
    "eauboi_sp": ["rainy_water", "rainy_season_water", "eau_hivernage", "water_rainy", "eau_saison_pluie"],
    "ordure": ["trash", "waste", "garbage_disposal", "dechets", "ordures", "evacuation_ordures"],
    "eva_toi": ["toilet_drainage", "sewage", "evacuation_toilette", "sewage_system"],
    "eva_eau": ["water_drainage", "evacuation_eau", "drainage_system", "greywater"],

    # Assets & Electrification
    "elec_ac": ["electricity", "grid_electricity", "electric_grid", "power", "electricite", "reseau_electrique", "has_electricity"],
    "elec_ur": ["solar", "solar_electricity", "offgrid_solar", "panneau_solaire", "solar_home_system"],
    "elec_ua": ["generator", "battery_power", "groupe_electrogene", "private_generator"],
    "tv": ["television", "tv_set", "televiseur", "has_tv"],
    "frigo": ["fridge", "refrigerator", "cooler", "refrigerateur", "has_fridge"],
    "car": ["car", "automobile", "vehicle", "motor_car", "voiture", "auto", "vehicule"],
    "decod": ["satellite", "cable_tv", "decoder", "decodeur", "canal", "canal_plus"],
    "ordin": ["computer", "pc", "laptop", "ordinateur", "desktop"],
    "cuisin": ["cooker", "stove", "gas_stove", "cuisiniere", "cookstove"],
    "fer": ["iron", "electric_iron", "fer_repasser", "clothing_iron"],

    # Agriculture & Livestock
    "superf": ["land_area", "agricultural_land", "farm_size", "superficie_agricole", "superficie", "farm_hectares", "land_ha"],
    "grosrum": ["cattle", "cows", "large_livestock", "bovins", "gros_ruminants", "cattle_count", "vaches"],
    "petitrum": ["goats", "sheep", "small_livestock", "caprins", "ovins", "petits_ruminants", "goats_count"],
    "porc": ["pigs", "swine", "porcins", "porcs", "pigs_count"],
    "lapin": ["rabbits", "lapins", "small_poultry"],
    "volail": ["poultry", "chickens", "volaille", "birds", "poules"],

    # Shocks
    "sh_id_demo": ["demographic_shock", "shock_death", "death_breadwinner", "choc_deces", "sh_demo"],
    "sh_co_natu": ["natural_shock", "drought_flood", "shock_climate", "choc_naturel", "sh_natu"],
    "sh_co_eco": ["economic_shock", "macro_shock", "price_spike", "choc_economique", "sh_eco"],
    "sh_id_eco": ["job_loss_shock", "loss_income", "perte_emploi", "sh_job"],
    "sh_co_vio": ["violence_shock", "conflict_shock", "choc_violence", "conflict"],
    "sh_co_oth": ["other_shock", "community_shock", "autre_choc"],

    # Head Demographics
    "hgender": ["head_gender", "gender_head", "sex_head", "sexe_chef", "genre_chef", "head_sex"],
    "hage": ["head_age", "age_head", "age_chef", "chef_age"],
    "hmstat": ["head_marital_status", "marital_status_head", "statut_matrimonial_chef", "h_marital"],
    "hreligion": ["head_religion", "religion_head", "religion_chef"],
    "hnation": ["head_nationality", "nationality_head", "nationalite_chef"],
    "hethnie": ["head_ethnicity", "ethnicity_head", "ethnie_chef", "head_tribe"],
    "halfa": ["head_literate_official", "head_literacy", "alphabetisation_chef", "chef_lit"],
    "halfa2": ["head_literate_local", "head_local_literacy", "alphabetisation_locale_chef"],
    "heduc": ["head_education", "head_education_level", "education_level_head", "niveau_education_chef"],
    "hdiploma": ["head_diploma", "head_degree", "diplome_chef", "head_highest_degree"],
    "hhandig": ["head_disability", "disability_head", "handicap_chef", "head_handicap"],
    "hactiv7j": ["head_employed_7d", "head_active_7d", "chef_actif_7j"],
    "hactiv12m": ["head_employed_12m", "head_active_12m", "chef_actif_12m"],
    "hbranch": ["head_industry", "head_sector_activity", "branche_chef", "industry_head"],
    "hsectins": ["head_institutional_sector", "secteur_institutionnel_chef", "formal_informal_head"],
    "hcsp": ["head_socio_prof", "csp_chef", "head_occupation_category"],

    # Household Composition & Geography
    "hhsize": ["household_size", "hh_size", "family_size", "members_count", "taille_menage", "total_members"],
    "eqadu1": ["adult_equivalent_oecd", "eqadu_scale1", "equivalents_adultes_1"],
    "eqadu2": ["adult_equivalent_sqrt", "eqadu_scale2", "equivalents_adultes_2"],
    "milieu": ["urban_rural", "area_type", "setting", "residence_milieu", "milieu_residence", "urban"],
    "zae": ["agro_zone", "ecological_zone", "zone_agro_ecologique", "region_zone", "agro_ecological_zone"],

    # Individual Aggregates
    "indiv_count": ["roster_count", "indiv_total", "roster_size", "taille_registre"],
    "ind_age": ["mean_age", "average_age_members", "age_moyen_membres"],
    "ind_sexe": ["gender_ratio", "sex_ratio", "proportion_femmes"],
    "ind_alfa": ["official_literacy_rate", "taux_alphabetisation_officiel"],
    "ind_alfa2": ["local_literacy_rate", "taux_alphabetisation_local"],
    "ind_scol": ["school_attendance_rate", "scolarisation_taux", "children_in_school"],
    "ind_educ_hi": ["highest_education", "max_education_level", "education_chef", "niveau_education"],
    "ind_diplome": ["diploma", "degrees_count", "certified_members", "diplomes", "highest_diploma_household"],
    "ind_telpor": ["mobile_phone", "cellphone", "phone", "phones_count", "telephone", "portable", "cellphones_count"],
    "ind_internet": ["internet", "internet_access", "web_access", "connexion_internet", "members_with_internet"],
    "ind_bank": ["bank", "bank_account", "banking", "mobile_money", "compte_bancaire", "banque", "banked_members"],
    "ind_activ7j": ["workers_7d", "active_workers", "employed_members", "actifs_7j", "share_working_7d"],
    "ind_activ12m": ["active_12m", "economically_active", "actifs_12m", "share_active_12m"],
    "ind_mal30j": ["sick_members", "illness_30d", "health_shock", "malades_30j", "illness_count_30d"],
    "ind_couvmal": ["health_insurance_rate", "taux_couverture_maladie", "insured_share"],
    "ind_moustiq": ["bednet_rate", "moustiquaire_taux", "bednets_share"],
    "ind_salaire": ["wage_earners", "formal_salary", "salaried_workers", "salaries", "salaire", "share_wage_earners"],
    "ind_hos12m": ["hospitalized_any", "hospitalisation_12m", "any_hospitalized"],
    "ind_emploi_sec": ["secondary_employment_any", "emploi_secondaire", "any_secondary_job"],
    "ind_handig": ["disabled_members_any", "handicap_membre", "any_disabled_member"],
}

# Build full reverse lookup including exact canonical features
NORMALIZED_SYNONYM_LOOKUP: Dict[str, str] = {}

# 1. First register all 73 canonical feature names directly
for canon in feature_contract.CANONICAL_FEATURES:
    clean_canon = re.sub(r"[^a-z0-9]", "", canon.lower())
    NORMALIZED_SYNONYM_LOOKUP[clean_canon] = canon

# 2. Add aliases from dictionary
for canonical, aliases in SYNONYM_DICTIONARY.items():
    clean_canon = re.sub(r"[^a-z0-9]", "", canonical.lower())
    NORMALIZED_SYNONYM_LOOKUP[clean_canon] = canonical
    for alias in aliases:
        clean_alias = re.sub(r"[^a-z0-9]", "", alias.lower())
        NORMALIZED_SYNONYM_LOOKUP[clean_alias] = canonical


def normalize_column_name(col: str) -> Optional[str]:
    """Match raw column name to canonical EHCVM feature name."""
    if not isinstance(col, str):
        return None
    clean = re.sub(r"[^a-z0-9]", "", col.lower())
    return NORMALIZED_SYNONYM_LOOKUP.get(clean)


# ── Multi-Module Survey Ingestion ───────────────────────────────────────────

def aggregate_individual_module(indiv_df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Aggregate individual-level survey roster (individu.csv) to household level.
    Consistent with EHCVM training aggregation:
      - Numeric columns -> mean per household
      - Binary columns  -> max (any member has condition = 1)
      - Count of members -> indiv_count
    """
    if "hhid" not in indiv_df.columns:
        raise ValueError("Individual module missing required join identifier 'hhid'.")

    # Map column names in indiv_df
    col_mapping = {}
    for c in indiv_df.columns:
        if c == "hhid":
            continue
        canon = normalize_column_name(c)
        if canon:
            col_mapping[c] = canon

    df_mapped = indiv_df.rename(columns=col_mapping)

    num_cols = [c for c in config.INDIV_NUMERIC_AGG if c in df_mapped.columns]
    bin_cols = [c for c in config.INDIV_BINARY_AGG if c in df_mapped.columns]

    agg_dict = {c: "mean" for c in num_cols}
    for c in bin_cols:
        agg_dict[c] = "max"

    # Ensure numeric conversion
    for c in num_cols + bin_cols:
        df_mapped[c] = pd.to_numeric(df_mapped[c], errors="coerce").fillna(0.0)

    if agg_dict:
        grouped = df_mapped.groupby("hhid").agg(agg_dict)
    else:
        grouped = pd.DataFrame(index=df_mapped["hhid"].unique())

    # Add member count
    grouped["indiv_count"] = df_mapped.groupby("hhid").size()

    # Prefix columns with ind_ to match canonical schema
    prefix_cols = {}
    for c in grouped.columns:
        if c == "indiv_count":
            continue
        prefix_cols[c] = f"ind_{c}" if not c.startswith("ind_") else c
    grouped = grouped.rename(columns=prefix_cols)

    audit = {
        "raw_individual_rows": len(indiv_df),
        "aggregated_households": len(grouped),
        "aggregated_features": list(grouped.columns),
    }
    return grouped.reset_index(), audit


def _audit_and_deduplicate_module(
    df: pd.DataFrame, module_name: str
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Safely audit and deduplicate survey module records:
    - Collapse strictly identical duplicate rows across ALL columns under a documented policy.
    - Reject conflicting duplicate records sharing the same 'hhid' with an explicit ValueError.
    - Report exact duplicate rows removed and unique household count.
    """
    if "hhid" not in df.columns:
        raise ValueError(f"{module_name} module missing required join identifier 'hhid'.")

    raw_count = len(df)
    if raw_count == 0:
        raise ValueError(f"{module_name} module contains 0 records.")

    # 1. Check for exact duplicate rows across all columns
    df_clean = df.drop_duplicates().copy()
    exact_collapsed = raw_count - len(df_clean)

    # 2. Check for conflicting duplicate 'hhid' records
    conflicting_mask = df_clean.duplicated(subset=["hhid"], keep=False)
    if conflicting_mask.any():
        conflicting_ids = list(df_clean.loc[conflicting_mask, "hhid"].unique()[:5])
        conflicting_count = int(df_clean["hhid"].duplicated().sum())
        raise ValueError(
            f"{module_name} module contains {conflicting_count} conflicting duplicate records for identifier 'hhid' "
            f"(sample conflicting IDs: {conflicting_ids}). "
            f"Conflicting records cannot be silently discarded by keeping the first occurrence. "
            f"Please provide a verified composite key or an explicit deduplication resolution rule."
        )

    audit = {
        "module": module_name,
        "raw_rows": raw_count,
        "exact_duplicates_collapsed": exact_collapsed,
        "unique_households": len(df_clean),
    }
    return df_clean, audit


def merge_survey_modules(
    menage_df: pd.DataFrame,
    welfare_df: Optional[pd.DataFrame] = None,
    indiv_df: Optional[pd.DataFrame] = None,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Safely join multiple related survey modules with verified cardinality & leakage prevention:
    - Collapses exact identical rows under an explicit, documented policy.
    - Rejects conflicting duplicate 'hhid' records to prevent silent data loss or arbitrary record selection.
    - Verifies non-zero key overlap between required modules; raises ValueError if zero overlap.
    - Fully reports unmatched and removed records in the audit dictionary and warnings.
    """
    warnings: List[str] = []
    audit: Dict[str, Any] = {
        "exact_duplicates_collapsed": {},
        "unmatched_records": {},
    }

    # 1. Deduplicate and audit Ménage module
    menage_clean, audit_m = _audit_and_deduplicate_module(menage_df, "Ménage")
    audit["exact_duplicates_collapsed"]["Ménage"] = audit_m["exact_duplicates_collapsed"]
    if audit_m["exact_duplicates_collapsed"] > 0:
        warnings.append(
            f"Collapsed {audit_m['exact_duplicates_collapsed']} exact identical duplicate records in Ménage module."
        )

    merged = menage_clean

    # 2. Deduplicate and merge Welfare module if supplied
    if welfare_df is not None:
        welfare_clean, audit_w = _audit_and_deduplicate_module(welfare_df, "Welfare")
        audit["exact_duplicates_collapsed"]["Welfare"] = audit_w["exact_duplicates_collapsed"]
        if audit_w["exact_duplicates_collapsed"] > 0:
            warnings.append(
                f"Collapsed {audit_w['exact_duplicates_collapsed']} exact identical duplicate records in Welfare module."
            )

        # Check key overlap
        m_keys = set(menage_clean["hhid"])
        w_keys = set(welfare_clean["hhid"])
        overlap = m_keys.intersection(w_keys)
        if len(overlap) == 0:
            raise ValueError(
                f"Zero overlapping 'hhid' identifiers between Ménage ({len(m_keys)} households) and "
                f"Welfare ({len(w_keys)} households) modules. Downstream inference cannot proceed."
            )

        unmatched_menage = len(m_keys) - len(overlap)
        unmatched_welfare = len(w_keys) - len(overlap)
        audit["unmatched_records"]["unmatched_menage_records"] = unmatched_menage
        audit["unmatched_records"]["unmatched_welfare_records"] = unmatched_welfare
        audit["matched_households"] = len(overlap)

        if unmatched_menage > 0 or unmatched_welfare > 0:
            warnings.append(
                f"Partial key overlap: {len(overlap)} households matched. "
                f"Omitted {unmatched_menage} unmatched Ménage records and {unmatched_welfare} unmatched Welfare records from joined dataset."
            )

        # Inner join to preserve consistent household records
        merged = merged.merge(welfare_clean, on="hhid", how="inner", suffixes=("", "_welfare"))

    # 3. Aggregate and merge individual roster if supplied
    if indiv_df is not None:
        indiv_agg, indiv_audit = aggregate_individual_module(indiv_df)
        audit["individual_aggregation"] = indiv_audit
        i_keys = set(indiv_agg["hhid"])
        m_keys = set(merged["hhid"])
        unmatched_indiv = len(m_keys - i_keys)
        audit["unmatched_records"]["unmatched_individual_households"] = unmatched_indiv
        if unmatched_indiv > 0:
            warnings.append(f"{unmatched_indiv} households in Ménage have no matching records in individual roster.")

        merged = merged.merge(indiv_agg, on="hhid", how="left")
        if "indiv_count" in merged.columns:
            merged["indiv_count"] = merged["indiv_count"].fillna(1.0)

    # 4. Strict Target & Expenditure Leakage Quarantine
    leaked_cols_found = [c for c in feature_contract.LEAKAGE_COLUMNS if c in merged.columns]
    if leaked_cols_found:
        warnings.append(f"Quarantined {len(leaked_cols_found)} target-leaking expenditure variables from feature matrix: {leaked_cols_found}")
        # Note: If 'poor' was provided, keep it in audit ground-truth storage, but remove from feature matrix
        audit["ground_truth_target"] = merged["poor"].copy() if "poor" in merged.columns else None
        merged = merged.drop(columns=[c for c in leaked_cols_found if c in merged.columns and c != "poor"])

    audit["final_merged_rows"] = len(merged)
    audit["warnings"] = warnings
    return merged, audit


# ── Feature Validation & Harmonization ──────────────────────────────────────

def validate_and_harmonize_survey(
    df_raw: pd.DataFrame,
    fallback_medians: Optional[Dict[str, float]] = None,
    canonical_features: Optional[List[str]] = None,
    allow_exploratory: bool = True,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Standardize raw external survey DataFrame into canonical model features.
    
    Robustness Guards:
      - Safely rejects empty, zero-row, or duplicate-column data.
      - Separates actual observation, deterministic derivation, and statistical imputation.
      - Enforces policy compatibility thresholds (COMPATIBLE vs EXPLORATORY vs INSUFFICIENT).
    """
    from .dashboard_utils import load_simulator_artifact

    artifact = load_simulator_artifact()
    if canonical_features is None:
        canonical_features = artifact.get("feature_cols", feature_contract.CANONICAL_FEATURES)
    if fallback_medians is None:
        fallback_medians = artifact.get("medians", {})

    warnings: List[str] = []
    errors: List[str] = []

    # 1. Guard against empty DataFrame or zero rows
    if df_raw is None or df_raw.empty or len(df_raw) == 0:
        return pd.DataFrame(columns=canonical_features), {
            "status": "INSUFFICIENT",
            "schema_compatibility": "INSUFFICIENT",
            "scientific_validation_status": "UNVALIDATED_EXTERNAL_DOMAIN",
            "eligibility_determination_permitted": False,
            "decision_boundary_notice": "Input dataset contains 0 rows or is empty; automated inference is blocked.",
            "status_message": "Uploaded survey contains 0 rows or is empty.",
            "reason": "Uploaded survey contains 0 rows or is empty.",
            "uploaded_rows": 0,
            "uploaded_columns": 0 if df_raw is None else len(df_raw.columns),
            "matched_count": 0,
            "observed_count": 0,
            "derived_count": 0,
            "imputed_count": len(canonical_features),
            "invalid_count": 0,
            "feature_coverage_pct": 0.0,
            "critical_coverage_pct": 0.0,
            "critical_domains_present": [],
            "critical_domains_missing": sorted(list(feature_contract.CRITICAL_DOMAINS)),
            "matched_features": [],
            "matched_mapping": {},
            "observed_features": [],
            "derived_features": [],
            "imputed_features": canonical_features,
            "invalid_features": [],
            "unmatched_columns": [],
            "warnings": ["Dataset contains zero household records."],
            "errors": ["Empty input dataset."],
        }

    # 2. Guard against duplicate column names in input
    if df_raw.columns.duplicated().any():
        dup_names = list(df_raw.columns[df_raw.columns.duplicated()].unique())
        warnings.append(f"Input contains duplicate column names: {dup_names}. Deduplicating columns by keeping first occurrence.")
        df_raw = df_raw.loc[:, ~df_raw.columns.duplicated()].copy()

    n_rows = len(df_raw)
    n_cols = len(df_raw.columns)

    # 3. Match columns via synonym lookup
    matched_mapping: Dict[str, str] = {}
    used_canonicals: Set[str] = set()
    unmatched_cols: List[str] = []

    for raw_col in df_raw.columns:
        canonical = normalize_column_name(raw_col)
        if canonical and canonical in canonical_features and canonical not in used_canonicals:
            matched_mapping[raw_col] = canonical
            used_canonicals.add(canonical)
        else:
            unmatched_cols.append(str(raw_col))

    # 4. Extract matched data, handle non-numeric values & types safely
    harmonized_dict: Dict[str, pd.Series] = {}
    invalid_features: List[str] = []
    observed_features: List[str] = []

    for raw_col, canonical in matched_mapping.items():
        s_raw = df_raw[raw_col]
        # Coerce to numeric safely
        s_num = pd.to_numeric(s_raw, errors="coerce")
        nan_count = int(s_num.isna().sum())

        if nan_count > (0.5 * n_rows) and int(s_raw.isna().sum()) < (0.5 * n_rows):
            # Column was largely text/unparseable non-numeric
            invalid_features.append(canonical)
            warnings.append(f"Column '{raw_col}' (mapped to '{canonical}') contains >50% non-numeric values; flagged as invalid.")
        else:
            observed_features.append(canonical)

        # Internal NaNs fill with fallback median
        median_val = fallback_medians.get(canonical, 0.0)
        harmonized_dict[canonical] = s_num.fillna(median_val)

    # 5. Deterministic Feature Derivation (e.g. eqadu1, eqadu2, indiv_count from hhsize)
    harmonized_dict, derived_features = feature_contract.derive_deterministic_features(harmonized_dict)

    # 6. Statistical Fallback Imputation for missing canonical features
    imputed_features: List[str] = []
    for col in canonical_features:
        if col not in harmonized_dict:
            imputed_features.append(col)
            median_val = fallback_medians.get(col, 0.0)
            harmonized_dict[col] = pd.Series([median_val] * n_rows, index=df_raw.index)

    # Build canonical DataFrame with strict feature order
    df_harmonized = pd.DataFrame(harmonized_dict)[canonical_features].fillna(0.0)

    # 7. Coverage and Critical Feature Policies
    total_model_features = len(canonical_features)
    grounded_count = len(observed_features) + len(derived_features)
    feature_coverage_pct = round((grounded_count / total_model_features) * 100, 1)

    # Check critical domain coverage
    critical_domains_present = set()
    for feat in observed_features + derived_features:
        domain = feature_contract.get_feature_domain(feat)
        if domain in feature_contract.CRITICAL_DOMAINS:
            critical_domains_present.add(domain)

    critical_domains_missing = sorted(list(feature_contract.CRITICAL_DOMAINS - critical_domains_present))
    critical_coverage_pct = round((len(critical_domains_present) / len(feature_contract.CRITICAL_DOMAINS)) * 100, 1)

    # Determine status according to policy
    if feature_coverage_pct >= 70.0 and len(critical_domains_missing) == 0:
        status = "COMPATIBLE"
        status_message = "Survey microdata satisfies standard schema coverage and includes all critical feature domains."
    elif feature_coverage_pct >= 30.0 and len(critical_domains_missing) <= 1:
        status = "EXPLORATORY"
        status_message = (
            f"Partial schema coverage ({feature_coverage_pct}%). "
            f"Missing critical domain: {critical_domains_missing}. Exploratory scoring only."
        )
        warnings.append(
            f"Exploratory mode active: {len(imputed_features)} of {total_model_features} features are statistically imputed. "
            "Policy decisions and certainty guarantees are disabled."
        )
    else:
        status = "INSUFFICIENT"
        status_message = (
            f"Insufficient feature coverage ({feature_coverage_pct}% < 30.0%) or missing multiple critical feature domains: "
            f"{critical_domains_missing}. Automated inference blocked."
        )
        errors.append(status_message)

    metadata = {
        "status": status,
        "schema_compatibility": status,
        "scientific_validation_status": "UNVALIDATED_EXTERNAL_DOMAIN",
        "eligibility_determination_permitted": False,
        "decision_boundary_notice": (
            "Model predictions are statistical risk assessments for research and planning only. "
            "Because the model has not been scientifically validated on this destination sovereign population, "
            "scores must NOT be used for verified aid eligibility or benefit-exclusion determinations."
        ),
        "status_message": status_message,
        "uploaded_rows": n_rows,
        "uploaded_columns": n_cols,
        "matched_count": len(matched_mapping),
        "observed_count": len(observed_features),
        "derived_count": len(derived_features),
        "imputed_count": len(imputed_features),
        "invalid_count": len(invalid_features),
        "feature_coverage_pct": feature_coverage_pct,
        "critical_coverage_pct": critical_coverage_pct,
        "critical_domains_present": sorted(list(critical_domains_present)),
        "critical_domains_missing": critical_domains_missing,
        "matched_features": sorted(list(matched_mapping.values())),
        "matched_mapping": matched_mapping,
        "observed_features": sorted(observed_features),
        "derived_features": sorted(derived_features),
        "imputed_features": sorted(imputed_features),
        "invalid_features": sorted(invalid_features),
        "unmatched_columns": unmatched_cols,
        "warnings": warnings,
        "errors": errors,
    }

    return df_harmonized, metadata


# Backward compatibility alias
harmonize_external_survey = validate_and_harmonize_survey


# ── Full Survey Evaluation Pipeline ─────────────────────────────────────────

def evaluate_external_survey(
    df_raw: pd.DataFrame,
    survey_title: str = "Uploaded Survey",
    policy_threshold: float = 0.35,
    alpha: float = 0.10,
    allow_exploratory: bool = True,
    destination_cal_data: Optional[Tuple[np.ndarray, np.ndarray]] = None,
) -> Dict[str, Any]:
    """
    End-to-end evaluation pipeline for unseen country / external survey upload:
    Harmonizes columns -> Compatibility policy check -> Domain shift diagnostics ->
    Qualified model inference -> Unvalidated conformal triage -> Guarded recourse.
    """
    from .dashboard_utils import load_simulator_artifact
    from .conformal import ConformalPovertyClassifier, load_calibrated_classifier
    from .recourse import compute_recourse

    artifact = load_simulator_artifact()
    if not artifact:
        raise RuntimeError("Simulator model artifact not found.")

    model = artifact["model"]
    feature_cols = artifact["feature_cols"]
    fallback_medians = artifact.get("medians", {})

    # 1. Harmonize & Validate Inputs
    df_clean, meta = validate_and_harmonize_survey(
        df_raw, fallback_medians, feature_cols, allow_exploratory=allow_exploratory
    )

    n_households = meta["uploaded_rows"]

    # 2. Check for ground-truth label in upload (for validation without leakage)
    ground_truth_poverty_rate = None
    y_true_external = None
    for cand in ["poor", "poverty", "is_poor"]:
        if cand in df_raw.columns:
            s_y = pd.to_numeric(df_raw[cand], errors="coerce").dropna()
            if len(s_y) == n_households:
                y_true_external = s_y.values.astype(int)
                ground_truth_poverty_rate = float(np.mean(y_true_external))
                break

    # 3. Domain Shift Diagnostics
    shift_diagnostics = domain_diagnostics.evaluate_domain_shift(
        df_raw, meta["matched_mapping"]
    )

    # 4. Handle INSUFFICIENT compatibility: abstain from scoring
    if meta["status"] == "INSUFFICIENT":
        audit_report = generate_survey_audit_report(survey_title, meta, shift_diagnostics, None, None)
        return {
            "status": "INSUFFICIENT",
            "schema_compatibility": "INSUFFICIENT",
            "scientific_validation_status": "UNVALIDATED_EXTERNAL_DOMAIN",
            "eligibility_determination_permitted": False,
            "decision_boundary_notice": (
                "Automated inference is blocked: uploaded microdata has insufficient schema coverage (<30%) "
                "or is missing multiple critical feature domains."
            ),
            "survey_title": survey_title,
            "metadata": meta,
            "domain_shift": shift_diagnostics,
            "n_households": n_households,
            "policy_headcount_rate": None,
            "ground_truth_poverty_rate": ground_truth_poverty_rate,
            "conformal_triage": None,
            "sample_recourse": None,
            "predictions_summary": None,
            "household_preview": [],
            "probs_list": [],
            "categories_list": [],
            "audit_report_markdown": audit_report,
            "message": (
                "Automated inference is blocked: uploaded microdata has insufficient schema coverage (<30%) "
                "or is missing multiple critical feature domains. See audit report for detailed missingness requirements."
            ),
        }

    # 5. Predict Probabilities (Compatible or Exploratory)
    probs = model.predict_proba(df_clean)[:, 1]
    is_poor_policy = (probs >= policy_threshold).astype(int)
    estimated_headcount = float(np.mean(is_poor_policy))

    schema_compatibility = meta["status"]
    scientific_validation_status = (
        "DESTINATION_CALIBRATED_UNVERIFIED_GENERALIZATION"
        if destination_cal_data is not None
        else "UNVALIDATED_EXTERNAL_DOMAIN"
    )
    eligibility_determination_permitted = False
    decision_boundary_notice = (
        "Model predictions are statistical risk assessments for research and planning only. "
        "Because the model has not been scientifically validated on this destination sovereign population, "
        "scores must NOT be used for verified aid eligibility or benefit-exclusion determinations."
    )

    # 6. Conformal Prediction Triage (Qualified for External Domain)
    # If destination-specific calibration data was provided, use it; otherwise use pooled classifier with external caveat
    if destination_cal_data is not None:
        p_cal, y_cal = destination_cal_data
        cp = ConformalPovertyClassifier(alpha=alpha).calibrate_destination(p_cal, y_cal)
        conformal_status = "DESTINATION_CALIBRATED"
        conformal_notice = (
            f"Calibrated on {len(y_cal)} destination-specific labeled households under stated exchangeability assumptions. "
            "Coverage guarantees remain conditional on data exchangeability and strict calibration/test separation."
        )
        triage_sets = cp.predict_sets(probs, is_external_unvalidated=False)
    else:
        cp = load_calibrated_classifier(alpha=alpha)
        conformal_status = "UNVALIDATED_EXTERNAL"
        conformal_notice = (
            "Unvalidated on external domain: Conformal prediction sets were calibrated on EHCVM training data. "
            "Because exchangeability is not established for this external survey, 90% coverage cannot be guaranteed."
        )
        triage_sets = cp.predict_sets(probs, is_external_unvalidated=True)

    categories = [s["category"] for s in triage_sets]

    n = len(df_clean)
    high_risk_pct = float(sum(1 for c in categories if "HIGH" in c or "POOR" in c) / n * 100) if n > 0 else 0.0
    low_risk_pct = float(sum(1 for c in categories if "LOW" in c or "NON_POOR" in c) / n * 100) if n > 0 else 0.0
    ambiguous_pct = float(sum(1 for c in categories if "AMBIGUOUS" in c) / n * 100) if n > 0 else 0.0

    # 7. Counterfactual Recourse (Suppressed or Guarded)
    recourse_sample = None
    if meta["status"] == "COMPATIBLE" and estimated_headcount > 0:
        worst_idx = int(np.argmax(probs))
        worst_hh = df_clean.iloc[worst_idx].to_dict()
        observed_set = set(meta["observed_features"])
        recourse_sample = compute_recourse(
            worst_hh, model, feature_cols,
            policy_threshold=policy_threshold,
            observed_features=observed_set,
        )
    elif meta["status"] == "EXPLORATORY":
        recourse_sample = {
            "status": "SUPPRESSED_EXPLORATORY",
            "message": (
                "Counterfactual recourse is suppressed for exploratory uploads: with partial feature coverage, "
                "algorithmic recommendations would rely heavily on imputed medians and produce ungrounded policy prescriptions."
            ),
        }

    # 8. Enriched household preview records (Explicitly Separated Statuses)
    hh_preview = []
    for i in range(min(100, n)):
        risk_tier = "HIGH_PREDICTED_RISK" if is_poor_policy[i] else "LOW_PREDICTED_RISK"
        if schema_compatibility == "EXPLORATORY":
            risk_tier += " [Exploratory]"
        hh_preview.append({
            "Household": i + 1,
            "Poverty_Probability": round(float(probs[i]), 3),
            "Model_Risk_Assessment": risk_tier,
            "Administrative_Eligibility": "BLOCKED (Unvalidated Domain)",
            "Conformal_Triage": categories[i].replace("_", " ").title(),
            "Schema_Compatibility": schema_compatibility,
            "Scientific_Validation": scientific_validation_status,
        })

    eval_result = {
        "status": schema_compatibility,
        "schema_compatibility": schema_compatibility,
        "scientific_validation_status": scientific_validation_status,
        "eligibility_determination_permitted": eligibility_determination_permitted,
        "decision_boundary_notice": decision_boundary_notice,
        "survey_title": survey_title,
        "metadata": meta,
        "domain_shift": shift_diagnostics,
        "n_households": n,
        "mean_poverty_probability": float(np.mean(probs)),
        "policy_headcount_rate": estimated_headcount,
        "ground_truth_poverty_rate": ground_truth_poverty_rate,
        "policy_threshold": policy_threshold,
        "conformal_status": conformal_status,
        "conformal_notice": conformal_notice,
        "conformal_triage": {
            "certain_poor_pct": high_risk_pct,
            "certain_non_poor_pct": low_risk_pct,
            "ambiguous_pct": ambiguous_pct,
            "status": conformal_status,
            "notice": conformal_notice,
            "coverage_guaranteed": False,
        },
        "sample_recourse": recourse_sample,
        "predictions_summary": {
            "min_prob": float(np.min(probs)),
            "p25_prob": float(np.percentile(probs, 25)),
            "median_prob": float(np.median(probs)),
            "p75_prob": float(np.percentile(probs, 75)),
            "max_prob": float(np.max(probs)),
        },
        "household_preview": hh_preview,
        "probs_list": [round(float(p), 4) for p in probs],
        "categories_list": categories,
    }

    eval_result["audit_report_markdown"] = generate_survey_audit_report(
        survey_title, meta, shift_diagnostics, eval_result, ground_truth_poverty_rate
    )

    return eval_result


def generate_survey_audit_report(
    survey_title: str,
    meta: Dict[str, Any],
    shift_diag: Dict[str, Any],
    eval_res: Optional[Dict[str, Any]],
    ground_truth_rate: Optional[float] = None,
) -> str:
    """Generate comprehensive, scientific audit report in Markdown."""
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    schema_compat = meta.get("schema_compatibility", meta.get("status", "UNKNOWN"))
    scientific_status = meta.get("scientific_validation_status", "UNVALIDATED_EXTERNAL_DOMAIN")

    md = [
        f"# Ingestion & Compatibility Audit Report: {survey_title}",
        f"**Generated**: {now_str}",
        f"- **Schema Compatibility Status**: `{schema_compat}`",
        f"- **Scientific Validation Status**: `{scientific_status}`",
        "- **Administrative Eligibility Decisions**: `STRICTLY PROHIBITED (UNVALIDATED DOMAIN)`\n",
        "## 0. Critical Distinction: Schema Compatibility vs. Scientific Validation",
        "- **Schema Compatibility**: Verifies that raw survey columns map to the 73 canonical model features, data types are parseable, and critical domains are observed.",
        "- **Scientific Validation**: Requires independent empirical verification of model accuracy, calibration, and demographic fairness on this destination country's population.",
        "- **Administrative Boundary**: A survey can be 100% schema compatible while the model remains entirely unvalidated on that population. Model scores represent purely statistical risk assessments for research and planning; they must **never** be used to determine verified cash-transfer aid enrollment or benefit exclusion without independent destination-country ground-truth evaluation.\n",
        "## 1. Input Validation & Schema Coverage",
        f"- **Total Rows Uploaded**: {meta['uploaded_rows']:,}",
        f"- **Total Columns Uploaded**: {meta['uploaded_columns']}",
        f"- **Feature Coverage**: {meta['feature_coverage_pct']}% ({meta['observed_count']} observed + {meta['derived_count']} derived / 73 canonical features)",
        f"- **Critical Domain Coverage**: {meta['critical_coverage_pct']}% ({len(meta['critical_domains_present'])} / {len(feature_contract.CRITICAL_DOMAINS)} domains)",
        f"- **Critical Domains Missing**: {', '.join(meta['critical_domains_missing']) if meta['critical_domains_missing'] else 'None (All Present)'}",
        f"- **Statistically Imputed Features**: {meta['imputed_count']} features filled with regional baseline medians.",
        f"- **Unmatched Uploaded Columns**: {len(meta['unmatched_columns'])} columns not mapped to canonical features.\n",
        "## 2. Domain-Shift Diagnostics",
        f"- **Overall Shift Index**: {shift_diag['overall_shift_index']}% ({shift_diag['overall_shift_level']} Shift)",
        f"- **Risk Assessment**: {shift_diag['risk_summary']}",
    ]

    if shift_diag["severe_alerts"]:
        md.append("- **Severe Shift Alerts**:")
        for a in shift_diag["severe_alerts"]:
            md.append(f"  - {a}")

    md.extend([
        "",
        "## 3. Scientific Disclaimers & Model Provenance",
        "- **Trained Model**: LightGBM Classifier (8-country West African EHCVM baseline).",
        "- **Calibration Validity**: Unvalidated on external destination survey. Conformal coverage is not guaranteed without destination-specific calibration data.",
        "- **Causal Policy Boundary**: Counterfactual recourse represents algorithmic sensitivity of the statistical model, NOT empirical proof of causal poverty alleviation.",
    ])

    if eval_res and eval_res.get("policy_headcount_rate") is not None:
        md.extend([
            "",
            "## 4. Inference & Targeting Summary",
            f"- **Model Estimated Headcount Rate**: {eval_res['policy_headcount_rate']:.1%}",
            f"- **Policy Threshold (tau*)**: {eval_res['policy_threshold']}",
            f"- **Mean Poverty Probability**: {eval_res['mean_poverty_probability']:.1%}",
        ])
        if ground_truth_rate is not None:
            gap = abs(eval_res['policy_headcount_rate'] - ground_truth_rate)
            md.append(f"- **Survey Ground-Truth Rate**: {ground_truth_rate:.1%} (Headcount Error: {gap*100:.1f} pp)")

    return "\n".join(md)
