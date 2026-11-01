import json
import time
from datetime import datetime, timezone

import pandas as pd
import requests

api_url = "https://data.cityofnewyork.us/resource/erm2-nwe9.json"

row_limit = 100000
batch_size = 1000
max_attempts = 3
selected_fields = [
    "unique_key",
    "created_date",
    "closed_date",
    "agency",
    "complaint_type",
    "descriptor",
    "borough",
    "status",
    "latitude",
    "longitude",
]


def get_json(params):
    for attempt in range(max_attempts):
        try:
            response = requests.get(api_url, params=params, timeout=50)
            if response.status_code == 429 or response.status_code >= 500:
                if attempt < max_attempts - 1:
                    response.close()
                    time.sleep(2**attempt)
                    continue
            response.raise_for_status()
            return response.json()
        except (requests.Timeout, requests.ConnectionError):
            if attempt == max_attempts - 1:
                raise
            time.sleep(2**attempt)

    raise RuntimeError("API request failed after all retry attempts")


started_at = datetime.now(timezone.utc)
max_key_result = get_json({"$select": "max(unique_key) AS max_key"})
if not max_key_result or max_key_result[0].get("max_key") is None:
    upper_key = None
    all_records = []
else:
    upper_key = int(max_key_result[0]["max_key"])
    all_records = []
    last_key = None

    while len(all_records) < row_limit:
        conditions = [f"unique_key <= {upper_key}"]
        if last_key is not None:
            conditions.append(f"unique_key > {last_key}")

        page_limit = min(batch_size, row_limit - len(all_records))
        params = {
            "$select": ",".join(selected_fields),
            "$where": " AND ".join(conditions),
            "$order": "unique_key ASC",
            "$limit": page_limit,
        }

        batch = get_json(params)
        if not batch:
            break

        all_records.extend(batch)
        last_key = int(batch[-1]["unique_key"])
        print(f"Fetched {len(all_records)} of up to {row_limit} records")

        if len(batch) < page_limit:
            break

nyc311_df = pd.DataFrame(all_records, columns=selected_fields)
nyc311_df.to_csv("nyc311_data.csv", index=False)

limitations = [
    "The upper_key cutoff is not a point-in-time snapshot. Records at or "
    "below the cutoff can still change while extraction is running."
]
if len(nyc311_df) == row_limit:
    limitations.append(
        "The configured row limit was reached; additional matching records "
        "may be available."
    )

metadata = {
    "extracted_at_utc": started_at.isoformat(),
    "api_url": api_url,
    "parameters": {
        "$select": ",".join(selected_fields),
        "$where": "unique_key <= upper_key and unique_key > last_key after page 1",
        "$order": "unique_key ASC",
        "$limit_per_page": batch_size,
        "row_limit": row_limit,
    },
    "upper_key": upper_key,
    "actual_row_count": len(nyc311_df),
    "limitations": limitations,
}
with open("nyc311_data_metadata.json", "w", encoding="utf-8") as metadata_file:
    json.dump(metadata, metadata_file, indent=2)

print(f"Saved {len(nyc311_df)} rows to nyc311_data.csv")
print("Saved extraction details to nyc311_data_metadata.json")
print(nyc311_df.head())
