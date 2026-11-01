"""STEP 2 - Clean the raw extract and add derived fields.

Rules from the project document: keep meaningful nulls, flag bad dates instead of silently
fixing them, document every change. Outputs: clean CSV, cleaning log, data dictionary.
Run:  python 02_clean.py
"""
import json

import pandas as pd

from config import CLEAN_FILE, DATE_COLS, DICT_FILE, LOG_FILE, RAW_FILE

NUM_COLS = ["latitude", "longitude", "x_coordinate_state_plane", "y_coordinate_state_plane"]

MEANINGS = {
    "unique_key": "Unique request ID (primary key)",
    "created_date": "When the request was created",
    "closed_date": "When the request was closed (empty if still open)",
    "due_date": "Date the agency expects to respond by (often empty)",
    "agency": "Agency code handling the request",
    "complaint_type": "Main category of the complaint",
    "descriptor": "More detail about the complaint type",
    "borough": "NYC borough (may be 'Unspecified')",
    "status": "Recorded status of the request",
    "latitude": "Latitude of the incident (may be empty)",
    "longitude": "Longitude of the incident (may be empty)",
    "is_closed": "DERIVED: True if closed_date exists",
    "closed_before_created": "DERIVED FLAG: closed_date earlier than created_date (invalid)",
    "resolution_hours": "DERIVED: hours from created to closed, only for valid closed rows",
    "created_year": "DERIVED: year of created_date",
    "created_month": "DERIVED: YYYY-MM of created_date",
    "created_weekday": "DERIVED: weekday name of created_date",
    "created_hour": "DERIVED: hour (0-23) of created_date",
    "coord_valid": "DERIVED FLAG: coordinates fall inside the NYC bounding box",
}


def main():
    df = pd.read_csv(RAW_FILE, dtype=str)  # read everything as text first (safest)
    log = {"raw_rows": int(len(df))}

    # 1. Tidy text: trim and collapse repeated spaces; empty text becomes a real null
    for col in df.columns:
        df[col] = df[col].str.strip().str.replace(r"\s+", " ", regex=True)
    df = df.replace("", pd.NA)

    # 2. Identifiers: drop rows with no key, drop duplicate keys
    df["unique_key"] = pd.to_numeric(df["unique_key"], errors="coerce")
    log["rows_dropped_missing_key"] = int(df["unique_key"].isna().sum())
    df = df.dropna(subset=["unique_key"])
    df["unique_key"] = df["unique_key"].astype("int64")
    log["duplicate_keys_dropped"] = int(df.duplicated("unique_key").sum())
    df = df.drop_duplicates("unique_key", keep="first")

    # 3. Dates: bad values become NaT (blank) and are counted
    for col in DATE_COLS:
        before = df[col].notna().sum()
        df[col] = pd.to_datetime(df[col], errors="coerce")
        log[f"{col}_unparseable"] = int(before - df[col].notna().sum())

    # 4. Numbers
    for col in NUM_COLS:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # 5. Category labels (only where it is clearly safe)
    df["borough"] = df["borough"].str.title()
    df["agency"] = df["agency"].str.upper()
    df["status"] = df["status"].str.title()

    # 6. Derived fields and data-quality flags
    df["is_closed"] = df["closed_date"].notna()
    df["closed_before_created"] = df["closed_date"] < df["created_date"]
    valid = df["is_closed"] & ~df["closed_before_created"] & df["created_date"].notna()
    df["resolution_hours"] = ((df["closed_date"] - df["created_date"]).dt.total_seconds() / 3600).where(valid)
    df["created_year"] = df["created_date"].dt.year
    df["created_month"] = df["created_date"].dt.strftime("%Y-%m")
    df["created_weekday"] = df["created_date"].dt.day_name()
    df["created_hour"] = df["created_date"].dt.hour
    df["coord_valid"] = df["latitude"].between(40.4, 41.0) & df["longitude"].between(-74.3, -73.6)

    log.update({
        "clean_rows": int(len(df)),
        "closed_rows": int(df["is_closed"].sum()),
        "closed_before_created_flagged": int(df["closed_before_created"].sum()),
        "valid_resolution_rows": int(df["resolution_hours"].notna().sum()),
        "rows_with_valid_coordinates": int(df["coord_valid"].sum()),
    })

    df.to_csv(CLEAN_FILE, index=False)
    LOG_FILE.write_text(json.dumps(log, indent=2))

    # Data dictionary (fill in the blank meanings by hand for the extra fields)
    dictionary = pd.DataFrame({
        "column": df.columns,
        "dtype": [str(t) for t in df.dtypes],
        "missing_count": df.isna().sum().values,
        "missing_pct": (df.isna().mean() * 100).round(1).values,
        "meaning": [MEANINGS.get(c, "") for c in df.columns],
    })
    dictionary.to_csv(DICT_FILE, index=False)

    print(json.dumps(log, indent=2))
    print(f"\nSaved: {CLEAN_FILE}\n       {LOG_FILE}\n       {DICT_FILE}")


if __name__ == "__main__":
    main()
