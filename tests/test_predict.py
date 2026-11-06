"""Tests for the ML feature engineering module using unittest."""

import os
import unittest
import numpy as np
import pandas as pd

os.environ["SMARTFUEL_ENV"] = "local"

from src.ml.features import build_station_features, build_training_data


class TestPredictFeatures(unittest.TestCase):
    def setUp(self):
        rows = []
        np.random.seed(42)
        base_date = pd.Timestamp("2026-10-01")

        for station_id in ["1001", "1002", "1003"]:
            base_price = 1.6 + np.random.random() * 0.3
            for day in range(30):
                price = base_price + np.random.normal(0, 0.02)
                rows.append({
                    "station_id": station_id,
                    "station_name": f"Station {station_id}",
                    "latitude": 40.0,
                    "longitude": -3.7,
                    "gasoline_95_price": round(price, 3),
                    "diesel_price": round(price + 0.1, 3),
                    "snapshot_date": base_date + pd.Timedelta(days=day),
                })

        self.price_history = pd.DataFrame(rows)

    def test_build_station_features(self):
        station_df = self.price_history[self.price_history["station_id"] == "1001"].copy()
        features = build_station_features(station_df, "1001")
        self.assertIn("price_lag_1d", features.columns)
        self.assertIn("day_of_week", features.columns)

    def test_build_training_data(self):
        X, y = build_training_data(self.price_history)
        self.assertGreater(len(X.columns), 3)
        self.assertEqual(len(X), len(y))


if __name__ == "__main__":
    unittest.main()
