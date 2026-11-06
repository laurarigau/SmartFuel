"""
Feature engineering module for SmartFuel ML.

Builds time-series features from historical price snapshots to feed the
price-trend classification model.
"""

import glob
import os
from typing import Any

import numpy as np
import pandas as pd

from src.utils.config import (
    MIN_HISTORY_DAYS,
    PARQUET_DIR,
    PREDICTION_HORIZON_DAYS,
)
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Primary price column used for feature engineering (Gasoline 95)
_PRICE_COL: str = "gasoline_95_price"

# Lag periods (days)
_LAG_DAYS: list[int] = [1, 2, 3, 4, 5, 6, 7]

# Rolling window sizes (days)
_ROLLING_WINDOWS: list[int] = [3, 7]


def load_price_history(data_dir: str | None = None) -> pd.DataFrame:
    """Load all parquet snapshots and return a combined, sorted DataFrame.

    Args:
        data_dir: Directory containing parquet files.  Defaults to
            ``config.PARQUET_DIR``.

    Returns:
        A single DataFrame with all stations × snapshots, sorted by
        ``(station_id, snapshot_date)``.

    Raises:
        FileNotFoundError: If the data directory does not exist or contains
            no parquet files.
    """
    data_dir = data_dir or PARQUET_DIR

    files = sorted(glob.glob(os.path.join(data_dir, "fuel_prices_*.parquet"))) if os.path.isdir(data_dir) else []
    frames: list[pd.DataFrame] = []
    for fp in files:
        try:
            frames.append(pd.read_parquet(fp))
        except Exception:
            pass

    if not frames:
        from src.utils.config import PROCESSED_DIR
        csv_files = sorted(glob.glob(os.path.join(PROCESSED_DIR, "fuel_prices_*.csv")))
        for fp in csv_files:
            try:
                frames.append(pd.read_csv(fp))
            except Exception:
                pass

    if not frames:
        raise FileNotFoundError("No processed data files (parquet or CSV) found")

    logger.info("Loaded %d data file(s)", len(frames))
    combined = pd.concat(frames, ignore_index=True)

    # Ensure correct types
    combined["station_id"] = combined["station_id"].astype(str)
    if "snapshot_date" in combined.columns:
        combined["snapshot_date"] = pd.to_datetime(
            combined["snapshot_date"], errors="coerce"
        )

    combined.sort_values(["station_id", "snapshot_date"], inplace=True)
    combined.reset_index(drop=True, inplace=True)

    logger.info(
        "Loaded price history: %d rows, %d unique stations",
        len(combined),
        combined["station_id"].nunique(),
    )
    return combined


def build_station_features(
    history_df: pd.DataFrame,
    station_id: str | None = None,
) -> pd.DataFrame:
    """Compute daily time-series features for a single station.

    Features produced:
        - ``price_lag_1d`` … ``price_lag_7d`` — lagged prices.
        - ``price_rolling_mean_3d``, ``price_rolling_mean_7d`` — rolling
          averages.
        - ``price_rolling_std_3d``, ``price_rolling_std_7d`` — rolling
          standard deviations.
        - ``day_of_week`` (0 = Monday … 6 = Sunday).
        - ``is_weekend`` (Saturday or Sunday).
        - ``price_momentum`` — price change over the last 3 days.

    Args:
        history_df: Price history DataFrame for the station or all stations.
        station_id: Optional station to build features for.

    Returns:
        DataFrame with one row per day for the requested station, including
        all engineered feature columns.
    """
    if station_id is not None and "station_id" in history_df.columns:
        station_df = history_df[history_df["station_id"] == station_id].copy()
    else:
        station_df = history_df.copy()

    if station_df.empty or _PRICE_COL not in station_df.columns:
        return pd.DataFrame()

    if "snapshot_date" in station_df.columns:
        if not pd.api.types.is_datetime64_any_dtype(station_df["snapshot_date"]):
            station_df["snapshot_date"] = pd.to_datetime(station_df["snapshot_date"], errors="coerce")
        station_df = station_df.sort_values("snapshot_date")

    # Keep only rows with a valid price
    station_df = station_df.dropna(subset=[_PRICE_COL])

    # Deduplicate to a single record per day (take the last snapshot of each day)
    if "snapshot_date" in station_df.columns:
        station_df["date"] = station_df["snapshot_date"].dt.date
    else:
        station_df["date"] = pd.date_range("2026-01-01", periods=len(station_df)).date

    station_df = station_df.drop_duplicates(subset=["date"], keep="last")
    station_df = station_df.sort_values("date").reset_index(drop=True)

    price = station_df[_PRICE_COL]

    # Lags
    for lag in _LAG_DAYS:
        station_df[f"price_lag_{lag}d"] = price.shift(lag)

    # Rolling statistics
    for window in _ROLLING_WINDOWS:
        station_df[f"price_rolling_mean_{window}d"] = (
            price.rolling(window=window, min_periods=window).mean()
        )
        station_df[f"price_rolling_std_{window}d"] = (
            price.rolling(window=window, min_periods=window).std()
        )

    # Calendar features
    snapshot_dates = pd.to_datetime(station_df["date"])
    station_df["day_of_week"] = snapshot_dates.dt.dayofweek
    station_df["is_weekend"] = station_df["day_of_week"].isin([5, 6])

    # Momentum: price change over the last 3 days
    station_df["price_momentum"] = price - price.shift(3)

    return station_df


def build_training_data(
    history_df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.Series]:
    """Build feature matrix (X) and binary target vector (y).

    For each station with at least ``config.MIN_HISTORY_DAYS`` days of data,
    compute features.  The target variable is *1* when the price goes **UP**
    within the next ``config.PREDICTION_HORIZON_DAYS`` days, *0* otherwise.

    Args:
        history_df: Full price history DataFrame (all stations).

    Returns:
        Tuple of ``(X, y)`` where *X* is a feature DataFrame and *y* is a
        binary Series aligned to *X*'s index.
    """
    logger.info("Building training data for stations")
    feature_frames: list[pd.DataFrame] = []

    if "station_id" in history_df.columns:
        grouped = history_df.groupby("station_id")
    else:
        grouped = [(None, history_df)]

    for sid, station_group in grouped:
        station_features = build_station_features(station_group)

        if station_features.empty:
            continue

        if len(station_features) < MIN_HISTORY_DAYS:
            continue

        # Build target: will price go UP in the next PREDICTION_HORIZON_DAYS?
        future_price = station_features[_PRICE_COL].shift(-PREDICTION_HORIZON_DAYS)
        station_features["target"] = (
            future_price > station_features[_PRICE_COL]
        ).astype(int)

        feature_frames.append(station_features)

    if not feature_frames:
        logger.warning("No stations have enough history for training")
        return pd.DataFrame(), pd.Series(dtype="int64")

    all_features = pd.concat(feature_frames, ignore_index=True)

    # Drop rows where target or features are NaN (edges of the time series)
    feature_cols = _get_feature_columns()
    all_features = all_features.dropna(subset=feature_cols + ["target"])

    X = all_features[feature_cols].copy()
    y = all_features["target"].astype(int).copy()

    logger.info("Training data ready: X=%s, y distribution: %s", X.shape, y.value_counts().to_dict())
    return X, y


def _get_feature_columns() -> list[str]:
    """Return the ordered list of feature column names used by the model."""
    cols: list[str] = []
    for lag in _LAG_DAYS:
        cols.append(f"price_lag_{lag}d")
    for window in _ROLLING_WINDOWS:
        cols.append(f"price_rolling_mean_{window}d")
        cols.append(f"price_rolling_std_{window}d")
    cols.extend(["day_of_week", "is_weekend", "price_momentum"])
    return cols
