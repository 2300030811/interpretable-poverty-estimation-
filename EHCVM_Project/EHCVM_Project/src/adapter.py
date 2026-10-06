"""
adapter.py — Universal Survey Adapter & Domain Generalisation Ingestion.

Enables seamless zero-shot ingestion and poverty prediction for new surveys and
unseen countries with arbitrary column names and variable subsets.
Features:
1. Multilingual synonym normalization (English, French, World Bank LSMS / DHS naming).
2. Robust schema imputation using regional median baselines.
3. Automated inference, conformal triage, and counterfactual policy generation.
"""
from typing import Dict, List, Tuple, Any, Optional
import re
import numpy as np
import pandas as pd

from . import config

# Comprehensive Multilingual Synonym Dictionary
SYNONYM_DICTIONARY = {
    # Housing & Shelter
    "toit": ["roof", "roof_type", "roof_material", "roofing", "toiture", "type_toit", "type_toiture", "materiau_toit"],
    "mur": ["wall", "wall_type", "wall_material", "walls", "type_mur"],
    "sol": ["floor", "floor_type", "floor_material", "flooring", "type_sol"],
    "logem": ["dwelling", "dwelling_type", "housing_type", "type_logement", "housing"],
    "toilet": ["toilet", "latrine", "sanitation", "sanitation_type", "type_toilette", "wc"],
    "eauboi_ss": ["drinking_water", "water_source", "dry_season_water", "water", "eau_boisson", "source_eau"],
    "eauboi_sp": ["rainy_water", "rainy_season_water", "eau_hivernage"],
    "ordure": ["trash", "waste", "garbage_disposal", "dechets", "ordures"],
    "eva_toi": ["toilet_drainage", "sewage", "evacuation_toilette"],
    "eva_eau": ["water_drainage", "evacuation_eau"],

    # Assets & Electrification
    "elec_ac": ["electricity", "grid_electricity", "electric_grid", "power", "electricite", "reseau_electrique"],
    "elec_ur": ["solar", "solar_electricity", "offgrid_solar", "panneau_solaire"],
    "elec_ua": ["generator", "battery_power", "groupe_electrogene"],
    "tv": ["television", "tv_set", "televiseur"],
    "frigo": ["fridge", "refrigerator", "cooler", "refrigerateur"],
    "car": ["car", "automobile", "vehicle", "motor_car", "voiture", "auto"],
    "decod": ["satellite", "cable_tv", "decoder", "decodeur", "canal"],
    "ordin": ["computer", "pc", "laptop", "ordinateur"],
    "cuisin": ["cooker", "stove", "gas_stove", "cuisiniere"],
    "fer": ["iron", "electric_iron", "fer_repasser"],

    # Connectivity, Finance & Labor
    "ind_telpor": ["mobile_phone", "cellphone", "phone", "phones_count", "telephone", "portable"],
    "ind_internet": ["internet", "internet_access", "web_access", "connexion_internet"],
    "ind_bank": ["bank", "bank_account", "banking", "mobile_money", "compte_bancaire", "banque"],
    "ind_salaire": ["wage_earners", "formal_salary", "salaried_workers", "salaries", "salaire"],
    "ind_activ7j": ["workers_7d", "active_workers", "employed_members", "actifs_7j"],
    "ind_activ12m": ["active_12m", "economically_active", "actifs_12m"],
    "ind_diplome": ["diploma", "degrees_count", "certified_members", "diplomes"],
    "ind_educ_hi": ["highest_education", "max_education_level", "education_chef", "niveau_education"],
    "ind_mal30j": ["sick_members", "illness_30d", "health_shock", "malades_30j"],

    # Demographics
    "hhsize": ["household_size", "hh_size", "family_size", "members_count", "taille_menage"],
    "hgender": ["head_gender", "gender_head", "sex_head", "sexe_chef", "genre_chef"],
    "hage": ["head_age", "age_head", "age_chef"],
    "milieu": ["urban_rural", "area_type", "setting", "residence_milieu", "milieu_residence"],
    "superf": ["land_area", "agricultural_land", "farm_size", "superficie_agricole", "superficie"],
    "grosrum": ["cattle", "cows", "large_livestock", "bovins", "gros_ruminants"],
    "petitrum": ["goats", "sheep", "small_livestock", "caprins", "ovins", "petits_ruminants"],
    "volail": ["poultry", "chickens", "volaille"],
}

# Reverse index: normalized string -> canonical feature
NORMALIZED_SYNONYM_LOOKUP = {}
for canonical, aliases in SYNONYM_DICTIONARY.items():
    NORMALIZED_SYNONYM_LOOKUP[canonical.lower()] = canonical
    for alias in aliases:
        clean_alias = re.sub(r"[^a-z0-9]", "", alias.lower())
        NORMALIZED_SYNONYM_LOOKUP[clean_alias] = canonical


def normalize_column_name(col: str) -> Optional[str]:
    """Match raw column name to canonical EHCVM feature name."""
    clean = re.sub(r"[^a-z0-9]", "", col.lower())
    return NORMALIZED_SYNONYM_LOOKUP.get(clean)


def harmonize_external_survey(
    df_raw: pd.DataFrame,
    fallback_medians: Optional[Dict[str, float]] = None,
    canonical_features: Optional[List[str]] = None,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Standardize arbitrary external survey DataFrame into canonical model features.
    Missing features are imputed using regional fallback medians.
    """
    from .dashboard_utils import load_simulator_artifact

    artifact = load_simulator_artifact()
    if canonical_features is None:
        canonical_features = artifact.get("feature_cols", [])
    if fallback_medians is None:
        fallback_medians = artifact.get("medians", {})

    n_rows = len(df_raw)
    matched_mapping = {}
    used_canonicals = set()

    # 1. Match columns via synonym lookup
    for raw_col in df_raw.columns:
        canonical = normalize_column_name(raw_col)
        if canonical and canonical in canonical_features and canonical not in used_canonicals:
            matched_mapping[raw_col] = canonical
            used_canonicals.add(canonical)

    # 2. Extract matched data and coerce to numeric
    harmonized_dict = {}
    for raw_col, canonical in matched_mapping.items():
        harmonized_dict[canonical] = pd.to_numeric(df_raw[raw_col], errors="coerce")

    # 3. Impute missing canonical features using regional medians
    imputed_features = []
    for col in canonical_features:
        if col in harmonized_dict:
            # Fill internal NaNs
            median_val = fallback_medians.get(col, 0.0)
            harmonized_dict[col] = harmonized_dict[col].fillna(median_val)
        else:
            imputed_features.append(col)
            median_val = fallback_medians.get(col, 0.0)
            harmonized_dict[col] = pd.Series([median_val] * n_rows, index=df_raw.index)

    # 4. Handle adult equivalent scales if hhsize was matched
    if "hhsize" in used_canonicals:
        size = harmonized_dict["hhsize"]
        if "eqadu1" not in used_canonicals:
            harmonized_dict["eqadu1"] = 1.0 + 0.7 * np.maximum(0.0, size - 1.0)
        if "eqadu2" not in used_canonicals:
            harmonized_dict["eqadu2"] = np.sqrt(np.maximum(1.0, size))
        if "indiv_count" not in used_canonicals:
            harmonized_dict["indiv_count"] = size

    # Build canonical DataFrame with strict feature order
    df_harmonized = pd.DataFrame(harmonized_dict)[canonical_features].fillna(0.0)

    metadata = {
        "uploaded_rows": n_rows,
        "uploaded_columns": len(df_raw.columns),
        "matched_features": sorted(list(used_canonicals)),
        "imputed_features": sorted(imputed_features),
        "matched_count": len(used_canonicals),
        "imputed_count": len(imputed_features),
        "coverage_ratio_pct": round(len(used_canonicals) / len(canonical_features) * 100, 1),
    }

    return df_harmonized, metadata


def evaluate_external_survey(
    df_raw: pd.DataFrame,
    survey_title: str = "Uploaded Survey",
    policy_threshold: float = 0.35,
    alpha: float = 0.10,
) -> Dict[str, Any]:
    """
    End-to-end evaluation pipeline for unseen country / survey upload:
    Harmonizes columns -> Model inference -> Conformal triage -> Recourse sample.
    """
    from .dashboard_utils import load_simulator_artifact
    from .conformal import ConformalPovertyClassifier
    from .recourse import compute_recourse

    artifact = load_simulator_artifact()
    if not artifact:
        raise RuntimeError("Simulator model artifact not found.")

    model = artifact["model"]
    feature_cols = artifact["feature_cols"]
    fallback_medians = artifact.get("medians", {})

    # 1. Harmonize
    df_clean, meta = harmonize_external_survey(df_raw, fallback_medians, feature_cols)

    # 2. Predict Probabilities
    probs = model.predict_proba(df_clean)[:, 1]
    is_poor_policy = (probs >= policy_threshold).astype(int)
    headcount = float(np.mean(is_poor_policy))

    # 3. Conformal Prediction Triage
    cp = ConformalPovertyClassifier(alpha=alpha)
    # Using baseline q_hat ~ 0.50 if calibration not passed
    cp.q_hat = 0.50
    triage_sets = cp.predict_sets(probs)
    categories = [s["category"] for s in triage_sets]
    n = len(df_clean)

    certain_poor_pct = float(categories.count("CERTAIN_POOR") / n * 100) if n > 0 else 0.0
    certain_non_poor_pct = float(categories.count("CERTAIN_NON_POOR") / n * 100) if n > 0 else 0.0
    ambiguous_pct = float(categories.count("AMBIGUOUS") / n * 100) if n > 0 else 0.0

    # 4. Compute Sample Recourse on worst predicted household
    recourse_sample = None
    if headcount > 0:
        worst_idx = int(np.argmax(probs))
        worst_hh = df_clean.iloc[worst_idx].to_dict()
        recourse_sample = compute_recourse(worst_hh, model, feature_cols, policy_threshold=policy_threshold)

    # 5. Enriched household preview records
    hh_preview = []
    for i in range(min(100, n)):
        hh_preview.append({
            "Household": i + 1,
            "Poverty_Probability": round(float(probs[i]), 3),
            "Policy_Decision": "POOR (Eligible)" if is_poor_policy[i] else "NON-POOR",
            "Conformal_Triage": categories[i].replace("_", " ").title(),
        })

    return {
        "survey_title": survey_title,
        "metadata": meta,
        "n_households": n,
        "mean_poverty_probability": float(np.mean(probs)),
        "policy_headcount_rate": headcount,
        "policy_threshold": policy_threshold,
        "conformal_triage": {
            "certain_poor_pct": certain_poor_pct,
            "certain_non_poor_pct": certain_non_poor_pct,
            "ambiguous_pct": ambiguous_pct,
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


if __name__ == "__main__":
    print("Testing Universal Survey Adapter...")
    # Synthetic unseen survey with English column names and only 12 features
    synthetic_external = pd.DataFrame({
        "household_id": [101, 102, 103, 104, 105],
        "family_size": [10, 8, 4, 3, 2],
        "grid_electricity": [0, 0, 1, 1, 1],
        "cellphone": [0, 1, 2, 3, 2],
        "bank_account": [0, 0, 1, 2, 2],
        "wage_earners": [0, 0, 1, 1, 2],
        "roof_material": [1, 2, 3, 3, 4],
        "floor_material": [1, 1, 3, 4, 4],
        "toilet_type": [0, 1, 2, 3, 3],
        "drinking_water": [0, 0, 1, 1, 1],
        "head_age": [52, 44, 38, 41, 60],
        "urban_rural": [2, 2, 1, 1, 1],
    })

    eval_result = evaluate_external_survey(synthetic_external, survey_title="Ghana Living Standards Survey (GLSS 7)")
    print(f"Survey: {eval_result['survey_title']}")
    print(f"Matched features: {eval_result['metadata']['matched_count']} / {len(eval_result['metadata']['matched_features'] + eval_result['metadata']['imputed_features'])}")
    print(f"Predicted poverty headcount: {eval_result['policy_headcount_rate']:.1%}")
    print(f"Conformal Triage: Certain Poor={eval_result['conformal_triage']['certain_poor_pct']:.0f}%, "
          f"Certain Non-Poor={eval_result['conformal_triage']['certain_non_poor_pct']:.0f}%, "
          f"Ambiguous={eval_result['conformal_triage']['ambiguous_pct']:.0f}%")
    if eval_result["sample_recourse"]:
        print(f"Sample Recourse status: {eval_result['sample_recourse']['status']}")
    assert eval_result["n_households"] == 5
    assert eval_result["policy_headcount_rate"] > 0
    print("Universal Survey Adapter self-check passed!")
