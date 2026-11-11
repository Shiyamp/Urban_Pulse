"""STEP 3 - Statistics and EDA on resolution_hours (spread, skewness, IQR outliers).

Outliers are FLAGGED for review, never deleted automatically.
Run:  python 03_eda.py     (charts and tables are saved in the outputs/ folder)
"""
import matplotlib.pyplot as plt
import pandas as pd

from config import CLEAN_FILE, DATE_COLS, OUT_DIR


def main():
    df = pd.read_csv(CLEAN_FILE, parse_dates=DATE_COLS, low_memory=False)
    print(f"Rows: {len(df):,}   Columns: {df.shape[1]}")
    print("\nMissing values (top 10 columns):")
    print(df.isna().sum().sort_values(ascending=False).head(10))

    s = df["resolution_hours"].dropna()
    if s.empty:
        raise SystemExit("No valid resolution durations found. Use a larger or older date window.")

    q1, q3 = s.quantile(0.25), s.quantile(0.75)
    iqr = q3 - q1
    low, high = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    outliers = df[(df["resolution_hours"] < low) | (df["resolution_hours"] > high)]

    stats = pd.Series({
        "count": len(s),
        "mean": s.mean(),
        "median": s.median(),
        "mode (rounded hours)": s.round(0).mode().iloc[0],
        "min": s.min(),
        "max": s.max(),
        "range": s.max() - s.min(),
        "Q1": q1,
        "Q3": q3,
        "IQR": iqr,
        "variance": s.var(),
        "std": s.std(),
        "skewness": s.skew(),
        "lower_fence": low,
        "upper_fence": high,
        "outlier_count": len(outliers),
        "outlier_pct": 100 * len(outliers) / len(s),
    }).round(2)
    print("\nResolution hours - summary:")
    print(stats.to_string())
    stats.to_csv(OUT_DIR / "resolution_stats.csv", header=["value"])
    outliers.to_csv(OUT_DIR / "resolution_outliers_for_review.csv", index=False)

    if stats["skewness"] > 1:
        print("\nNote: strongly right-skewed -> report the MEDIAN, not only the mean.")

    # Charts (clipped at the 99th percentile so a few extreme values don't flatten the picture)
    clip = s[s <= s.quantile(0.99)]
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    axes[0].hist(clip, bins=50, color="#4C78A8")
    axes[0].set(title="Resolution hours (up to 99th percentile)", xlabel="hours", ylabel="requests")
    axes[1].boxplot(clip, vert=False)
    axes[1].set(title="Boxplot (up to 99th percentile)", xlabel="hours")
    plt.tight_layout()
    plt.savefig(OUT_DIR / "resolution_distribution.png", dpi=120)
    plt.close()

    # Quick views for analyst tasks 2, 3, 4
    for col in ("complaint_type", "agency", "borough"):
        print(f"\nTop values - {col}:")
        print(df[col].value_counts().head(10).to_string())

    print(f"\nSaved tables and chart in: {OUT_DIR}")


if __name__ == "__main__":
    main()
