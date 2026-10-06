"""
config.py — Country metadata, file paths, and column definitions for EHCVM 2021.
"""
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_RAW = PROJECT_ROOT / "data"
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"
OUTPUT_EDA = PROJECT_ROOT / "outputs" / "eda"
DB_PATH = DATA_PROCESSED / "ehcvm.duckdb"

# ── Country registry ─────────────────────────────────────────────────────────
# code is the ISO-ish suffix used in EHCVM filenames
COUNTRIES = {
    "Benin":          {"code": "ben", "folder": "Benin"},
    "Burkina Faso":   {"code": "bfa", "folder": "Burkina Faso"},
    "Côte d'Ivoire":  {"code": "civ", "folder": "Côte d'Ivoire"},
    "Guinea-Bissau":  {"code": "gnb", "folder": "Guinea-Bissau"},
    "Mali":           {"code": "mli", "folder": "Mali"},
    "Niger":          {"code": "ner", "folder": "Niger"},
    "Senegal":        {"code": "sen", "folder": "Senegal"},
    "Togo":           {"code": "tgo", "folder": "Togo"},
}

# Burkina Faso has a differently-named welfare file
WELFARE_OVERRIDES = {
    "Burkina Faso": "ehcvm_welfare_2b_bfa2021.csv",
}


def get_file_paths(country_name: str) -> dict[str, Path]:
    """Return dict with keys 'menage', 'welfare', 'individu' → absolute CSV paths."""
    meta = COUNTRIES[country_name]
    code, folder = meta["code"], meta["folder"]
    base = DATA_RAW / folder

    welfare_file = WELFARE_OVERRIDES.get(
        country_name, f"ehcvm_welfare_{code}2021.csv"
    )
    return {
        "menage":   base / f"ehcvm_menage_{code}2021.csv",
        "welfare":  base / welfare_file,
        "individu": base / f"ehcvm_individu_{code}2021.csv",
    }


# ── Column groups (common across all 8 countries) ────────────────────────────
# Identifiers / join keys (excluded from features)
ID_COLS = ["country", "hhid", "grappe", "menage", "vague", "year"]

# menage: housing quality
HOUSING_COLS = ["logem", "mur", "toit", "sol"]

# menage: water & sanitation
WASH_COLS = ["eauboi_ss", "eauboi_sp", "toilet", "eva_toi", "eva_eau", "ordure"]

# menage: electricity
ELEC_COLS = ["elec_ac", "elec_ur", "elec_ua"]

# menage: durable assets
ASSET_COLS = ["tv", "fer", "frigo", "cuisin", "ordin", "decod", "car"]

# menage: land & livestock
AGRI_COLS = ["superf", "grosrum", "petitrum", "porc", "lapin", "volail"]

# menage: shocks
SHOCK_COLS = ["sh_id_demo", "sh_co_natu", "sh_co_eco", "sh_id_eco", "sh_co_vio", "sh_co_oth"]

# All menage feature columns
MENAGE_FEATURE_COLS = HOUSING_COLS + WASH_COLS + ELEC_COLS + ASSET_COLS + AGRI_COLS + SHOCK_COLS

# welfare: household-head demographics
HEAD_DEMO_COLS = [
    "hgender", "hage", "hmstat", "hreligion", "hnation", "hethnie",
    "halfa", "halfa2", "heduc", "hdiploma", "hhandig",
    "hactiv7j", "hactiv12m", "hbranch", "hsectins", "hcsp",
]

# welfare: household composition & geography
HH_COMP_COLS = ["hhsize", "eqadu1", "eqadu2", "milieu", "zae"]

# welfare: expenditure (target source)
EXPENDITURE_COLS = ["pcexp", "zref", "dali", "dnal", "dtot", "def_spa", "def_temp"]

# welfare: all feature columns (excluding target-source cols that leak)
WELFARE_FEATURE_COLS = HEAD_DEMO_COLS + HH_COMP_COLS

# Target construction
TARGET_COL = "poor"  # binary: 1 if pcexp < zref

# individu: columns to aggregate to household level
INDIV_NUMERIC_AGG = [
    "age", "sexe", "alfa", "alfa2", "scol", "educ_hi", "diplome",
    "telpor", "internet", "bank", "activ7j", "activ12m",
    "mal30j", "couvmal", "moustiq", "salaire",
]

INDIV_BINARY_AGG = [
    "hos12m", "emploi_sec", "handig",
]

# ── O2–O5 Model and evaluation settings ──────────────────────────────────────
RANDOM_SEED = 42
OUTPUT_MODELS = PROJECT_ROOT / "outputs" / "models"
OUTPUT_RESULTS = PROJECT_ROOT / "outputs" / "results"
OUTPUT_ACCEPTANCE = PROJECT_ROOT / "outputs" / "acceptance"

# Features to exclude from modelling (identifiers + target)
EXCLUDE_FROM_FEATURES = ["hhid", "country", TARGET_COL]

# Model hyperparameters (AC-4: frozen envelope)
MODEL_PARAMS = {
    "random_forest": {
        "n_estimators": 300, "max_depth": 15, "min_samples_leaf": 5,
        "class_weight": "balanced", "n_jobs": -1,
    },
    "xgboost": {
        "n_estimators": 300, "max_depth": 6, "learning_rate": 0.1,
        "subsample": 0.8, "colsample_bytree": 0.8,
        "eval_metric": "logloss", "use_label_encoder": False,
    },
    "lightgbm": {
        "n_estimators": 300, "max_depth": 6, "learning_rate": 0.1,
        "subsample": 0.8, "colsample_bytree": 0.8,
        "verbose": -1,
    },
    "logistic_regression": {
        "max_iter": 1000, "solver": "saga", "class_weight": "balanced",
    },
    "ebm": {
        "max_bins": 256, "interactions": 10, "outer_bags": 8, "inner_bags": 0,
    },
}

# Targeting error cost ratios: exclusion_cost / inclusion_cost
COST_RATIOS = [1.0, 2.0, 3.0, 5.0, 10.0]
