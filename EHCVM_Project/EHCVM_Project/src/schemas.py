"""
schemas.py — Pandera schemas for EHCVM 2021 data validation.

Validates the 38/34/51 common columns across all 8 countries.
Extra country-specific columns are allowed (strict=False on columns).
"""
import pandera as pa
from pandera import Column, Check, DataFrameSchema
import pandas as pd

from . import config


# ── Helper: build a schema from column specs ─────────────────────────────────

def _int_col(nullable=False):
    return Column(pa.Int, nullable=nullable, coerce=True)

def _float_col(nullable=False):
    return Column(pa.Float, nullable=nullable, coerce=True)

def _obj_col(nullable=False):
    return Column(pa.Object, nullable=nullable)


# ── Ménage (household) schema ────────────────────────────────────────────────

MENAGE_SCHEMA = DataFrameSchema(
    columns={
        # identifiers
        "hhid":   _int_col(),
        "grappe": _float_col(nullable=True),
        "menage": _float_col(nullable=True),
        "vague":  _float_col(nullable=True),
        "year":   _float_col(nullable=True),
        "country": _obj_col(nullable=True),

        # housing — ponytail: CIV has 898 fully-blank rows, so all nullable
        "logem": _float_col(nullable=True), "mur": _float_col(nullable=True),
        "toit": _float_col(nullable=True), "sol": _float_col(nullable=True),

        # WASH
        "eauboi_ss": _float_col(nullable=True), "eauboi_sp": _float_col(nullable=True),
        "toilet": _float_col(nullable=True), "eva_toi": _float_col(nullable=True),
        "eva_eau": _float_col(nullable=True), "ordure": _float_col(nullable=True),

        # electricity
        "elec_ac": _float_col(nullable=True), "elec_ur": _float_col(nullable=True),
        "elec_ua": _float_col(nullable=True),

        # assets
        "tv": _float_col(nullable=True), "fer": _float_col(nullable=True),
        "frigo": _float_col(nullable=True), "cuisin": _float_col(nullable=True),
        "ordin": _float_col(nullable=True), "decod": _float_col(nullable=True),
        "car": _float_col(nullable=True),

        # agriculture
        "superf":   _float_col(nullable=True),
        "grosrum":  _float_col(nullable=True), "petitrum": _float_col(nullable=True),
        "porc":     _float_col(nullable=True), "lapin":    _float_col(nullable=True),
        "volail":   _float_col(nullable=True),

        # shocks
        "sh_id_demo": _float_col(nullable=True), "sh_co_natu": _float_col(nullable=True),
        "sh_co_eco":  _float_col(nullable=True), "sh_id_eco":  _float_col(nullable=True),
        "sh_co_vio":  _float_col(nullable=True), "sh_co_oth":  _float_col(nullable=True),
    },
    strict="filter",  # ponytail: allow extra cols, just validate known ones
    coerce=True,
)


# ── Welfare schema ───────────────────────────────────────────────────────────

WELFARE_SCHEMA = DataFrameSchema(
    columns={
        # identifiers
        "hhid":   _int_col(),
        "grappe": _int_col(),
        "menage": _int_col(),
        "vague":  _int_col(),
        "year":   _int_col(),
        "country": _obj_col(),

        # head demographics
        "hgender": _int_col(),
        "hage":    Column(pa.Int, Check.ge(0), coerce=True),
        "hmstat":  _int_col(),
        "hreligion": _int_col(),
        "hnation": _int_col(),
        "hethnie": _float_col(nullable=True),
        "halfa":   _int_col(),
        "halfa2":  _int_col(),
        "heduc":   _float_col(nullable=True),
        "hdiploma": _int_col(),
        "hhandig": _int_col(),
        "hactiv7j":  _int_col(),
        "hactiv12m": _int_col(),
        "hbranch":   _float_col(nullable=True),
        "hsectins":  _float_col(nullable=True),
        "hcsp":      _float_col(nullable=True),

        # composition & geography
        "hhsize": Column(pa.Int, Check.ge(1), coerce=True),
        "eqadu1": _float_col(),
        "eqadu2": _float_col(),
        "milieu": Column(pa.Int, Check.isin([1, 2]), coerce=True),
        "zae":    _int_col(),

        # expenditure / target source
        "pcexp": Column(pa.Float, Check.gt(0), coerce=True),
        "zref":  Column(pa.Float, Check.gt(0), coerce=True),
        "dali":  _float_col(nullable=True),
        "dnal":  _float_col(nullable=True),
        "dtot":  _float_col(nullable=True),
        "def_spa":  _float_col(),
        "def_temp": _float_col(),
    },
    strict="filter",
    coerce=True,
)


# ── Individu (individual) schema ─────────────────────────────────────────────

INDIVIDU_SCHEMA = DataFrameSchema(
    columns={
        # identifiers
        "hhid":   _int_col(),
        "grappe": _int_col(),
        "menage": _int_col(),
        "vague":  _int_col(),
        "year":   _int_col(),
        "country": _obj_col(),

        # demographics
        "sexe": Column(pa.Float, nullable=True, coerce=True),
        "age":  Column(pa.Float, nullable=True, coerce=True),
        "lien": _float_col(nullable=True),
        "mstat": _float_col(nullable=True),
        "religion": _float_col(nullable=True),
        "ethnie": _float_col(nullable=True),
        "nation": _float_col(nullable=True),
        "resid": _int_col(),
        "milieu": _int_col(),

        # education
        "alfa":  _int_col(), "alfa2": _int_col(),
        "scol":  _int_col(),
        "educ_scol": _float_col(nullable=True),
        "educ_hi": _float_col(nullable=True),
        "diplome": _int_col(),

        # health
        "mal30j":  _int_col(),
        "aff30j":  _float_col(nullable=True),
        "arrmal":  _int_col(),
        "durarr":  _float_col(nullable=True),
        "con30j":  _float_col(nullable=True),
        "hos12m":  _int_col(),
        "couvmal": _int_col(),
        "moustiq": _int_col(),
        "handit":  _float_col(nullable=True),
        "handig":  _float_col(nullable=True),

        # digital & financial
        "telpor":   _int_col(),
        "internet": _int_col(),
        "bank":     _int_col(),

        # employment
        "activ7j":  _int_col(),
        "activ12m": _int_col(),
        "branch":   _float_col(nullable=True),
        "sectins":  _float_col(nullable=True),
        "csp":      _float_col(nullable=True),
        "volhor":   _float_col(nullable=True),
        "salaire":  _float_col(nullable=True),
        "emploi_sec":   _int_col(),
        "sectins_sec":  _float_col(nullable=True),
        "csp_sec":      _float_col(nullable=True),
        "volhor_sec":   _float_col(nullable=True),
        "salaire_sec":  _float_col(nullable=True),

        # other
        "agemar":          _float_col(nullable=True),
        "serviceconsult":  _float_col(nullable=True),
        "persconsult":     _float_col(nullable=True),
        "zae":    _int_col(),
        "zaemil": _int_col(),
    },
    strict="filter",
    coerce=True,
)


# ── Validation runner ────────────────────────────────────────────────────────

SCHEMAS = {
    "menage":   MENAGE_SCHEMA,
    "welfare":  WELFARE_SCHEMA,
    "individu": INDIVIDU_SCHEMA,
}


def validate_country(country_data: dict) -> dict[str, bool]:
    """
    Validate menage/welfare/individu DataFrames for one country.
    Returns {table: passed_bool}. Prints errors inline.
    """
    name = country_data["_country"]
    results = {}
    for table, schema in SCHEMAS.items():
        try:
            schema.validate(country_data[table], lazy=True)
            results[table] = True
            print(f"  ✓ {name:20s} {table:10s} schema OK")
        except pa.errors.SchemaErrors as e:
            results[table] = False
            print(f"  ✗ {name:20s} {table:10s} FAILED")
            # Show first 5 errors only
            for _, row in e.failure_cases.head(5).iterrows():
                print(f"      column={row.get('column', '?')}  check={row.get('check', '?')}  value={row.get('failure_case', '?')}")
    return results


def validate_all(all_data: dict) -> dict[str, dict[str, bool]]:
    """Validate all countries. Returns {country: {table: bool}}."""
    results = {}
    for name, data in all_data.items():
        print(f"Validating {name}...")
        results[name] = validate_country(data)
    return results


if __name__ == "__main__":
    from . import ingest
    all_data = ingest.load_all_countries()
    results = validate_all(all_data)
    total = sum(1 for r in results.values() for v in r.values() if v)
    expected = len(results) * 3
    print(f"\n{'='*50}")
    print(f"Validation: {total}/{expected} tables passed")
