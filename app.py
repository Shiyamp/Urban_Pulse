"""STEP 5 - Urban Pulse Streamlit dashboard.
Run:  streamlit run app.py
Data source can be switched in the sidebar: CSV (works right after Step 2) or MySQL (after Step 4).
"""
import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import create_engine
from sqlalchemy.engine import URL

from config import CLEAN_FILE, DATE_COLS, MYSQL

st.set_page_config(page_title="Urban Pulse", page_icon="🏙️", layout="wide")
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


@st.cache_data(show_spinner="Loading CSV...")
def load_csv():
    return pd.read_csv(CLEAN_FILE, parse_dates=DATE_COLS, low_memory=False)


@st.cache_data(show_spinner="Querying MySQL...")
def load_mysql():
    url = URL.create("mysql+pymysql", username=MYSQL["user"], password=MYSQL["password"],
                     host=MYSQL["host"], port=MYSQL["port"], database=MYSQL["database"])
    return pd.read_sql("SELECT * FROM service_requests", create_engine(url), parse_dates=DATE_COLS)


def fmt(value, suffix=""):
    return "n/a" if pd.isna(value) else f"{value:,.1f}{suffix}"


# ---------------- Load data (with readable error handling) ----------------
st.title("🏙️ Urban Pulse - NYC 311 Complaint Analytics")
source = st.sidebar.selectbox("Data source", ["CSV (pilot)", "MySQL"])
try:
    df = load_csv() if source.startswith("CSV") else load_mysql()
except FileNotFoundError:
    st.error("Cleaned CSV not found. Run 01_extract.py and 02_clean.py first.")
    st.stop()
except Exception as err:  # noqa: BLE001
    st.error(f"Could not load data from {source}. Check MySQL is running and .env is correct.\n\n{err}")
    st.stop()

df["is_closed"] = df["is_closed"].astype(bool)
df["coord_valid"] = df["coord_valid"].astype(bool)

# ---------------- Sidebar filters ----------------
st.sidebar.header("Filters")
dmin, dmax = df["created_date"].min().date(), df["created_date"].max().date()
date_range = st.sidebar.date_input("Created between", (dmin, dmax), min_value=dmin, max_value=dmax)
if len(date_range) != 2:
    st.info("Pick both a start and an end date.")
    st.stop()

boroughs = st.sidebar.multiselect("Borough", sorted(df["borough"].dropna().unique()),
                                  default=sorted(df["borough"].dropna().unique()))
top_types = df["complaint_type"].value_counts().head(100).index.tolist()
types = st.sidebar.multiselect("Complaint type (empty = all)", top_types)

mask = df["created_date"].dt.date.between(*date_range) & df["borough"].isin(boroughs)
if types:
    mask &= df["complaint_type"].isin(types)
f = df[mask]
if f.empty:
    st.warning("No records match these filters. Widen the date range or choose more boroughs.")
    st.stop()

# ---------------- Five KPIs ----------------
valid = f["resolution_hours"].dropna()
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Total requests", f"{f['unique_key'].nunique():,}")
c2.metric("Recorded closure", fmt(100 * f["is_closed"].mean(), "%"))
c3.metric("Open requests", f"{(~f['is_closed']).sum():,}")
c4.metric("Median resolution (h)", fmt(valid.median() if len(valid) else float("nan")))
c5.metric("Over 72 hours", fmt(100 * (valid > 72).mean() if len(valid) else float("nan"), "%"))
st.caption("Closure = a closed date is recorded; it is NOT a measure of citizen satisfaction. "
           "The 72-hour line is an illustrative project cut-off, not an official standard.")

# ---------------- Analyst pages ----------------
t1, t2, t3, t4, t5 = st.tabs(["Overview", "Trends", "Resolution", "Geography", "Data"])

with t1:
    a, b = st.columns(2)
    top = f["complaint_type"].value_counts().head(10).reset_index()
    top.columns = ["complaint_type", "requests"]
    a.plotly_chart(px.bar(top, x="requests", y="complaint_type", orientation="h",
                          title="Top 10 complaint types").update_yaxes(autorange="reversed"),
                   use_container_width=True)
    bor = f["borough"].value_counts().reset_index()
    bor.columns = ["borough", "requests"]
    b.plotly_chart(px.bar(bor, x="borough", y="requests", title="Requests by borough"),
                   use_container_width=True)
    a, b = st.columns(2)
    ag = f["agency"].value_counts().head(10).reset_index()
    ag.columns = ["agency", "requests"]
    a.plotly_chart(px.bar(ag, x="agency", y="requests", title="Agency workload (top 10)"),
                   use_container_width=True)
    stt = f["status"].value_counts().reset_index()
    stt.columns = ["status", "requests"]
    b.plotly_chart(px.pie(stt, names="status", values="requests", title="Recorded status"),
                   use_container_width=True)

with t2:
    monthly = f.groupby("created_month").size().reset_index(name="requests")
    st.plotly_chart(px.line(monthly, x="created_month", y="requests", markers=True,
                            title="Monthly request trend"), use_container_width=True)
    heat = (f.groupby(["created_weekday", "created_hour"]).size().unstack(fill_value=0)
              .reindex(WEEKDAYS))
    st.plotly_chart(px.imshow(heat, aspect="auto", labels=dict(x="Hour", y="Weekday", color="Requests"),
                              title="Demand by weekday and hour"), use_container_width=True)

with t3:
    if valid.empty:
        st.info("No valid resolution durations in the current filter.")
    else:
        clipped = valid[valid <= valid.quantile(0.99)]
        a, b = st.columns(2)
        a.plotly_chart(px.histogram(clipped, nbins=50, title="Resolution hours (to 99th percentile)"),
                       use_container_width=True)
        b.plotly_chart(px.box(clipped, title="Boxplot (to 99th percentile)"), use_container_width=True)
        st.write(f"Mean {valid.mean():,.1f} h | Median {valid.median():,.1f} h | "
                 f"Skewness {valid.skew():,.2f} (above 1 means strongly right-skewed: trust the median)")
        grp = (f.dropna(subset=["resolution_hours"]).groupby("complaint_type")["resolution_hours"]
                 .agg(valid_cases="count", median_hours="median").reset_index())
        grp = grp[grp["valid_cases"] >= 30].sort_values("median_hours", ascending=False)
        st.subheader("Median resolution by complaint type (30+ valid cases)")
        st.dataframe(grp.head(20), use_container_width=True)
        st.caption("Outliers are prompts for investigation, not errors: long cases can be legitimate.")

with t4:
    geo = f[f["coord_valid"]]
    st.write(f"{len(geo):,} of {len(f):,} filtered rows have usable coordinates.")
    if len(geo):
        st.map(geo.sample(min(5000, len(geo)), random_state=1)[["latitude", "longitude"]])
    st.subheader("Borough summary")
    st.dataframe(f.groupby("borough").agg(requests=("unique_key", "count"),
                                          closure_rate_pct=("is_closed", lambda s: round(100 * s.mean(), 1))),
                 use_container_width=True)

with t5:
    st.write("Filtered record preview (first 500 rows)")
    st.dataframe(f.head(500), use_container_width=True)
    st.download_button("Download filtered data (CSV)", f.to_csv(index=False).encode("utf-8"),
                       "urban_pulse_filtered.csv", "text/csv")
