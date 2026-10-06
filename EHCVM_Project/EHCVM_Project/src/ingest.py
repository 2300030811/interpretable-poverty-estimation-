"""
ingest.py — Load raw EHCVM CSVs with lineage tracking.
"""
import json
import datetime
import pandas as pd
from pathlib import Path

from . import config


def _file_meta(path: Path, df: pd.DataFrame) -> dict:
    """Lineage record for one loaded file."""
    return {
        "file": str(path.relative_to(config.PROJECT_ROOT)),
        "rows": len(df),
        "columns": len(df.columns),
        "size_bytes": path.stat().st_size,
        "loaded_at": datetime.datetime.now().isoformat(),
    }


def load_country(country_name: str) -> dict[str, pd.DataFrame]:
    """
    Load menage, welfare, and individu CSVs for one country.

    Returns dict with keys 'menage', 'welfare', 'individu' and a '_lineage' list.
    """
    paths = config.get_file_paths(country_name)
    result = {"_lineage": [], "_country": country_name}

    for table, path in paths.items():
        if not path.exists():
            raise FileNotFoundError(f"{country_name}/{table}: {path}")
        df = pd.read_csv(path)
        result[table] = df
        result["_lineage"].append({"table": table, **_file_meta(path, df)})
        print(f"  ✓ {country_name:20s} {table:10s} → {len(df):>6,} rows × {len(df.columns):>3} cols")

    return result


def load_all_countries() -> dict[str, dict]:
    """Load all 8 countries. Returns {country_name: load_country result}."""
    all_data = {}
    for name in config.COUNTRIES:
        print(f"Loading {name}...")
        all_data[name] = load_country(name)
    return all_data


def save_lineage_report(all_data: dict, out_path: Path | None = None):
    """Write lineage report JSON summarising all ingested files."""
    out_path = out_path or config.DATA_PROCESSED / "lineage_report.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    report = {
        "generated_at": datetime.datetime.now().isoformat(),
        "countries": {},
    }
    for name, data in all_data.items():
        report["countries"][name] = data["_lineage"]

    total_files = sum(len(v) for v in report["countries"].values())
    report["total_files_ingested"] = total_files

    out_path.write_text(json.dumps(report, indent=2))
    print(f"\nLineage report → {out_path}  ({total_files} files tracked)")
