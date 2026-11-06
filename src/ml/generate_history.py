"""
Generate synthetic historical snapshots for initial model bootstrapping.

As noted in the Project Draft:
'The first model will be trained on our laptops and uploaded to S3.'
Since historical daily data collection takes weeks to accumulate organically,
this script creates 14 days of realistic historical snapshots based on the
actual stations in `data/processed/`, allowing the initial model to be trained
and evaluated immediately.
"""

import glob
import os
import sys
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.utils import config
from src.utils.logger import get_logger

logger = get_logger(__name__)


def generate_history(days: int = 14, output_dir: str | None = None) -> list[str]:
    """
    Generate synthetic historical daily snapshots backwards from the latest file.

    Args:
        days: Number of days of historical snapshots to generate (default: 14).
        output_dir: Target directory (default: config.PROCESSED_DIR).

    Returns:
        list of generated CSV file paths.
    """
    output_dir = output_dir or config.PROCESSED_DIR
    os.makedirs(output_dir, exist_ok=True)

    csv_files = sorted(glob.glob(os.path.join(output_dir, "fuel_prices_*.csv")))
    if not csv_files:
        raise FileNotFoundError(f"No base processed CSV found in {output_dir}")

    base_path = csv_files[-1]
    logger.info(f"Using base station snapshot: {base_path}")
    base_df = pd.read_csv(base_path)

    # Use a fixed seed for reproducible simulation
    np.random.seed(42)
    n_stations = len(base_df)

    today = datetime.now()
    generated_paths = []

    for day_offset in range(days, 0, -1):
        snapshot_date = today - timedelta(days=day_offset)
        timestamp_str = snapshot_date.strftime("%Y-%m-%d_1200")
        output_filename = f"fuel_prices_{timestamp_str}.csv"
        file_path = os.path.join(output_dir, output_filename)

        df = base_df.copy()

        # Simulate small price drift per station (+/- 1-2 cents per day)
        # Fuel prices in Spain change slightly every few days
        random_gas_walk = np.random.normal(loc=0.0, scale=0.015, size=n_stations)
        random_diesel_walk = np.random.normal(loc=0.0, scale=0.015, size=n_stations)

        if "gasoline_95_price" in df.columns:
            df["gasoline_95_price"] = np.round(
                np.clip(df["gasoline_95_price"] + random_gas_walk, 1.20, 2.50), 3
            )
        if "diesel_price" in df.columns:
            df["diesel_price"] = np.round(
                np.clip(df["diesel_price"] + random_diesel_walk, 1.20, 2.50), 3
            )

        df["snapshot_date"] = snapshot_date.strftime("%Y-%m-%d %H:%M:%S")

        df.to_csv(file_path, index=False)
        generated_paths.append(file_path)
        logger.info(f"Generated historical snapshot: {output_filename} ({len(df)} stations)")

    return generated_paths


if __name__ == "__main__":
    generate_history(days=14)
