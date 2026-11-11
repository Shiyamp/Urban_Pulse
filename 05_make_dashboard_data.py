"""STEP 5 - Make a small data file for the cloud dashboard.

Keeps only the columns the dashboard uses (no street addresses or free-text fields) and
compresses it, so it can be committed to GitHub and read by Streamlit Community Cloud.
Run:  python 05_make_dashboard_data.py
"""
import pandas as pd

from config import CLEAN_FILE, DEPLOY_FILE

COLUMNS = [
    "unique_key", "created_date", "closed_date", "agency", "complaint_type", "borough", "status",
    "latitude", "longitude", "is_closed", "resolution_hours", "created_month", "created_weekday",
    "created_hour", "coord_valid",
]

df = pd.read_csv(CLEAN_FILE, usecols=COLUMNS, low_memory=False)
DEPLOY_FILE.parent.mkdir(exist_ok=True)
df.to_csv(DEPLOY_FILE, index=False)  # the .gz ending makes pandas compress it
print(f"Saved {len(df):,} rows, {len(COLUMNS)} columns -> {DEPLOY_FILE} "
      f"({DEPLOY_FILE.stat().st_size / 1_048_576:.1f} MB)")
