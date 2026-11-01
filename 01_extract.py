"""STEP 1 - Extract NYC 311 data from the NYC Open Data (Socrata) API.

Design:
  * SYSTEMATIC SAMPLE: keeps only requests whose ID ends in SAMPLE_ENDINGS. IDs are issued in time order,
    so this picks a thin, even slice of EVERY hour of EVERY day (about 3% of all requests). Daily volume
    stays proportional to real demand, so monthly/weekday/hour patterns are valid.
  * Works in small DAY slices, so every API call is cheap (no deep paging).
  * Saves each finished slice to a chunk file. If the run stops, just run it again:
    finished days are skipped and only the missing days are fetched.
  * If calls keep failing, the batch size is halved automatically.
  * A day that still fails is skipped and reported; rerun to fill it in.
Run:  python 01_extract.py
"""
import json
import time
from datetime import datetime

import pandas as pd
import requests

from config import (API_URL, APP_TOKEN, BATCH_SIZE, END_DATE, FIELDS, META_FILE, RAW_DIR,
                    RAW_FILE, REQUEST_TIMEOUT, SAMPLE_ENDINGS, MAX_PER_SLICE, SLICE_DAYS,
                    START_DATE)

FMT = "%Y-%m-%dT%H:%M:%S"
MIN_BATCH = 100


def make_slices(start, end, days):
    """Split the date window into slices of `days` days."""
    s, e = pd.Timestamp(start), pd.Timestamp(end)
    slices, cur = [], s
    step = pd.Timedelta(days=days)
    while cur <= e:
        slice_end = min(cur + step - pd.Timedelta(seconds=1), e)
        slices.append((cur.strftime(FMT), slice_end.strftime(FMT)))
        cur += step
    return slices


def fetch_page(session, params, retries=5):
    """One API call with timeout + retries. Returns None if all attempts fail."""
    for attempt in range(1, retries + 1):
        try:
            resp = session.get(API_URL, params=params, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as err:
            print(f"   attempt {attempt}/{retries} failed ({type(err).__name__})")
            if attempt < retries:
                time.sleep(min(2 ** attempt, 60))
    return None


LIKE_FILTER = " OR ".join(f"unique_key like '%{e}'" for e in SAMPLE_ENDINGS)


def fetch_slice(session, start, end, quota, batch):
    """Fetch up to `quota` rows for one slice. Returns (rows or None, batch size to keep using)."""
    rows, got = [], 0
    while got < quota:
        n = min(batch, quota - got)
        params = {
            "$select": ",".join(FIELDS),
            "$where": f"created_date between '{start}' and '{end}' AND ({LIKE_FILTER})",
            "$order": ":id",
            "$limit": n,
            "$offset": got,
        }
        page = fetch_page(session, params)
        if page is None:
            if batch > MIN_BATCH:
                batch = max(MIN_BATCH, batch // 2)
                print(f"   reducing batch size to {batch} and trying again")
                continue
            return None, batch
        rows.extend(page)
        got += len(page)
        if len(page) < n:  # no more rows in this slice
            break
        time.sleep(0.2)  # be polite to the API
    return rows, batch


def main():
    session = requests.Session()
    if APP_TOKEN:
        session.headers["X-App-Token"] = APP_TOKEN

    slices = make_slices(START_DATE, END_DATE, SLICE_DAYS)
    quota = MAX_PER_SLICE
    chunk_dir = RAW_DIR / f"chunks_{START_DATE[:10]}_{END_DATE[:10]}_ends{'-'.join(SAMPLE_ENDINGS)}"
    chunk_dir.mkdir(exist_ok=True)
    print(f"{len(slices)} slice(s) of {SLICE_DAYS} day(s); keeping IDs ending in {SAMPLE_ENDINGS} "
          f"(~{len(SAMPLE_ENDINGS)}% of all requests). Finished slices are saved in {chunk_dir.name}; rerun the script to resume.")

    batch, failed, fetched_now = BATCH_SIZE, [], 0
    for i, (start, end) in enumerate(slices, 1):
        chunk_file = chunk_dir / f"{start[:10]}.json"
        if chunk_file.exists():
            continue  # already done in an earlier run
        rows, batch = fetch_slice(session, start, end, quota, batch)
        if rows is None:
            failed.append(start[:10])
            print(f"  [{i}/{len(slices)}] {start[:10]}: FAILED (will be retried on next run)")
            continue
        chunk_file.write_text(json.dumps(rows))
        fetched_now += 1
        if fetched_now % 10 == 0 or i == len(slices):
            print(f"  [{i}/{len(slices)}] {start[:10]}: {len(rows)} rows")

    # Combine every saved slice into the raw file
    records = []
    for chunk_file in sorted(chunk_dir.glob("*.json")):
        records.extend(json.loads(chunk_file.read_text()))
    df = pd.DataFrame(records).reindex(columns=FIELDS)  # missing fields become empty columns
    df.to_csv(RAW_FILE, index=False)

    meta = {
        "extraction_date": datetime.now().isoformat(timespec="seconds"),
        "api_url": API_URL,
        "window_start": START_DATE,
        "window_end": END_DATE,
        "sampling": f"systematic: unique_key ends in {SAMPLE_ENDINGS} (~{len(SAMPLE_ENDINGS)}% of requests)",
        "slice_days": SLICE_DAYS,
        "max_rows_per_slice": quota,
        "actual_rows": int(len(df)),
        "failed_slices": failed,
        "fields": FIELDS,
        "note": "Systematic sample by ID ending; ID order follows time, so all hours/days are covered evenly.",
    }
    META_FILE.write_text(json.dumps(meta, indent=2))
    print(f"\nSaved {len(df):,} rows -> {RAW_FILE}")
    if failed:
        print(f"WARNING: {len(failed)} slice(s) failed: {failed[:5]}{'...' if len(failed) > 5 else ''}")
        print("Run the script again to fetch just the missing slices.")


if __name__ == "__main__":
    main()
