"""
API request handlers for SmartFuel.

Can be called directly from Lambda or run locally with a lightweight HTTP server.
"""

import json
from typing import Any, Dict, List, Optional
import pandas as pd
import glob
import os

from src.utils import config
from src.utils.logger import get_logger

logger = get_logger(__name__)


def list_stations(
    limit: int = 100,
    geohash: Optional[str] = None,
    province: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """List stations with optional filtering."""
    csv_files = glob.glob(os.path.join(config.PROCESSED_DIR, "fuel_prices_*.csv"))
    if not csv_files:
        return []

    df = pd.read_csv(max(csv_files))

    if geohash:
        df = df[df["geohash"].str.startswith(geohash, na=False)]
    if province:
        df = df[df["province"].str.upper() == province.upper()]

    return df.head(limit).to_dict(orient="records")


def get_station(station_id: str) -> Optional[Dict[str, Any]]:
    """Fetch details for a single fuel station by ID."""
    csv_files = glob.glob(os.path.join(config.PROCESSED_DIR, "fuel_prices_*.csv"))
    if not csv_files:
        return None

    df = pd.read_csv(max(csv_files))
    match = df[df["station_id"].astype(str) == str(station_id)]
    if match.empty:
        return None

    return match.iloc[0].to_dict()
