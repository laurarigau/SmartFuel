"""
Data cleaning module for SmartFuel.

Transforms raw JSON snapshots into analysis-ready DataFrames, converting
Spanish field names to English, parsing decimal formats, computing geohash
codes, and persisting results as Parquet and CSV.
"""

import json
import math
import os
from datetime import datetime
from typing import Any

import pandas as pd

from src.utils.config import (
    CLEAN_COLUMNS,
    COLUMN_MAPPING,
    GEOHASH_PRECISION,
    NUMERIC_COLUMNS,
    PARQUET_DIR,
    PROCESSED_DIR,
    RAW_COLUMNS,
)
from src.utils.logger import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Base-32 alphabet used by the standard geohash specification
# ---------------------------------------------------------------------------
_GEOHASH_BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"


# ---------------------------------------------------------------------------
# Spanish-decimal conversion
# ---------------------------------------------------------------------------


def convert_spanish_decimal(value: Any) -> float | None:
    """Convert a Spanish-format decimal string to a Python float.

    Spanish numbers use a comma as the decimal separator (e.g. ``"1,699"``).
    Empty strings, ``None``, and other non-convertible values return ``None``.

    Args:
        value: Raw value from the API response.

    Returns:
        The numeric value as a ``float``, or ``None`` if the input cannot be
        parsed.
    """
    if value is None:
        return None

    if isinstance(value, (int, float)):
        if math.isnan(value):
            return None
        return float(value)

    text = str(value).strip()
    if text == "":
        return None

    try:
        return float(text.replace(",", "."))
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Geohash implementation (no external library)
# ---------------------------------------------------------------------------


def _encode_geohash(latitude: float, longitude: float, precision: int) -> str:
    """Encode a (lat, lon) pair into a geohash string.

    This is a self-contained implementation of the public-domain geohash
    algorithm.  It interleaves longitude and latitude bits and maps each
    5-bit group to the base-32 alphabet.

    Args:
        latitude: Latitude in decimal degrees (−90 to 90).
        longitude: Longitude in decimal degrees (−180 to 180).
        precision: Number of characters in the returned geohash.

    Returns:
        Geohash string of length ``precision``.
    """
    lat_range = [-90.0, 90.0]
    lon_range = [-180.0, 180.0]
    bits = 0
    char_index = 0
    geohash_chars: list[str] = []
    is_longitude = True  # longitude bit comes first

    while len(geohash_chars) < precision:
        if is_longitude:
            mid = (lon_range[0] + lon_range[1]) / 2.0
            if longitude >= mid:
                char_index = (char_index << 1) | 1
                lon_range[0] = mid
            else:
                char_index = char_index << 1
                lon_range[1] = mid
        else:
            mid = (lat_range[0] + lat_range[1]) / 2.0
            if latitude >= mid:
                char_index = (char_index << 1) | 1
                lat_range[0] = mid
            else:
                char_index = char_index << 1
                lat_range[1] = mid

        is_longitude = not is_longitude
        bits += 1

        if bits == 5:
            geohash_chars.append(_GEOHASH_BASE32[char_index])
            bits = 0
            char_index = 0

    return "".join(geohash_chars)


def _safe_geohash(row: pd.Series) -> str | None:
    """Compute geohash for a DataFrame row, returning *None* on error."""
    try:
        lat = row["latitude"]
        lon = row["longitude"]
        if lat is None or lon is None or math.isnan(lat) or math.isnan(lon):
            return None
        return _encode_geohash(lat, lon, GEOHASH_PRECISION)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# DataFrame cleaning
# ---------------------------------------------------------------------------


def clean_dataframe(
    df: pd.DataFrame,
    snapshot_date: str | None = None,
) -> pd.DataFrame:
    """Apply all cleaning transformations to a raw station DataFrame.

    Steps:
        1. Select only the columns listed in ``config.RAW_COLUMNS``.
        2. Rename them using ``config.COLUMN_MAPPING``.
        3. Convert numeric columns from Spanish decimal format.
        4. Parse ``snapshot_date`` if present.
        5. Drop rows that have no ``station_id``.
        6. Add a ``geohash`` column computed from latitude / longitude.

    Args:
        df: Raw DataFrame whose columns match the API field names.
        snapshot_date: Optional snapshot timestamp string to set if not in df.

    Returns:
        Cleaned DataFrame with standardised column names and types.
    """
    if snapshot_date and "snapshot_date" not in df.columns:
        df = df.copy()
        df["snapshot_date"] = snapshot_date

    # 1. Select & rename
    available_cols = [c for c in RAW_COLUMNS if c in df.columns]
    # Preserve snapshot_date if present
    extra_cols = [c for c in ["snapshot_date"] if c in df.columns and c not in available_cols]
    df = df[available_cols + extra_cols].copy()
    df.rename(columns=COLUMN_MAPPING, inplace=True)

    # 2. Convert numeric columns
    for col in NUMERIC_COLUMNS:
        if col in df.columns:
            df[col] = df[col].apply(convert_spanish_decimal)

    # 3. Parse snapshot_date
    if "snapshot_date" in df.columns:
        df["snapshot_date"] = pd.to_datetime(df["snapshot_date"], errors="coerce")

    # 4. Drop rows without station_id
    if "station_id" in df.columns:
        df = df.dropna(subset=["station_id"]).copy()
        df["station_id"] = df["station_id"].astype(str)

    # 5. Geohash
    df["geohash"] = df.apply(_safe_geohash, axis=1)

    logger.info("Cleaned DataFrame: %d rows, %d columns", len(df), len(df.columns))
    return df


# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------


def save_parquet(
    df: pd.DataFrame,
    timestamp: str,
    output_dir: str | None = None,
) -> str:
    """Save a DataFrame as a Parquet file.

    Args:
        df: DataFrame to persist.
        timestamp: Timestamp string used in the file name (``YYYY-MM-DD_HHMM``).
        output_dir: Target directory. Defaults to ``config.PARQUET_DIR``.

    Returns:
        Absolute path of the saved file.
    """
    output_dir = output_dir or PARQUET_DIR
    os.makedirs(output_dir, exist_ok=True)
    filename = f"fuel_prices_{timestamp}.parquet"
    path = os.path.join(output_dir, filename)
    try:
        df.to_parquet(path, index=False)
        logger.info("Saved Parquet to %s (%d rows)", path, len(df))
        return path
    except (ImportError, ModuleNotFoundError) as exc:
        logger.warning("Parquet engine (pyarrow) not installed: %s. Skipping parquet save.", exc)
        return ""


def save_csv(
    df: pd.DataFrame,
    timestamp: str,
    output_dir: str | None = None,
) -> str:
    """Save a DataFrame as a CSV file.

    Args:
        df: DataFrame to persist.
        timestamp: Timestamp string used in the file name (``YYYY-MM-DD_HHMM``).
        output_dir: Target directory. Defaults to ``config.PROCESSED_DIR``.

    Returns:
        Absolute path of the saved file.
    """
    output_dir = output_dir or PROCESSED_DIR
    os.makedirs(output_dir, exist_ok=True)
    filename = f"fuel_prices_{timestamp}.csv"
    path = os.path.join(output_dir, filename)
    df.to_csv(path, index=False, encoding="utf-8")
    logger.info("Saved CSV to %s (%d rows)", path, len(df))
    return path


# ---------------------------------------------------------------------------
# End-to-end cleaning of a raw JSON file
# ---------------------------------------------------------------------------


def clean_raw_file(
    file_path: str,
    parquet_dir: str | None = None,
    csv_dir: str | None = None,
) -> dict[str, Any]:
    """Load a raw JSON snapshot, clean it, and persist as Parquet + CSV.

    Args:
        file_path: Path to the raw JSON file (output of the ingestion step).
        parquet_dir: Optional override for Parquet output directory.
        csv_dir: Optional override for CSV output directory.

    Returns:
        Dictionary with keys:
            - ``parquet_path`` (*str*)
            - ``csv_path`` (*str*)
            - ``row_count`` (*int*)
            - ``timestamp`` (*str*)
    """
    logger.info("Cleaning raw file: %s", file_path)

    with open(file_path, "r", encoding="utf-8") as fh:
        data: dict[str, Any] = json.load(fh)

    # Extract timestamp from the Fecha field
    fecha_str: str = data.get("Fecha", "")
    try:
        snapshot_dt = datetime.strptime(fecha_str, "%d/%m/%Y %H:%M:%S")
    except (ValueError, TypeError):
        logger.warning("Could not parse Fecha '%s'; using current time", fecha_str)
        snapshot_dt = datetime.utcnow()

    timestamp = snapshot_dt.strftime("%Y-%m-%d_%H%M")

    # Build DataFrame from station list
    stations = data.get("ListaEESSPrecio", [])
    df = pd.DataFrame(stations)

    # Attach the snapshot date so it survives cleaning
    df["snapshot_date"] = fecha_str

    df = clean_dataframe(df)

    parquet_path = save_parquet(df, timestamp, output_dir=parquet_dir)
    csv_path = save_csv(df, timestamp, output_dir=csv_dir)

    result = {
        "parquet_path": parquet_path,
        "csv_path": csv_path,
        "row_count": len(df),
        "timestamp": timestamp,
    }
    logger.info("Cleaning complete: %s", result)
    return result
