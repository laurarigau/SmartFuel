"""
Price change detection module for SmartFuel.

Compares consecutive fuel-price snapshots to identify stations where prices
have moved, including the magnitude and direction of each change.
"""

import glob
import json
import os
from datetime import datetime
from typing import Any

import pandas as pd

from src.utils.config import PARQUET_DIR
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Fuel-type columns whose price changes we track
_FUEL_COLUMNS: list[str] = [
    "gasoline_95_price",
    "diesel_price",
    "gasoline_98_price",
    "diesel_premium_price",
]

# Human-friendly labels for each fuel column
_FUEL_LABELS: dict[str, str] = {
    "gasoline_95_price": "Gasoline 95 E5",
    "diesel_price": "Diesel A",
    "gasoline_98_price": "Gasoline 98 E5",
    "diesel_premium_price": "Diesel Premium",
}


def detect_price_changes(
    current_df: pd.DataFrame,
    previous_df: pd.DataFrame | None,
) -> pd.DataFrame:
    """Compare two snapshots and return rows where prices have changed.

    For every station × fuel-type combination where the price differs between
    *previous_df* and *current_df*, a row is emitted with the old / new price,
    absolute change, and percentage change.

    Args:
        current_df: Cleaned DataFrame for the latest snapshot.
        previous_df: Cleaned DataFrame for the immediately preceding snapshot,
            or ``None`` if no prior data is available.

    Returns:
        DataFrame with columns: ``station_id``, ``station_name``,
        ``municipality``, ``province``, ``fuel_type``, ``old_price``,
        ``new_price``, ``price_change``, ``pct_change``, ``snapshot_date``.
        Empty DataFrame (with the same schema) when *previous_df* is ``None``
        or when no prices changed.
    """
    empty_schema = {
        "station_id": pd.Series(dtype="str"),
        "station_name": pd.Series(dtype="str"),
        "municipality": pd.Series(dtype="str"),
        "province": pd.Series(dtype="str"),
        "fuel_type": pd.Series(dtype="str"),
        "old_price": pd.Series(dtype="float64"),
        "new_price": pd.Series(dtype="float64"),
        "price_change": pd.Series(dtype="float64"),
        "pct_change": pd.Series(dtype="float64"),
        "snapshot_date": pd.Series(dtype="object"),
    }

    if previous_df is None or previous_df.empty:
        logger.info("No previous snapshot available — returning empty changes")
        return pd.DataFrame(empty_schema)

    # Ensure station_id is string in both DataFrames
    current_df = current_df.copy()
    previous_df = previous_df.copy()
    current_df["station_id"] = current_df["station_id"].astype(str)
    previous_df["station_id"] = previous_df["station_id"].astype(str)

    # Merge on station_id — inner join keeps only stations present in both
    merge_cols = ["station_id"]
    merged = current_df.merge(
        previous_df[merge_cols + _FUEL_COLUMNS],
        on="station_id",
        suffixes=("_new", "_old"),
        how="inner",
    )

    change_records: list[dict[str, Any]] = []

    for fuel_col in _FUEL_COLUMNS:
        new_col = f"{fuel_col}_new"
        old_col = f"{fuel_col}_old"

        if new_col not in merged.columns or old_col not in merged.columns:
            continue

        # Subset rows where both prices are present and differ
        mask = (
            merged[new_col].notna()
            & merged[old_col].notna()
            & (merged[new_col] != merged[old_col])
        )
        subset = merged.loc[mask]

        for _, row in subset.iterrows():
            old_price = float(row[old_col])
            new_price = float(row[new_col])
            price_change = new_price - old_price
            pct_change = (price_change / old_price) * 100.0 if old_price != 0 else 0.0

            snapshot_date = ""
            if "snapshot_date" in current_df.columns:
                # Use the first non-null snapshot_date from the current frame
                sd = current_df["snapshot_date"].dropna()
                if not sd.empty:
                    snapshot_date = str(sd.iloc[0])

            change_records.append(
                {
                    "station_id": str(row["station_id"]),
                    "station_name": row.get("station_name", ""),
                    "municipality": row.get("municipality", ""),
                    "province": row.get("province", ""),
                    "fuel_type": _FUEL_LABELS.get(fuel_col, fuel_col),
                    "old_price": old_price,
                    "new_price": new_price,
                    "price_change": round(price_change, 4),
                    "pct_change": round(pct_change, 2),
                    "snapshot_date": snapshot_date,
                }
            )

    if not change_records:
        logger.info("No price changes detected between the two snapshots")
        return pd.DataFrame(empty_schema)

    changes_df = pd.DataFrame(change_records)
    logger.info("Detected %d price changes", len(changes_df))
    return changes_df


def load_previous_snapshot(
    current_timestamp: str,
    data_dir: str | None = None,
) -> pd.DataFrame | None:
    """Find and load the most recent snapshot before *current_timestamp*.

    Checks for Parquet files first; falls back to CSV in PROCESSED_DIR.
    """
    data_dir = data_dir or PARQUET_DIR

    # Try parquet first
    parquet_files = sorted(glob.glob(os.path.join(data_dir, "fuel_prices_*.parquet")))
    prior_files: list[tuple[str, str]] = []
    for fp in parquet_files:
        ts = os.path.basename(fp).replace("fuel_prices_", "").replace(".parquet", "")
        if ts < current_timestamp:
            prior_files.append((ts, fp))

    if prior_files:
        prior_files.sort(key=lambda x: x[0])
        _, latest_path = prior_files[-1]
        try:
            return pd.read_parquet(latest_path)
        except Exception:
            pass

    # Fallback to CSV in PROCESSED_DIR
    from src.utils.config import PROCESSED_DIR
    csv_files = sorted(glob.glob(os.path.join(PROCESSED_DIR, "fuel_prices_*.csv")))
    prior_csv: list[tuple[str, str]] = []
    for fp in csv_files:
        ts = os.path.basename(fp).replace("fuel_prices_", "").replace(".csv", "")
        if ts < current_timestamp:
            prior_csv.append((ts, fp))

    if prior_csv:
        prior_csv.sort(key=lambda x: x[0])
        _, latest_csv = prior_csv[-1]
        return pd.read_csv(latest_csv)

    return None


def find_price_changes(file_path: str) -> dict[str, Any]:
    """Orchestrate change detection for a raw JSON file.

    Steps:
        1. Clean the current raw file.
        2. Load the most recent previous snapshot.
        3. Detect price changes.
    """
    from src.pipeline.clean import clean_raw_file

    clean_result = clean_raw_file(file_path)

    # Read current DataFrame from parquet if available, otherwise CSV
    if clean_result["parquet_path"] and os.path.exists(clean_result["parquet_path"]):
        try:
            current_df = pd.read_parquet(clean_result["parquet_path"])
        except Exception:
            current_df = pd.read_csv(clean_result["csv_path"])
    else:
        current_df = pd.read_csv(clean_result["csv_path"])

    previous_df = load_previous_snapshot(clean_result["timestamp"])

    changes = detect_price_changes(current_df, previous_df)

    result = {
        "changes_count": len(changes),
        "changes": changes,
    }
    logger.info("Price change detection complete: %d changes", result["changes_count"])
    return result
