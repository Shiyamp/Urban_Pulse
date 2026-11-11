"""Shared settings for every Urban Pulse script.
Edit only the PILOT SETTINGS block. Secrets (MySQL password) go in the .env file, never in code."""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()  # reads the .env file in this folder

BASE_DIR = Path(__file__).parent
RAW_DIR = BASE_DIR / "data" / "raw"
CLEAN_DIR = BASE_DIR / "data" / "clean"
OUT_DIR = BASE_DIR / "outputs"
for folder in (RAW_DIR, CLEAN_DIR, OUT_DIR):
    folder.mkdir(parents=True, exist_ok=True)

# ---------------- PILOT SETTINGS ----------------
API_URL = "https://data.cityofnewyork.us/resource/erm2-nwe9.json"
SAMPLE_ENDINGS = ["07", "17", "27"]  # keep requests whose ID ends in these 2 digits. Each ending is ~1% of all
                                     # requests (3 endings = ~3% = roughly 100,000 rows for 2024). Add/remove endings to scale.
MAX_PER_SLICE = 2_000       # safety cap on rows per slice (normally never reached)
BATCH_SIZE = 500            # rows requested per API call (script halves it automatically if calls fail)
SLICE_DAYS = 1              # fetch this many days per slice (1 = day by day: fast and evenly spread)
REQUEST_TIMEOUT = 120       # seconds to wait for one API call
START_DATE = "2024-01-01T00:00:00"
END_DATE = "2024-12-31T23:59:59"
APP_TOKEN = os.getenv("SOCRATA_APP_TOKEN", "")  # optional, free, gives higher API limits

# 25 source fields. If the API answers "400 / no-such-column", delete that field here.
FIELDS = [
    "unique_key", "created_date", "closed_date", "due_date", "agency", "agency_name",
    "complaint_type", "descriptor", "location_type", "incident_zip", "incident_address",
    "street_name", "city", "borough", "status", "resolution_description",
    "resolution_action_updated_date", "community_board", "latitude", "longitude",
    "open_data_channel_type", "bbl", "park_borough", "x_coordinate_state_plane",
    "y_coordinate_state_plane",
]
# ------------------------------------------------

RAW_FILE = RAW_DIR / "nyc311_raw.csv"
META_FILE = RAW_DIR / "extraction_metadata.json"
CLEAN_FILE = CLEAN_DIR / "nyc311_clean.csv"
DEPLOY_FILE = BASE_DIR / "dashboard_data" / "nyc311_dashboard.csv.gz"  # small file committed to GitHub for the cloud app
LOG_FILE = CLEAN_DIR / "cleaning_log.json"
DICT_FILE = CLEAN_DIR / "data_dictionary.csv"

MYSQL = {
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", ""),
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "port": int(os.getenv("MYSQL_PORT", "3306")),
    "database": os.getenv("MYSQL_DB", "urban_pulse_db"),
}

DATE_COLS = ["created_date", "closed_date", "due_date", "resolution_action_updated_date"]
