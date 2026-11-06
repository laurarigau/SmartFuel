"""Tests for the price alerts module using unittest."""

import os
import tempfile
import unittest
import pandas as pd

os.environ["SMARTFUEL_ENV"] = "local"

from src.alerts.alerts import check_alerts, format_alert_email, load_subscriptions_local


class TestAlerts(unittest.TestCase):
    def setUp(self):
        self.price_changes = pd.DataFrame([
            {
                "station_id": "1001",
                "station_name": "Repsol Madrid",
                "municipality": "Madrid",
                "province": "MADRID",
                "fuel_type": "gasoline_95",
                "old_price": 1.699,
                "new_price": 1.599,
                "price_change": -0.100,
                "pct_change": -5.89,
                "snapshot_date": "2026-11-04",
            },
        ])
        self.subscriptions = [
            {
                "user_id": "user1",
                "email": "user1@test.com",
                "station_id": "1001",
                "fuel_type": "gasoline_95",
                "target_price": 1.650,
            },
        ]

    def test_triggers_below_target(self):
        alerts = check_alerts(self.price_changes, self.subscriptions)
        self.assertGreaterEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["station_id"], "1001")

    def test_format_alert_email(self):
        alert = {
            "user_id": "user1",
            "email": "user1@test.com",
            "station_id": "1001",
            "station_name": "Repsol Madrid",
            "fuel_type": "gasoline_95",
            "old_price": 1.699,
            "new_price": 1.599,
            "target_price": 1.650,
            "reason": "below_target",
        }
        email = format_alert_email(alert)
        self.assertIn("subject", email)
        self.assertIn("body_text", email)
        self.assertIn("body_html", email)

    def test_load_subscriptions_local(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = os.path.join(temp_dir, "subs.json")
            subs = load_subscriptions_local(file_path=path)
            self.assertIsInstance(subs, list)
            self.assertTrue(os.path.exists(path))


if __name__ == "__main__":
    unittest.main()
