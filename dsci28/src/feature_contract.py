"""
feature_contract.py — Formal Schema and Feature Contract for Cross-Country Poverty Estimation.

Defines the 73 canonical features, expected types, plausible ranges, critical domains,
deterministic derivations, target-leakage quarantine, and baseline reference distributions.
"""
from typing import Dict, List, Any, Optional, Tuple
import math
from pathlib import Path
import json
import numpy as np
import pandas as pd

from . import config

# ── Feature Domains ─────────────────────────────────────────────────────────
DOMAIN_HOUSING = "Housing Quality"
DOMAIN_WASH = "WASH (Water & Sanitation)"
DOMAIN_ELEC = "Electrification & Energy"
DOMAIN_ASSETS = "Durable Assets"
DOMAIN_AGRI = "Land & Livestock"
DOMAIN_SHOCKS = "Vulnerability Shocks"
DOMAIN_HEAD_DEMO = "Household Head Demographics"
DOMAIN_HH_COMP = "Household Composition & Geography"
DOMAIN_INDIV = "Individual Roster Aggregates"

# Critical feature domains required for reliable cross-country estimation
CRITICAL_DOMAINS = {
    DOMAIN_HOUSING,
    DOMAIN_WASH,
    DOMAIN_ELEC,
    DOMAIN_ASSETS,
    DOMAIN_HH_COMP,
    DOMAIN_HEAD_DEMO,
}

# ── Target & Leakage Quarantine ─────────────────────────────────────────────
TARGET_COL = "poor"
LEAKAGE_COLUMNS = [
    "pcexp", "zref", "dali", "dnal", "dtot", "def_spa", "def_temp",
    "poor", "poverty", "is_poor", "statut_pauvrete", "depense_pc"
]

# ── 73 Canonical Feature Definitions ────────────────────────────────────────
# Maps canonical name -> metadata
CANONICAL_FEATURE_CONTRACT = {
    # Housing Quality
    "logem": {"domain": DOMAIN_HOUSING, "type": "categorical_code", "range": (1, 6), "desc": "Dwelling tenancy type"},
    "mur": {"domain": DOMAIN_HOUSING, "type": "categorical_code", "range": (1, 6), "desc": "Wall construction material"},
    "toit": {"domain": DOMAIN_HOUSING, "type": "categorical_code", "range": (1, 6), "desc": "Roof construction material"},
    "sol": {"domain": DOMAIN_HOUSING, "type": "categorical_code", "range": (1, 6), "desc": "Floor construction material"},

    # WASH
    "eauboi_ss": {"domain": DOMAIN_WASH, "type": "categorical_code", "range": (1, 15), "desc": "Dry season drinking water source"},
    "eauboi_sp": {"domain": DOMAIN_WASH, "type": "categorical_code", "range": (1, 15), "desc": "Rainy season drinking water source"},
    "toilet": {"domain": DOMAIN_WASH, "type": "categorical_code", "range": (1, 10), "desc": "Sanitation / latrine facility type"},
    "eva_toi": {"domain": DOMAIN_WASH, "type": "categorical_code", "range": (1, 6), "desc": "Toilet waste drainage mechanism"},
    "eva_eau": {"domain": DOMAIN_WASH, "type": "categorical_code", "range": (1, 6), "desc": "Domestic wastewater drainage"},
    "ordure": {"domain": DOMAIN_WASH, "type": "categorical_code", "range": (1, 7), "desc": "Solid waste / garbage disposal"},

    # Electrification
    "elec_ac": {"domain": DOMAIN_ELEC, "type": "binary", "range": (0, 1), "desc": "Connection to national electric grid"},
    "elec_ur": {"domain": DOMAIN_ELEC, "type": "binary", "range": (0, 1), "desc": "Solar home system / off-grid electricity"},
    "elec_ua": {"domain": DOMAIN_ELEC, "type": "binary", "range": (0, 1), "desc": "Diesel generator / private battery electricity"},

    # Durable Assets
    "tv": {"domain": DOMAIN_ASSETS, "type": "binary", "range": (0, 1), "desc": "Television set ownership"},
    "fer": {"domain": DOMAIN_ASSETS, "type": "binary", "range": (0, 1), "desc": "Electric iron ownership"},
    "frigo": {"domain": DOMAIN_ASSETS, "type": "binary", "range": (0, 1), "desc": "Refrigerator / freezer ownership"},
    "cuisin": {"domain": DOMAIN_ASSETS, "type": "binary", "range": (0, 1), "desc": "Modern gas/electric stove ownership"},
    "ordin": {"domain": DOMAIN_ASSETS, "type": "binary", "range": (0, 1), "desc": "Computer / laptop ownership"},
    "decod": {"domain": DOMAIN_ASSETS, "type": "binary", "range": (0, 1), "desc": "TV decoder / satellite receiver"},
    "car": {"domain": DOMAIN_ASSETS, "type": "binary", "range": (0, 1), "desc": "Motor vehicle / car ownership"},

    # Land & Livestock
    "superf": {"domain": DOMAIN_AGRI, "type": "continuous", "range": (0.0, 500.0), "desc": "Agricultural land farmed (hectares)"},
    "grosrum": {"domain": DOMAIN_AGRI, "type": "integer_count", "range": (0, 500), "desc": "Cattle and large ruminants head count"},
    "petitrum": {"domain": DOMAIN_AGRI, "type": "integer_count", "range": (0, 500), "desc": "Goats and sheep head count"},
    "porc": {"domain": DOMAIN_AGRI, "type": "integer_count", "range": (0, 200), "desc": "Pigs count"},
    "lapin": {"domain": DOMAIN_AGRI, "type": "integer_count", "range": (0, 500), "desc": "Rabbits and small poultry count"},
    "volail": {"domain": DOMAIN_AGRI, "type": "integer_count", "range": (0, 1000), "desc": "Poultry / chicken head count"},

    # Vulnerability Shocks
    "sh_id_demo": {"domain": DOMAIN_SHOCKS, "type": "binary", "range": (0, 1), "desc": "Demographic shock (death/illness of breadwinner)"},
    "sh_co_natu": {"domain": DOMAIN_SHOCKS, "type": "binary", "range": (0, 1), "desc": "Natural disaster shock (drought/flood)"},
    "sh_co_eco": {"domain": DOMAIN_SHOCKS, "type": "binary", "range": (0, 1), "desc": "Macroeconomic shock (inflation/price surge)"},
    "sh_id_eco": {"domain": DOMAIN_SHOCKS, "type": "binary", "range": (0, 1), "desc": "Idiosyncratic economic shock (job loss/theft)"},
    "sh_co_vio": {"domain": DOMAIN_SHOCKS, "type": "binary", "range": (0, 1), "desc": "Violence / conflict shock"},
    "sh_co_oth": {"domain": DOMAIN_SHOCKS, "type": "binary", "range": (0, 1), "desc": "Other collective community shock"},

    # Household Head Demographics
    "hgender": {"domain": DOMAIN_HEAD_DEMO, "type": "binary", "range": (1, 2), "desc": "Household head gender (1=Male, 2=Female)"},
    "hage": {"domain": DOMAIN_HEAD_DEMO, "type": "integer_count", "range": (15, 115), "desc": "Household head age in years"},
    "hmstat": {"domain": DOMAIN_HEAD_DEMO, "type": "categorical_code", "range": (1, 6), "desc": "Marital status of head"},
    "hreligion": {"domain": DOMAIN_HEAD_DEMO, "type": "categorical_code", "range": (1, 5), "desc": "Religion of household head"},
    "hnation": {"domain": DOMAIN_HEAD_DEMO, "type": "categorical_code", "range": (1, 3), "desc": "Nationality status of head"},
    "hethnie": {"domain": DOMAIN_HEAD_DEMO, "type": "categorical_code", "range": (0, 99), "desc": "Ethnic group code of head"},
    "halfa": {"domain": DOMAIN_HEAD_DEMO, "type": "binary", "range": (0, 1), "desc": "Head literacy in national/official language"},
    "halfa2": {"domain": DOMAIN_HEAD_DEMO, "type": "binary", "range": (0, 1), "desc": "Head literacy in local language"},
    "heduc": {"domain": DOMAIN_HEAD_DEMO, "type": "categorical_code", "range": (0, 7), "desc": "Head education level"},
    "hdiploma": {"domain": DOMAIN_HEAD_DEMO, "type": "categorical_code", "range": (0, 8), "desc": "Head formal diploma obtained"},
    "hhandig": {"domain": DOMAIN_HEAD_DEMO, "type": "binary", "range": (0, 1), "desc": "Head severe disability status"},
    "hactiv7j": {"domain": DOMAIN_HEAD_DEMO, "type": "binary", "range": (0, 1), "desc": "Head economically active in past 7 days"},
    "hactiv12m": {"domain": DOMAIN_HEAD_DEMO, "type": "binary", "range": (0, 1), "desc": "Head economically active in past 12 months"},
    "hbranch": {"domain": DOMAIN_HEAD_DEMO, "type": "categorical_code", "range": (0, 15), "desc": "Head sector / industry of employment"},
    "hsectins": {"domain": DOMAIN_HEAD_DEMO, "type": "categorical_code", "range": (0, 5), "desc": "Head institutional sector (formal/informal)"},
    "hcsp": {"domain": DOMAIN_HEAD_DEMO, "type": "categorical_code", "range": (0, 10), "desc": "Head socio-professional category"},

    # Household Composition & Geography
    "hhsize": {"domain": DOMAIN_HH_COMP, "type": "integer_count", "range": (1, 60), "desc": "Total household resident members count"},
    "eqadu1": {"domain": DOMAIN_HH_COMP, "type": "continuous", "range": (1.0, 50.0), "desc": "OECD adult equivalent units (Scale 1)"},
    "eqadu2": {"domain": DOMAIN_HH_COMP, "type": "continuous", "range": (1.0, 10.0), "desc": "Square root adult equivalent units (Scale 2)"},
    "milieu": {"domain": DOMAIN_HH_COMP, "type": "categorical_code", "range": (1, 2), "desc": "Place of residence (1=Urban, 2=Rural)"},
    "zae": {"domain": DOMAIN_HH_COMP, "type": "categorical_code", "range": (1, 10), "desc": "Agro-ecological zone code"},

    # Individual Roster Aggregates (Household Level)
    "indiv_count": {"domain": DOMAIN_INDIV, "type": "integer_count", "range": (1, 60), "desc": "Total individual roster count"},
    "ind_age": {"domain": DOMAIN_INDIV, "type": "continuous", "range": (0.0, 100.0), "desc": "Mean age of household members"},
    "ind_sexe": {"domain": DOMAIN_INDIV, "type": "continuous", "range": (1.0, 2.0), "desc": "Mean gender ratio of members"},
    "ind_alfa": {"domain": DOMAIN_INDIV, "type": "continuous", "range": (0.0, 1.0), "desc": "Share of members literate in official language"},
    "ind_alfa2": {"domain": DOMAIN_INDIV, "type": "continuous", "range": (0.0, 1.0), "desc": "Share of members literate in local language"},
    "ind_scol": {"domain": DOMAIN_INDIV, "type": "continuous", "range": (0.0, 1.0), "desc": "Share of school-age children attending school"},
    "ind_educ_hi": {"domain": DOMAIN_INDIV, "type": "continuous", "range": (0.0, 6.0), "desc": "Highest educational attainment in household"},
    "ind_diplome": {"domain": DOMAIN_INDIV, "type": "continuous", "range": (0.0, 6.0), "desc": "Highest diploma attained in household"},
    "ind_telpor": {"domain": DOMAIN_INDIV, "type": "integer_count", "range": (0, 30), "desc": "Count of mobile phone owners in household"},
    "ind_internet": {"domain": DOMAIN_INDIV, "type": "integer_count", "range": (0, 30), "desc": "Count of members with internet access"},
    "ind_bank": {"domain": DOMAIN_INDIV, "type": "integer_count", "range": (0, 30), "desc": "Count of members with bank/mobile money"},
    "ind_activ7j": {"domain": DOMAIN_INDIV, "type": "continuous", "range": (0.0, 1.0), "desc": "Share of members working past 7 days"},
    "ind_activ12m": {"domain": DOMAIN_INDIV, "type": "continuous", "range": (0.0, 1.0), "desc": "Share of members active past 12 months"},
    "ind_mal30j": {"domain": DOMAIN_INDIV, "type": "integer_count", "range": (0, 30), "desc": "Members experiencing illness in past 30 days"},
    "ind_couvmal": {"domain": DOMAIN_INDIV, "type": "continuous", "range": (0.0, 1.0), "desc": "Share of members covered by health insurance"},
    "ind_moustiq": {"domain": DOMAIN_INDIV, "type": "continuous", "range": (0.0, 1.0), "desc": "Share of members sleeping under bed nets"},
    "ind_salaire": {"domain": DOMAIN_INDIV, "type": "continuous", "range": (0.0, 1.0), "desc": "Share of members receiving formal salary"},
    "ind_hos12m": {"domain": DOMAIN_INDIV, "type": "binary", "range": (0, 1), "desc": "Any member hospitalized in past 12 months"},
    "ind_emploi_sec": {"domain": DOMAIN_INDIV, "type": "binary", "range": (0, 1), "desc": "Any member with secondary employment"},
    "ind_handig": {"domain": DOMAIN_INDIV, "type": "binary", "range": (0, 1), "desc": "Any member with severe disability"},
}

CANONICAL_FEATURES = sorted(list(CANONICAL_FEATURE_CONTRACT.keys()))
assert len(CANONICAL_FEATURES) == 73, f"Expected 73 canonical features, got {len(CANONICAL_FEATURES)}"


def get_feature_domain(feature_name: str) -> str:
    """Return the policy/survey domain for a given canonical feature."""
    meta = CANONICAL_FEATURE_CONTRACT.get(feature_name)
    return meta["domain"] if meta else "Other"


def is_critical_feature(feature_name: str) -> bool:
    """Return True if feature belongs to one of the 6 critical feature domains."""
    return get_feature_domain(feature_name) in CRITICAL_DOMAINS


def load_baseline_reference_stats() -> Dict[str, Dict[str, float]]:
    """
    Load pre-computed empirical distributions (medians, IQR, ranges)
    for the 73 canonical features from the 55,922 EHCVM households.
    """
    stats_file = config.OUTPUT_MODELS / "feature_baseline_stats.json"
    if stats_file.exists():
        try:
            return json.loads(stats_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    # Fallback to defaults if file missing
    return {
        col: {
            "median": 0.0,
            "q25": 0.0,
            "q75": 1.0,
            "mean": 0.0,
            "std": 1.0,
            "min": CANONICAL_FEATURE_CONTRACT[col]["range"][0],
            "max": CANONICAL_FEATURE_CONTRACT[col]["range"][1],
        }
        for col in CANONICAL_FEATURES
    }


def derive_deterministic_features(df_dict: Dict[str, pd.Series]) -> Tuple[Dict[str, pd.Series], List[str]]:
    """
    Compute mathematically deterministic derived features from observed base inputs.
    Specifically:
      - eqadu1 = 1.0 + 0.7 * max(0.0, hhsize - 1.0)
      - eqadu2 = sqrt(max(1.0, hhsize))
      - indiv_count = hhsize (when individual roster count is absent)
    Returns updated dictionary and list of derived feature names.
    """
    derived = []
    if "hhsize" in df_dict:
        hhsize = df_dict["hhsize"]
        if "eqadu1" not in df_dict:
            df_dict["eqadu1"] = 1.0 + 0.7 * np.maximum(0.0, hhsize - 1.0)
            derived.append("eqadu1")
        if "eqadu2" not in df_dict:
            df_dict["eqadu2"] = np.sqrt(np.maximum(1.0, hhsize))
            derived.append("eqadu2")
        if "indiv_count" not in df_dict:
            df_dict["indiv_count"] = hhsize
            derived.append("indiv_count")
    return df_dict, derived
