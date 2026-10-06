"""
Root runner for DuckDB database sync and inspection.
Allows running `python run_db.py` directly from the repository root.
"""
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent / "EHCVM_Project" / "EHCVM_Project"
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from src.db import populate_db, get_country_summary, query_df

if __name__ == "__main__":
    print("Populating / verifying DuckDB database from root...")
    counts = populate_db()
    print("Database populated successfully:")
    for table, count in counts.items():
        print(f"  {table:30s} -> {count} records")
    total_hh = query_df("SELECT COUNT(*) AS n FROM clean_households").iloc[0]["n"]
    print(f"Total households verified in DuckDB: {total_hh}")
