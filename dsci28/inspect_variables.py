from pathlib import Path
import pandas as pd
import pyreadstat

DATA_FOLDER = Path("data")

# Dataset types we want to inspect
dataset_types = {
    "household": "ehcvm_menage",
    "individual": "ehcvm_individu",
    "welfare": "ehcvm_welfare"
}

countries = [
    "Benin",
    "Burkina Faso",
    "Côte d'Ivoire",
    "Guinea-Bissau",
    "Mali",
    "Niger",
    "Senegal",
    "Togo"
]

for dataset_type, keyword in dataset_types.items():

    print("\n" + "=" * 80)
    print(f"{dataset_type.upper()} VARIABLES")
    print("=" * 80)

    for country in countries:

        folder = DATA_FOLDER / country

        files = [
            f for f in folder.glob("*.dta")
            if keyword.lower() in f.name.lower()
        ]

        if not files:
            print(f"\n❌ {country}: file not found")
            continue

        file = files[0]

        try:
            df, meta = pyreadstat.read_dta(file)

            print("\n" + "-" * 80)
            print(f"COUNTRY: {country}")
            print(f"FILE: {file.name}")
            print(f"ROWS: {len(df)}")
            print(f"COLUMNS: {len(df.columns)}")
            print("-" * 80)

            # Variable name + label
            for i, column in enumerate(df.columns):

                label = meta.column_names_to_labels.get(
                    column,
                    ""
                )

                print(
                    f"{i+1:3}. {column:25} | {label}"
                )

        except Exception as e:
            print(f"\n❌ ERROR: {country}")
            print(e)

print("\n" + "=" * 80)
print("DONE")
print("=" * 80)
