# Urban Pulse: NYC 311 Complaint Analytics (Pilot)

A pilot data project that extracts NYC 311 service-request data from the NYC Open Data API, cleans it, analyses it in Python and MySQL, and presents it in a Streamlit dashboard.

**Author:** Shiyamp 
**Data source:** [NYC 311 Service Requests](https://data.cityofnewyork.us/resource/erm2-nwe9) (NYC Open Data, dataset `erm2-nwe9`)  
**Period covered:** 1 Jan 2024 to 31 Dec 2024

## Pipeline

```
NYC Open Data API -> 01_extract.py -> data/raw/nyc311_raw.csv
                  -> 02_clean.py   -> data/clean/nyc311_clean.csv (+ cleaning log, data dictionary)
                  -> 03_eda.py     -> outputs/ (statistics, outliers, charts)
                  -> 04_load_mysql.py -> MySQL table service_requests
                  -> queries.sql   -> 15 analyst tasks (run in MySQL Workbench)
                  -> app.py        -> Streamlit dashboard
```

## Tools

| Purpose | Tool |
|---|---|
| Language and editor | Python 3.12, VS Code |
| API extraction | `requests` |
| Cleaning and statistics | `pandas` |
| Charts | `matplotlib` (EDA), `plotly` (dashboard) |
| Database | MySQL 8 and MySQL Workbench |
| Python to MySQL | `SQLAlchemy`, `PyMySQL`, `cryptography` |
| Dashboard | `Streamlit` |
| Secrets | `python-dotenv` (`.env` file) |

## Files

| File | Purpose |
|---|---|
| `config.py` | Shared settings: paths, API window, sampling, MySQL connection |
| `01_extract.py` | Day-by-day API extraction with retries and resumable chunk files |
| `02_clean.py` | Cleaning, derived fields, quality flags, cleaning log, data dictionary |
| `03_eda.py` | Descriptive statistics, skewness, IQR outliers, charts |
| `04_load_mysql.py` | Loads into a staging table, validates counts, then publishes |
| `queries.sql` | The 15 analyst queries (MySQL 8 window functions) |
| `app.py` | Streamlit dashboard (CSV or MySQL as the data source) |
| `.env.example` | Template for the private `.env` settings file |
| `requirements.txt` | Python packages |

## How to run

1. **Clone and enter the project**
   ```powershell
   git clone https://github.com/YOUR_USERNAME/Urban_Pulse.git
   cd Urban_Pulse
   ```
2. **Create a virtual environment and install packages**
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install -r requirements.txt
   ```
3. **Create your private settings file.** Copy `.env.example` to `.env` and enter your own MySQL password. The `.env` file is not part of this repository.
4. **Install MySQL 8** and make sure the service is running.
5. **Run the steps in order**
   ```powershell
   python 01_extract.py
   python 02_clean.py
   python 03_eda.py
   python 04_load_mysql.py
   python -m streamlit run app.py
   ```
6. Open `queries.sql` in MySQL Workbench and run the queries one at a time.

The dashboard's CSV option works after step 02, before MySQL is set up.

## Sampling method

The full dataset has millions of rows, so the pilot uses a **systematic sample of about 3%**: only requests whose `unique_key` ends in `07`, `17` or `27` are kept. Request IDs are issued in time order, so this takes a thin slice from every day and every hour of the year. Busy days keep more rows and quiet days keep fewer, so monthly, weekday and hourly patterns reflect real demand.

An earlier design that took the first rows of each day was rejected: it covered only the first minutes after midnight and distorted hourly patterns and agency shares. The hourly counts of the final sample cover all 24 hours with a realistic daily curve.

The result is **103,716 rows**. Counts are about 1/33 of citywide volumes, so results are reported as shares and medians, not citywide totals. The extraction settings and row count are saved in `data/raw/extraction_metadata.json`.

## Data quality (from the cleaning log)

| Check | Result |
|---|---|
| Rows extracted and kept | 103,716 |
| Missing or duplicate request IDs | 0 |
| Unparseable dates (all four date columns) | 0 |
| Requests with a closed date | 101,885 (98.2%) |
| Closed date earlier than created date (flagged, excluded from durations) | 27 |
| Valid resolution durations | 101,858 (98.2%) |
| Coordinates inside an approximate NYC bounding box | 102,109 (98.5%) |

`due_date` is empty for 99.5% of rows and is not used.

## Key findings (3% sample)

- **Resolution time is extremely right-skewed.** Median 7.96 hours, mean 327.5 hours, skewness 6.84. The median is the typical value.
- **Speed depends on the agency.** Median resolution: NYPD 1.1 hours, DSNY about 1.2 days, DOT 1.9 days, HPD 3.8 days, DOB 16.5 days, TLC 73 days.
- **The slowest complaint categories** have medians of months (for example New Tree Request, about 338 days), but several have few cases.
- **Volume:** Illegal Parking 14.6%, Noise - Residential 10.9% and Heat/Hot Water 7.6% of requests. NYPD handles 45.1% and HPD 21.1%.
- **Boroughs:** Brooklyn 30.2%, Queens 24.0%, Bronx 21.5%, Manhattan 20.8%, Staten Island 3.4%.
- **Daily pattern:** requests peak around 9 to 11 am and are lowest around 4 am, with a smaller rise at 9 to 10 pm.
- **Outliers:** 16.6% of durations lie above the IQR upper fence (202 hours). They are flagged for review and kept, because they mostly reflect different request types.

## Limitations

- "Closed" means a closed date is recorded. It does not show that the issue was solved or that the citizen was satisfied.
- Some categories have a median of exactly 0 hours (for example Rodent), which suggests the closed date is recorded at creation. These are not the "fastest" categories.
- Results come from a systematic sample and are not random. Raw counts are not rates, so boroughs should not be ranked as better or worse without population figures.
- Differences between agencies reflect different kinds of work and are not evidence of performance.
- Latitude and longitude validity uses a rough rectangle around NYC, so a few points just outside the city may pass.
- Categories with few valid cases have unstable medians.

## Security note

The MySQL password is stored only in a local `.env` file, which is excluded by `.gitignore`. Never commit it.
