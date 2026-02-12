"""
Generate EDA outputs and write reports/m1_proposal.md.
Run from project root: python scripts/run_eda.py
"""

import sys
from pathlib import Path

project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

import pandas as pd

from src.eda_code import (
    load_housing_data,
    basic_shape_table,
    missingness_table,
    dtypes_table,
    summary_stats_table,
    correlation_table,
    category_counts_table,
    histograms_numeric,
    target_distribution,
    scatter_matrix_like,
    correlation_heatmap,
    ocean_proximity_bar,
    geo_value_scatter,
    geo_value_binned_mean,
    geo_value_extremes,
)

OUTPUT_DIR = project_root / "reports" / "eda_outputs"
DATA_PATH = project_root / "data" / "raw" / "housing.csv"


def df_to_markdown(df: pd.DataFrame) -> str:
    """Convert DataFrame to markdown table string."""
    if df.empty:
        return "*No data*"
    try:
        return df.to_markdown(index=False)
    except AttributeError:
        return df.to_html(index=False)


def save_chart(chart, path: Path) -> None:
    """Save Altair chart to PNG using vl-convert if available."""
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        import vl_convert as vlc
        png_data = vlc.vegalite_to_png(chart.to_json(), scale=2)
        path.write_bytes(png_data)
    except ImportError:
        try:
            chart.save(str(path))
        except Exception:
            chart.save(str(path.with_suffix(".html")))


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    df = load_housing_data(DATA_PATH)

    # Save tables
    basic_shape_table(df).to_csv(OUTPUT_DIR / "basic_shape.csv", index=False)
    missingness_table(df).to_csv(OUTPUT_DIR / "missingness.csv", index=False)
    dtypes_table(df).to_csv(OUTPUT_DIR / "dtypes.csv", index=False)
    summary_stats_table(df).to_csv(OUTPUT_DIR / "summary_stats.csv", index=False)
    correlation_table(df).to_csv(OUTPUT_DIR / "correlation.csv", index=False)
    category_counts_table(df, "ocean_proximity").to_csv(OUTPUT_DIR / "ocean_proximity_counts.csv", index=False)

    # Save charts
    save_chart(histograms_numeric(df), OUTPUT_DIR / "histograms_numeric.png")
    save_chart(target_distribution(df), OUTPUT_DIR / "target_distribution.png")
    save_chart(scatter_matrix_like(df, cols=["median_income", "housing_median_age", "latitude", "longitude"]), OUTPUT_DIR / "scatter_matrix.png")
    save_chart(correlation_heatmap(df), OUTPUT_DIR / "correlation_heatmap.png")
    save_chart(ocean_proximity_bar(df), OUTPUT_DIR / "ocean_proximity_bar.png")
    save_chart(geo_value_scatter(df), OUTPUT_DIR / "geo_value_scatter.png")
    save_chart(geo_value_binned_mean(df, bin_size=0.25), OUTPUT_DIR / "geo_value_binned.png")
    save_chart(geo_value_extremes(df), OUTPUT_DIR / "geo_value_extremes.png")

    # Build EDA section with markdown tables
    shape_md = df_to_markdown(basic_shape_table(df))
    missing_df = missingness_table(df)
    missing_md = df_to_markdown(missing_df) if not missing_df.empty else "*No missing values*"
    dtypes_md = df_to_markdown(dtypes_table(df))
    summary_md = df_to_markdown(summary_stats_table(df))
    corr_md = df_to_markdown(correlation_table(df))
    ocean_counts_md = df_to_markdown(category_counts_table(df, "ocean_proximity"))

    eda_section = f"""
## Exploratory Data Analysis (EDA)

Run `python scripts/run_eda.py` to regenerate outputs.

### Data overview and quality

{shape_md}

- Dataset has ~20k rows and 10 columns; duplicates and memory use reported above.

{missing_md}

- Any missing values are listed above (e.g. total_bedrooms often has some missings).

{dtypes_md}

- Most columns are numeric; ocean_proximity is categorical.

{summary_md}

![Numeric histograms](eda_outputs/histograms_numeric.png)

### Target and predictor relationships

![Target distribution](eda_outputs/target_distribution.png)

- Target median_house_value is right-skewed; log transform may help for modeling.

{corr_md}

- Median income has the strongest correlation with value; geographic coordinates also matter.

![Correlation heatmap](eda_outputs/correlation_heatmap.png)

![Scatter matrix](eda_outputs/scatter_matrix.png)

- Income shows a clear linear-like relationship with value; age and geography are weaker.

### Categorical EDA

{ocean_counts_md}

![Value by ocean proximity](eda_outputs/ocean_proximity_bar.png)

- Coastal and bay-adjacent blocks tend to have higher median values.

### Spatial Distribution and Clusters (Urban Economics Focus)

![Geographic scatter](eda_outputs/geo_value_scatter.png)

- Interactive scatter over California; color encodes house value. Bay Area and LA basin stand out as high-value clusters; inland regions tend lower.

![Spatial aggregation](eda_outputs/geo_value_binned.png)

- Binning reveals regional gradients: coastal premium and metro effects are visible.

![Value extremes](eda_outputs/geo_value_extremes.png)

- Top 10% (green) and bottom 10% (red) value blocks show clear spatial clustering. High-value regions concentrate near coasts and metros; low-value regions are mostly inland.
"""

    # Write m1_proposal.md
    md_content = """# Milestone 1 Proposal

## Section 1: Motivation and Purpose

**Our role:** Real Estate Firm
**Target audience:** Real Estate Traders

The California housing market is incredibly complex, and for real estate traders, finding the right investment depends on understanding how location and local demographics drive property values. It can be difficult to see the big picture when looking at raw data, often causing investors to miss out on undervalued neighborhoods or emerging trends. To solve this, we are building a data visualization app that lets traders easily explore the California housing dataset through interactive maps and charts. By filtering for factors like proximity to the ocean, median income, and house age, users can quickly spot price patterns and compare different regions at a glance. Our goal is to turn complicated census data into a clear, visual tool that helps traders make faster and more confident decisions on where to put their money.

## Section 2: Description of the Data

We will be visualizing a dataset of approximately 20,000 California housing blocks. Each block has 10 associated variables that describe the following characteristics, which we hypothesize could be helpful in determining the market value of properties in a given area:

- Geographic location (`longitude`, `latitude`, `ocean_proximity`)
- Property traits(`housing_median_age`, `total_rooms`, `total_bedrooms`)
- Demographic and economic indicators (`population`, `households`, `median_income`, `median_house_value`)

Using this data, we will also derive new variables, such as the average number of rooms per household (`rooms_per_household`) and the population density per house (`population_per_household`), as it would be interesting to explore if these ratios are stronger indicators of neighborhood prestige and investment potential than the raw totals alone.
""" + eda_section + """
## Research Questions & Usage Scenarios

### Usage scenario

Dr. Elena Ramirez is an urban economics professor and researcher at the University of California, Berkeley. Her research focuses on understanding patterns in California's housing market during the late 20th century. She is interested in examining how economic and geographic factors — such as median income, proximity to the ocean, housing age, and housing density — were associated with property values in 1990.

She uses the California Housing 1990 Dashboard to explore a geographic overview of median house values across the state. Through an interactive map, she identifies clusters of high and low value regions. She then examines scatter plots comparing median house value with median income and housing median age to evaluate which factors appear most strongly associated with price. Using bar charts, she compares housing values across ocean proximity categories and across structural characteristics such as total rooms and number of households per block.

By interactively exploring these variables, Dr. Ramirez can better understand the drivers of housing value in 1990 California. Her findings may contribute to broader discussions on long-term housing affordability, regional disparities, and the economic geography of the state.

### User stories

**User story 1:** As an urban economics researcher, I want to analyze the relationship between median income and median house value in order to determine whether higher income areas were associated with higher property prices in 1990.

**User story 2:** As an urban economics researcher, I want to compare median house values across ocean proximity categories in order to assess whether coastal access was associated with higher property values in 1990.

**User story 3:** As an urban economics researcher, I want to visualize the geographic distribution of house values across California to identify spatial clusters of high and low value regions.
"""

    report_path = project_root / "reports" / "m1_proposal.md"
    report_path.write_text(md_content, encoding="utf-8")
    print(f"EDA outputs saved to {OUTPUT_DIR}")
    print(f"Report written to {report_path}")


if __name__ == "__main__":
    main()
