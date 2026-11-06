"""
Price alert logic for SmartFuel.

Evaluates price changes against user subscriptions and generates alert
notifications when a target price is reached or a significant drop occurs.
"""

import json
import os
from typing import Any

import pandas as pd

from src.utils.config import DATA_DIR
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Percentage-drop threshold that automatically triggers an alert
_LARGE_DROP_PCT: float = 5.0

# Default subscriptions file path
_DEFAULT_SUBSCRIPTIONS_PATH: str = os.path.join(DATA_DIR, "subscriptions.json")

# Sample subscriptions used when the file doesn't exist yet
_SAMPLE_SUBSCRIPTIONS: list[dict[str, Any]] = [
    {
        "user_id": "user-001",
        "email": "alice@example.com",
        "station_id": "1234",
        "fuel_type": "Gasoline 95 E5",
        "target_price": 1.45,
    },
    {
        "user_id": "user-002",
        "email": "bob@example.com",
        "station_id": "5678",
        "fuel_type": "Diesel A",
        "target_price": 1.35,
    },
]


def check_alerts(
    price_changes: pd.DataFrame,
    subscriptions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Check price changes against user subscriptions and return alerts.

    An alert is triggered when:
        * The new price drops **below** (or equals) the user's
          ``target_price`` for the subscribed station / fuel combination, OR
        * The price dropped by more than 5 % in a single snapshot (for any
          matching subscription).

    Args:
        price_changes: DataFrame produced by
            :func:`src.pipeline.changes.detect_price_changes`.
        subscriptions: List of subscription dicts, each containing
            ``user_id``, ``email``, ``station_id``, ``fuel_type``, and
            ``target_price``.

    Returns:
        List of alert dicts ready for delivery.
    """
    if price_changes.empty or not subscriptions:
        logger.info(
            "No alerts to check (changes=%d, subscriptions=%d)",
            len(price_changes),
            len(subscriptions),
        )
        return []

    alerts: list[dict[str, Any]] = []

    for sub in subscriptions:
        sub_station = str(sub["station_id"])
        sub_fuel = sub["fuel_type"]
        target = float(sub["target_price"])

        # Filter price_changes to this subscription's station + fuel
        mask = (price_changes["station_id"].astype(str) == sub_station) & (
            price_changes["fuel_type"] == sub_fuel
        )
        matching = price_changes[mask]

        for _, row in matching.iterrows():
            new_price = float(row["new_price"])
            old_price = float(row["old_price"])
            pct_change = float(row["pct_change"])

            reasons: list[str] = []

            # Rule 1: price dropped below (or to) target
            if new_price <= target:
                reasons.append("below_target")

            # Rule 2: large drop (> 5 %)
            if pct_change <= -_LARGE_DROP_PCT:
                reasons.append("large_drop")

            for reason in reasons:
                alert: dict[str, Any] = {
                    "user_id": sub["user_id"],
                    "email": sub["email"],
                    "station_id": sub_station,
                    "station_name": row.get("station_name", ""),
                    "fuel_type": sub_fuel,
                    "old_price": old_price,
                    "new_price": new_price,
                    "target_price": target,
                    "reason": reason,
                }
                alerts.append(alert)
                logger.info(
                    "Alert triggered [%s] for user %s at station %s: %.3f → %.3f",
                    reason,
                    sub["user_id"],
                    sub_station,
                    old_price,
                    new_price,
                )

    logger.info("Total alerts generated: %d", len(alerts))
    return alerts


def format_alert_email(alert: dict[str, Any]) -> dict[str, str]:
    """Format an alert dict into email-ready subject, text body, and HTML body.

    Args:
        alert: Single alert dictionary produced by :func:`check_alerts`.

    Returns:
        Dictionary with keys ``subject``, ``body_text``, and ``body_html``.
    """
    station_name = alert.get("station_name", alert["station_id"])
    fuel_type = alert["fuel_type"]
    old_price = alert["old_price"]
    new_price = alert["new_price"]
    target_price = alert["target_price"]
    reason = alert["reason"]

    if reason == "below_target":
        reason_text = (
            f"The price has dropped to €{new_price:.3f}, which is at or below "
            f"your target of €{target_price:.3f}."
        )
        emoji = "🎯"
    else:
        drop_pct = abs(((new_price - old_price) / old_price) * 100) if old_price else 0
        reason_text = (
            f"The price dropped by {drop_pct:.1f}% in one update "
            f"(€{old_price:.3f} → €{new_price:.3f})."
        )
        emoji = "📉"

    subject = f"{emoji} SmartFuel Alert: {fuel_type} price change at {station_name}"

    body_text = (
        f"SmartFuel Price Alert\n"
        f"{'=' * 40}\n\n"
        f"Station: {station_name}\n"
        f"Fuel type: {fuel_type}\n"
        f"Previous price: €{old_price:.3f}\n"
        f"New price: €{new_price:.3f}\n"
        f"Your target: €{target_price:.3f}\n\n"
        f"{reason_text}\n\n"
        f"—\n"
        f"SmartFuel · Fuel price alerts for Spain\n"
    )

    body_html = (
        f"<html><body>"
        f"<h2>{emoji} SmartFuel Price Alert</h2>"
        f"<table style='border-collapse:collapse;'>"
        f"<tr><td style='padding:4px 12px;font-weight:bold;'>Station</td>"
        f"<td style='padding:4px 12px;'>{station_name}</td></tr>"
        f"<tr><td style='padding:4px 12px;font-weight:bold;'>Fuel type</td>"
        f"<td style='padding:4px 12px;'>{fuel_type}</td></tr>"
        f"<tr><td style='padding:4px 12px;font-weight:bold;'>Previous price</td>"
        f"<td style='padding:4px 12px;'>€{old_price:.3f}</td></tr>"
        f"<tr><td style='padding:4px 12px;font-weight:bold;'>New price</td>"
        f"<td style='padding:4px 12px;'><strong>€{new_price:.3f}</strong></td></tr>"
        f"<tr><td style='padding:4px 12px;font-weight:bold;'>Your target</td>"
        f"<td style='padding:4px 12px;'>€{target_price:.3f}</td></tr>"
        f"</table>"
        f"<p>{reason_text}</p>"
        f"<hr><p style='color:#888;font-size:12px;'>"
        f"SmartFuel · Fuel price alerts for Spain</p>"
        f"</body></html>"
    )

    return {
        "subject": subject,
        "body_text": body_text,
        "body_html": body_html,
    }


def load_subscriptions_local(
    file_path: str | None = None,
) -> list[dict[str, Any]]:
    """Load subscriptions from a local JSON file.

    If the file does not exist, a sample file is created with example
    subscriptions.

    Args:
        file_path: Path to the JSON file. Defaults to
            ``data/subscriptions.json``.

    Returns:
        List of subscription dictionaries.
    """
    file_path = file_path or _DEFAULT_SUBSCRIPTIONS_PATH

    if not os.path.isfile(file_path):
        logger.info("Subscriptions file not found — creating sample at %s", file_path)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as fh:
            json.dump(_SAMPLE_SUBSCRIPTIONS, fh, indent=2, ensure_ascii=False)
        return list(_SAMPLE_SUBSCRIPTIONS)

    with open(file_path, "r", encoding="utf-8") as fh:
        subscriptions: list[dict[str, Any]] = json.load(fh)

    logger.info("Loaded %d subscriptions from %s", len(subscriptions), file_path)
    return subscriptions
