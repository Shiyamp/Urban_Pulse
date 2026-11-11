"""STEP 4 - Load the cleaned data into MySQL safely.

Flow (from the project document): load into a STAGING table -> validate row counts ->
only then publish it as the real table `service_requests`.
Needs MySQL 8 running and the .env file filled in.
Run:  python 04_load_mysql.py
"""
import time

import pandas as pd
from sqlalchemy import BigInteger, String, create_engine, text
from sqlalchemy.engine import URL

from config import CLEAN_FILE, DATE_COLS, MYSQL

STAGING, FINAL = "service_requests_staging", "service_requests"

# Short text types so these columns can be indexed
COLUMN_TYPES = {
    "unique_key": BigInteger(),
    "agency": String(20),
    "complaint_type": String(150),
    "borough": String(30),
    "status": String(40),
    "created_month": String(7),
    "created_weekday": String(12),
}


def make_url(database=None):
    return URL.create("mysql+pymysql", username=MYSQL["user"], password=MYSQL["password"],
                      host=MYSQL["host"], port=MYSQL["port"], database=database)


def with_retry(action, tries=3):
    for attempt in range(1, tries + 1):
        try:
            return action()
        except Exception as err:  # noqa: BLE001 - beginner-friendly: retry any temporary failure
            print(f"  attempt {attempt} failed: {err}")
            if attempt == tries:
                raise
            time.sleep(3 * attempt)


def main():
    df = pd.read_csv(CLEAN_FILE, parse_dates=DATE_COLS, low_memory=False)
    print(f"Cleaned rows to load: {len(df):,}")

    # 1. Create the database if needed
    admin = create_engine(make_url())
    with admin.begin() as conn:
        conn.execute(text(f"CREATE DATABASE IF NOT EXISTS `{MYSQL['database']}`"))

    engine = create_engine(make_url(MYSQL["database"]))

    # 2. Load into staging (replaces any old staging table)
    with_retry(lambda: df.to_sql(STAGING, engine, if_exists="replace", index=False,
                                 chunksize=5000, dtype=COLUMN_TYPES))

    # 3. Validate staging BEFORE touching the real table
    with engine.connect() as conn:
        rows = conn.execute(text(f"SELECT COUNT(*) FROM {STAGING}")).scalar()
        keys = conn.execute(text(f"SELECT COUNT(DISTINCT unique_key) FROM {STAGING}")).scalar()
    print(f"CSV rows: {len(df):,} | staged rows: {rows:,} | distinct keys: {keys:,}")
    if rows != len(df) or keys != len(df):
        raise SystemExit("Validation FAILED: counts do not match. Real table left untouched.")

    # 4. Publish: swap staging in as the real table, then add key and indexes
    with engine.begin() as conn:
        conn.execute(text(f"DROP TABLE IF EXISTS {FINAL}"))
        conn.execute(text(f"RENAME TABLE {STAGING} TO {FINAL}"))
        conn.execute(text(f"ALTER TABLE {FINAL} ADD PRIMARY KEY (unique_key)"))
        for col in ("created_date", "borough", "agency", "complaint_type"):
            conn.execute(text(f"CREATE INDEX idx_{col} ON {FINAL} ({col})"))

    # 5. Sample check after loading
    print("\nPublished. Sample rows:")
    print(pd.read_sql(f"SELECT unique_key, created_date, agency, complaint_type, borough, "
                      f"resolution_hours FROM {FINAL} LIMIT 5", engine))


if __name__ == "__main__":
    main()
