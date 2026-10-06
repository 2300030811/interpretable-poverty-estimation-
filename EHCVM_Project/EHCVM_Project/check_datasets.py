from pathlib import Path
import pandas as pd

DATA_FOLDER = Path("data")

# Find all Stata files
files = list(DATA_FOLDER.rglob("*.dta"))

if not files:
    print("No .dta files found.")
    print("Check that your files are inside the data/ folder.")
    exit()

print(f"\nFound {len(files)} .dta files.\n")

# Store information
results = []

for file in files:
    try:
        df = pd.read_stata(file, convert_categoricals=False)

        results.append({
            "Country": file.parent.name,
            "File": file.name,
            "Rows": len(df),
            "Columns": len(df.columns),
            "Size_MB": round(file.stat().st_size / (1024 * 1024), 2)
        })

        print(f"✓ {file.parent.name:20} {file.name:40} "
              f"{len(df):8} rows × {len(df.columns):4} columns")

    except Exception as e:
        print(f"✗ ERROR: {file}")
        print(f"  {e}")

# Save summary
summary = pd.DataFrame(results)
summary.to_csv("dataset_summary.csv", index=False)

print("\n--------------------------------")
print("Summary saved as dataset_summary.csv")
print("--------------------------------")