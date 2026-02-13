"""
Exploratory Data Analysis utilities for California Housing dataset.
Uses pandas + Altair only. No side effects; all functions return DataFrames or Altair Charts.
"""

from __future__ import annotations

from pathlib import Path

import altair as alt
import numpy as np
import pandas as pd

# Allow full dataset for Altair (default 5000-row limit)
alt.data_transformers.disable_max_rows()

CHART_WIDTH = 420
CHART_HEIGHT = 300


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------


def load_housing_data(path: str | Path = "data/raw/housing.csv") -> pd.DataFrame:
    """
    Load California Housing dataset from CSV.
    Returns a DataFrame; path is relative to project root.
    """
    p = Path(path)
    if not p.is_absolute():
        # Resolve relative to common project roots
        for root in [Path.cwd(), Path.cwd().parent]:
            candidate = root / path
            if candidate.exists():
                return pd.read_csv(candidate)
        p = Path.cwd() / path
    return pd.read_csv(p)


# ---------------------------------------------------------------------------
# Table functions
# ---------------------------------------------------------------------------


def basic_shape_table(df: pd.DataFrame) -> pd.DataFrame:
    """
    Basic dataset shape: rows, columns, memory, duplicates.
    """
    return pd.DataFrame(
        [
            {"metric": "rows", "value": df.shape[0]},
            {"metric": "columns", "value": df.shape[1]},
            {"metric": "memory (MB)", "value": round(df.memory_usage(deep=True).sum() / 1024**2, 4)},
            {"metric": "duplicate rows", "value": df.duplicated().sum()},
        ]
    )


def missingness_table(df: pd.DataFrame) -> pd.DataFrame:
    """
    Missing count and percentage per column, sorted descending.
    """
    n = len(df)
    miss = df.isna().sum()
    pct = (miss / n * 100).round(2)
    out = pd.DataFrame({"column": miss.index, "missing_count": miss.values, "missing_pct": pct.values})
    out = out[out["missing_count"] > 0].sort_values("missing_count", ascending=False).reset_index(drop=True)
    return out if len(out) > 0 else pd.DataFrame({"column": [], "missing_count": [], "missing_pct": []})


def dtypes_table(df: pd.DataFrame) -> pd.DataFrame:
    """
    Column dtypes overview.
    """
    return pd.DataFrame({"column": df.columns, "dtype": [str(t) for t in df.dtypes]}).reset_index(drop=True)


def summary_stats_table(df: pd.DataFrame) -> pd.DataFrame:
    """
    Summary statistics for numeric columns (describe + extra quantiles).
    """
    numeric = df.select_dtypes(include=[np.number])
    if numeric.empty:
        return pd.DataFrame()
    desc = numeric.describe().T
    desc["q10"] = numeric.quantile(0.10)
    desc["q90"] = numeric.quantile(0.90)
    desc = desc.round(4)
    desc.insert(0, "column", desc.index)
    return desc.reset_index(drop=True)


def correlation_table(
    df: pd.DataFrame,
    target_col: str = "median_house_value",
    method: str = "pearson",
) -> pd.DataFrame:
    """
    Correlations with target, sorted by absolute value.
    """
    numeric = df.select_dtypes(include=[np.number])
    if target_col not in numeric.columns or len(numeric.columns) < 2:
        return pd.DataFrame({"column": [], "correlation": []})
    numeric = numeric.drop(columns=[target_col], errors="ignore")
    if numeric.empty:
        return pd.DataFrame({"column": [], "correlation": []})
    corr = numeric.corrwith(df[target_col], method=method).sort_values(key=abs, ascending=False)
    return pd.DataFrame({"column": corr.index, "correlation": corr.values.round(4)}).reset_index(drop=True)


def category_counts_table(df: pd.DataFrame, col: str = "ocean_proximity") -> pd.DataFrame:
    """
    Value counts for a categorical column.
    """
    if col not in df.columns:
        return pd.DataFrame({col: [], "count": []})
    counts = df[col].value_counts().reset_index()
    counts.columns = [col, "count"]
    return counts


# ---------------------------------------------------------------------------
# Plot functions (Altair; returned, not saved)
# ---------------------------------------------------------------------------


def _optimal_bins(series: pd.Series) -> int:
    """Compute optimal bin count using Sturges' formula, clamped to reasonable range."""
    n = series.dropna().count()
    if n < 2:
        return 10
    k = int(np.ceil(1 + np.log2(n)))
    return min(50, max(15, k))


def histograms_numeric(df: pd.DataFrame) -> alt.Chart:
    """
    3×3 grid of histograms for numeric columns, each with optimal bin count.
    """
    numeric = df.select_dtypes(include=[np.number])
    if numeric.empty:
        return alt.Chart(pd.DataFrame()).mark_bar().properties(width=CHART_WIDTH, height=CHART_HEIGHT)
    cols = list(numeric.columns)
    cell_width = 180
    cell_height = 140
    charts = []
    for col in cols:
        n_bins = _optimal_bins(numeric[col])
        chart = (
            alt.Chart(numeric)
            .mark_bar(opacity=0.8)
            .encode(
                alt.X(col, bin=alt.Bin(maxbins=n_bins), title=col[:14]),
                alt.Y("count()", title="Count"),
            )
            .properties(width=cell_width, height=cell_height, title=col)
        )
        charts.append(chart)
    # Pad to 9 for 3×3 grid
    while len(charts) < 9:
        charts.append(alt.Chart(pd.DataFrame()).mark_bar().properties(width=cell_width, height=cell_height))
    # Build 3×3: 3 rows of 3 charts each
    row1 = alt.hconcat(*charts[0:3], spacing=10)
    row2 = alt.hconcat(*charts[3:6], spacing=10)
    row3 = alt.hconcat(*charts[6:9], spacing=10)
    return alt.vconcat(row1, row2, row3, spacing=10).properties(title="Numeric variable distributions")


def target_distribution(df: pd.DataFrame, target_col: str = "median_house_value") -> alt.Chart:
    """
    Histogram of target variable (median_house_value).
    """
    if target_col not in df.columns:
        return alt.Chart(pd.DataFrame()).mark_bar().properties(width=CHART_WIDTH, height=CHART_HEIGHT)
    return (
        alt.Chart(df)
        .mark_bar(opacity=0.8)
        .encode(
            alt.X(target_col, bin=alt.Bin(maxbins=50), title=f"{target_col} ($)"),
            alt.Y("count()", title="Count"),
        )
        .properties(width=CHART_WIDTH, height=CHART_HEIGHT, title=f"Distribution of {target_col}")
    )


def scatter_matrix_like(
    df: pd.DataFrame,
    cols: list[str] | None = None,
    target_col: str = "median_house_value",
) -> alt.Chart:
    """
    2×2 grid of scatter plots: target vs predictors. Each plot has independent scales.
    """
    numeric = df.select_dtypes(include=[np.number])
    if target_col not in numeric.columns:
        return alt.Chart(pd.DataFrame()).mark_point().properties(width=CHART_WIDTH, height=CHART_HEIGHT)
    preds = [c for c in (cols or numeric.columns) if c != target_col and c in df.columns][:4]
    if not preds:
        return alt.Chart(pd.DataFrame()).mark_point().properties(width=CHART_WIDTH, height=CHART_HEIGHT)
    cell_width = 220
    cell_height = 220
    charts = []
    for p in preds:
        chart = (
            alt.Chart(df)
            .mark_circle(opacity=0.4, size=8)
            .encode(
                alt.X(f"{p}:Q", title=p, scale=alt.Scale(zero=False)),
                alt.Y(f"{target_col}:Q", title=target_col, scale=alt.Scale(zero=False)),
                alt.Tooltip([p, target_col]),
            )
            .properties(width=cell_width, height=cell_height, title=f"{target_col} vs {p}")
        )
        charts.append(chart)
    row1 = alt.hconcat(*charts[0:2], spacing=10)
    row2 = alt.hconcat(*charts[2:4], spacing=10)
    return alt.vconcat(row1, row2, spacing=10)


def correlation_heatmap(df: pd.DataFrame) -> alt.Chart:
    """
    Altair heatmap of numeric correlation matrix.
    """
    numeric = df.select_dtypes(include=[np.number])
    if numeric.empty or len(numeric.columns) < 2:
        return alt.Chart(pd.DataFrame()).mark_rect().properties(width=CHART_WIDTH, height=CHART_HEIGHT)
    corr = numeric.corr().stack().reset_index()
    corr.columns = ["var1", "var2", "correlation"]
    return (
        alt.Chart(corr)
        .mark_rect()
        .encode(
            alt.X("var1:N", title=""),
            alt.Y("var2:N", title=""),
            alt.Color(
                "correlation:Q",
                scale=alt.Scale(scheme="blueorange", domainMid=0),
                legend=alt.Legend(title="Correlation"),
            ),
        )
        .properties(width=CHART_WIDTH, height=CHART_HEIGHT, title="Correlation heatmap")
    )


def ocean_proximity_boxplot(df: pd.DataFrame) -> alt.Chart:
    """
    Box plot of median house value by ocean_proximity.
    """
    col = "ocean_proximity"
    if col not in df.columns or "median_house_value" not in df.columns:
        return alt.Chart(pd.DataFrame()).mark_boxplot().properties(width=CHART_WIDTH, height=CHART_HEIGHT)
    data = df[[col, "median_house_value"]].dropna()
    if data.empty:
        return alt.Chart(pd.DataFrame()).mark_boxplot().properties(width=CHART_WIDTH, height=CHART_HEIGHT)
    return (
        alt.Chart(data)
        .mark_boxplot(extent="min-max")
        .encode(
            alt.X(f"{col}:N", title="Ocean proximity"),
            alt.Y("median_house_value:Q", title="Median house value ($)", scale=alt.Scale(zero=False)),
            alt.Color(f"{col}:N", legend=alt.Legend(title="Ocean proximity", orient="right")),
        )
        .properties(width=CHART_WIDTH, height=CHART_HEIGHT, title="Median house value by ocean proximity")
    )


# ---------------------------------------------------------------------------
# Geographic / urban economics focus
# ---------------------------------------------------------------------------


def geo_value_scatter(
    df: pd.DataFrame,
    lon_col: str = "longitude",
    lat_col: str = "latitude",
    value_col: str = "median_house_value",
    color_scheme: str = "viridis",
) -> alt.Chart:
    """
    Geographic scatter: lat/lon, color by median_house_value.
    Interactive (zoom/pan), tooltip with lat, lon, value, median_income.
    """
    cols = [lon_col, lat_col, value_col]
    extra = "median_income" if "median_income" in df.columns else None
    tooltip = cols + ([extra] if extra else [])
    for c in cols:
        if c not in df.columns:
            return alt.Chart(pd.DataFrame()).mark_circle().properties(width=CHART_WIDTH, height=CHART_HEIGHT)
    return (
        alt.Chart(df)
        .mark_circle(opacity=0.6, size=12)
        .encode(
            alt.X(f"{lon_col}:Q", title="Longitude", scale=alt.Scale(domain=[df[lon_col].min(), df[lon_col].max()])),
            alt.Y(f"{lat_col}:Q", title="Latitude", scale=alt.Scale(domain=[df[lat_col].min(), df[lat_col].max()])),
            alt.Color(f"{value_col}:Q", scale=alt.Scale(scheme=color_scheme), legend=alt.Legend(title=f"{value_col} ($)")),
            alt.Tooltip(tooltip),
        )
        .properties(width=CHART_WIDTH, height=CHART_HEIGHT, title="Geographic distribution of house values")
        .interactive()
    )


def geo_value_extremes(
    df: pd.DataFrame,
    lon_col: str = "longitude",
    lat_col: str = "latitude",
    value_col: str = "median_house_value",
    top_pct: float = 0.10,
    bottom_pct: float = 0.10,
) -> alt.Chart:
    """
    Geographic scatter with top/bottom value quantiles emphasized.
    Highlights clusters of high-value (top 10%) and low-value (bottom 10%) regions.
    """
    cols = [lon_col, lat_col, value_col]
    for c in cols:
        if c not in df.columns:
            return alt.Chart(pd.DataFrame()).mark_circle().properties(width=CHART_WIDTH, height=CHART_HEIGHT)
    df_ = df.copy()
    q_high = df_[value_col].quantile(1 - top_pct)
    q_low = df_[value_col].quantile(bottom_pct)
    df_["band"] = "middle"
    df_.loc[df_[value_col] >= q_high, "band"] = "top"
    df_.loc[df_[value_col] <= q_low, "band"] = "bottom"
    lon_min, lon_max = df_[lon_col].min(), df_[lon_col].max()
    lat_min, lat_max = df_[lat_col].min(), df_[lat_col].max()
    domain = ["bottom", "middle", "top"]
    range_ = ["#c0392b", "lightgray", "#27ae60"]  # red, gray, green
    df_["_size"] = df_["band"].map({"middle": 20, "top": 80, "bottom": 80})
    return (
        alt.Chart(df_)
        .mark_circle(opacity=0.7)
        .encode(
            alt.X(f"{lon_col}:Q", title="Longitude", scale=alt.Scale(domain=[lon_min, lon_max])),
            alt.Y(f"{lat_col}:Q", title="Latitude", scale=alt.Scale(domain=[lat_min, lat_max])),
            alt.Color(
                "band:N",
                scale=alt.Scale(domain=domain, range=range_),
                legend=alt.Legend(title="Value band", orient="bottom"),
            ),
            alt.Size("_size:Q", scale=alt.Scale(range=[20, 80]), legend=None),
            alt.Tooltip([lon_col, lat_col, value_col, "band"]),
        )
        .properties(
            width=CHART_WIDTH, height=CHART_HEIGHT,
            title=f"Value extremes: top {int(top_pct*100)}% vs bottom {int(bottom_pct*100)}%",
        )
    )


def geo_value_binned_mean(
    df: pd.DataFrame,
    lon_col: str = "longitude",
    lat_col: str = "latitude",
    value_col: str = "median_house_value",
    bin_size: float = 0.25,
) -> alt.Chart:
    """
    Spatial aggregation: bin lon/lat, color by mean house value per cell.
    Reveals clusters of high/low value regions.
    """
    cols = [lon_col, lat_col, value_col]
    for c in cols:
        if c not in df.columns:
            return alt.Chart(pd.DataFrame()).mark_rect().properties(width=CHART_WIDTH, height=CHART_HEIGHT)
    df_ = df.copy()
    df_["lon_bin"] = (df_[lon_col] // bin_size) * bin_size
    df_["lat_bin"] = (df_[lat_col] // bin_size) * bin_size
    agg = df_.groupby(["lon_bin", "lat_bin"])[value_col].mean().reset_index()
    agg["lon_end"] = agg["lon_bin"] + bin_size
    agg["lat_end"] = agg["lat_bin"] + bin_size
    lon_min, lon_max = df_[lon_col].min(), df_[lon_col].max()
    lat_min, lat_max = df_[lat_col].min(), df_[lat_col].max()
    return (
        alt.Chart(agg)
        .mark_rect()
        .encode(
            alt.X("lon_bin:Q", title="Longitude", scale=alt.Scale(domain=[lon_min, lon_max])),
            alt.X2("lon_end:Q"),
            alt.Y("lat_bin:Q", title="Latitude", scale=alt.Scale(domain=[lat_min, lat_max])),
            alt.Y2("lat_end:Q"),
            alt.Color(f"{value_col}:Q", scale=alt.Scale(scheme="viridis"), legend=alt.Legend(title=f"Mean {value_col} ($)")),
            alt.Tooltip(["lon_bin", "lat_bin", value_col]),
        )
        .properties(width=CHART_WIDTH, height=CHART_HEIGHT, title="Spatial aggregation: mean value by grid")
        .interactive()
    )