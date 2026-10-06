from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def convert_file(source_path: Path, overwrite: bool) -> tuple[bool, str]:
    target_path = source_path.with_suffix(".csv")

    if target_path.exists() and not overwrite:
        return False, f"skipped (exists): {target_path}"

    data_frame = pd.read_stata(
        source_path,
        convert_categoricals=False,
    )
    data_frame.to_csv(target_path, index=False, encoding="utf-8-sig")

    return True, f"written: {target_path}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert every .dta file under data/ to a sibling .csv file."
    )
    parser.add_argument(
        "--data-folder",
        type=Path,
        default=Path("data"),
        help="Folder containing the .dta files.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace existing .csv files if they are already present.",
    )
    args = parser.parse_args()

    data_folder = args.data_folder
    files = sorted(data_folder.rglob("*.dta"))

    if not files:
        print(f"No .dta files found under {data_folder}.")
        return 1

    converted = 0
    skipped = 0
    failures = 0

    for source_path in files:
        try:
            did_convert, message = convert_file(source_path, args.overwrite)
            print(f"✓ {source_path}: {message}")
            if did_convert:
                converted += 1
            else:
                skipped += 1
        except Exception as error:
            failures += 1
            print(f"✗ {source_path}: {error}")

    print("\nConversion complete.")
    print(f"Converted: {converted}")
    print(f"Skipped: {skipped}")
    print(f"Failed: {failures}")

    return 0 if failures == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())