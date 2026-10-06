"""
db.py — DuckDB Analytical Database Layer matching ER Diagram.

Provides embedded relational storage and analytics for:
1. countries: Sovereign state metadata, sample size, poverty rates
2. clean_households: 55,922 harmonized household survey records (74 features + target)
3. model_experiments: LOCO and pooled benchmark evaluation metrics
4. policy_targeting_calibration: Asymmetric error tradeoff thresholds
5. assurance_audit_record: AC-1..AC-4 and NT-1..NT-5 compliance checks
"""
from pathlib import Path
import json
import hashlib
import duckdb
import pandas as pd
from . import config

def get_connection(db_path: Path = None, read_only: bool = False) -> duckdb.DuckDBPyConnection:
    """Return a DuckDB connection for the capstone database."""
    target_path = Path(db_path or config.DB_PATH)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(target_path), read_only=read_only)


def init_db(db_path: Path = None) -> None:
    """Initialize relational schema matching the Capstone ER diagram."""
    conn = get_connection(db_path)
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS countries (
                country_code VARCHAR PRIMARY KEY,
                country_name VARCHAR NOT NULL,
                zref_threshold DOUBLE,
                total_households INTEGER,
                poverty_headcount DOUBLE
            );

            CREATE TABLE IF NOT EXISTS model_experiments (
                experiment_id VARCHAR PRIMARY KEY,
                model_architecture VARCHAR NOT NULL,
                evaluation_protocol VARCHAR NOT NULL,
                macro_accuracy DOUBLE,
                macro_auc_roc DOUBLE,
                macro_f1 DOUBLE,
                macro_brier DOUBLE,
                country_results_json VARCHAR
            );

            CREATE TABLE IF NOT EXISTS policy_targeting_calibration (
                calibration_id VARCHAR PRIMARY KEY,
                country_name VARCHAR,
                cost_ratio_c DOUBLE,
                optimal_threshold_tau DOUBLE,
                exclusion_error_pct DOUBLE,
                inclusion_error_pct DOUBLE,
                accuracy DOUBLE,
                weighted_cost DOUBLE
            );

            CREATE TABLE IF NOT EXISTS assurance_audit_record (
                audit_id VARCHAR PRIMARY KEY,
                test_code VARCHAR,
                check_name VARCHAR,
                verification_status VARCHAR,
                passed BOOLEAN,
                telemetry_hash VARCHAR
            );
        """)
    finally:
        conn.close()


def populate_db(db_path: Path = None, force: bool = False) -> dict:
    """
    Populate DuckDB from processed CSVs and JSON evaluation artifacts.
    Returns dictionary with populated row counts.
    """
    init_db(db_path)
    conn = get_connection(db_path)
    counts = {}

    try:
        # 1. Clean households & Countries
        household_dfs = []
        country_rows = []

        for name, meta in config.COUNTRIES.items():
            code = meta["code"]
            csv_path = config.DATA_PROCESSED / f"{code}_clean.csv"
            if not csv_path.exists():
                continue

            df = pd.read_csv(csv_path).fillna(0)
            df.insert(0, "country_code", code.upper())
            household_dfs.append(df)

            n_hh = len(df)
            headcount = float(df[config.TARGET_COL].mean()) if config.TARGET_COL in df.columns else 0.0

            country_rows.append({
                "country_code": code.upper(),
                "country_name": name,
                "zref_threshold": None, # Will be filled if present
                "total_households": n_hh,
                "poverty_headcount": headcount
            })

        if household_dfs:
            combined_hh = pd.concat(household_dfs, ignore_index=True)
            conn.execute("DROP TABLE IF EXISTS clean_households")
            conn.register("combined_hh_view", combined_hh)
            conn.execute("CREATE TABLE clean_households AS SELECT * FROM combined_hh_view")
            conn.unregister("combined_hh_view")
            counts["clean_households"] = len(combined_hh)

        if country_rows:
            countries_df = pd.DataFrame(country_rows)
            conn.execute("DELETE FROM countries")
            conn.register("countries_view", countries_df)
            conn.execute("INSERT INTO countries SELECT * FROM countries_view")
            conn.unregister("countries_view")
            counts["countries"] = len(countries_df)

        # 2. Model experiments from outputs/results/*.json
        exp_rows = []
        results_dir = config.OUTPUT_RESULTS
        if results_dir.exists():
            for json_file in results_dir.glob("*.json"):
                # Matches files like o2_rf_loco.json, o3_ebm_loco.json, etc.
                if json_file.name.startswith("o") and "_loco" in json_file.name or "_pooled" in json_file.name:
                    try:
                        data = json.loads(json_file.read_text())
                        macro = data.get("macro", {})
                        exp_id = json_file.stem
                        parts = exp_id.split("_")
                        arch = parts[1].upper() if len(parts) > 1 else exp_id
                        protocol = data.get("method", "UNKNOWN")

                        exp_rows.append({
                            "experiment_id": exp_id,
                            "model_architecture": arch,
                            "evaluation_protocol": protocol,
                            "macro_accuracy": macro.get("accuracy"),
                            "macro_auc_roc": macro.get("roc_auc"),
                            "macro_f1": macro.get("f1"),
                            "macro_brier": macro.get("brier"),
                            "country_results_json": json.dumps(data.get("countries", {}))
                        })
                    except Exception:
                        pass

        if exp_rows:
            exp_df = pd.DataFrame(exp_rows)
            conn.execute("DELETE FROM model_experiments")
            conn.register("exp_view", exp_df)
            conn.execute("INSERT INTO model_experiments SELECT * FROM exp_view")
            conn.unregister("exp_view")
            counts["model_experiments"] = len(exp_df)

        # 3. Policy targeting calibration
        targeting_csv = config.OUTPUT_RESULTS / "targeting_summary.csv"
        if targeting_csv.exists():
            t_df = pd.read_csv(targeting_csv)
            calib_rows = []
            for i, row in t_df.iterrows():
                calib_rows.append({
                    "calibration_id": f"CALIB_{row['Country']}_{row['Cost Ratio']:.1f}",
                    "country_name": row["Country"],
                    "cost_ratio_c": float(row["Cost Ratio"]),
                    "optimal_threshold_tau": float(row["Threshold"]),
                    "exclusion_error_pct": float(row["Exclusion Error"]) * 100,
                    "inclusion_error_pct": float(row["Inclusion Error"]) * 100,
                    "accuracy": float(row["Accuracy"]),
                    "weighted_cost": float(row["Weighted Cost"])
                })
            calib_df = pd.DataFrame(calib_rows)
            conn.execute("DELETE FROM policy_targeting_calibration")
            conn.register("calib_view", calib_df)
            conn.execute("INSERT INTO policy_targeting_calibration SELECT * FROM calib_view")
            conn.unregister("calib_view")
            counts["policy_targeting_calibration"] = len(calib_df)

        # 4. Assurance audit records
        audit_rows = []
        ac_file = config.OUTPUT_ACCEPTANCE / "o5_acceptance.json"
        if ac_file.exists():
            try:
                ac_data = json.loads(ac_file.read_text())
                for ac_code, check_info in ac_data.items():
                    for t_idx, t in enumerate(check_info.get("tests", [])):
                        h = hashlib.sha256(f"{ac_code}_{t['check']}".encode()).hexdigest()[:12]
                        audit_rows.append({
                            "audit_id": f"{ac_code}_{t_idx+1}",
                            "test_code": ac_code,
                            "check_name": t["check"],
                            "verification_status": "PASS OK" if t["passed"] else "FAIL",
                            "passed": bool(t["passed"]),
                            "telemetry_hash": h
                        })
            except Exception:
                pass

        nt_file = config.OUTPUT_ACCEPTANCE / "negative_tests.json"
        if nt_file.exists():
            try:
                nt_data = json.loads(nt_file.read_text())
                for nt_code, res in nt_data.items():
                    if isinstance(res, dict) and "test" in res:
                        passed = bool(res.get("passed", False))
                        desc = res.get("description", nt_code)
                        h = hashlib.sha256(f"{nt_code}_{desc}".encode()).hexdigest()[:12]
                        audit_rows.append({
                            "audit_id": nt_code,
                            "test_code": nt_code,
                            "check_name": desc,
                            "verification_status": "PASS OK" if passed else "FAIL",
                            "passed": passed,
                            "telemetry_hash": h
                        })
            except Exception:
                pass

        if audit_rows:
            audit_df = pd.DataFrame(audit_rows)
            conn.execute("DELETE FROM assurance_audit_record")
            conn.register("audit_view", audit_df)
            conn.execute("INSERT INTO assurance_audit_record SELECT * FROM audit_view")
            conn.unregister("audit_view")
            counts["assurance_audit_record"] = len(audit_df)

    finally:
        conn.close()

    return counts


def query_df(sql: str, params: list = None, db_path: Path = None) -> pd.DataFrame:
    """Execute SQL query against DuckDB and return result as pandas DataFrame."""
    conn = get_connection(db_path, read_only=True)
    try:
        if params:
            return conn.execute(sql, params).df()
        return conn.execute(sql).df()
    finally:
        conn.close()


def get_country_summary(db_path: Path = None) -> pd.DataFrame:
    """Query country registry summary."""
    return query_df("SELECT * FROM countries ORDER BY country_name", db_path=db_path)


def get_model_leaderboard(protocol: str = "LOCO", db_path: Path = None) -> pd.DataFrame:
    """Query model experiments ordered by macro AUC-ROC descending."""
    return query_df(
        """
        SELECT model_architecture, evaluation_protocol, macro_accuracy, macro_auc_roc, macro_f1
        FROM model_experiments
        WHERE evaluation_protocol = ?
        ORDER BY macro_auc_roc DESC
        """,
        params=[protocol],
        db_path=db_path
    )


def get_audit_records(db_path: Path = None) -> pd.DataFrame:
    """Query all audit check results."""
    return query_df("SELECT * FROM assurance_audit_record ORDER BY test_code, audit_id", db_path=db_path)


def get_targeting_summary(cost_ratio: float = 3.0, db_path: Path = None) -> pd.DataFrame:
    """Query policy targeting calibration table."""
    if cost_ratio is not None:
        return query_df(
            "SELECT * FROM policy_targeting_calibration WHERE cost_ratio_c = ? ORDER BY country_name",
            params=[cost_ratio],
            db_path=db_path
        )
    return query_df("SELECT * FROM policy_targeting_calibration ORDER BY country_name, cost_ratio_c", db_path=db_path)


def get_household_sample(country_code: str, limit: int = 100, db_path: Path = None) -> pd.DataFrame:
    """Fetch sample households for a country."""
    return query_df(
        "SELECT * FROM clean_households WHERE country_code = ? LIMIT ?",
        params=[country_code.upper(), limit],
        db_path=db_path
    )


if __name__ == "__main__":
    print("Populating DuckDB database...")
    counts = populate_db()
    print("Database populated successfully:")
    for table, count in counts.items():
        print(f"  {table:30s} -> {count} records")

    # runnable check / assertion
    df_countries = get_country_summary()
    assert len(df_countries) >= 8, f"Expected at least 8 countries, got {len(df_countries)}"
    total_hh = query_df("SELECT COUNT(*) AS n FROM clean_households").iloc[0]["n"]
    assert total_hh > 50000, f"Expected >50k households, got {total_hh}"
    print(f"All checks passed! Total households in DuckDB: {total_hh}")
