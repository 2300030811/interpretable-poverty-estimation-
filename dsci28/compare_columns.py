from pathlib import Path
import pandas as pd

DATA_FOLDER = Path("data")

# Dataset types we want to compare
dataset_types = {
    "household": "ehcvm_menage",
    "individual": "ehcvm_individu",
    "welfare": "ehcvm_welfare",
    "weights": "ponderations",
    "consumption": "ehcvm_conso"
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

    print("\n" + "=" * 70)
    print(f"{dataset_type.upper()} DATASETS")
    print("=" * 70)

    country_columns = {}

    for country in countries:

        country_folder = DATA_FOLDER / country

        matching_files = [
            f for f in country_folder.glob("*.dta")
            if keyword.lower() in f.name.lower()
        ]

        if not matching_files:
            print(f"\n❌ {country}: file not found")
            continue

        file = matching_files[0]

        try:
            df = pd.read_stata(
                file,
                convert_categoricals=False
            )

            country_columns[country] = set(df.columns)

            print(
                f"✓ {country:20} "
                f"{len(df):8} rows × "
                f"{len(df.columns):4} columns"
            )

        except Exception as e:
            print(f"❌ {country}: {e}")

    if not country_columns:
        continue

    # Find columns common to ALL countries
    common_columns = set.intersection(
        *country_columns.values()
    )

    print("\nCOMMON COLUMNS ACROSS ALL COUNTRIES:")
    print(f"Total: {len(common_columns)}")

    for column in sorted(common_columns):
        print(f"  {column}")

    # Find country-specific columns
    print("\nCOUNTRY-SPECIFIC DIFFERENCES:")

    for country, columns in country_columns.items():

        missing = common_columns - columns

        print(
            f"{country}: "
            f"{len(columns)} total columns"
        )

print("\n\nDONE.")