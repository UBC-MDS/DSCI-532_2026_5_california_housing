"""
DuckDB-backed data layer. All filtering happens in SQL before materializing to DataFrame.
"""
from pathlib import Path

import duckdb
import pandas as pd

PARQUET_PATH = Path(__file__).resolve().parent.parent / "data" / "processed" / "housing_with_county.parquet"


def get_connection() -> duckdb.DuckDBPyConnection:
    """Return a DuckDB connection (in-memory, reads parquet)."""
    con = duckdb.connect()
    return con


def get_state_stats(con: duckdb.DuckDBPyConnection) -> dict:
    """
    Query min, max, quantiles for slider initialization and state-level medians.
    Uses median_income * 10000 as median_income_usd.
    """
    sql = """
    SELECT
        MIN(median_house_value) AS house_val_min,
        MAX(median_house_value) AS house_val_max,
        MIN(median_income * 10000) AS income_min,
        MAX(median_income * 10000) AS income_max,
        PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY median_income * 10000) AS income_q75,
        MIN(housing_median_age) AS age_min,
        MAX(housing_median_age) AS age_max,
        MIN(total_rooms) AS rooms_min,
        MAX(total_rooms) AS rooms_max,
        MIN(total_bedrooms) AS beds_min,
        MAX(total_bedrooms) AS beds_max,
        MIN(population) AS pop_min,
        MAX(population) AS pop_max,
        MIN(households) AS households_min,
        MAX(households) AS households_max,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY median_house_value) AS state_median_house_value,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY median_income * 10000) AS state_median_income_usd
    FROM read_parquet(?)
    """
    row = con.execute(sql, [str(PARQUET_PATH)]).fetchone()
    return {
        "house_val_min": row[0],
        "house_val_max": row[1],
        "income_min": row[2],
        "income_max": row[3],
        "income_q75": row[4],
        "age_min": row[5],
        "age_max": row[6],
        "rooms_min": row[7],
        "rooms_max": row[8],
        "beds_min": row[9],
        "beds_max": row[10],
        "pop_min": row[11],
        "pop_max": row[12],
        "households_min": row[13],
        "households_max": row[14],
        "state_median_house_value": row[15],
        "state_median_income_usd": row[16],
    }


def get_filtered_data(
    con: duckdb.DuckDBPyConnection,
    *,
    house_val_range: tuple[float, float],
    income_range: tuple[float, float],
    age_range: tuple[float, float],
    rooms_range: tuple[float, float],
    beds_range: tuple[float, float],
    pop_range: tuple[float, float],
    households_range: tuple[float, float],
    ocean_proximity: list[str],
    county_select: list[str],
) -> pd.DataFrame:
    """
    Execute filtered query. All filtering happens in DuckDB before returning DataFrame.
    Returns DataFrame with median_income_usd = median_income * 10000.
    """
    path = str(PARQUET_PATH)
    hv_lo, hv_hi = house_val_range
    inc_lo, inc_hi = income_range
    age_lo, age_hi = age_range
    rooms_lo, rooms_hi = rooms_range
    beds_lo, beds_hi = beds_range
    pop_lo, pop_hi = pop_range
    hh_lo, hh_hi = households_range

    ocean_list = ocean_proximity if ocean_proximity else []
    counties = [c.strip() for c in county_select] if county_select else []

    sql = f"""
    SELECT
        longitude, latitude, housing_median_age, total_rooms, total_bedrooms,
        population, households, median_income, median_house_value,
        median_income * 10000 AS median_income_usd,
        ocean_proximity, county, county_name_alt
    FROM read_parquet(?)
    WHERE
        median_house_value BETWEEN ? AND ?
        AND (median_income * 10000) BETWEEN ? AND ?
        AND housing_median_age BETWEEN ? AND ?
        AND total_rooms BETWEEN ? AND ?
        AND total_bedrooms BETWEEN ? AND ?
        AND population BETWEEN ? AND ?
        AND households BETWEEN ? AND ?
    """

    params: list = [path, hv_lo, hv_hi, inc_lo, inc_hi, age_lo, age_hi, rooms_lo, rooms_hi, beds_lo, beds_hi, pop_lo, pop_hi, hh_lo, hh_hi]

    if ocean_list:
        placeholders = ", ".join("?" * len(ocean_list))
        sql += f" AND ocean_proximity IN ({placeholders})"
        params.extend(ocean_list)

    if counties:
        c_placeholders = ", ".join("?" * len(counties))
        sql += f" AND county IN ({c_placeholders})"
        params.extend(counties)

    return con.execute(sql, params).df()


def get_counties(con: duckdb.DuckDBPyConnection) -> list[str]:
    """Return sorted list of unique county names for the dropdown."""
    df = con.execute(
        "SELECT DISTINCT county FROM read_parquet(?) WHERE county IS NOT NULL ORDER BY county",
        [str(PARQUET_PATH)],
    ).df()
    return df["county"].astype(str).tolist()


def get_full_dataframe(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """
    Load full dataset as DataFrame (for querychat). Adds median_income_usd.
    Filtering for Manual Filtering tab happens in get_filtered_data.
    """
    return con.execute(
        """
        SELECT *, median_income * 10000 AS median_income_usd
        FROM read_parquet(?)
        """,
        [str(PARQUET_PATH)],
    ).df()
