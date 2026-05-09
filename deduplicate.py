#!/usr/bin/env python3
"""
Deduplicate doctor entries pulled from a Google Sheet.

Reads the Overrides tab via the Sheets API, merges duplicate rows
(same doctor + type + id_inst), and writes a cleaned TSV that can be
pasted/imported back over the existing tab.

Logic:
1. Group rows by (doctor, type, id_inst).
2. Within each group, keep the row with the latest `date_override` as the base.
3. For each fillable column that is empty in the base row, copy the value
   from the most recent older row in the group that has it filled.
4. Drop the older rows.
"""

import os
import sys
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

GOOGLE_API_KEY = os.environ["GOOGLE_API_KEY"]
SHEET_OVERRIDES = "1gsIkUsvO-2_atHTsU9UcH2q69Js9PuvskTbtuY3eEWQ"
RANGE_OVERRIDES = "Overrides!A1:AA"

KEY_COLS = ["doctor", "type", "id_inst"]
FILL_COLS = [
    "accepts_override",
    "availability_override",
    "address",
    "city",
    "post",
    "phone",
    "website",
    "email",
    "orderform",
]


def fetch_sheet(sheet_id: str, range_a1: str, api_key: str) -> pd.DataFrame:
    """Pull a sheet range via the v4 values endpoint and return a DataFrame."""
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values/{range_a1}"
    r = requests.get(
        url,
        params={"key": api_key, "valueRenderOption": "FORMATTED_VALUE"},
        timeout=30,
    )
    r.raise_for_status()
    values = r.json().get("values", [])
    if not values:
        raise SystemExit("Sheet returned no values.")

    header, *rows = values
    # The API trims trailing empty cells; pad each row to header width.
    width = len(header)
    rows = [row + [""] * (width - len(row)) for row in rows]
    return pd.DataFrame(rows, columns=header)


def is_empty(val) -> bool:
    if pd.isna(val):
        return True
    return isinstance(val, str) and val.strip() == ""


def clean(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    missing = [c for c in KEY_COLS + ["date_override"] + FILL_COLS if c not in df.columns]
    if missing:
        raise SystemExit(f"Sheet is missing expected columns: {missing}")

    df = df.copy()
    # Parse dates only for sorting; the original strings stay in the column.
    df["_parsed_date"] = pd.to_datetime(df["date_override"], errors="coerce")

    out_rows = []
    merged_groups = 0
    filled_cells = 0
    merge_log: list[str] = []

    for key, group in df.groupby(KEY_COLS, sort=False, dropna=False):
        group = group.sort_values("_parsed_date", kind="stable")
        latest = group.iloc[-1].copy()

        if len(group) > 1:
            merged_groups += 1
            older = group.iloc[:-1].iloc[::-1]  # newest-older first
            filled_here: list[str] = []
            for col in FILL_COLS:
                if is_empty(latest[col]):
                    for _, old_row in older.iterrows():
                        if not is_empty(old_row[col]):
                            latest[col] = old_row[col]
                            filled_cells += 1
                            filled_here.append(col)
                            break
            doctor, dtype, idinst = key
            note = f"  merged {len(group)} rows for {doctor!r} / {dtype} / {idinst}"
            if filled_here:
                note += f" -> filled: {', '.join(filled_here)}"
            merge_log.append(note)

        out_rows.append(latest)

    out = pd.DataFrame(out_rows).drop(columns=["_parsed_date"])
    stats = {
        "rows_in": len(df),
        "rows_out": len(out),
        "groups_merged": merged_groups,
        "cells_filled": filled_cells,
        "merge_log": merge_log,
    }
    return out, stats


def main() -> None:
    output_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("overrides_cleaned.tsv")

    print("Fetching Overrides sheet...")
    df = fetch_sheet(SHEET_OVERRIDES, RANGE_OVERRIDES, GOOGLE_API_KEY)

    cleaned, stats = clean(df)
    cleaned.to_csv(output_path, sep="\t", index=False)

    print()
    for line in stats["merge_log"]:
        print(line)
    print()
    print(f"Rows in:                 {stats['rows_in']}")
    print(f"Rows out:                {stats['rows_out']}")
    print(f"Duplicate groups merged: {stats['groups_merged']}")
    print(f"Empty cells filled:      {stats['cells_filled']}")
    print(f"Wrote: {output_path}")


if __name__ == "__main__":
    main()