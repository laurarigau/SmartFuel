"""
Lambda handler for price alerts.

Triggered by DynamoDB Streams whenever a new price record is written.
Checks user subscriptions, compares against targets, and sends SES emails.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pandas as pd

from src.alerts.alerts import check_alerts, format_alert_email, load_subscriptions_local
from src.utils import config
from src.utils.logger import get_logger

logger = get_logger("lambda.alerts")


def handler(event, context):
    """
    AWS Lambda entry point for DynamoDB Streams alert processing.

    Args:
        event: DynamoDB Streams event with NewImage records.
        context: AWS Lambda context.

    Returns:
        dict: Count of alerts evaluated and emails sent.
    """
    logger.info(f"Processing DynamoDB stream records: {len(event.get('Records', []))}")

    records = event.get("Records", [])
    if not records:
        return {"statusCode": 200, "alerts_sent": 0}

    # Extract price changes from the stream records
    changes = []
    for record in records:
        if record.get("eventName") in ("INSERT", "MODIFY"):
            new_image = record.get("dynamodb", {}).get("NewImage", {})
            try:
                station_id = new_image.get("station_id", {}).get("S", "")
                fuel_type = new_image.get("fuel_type", {}).get("S", "")
                new_price = float(new_image.get("price", {}).get("S", 0))
                old_price = float(new_image.get("old_price", {}).get("S", new_price))
                price_change = float(new_image.get("price_change", {}).get("S", 0))
                pct_change = float(new_image.get("pct_change", {}).get("S", 0))

                changes.append({
                    "station_id": station_id,
                    "station_name": new_image.get("station_name", {}).get("S", f"Station {station_id}"),
                    "fuel_type": fuel_type,
                    "old_price": old_price,
                    "new_price": new_price,
                    "price_change": price_change,
                    "pct_change": pct_change,
                })
            except (ValueError, TypeError) as e:
                logger.warning(f"Error parsing DynamoDB stream record: {e}")

    if not changes:
        return {"statusCode": 200, "alerts_sent": 0}

    changes_df = pd.DataFrame(changes)

    # Load subscriptions
    if config.ENVIRONMENT == "aws":
        import boto3
        from boto3.dynamodb.conditions import Key

        dynamodb = boto3.resource("dynamodb")
        sub_table = dynamodb.Table(config.DYNAMODB_SUBSCRIPTIONS_TABLE)
        ses = boto3.client("ses", region_name=config.AWS_REGION)

        # Query subscriptions for each station that changed
        station_ids = changes_df["station_id"].unique()
        subscriptions = []
        for sid in station_ids:
            resp = sub_table.query(
                IndexName="station-index",
                KeyConditionExpression=Key("station_id").eq(sid),
            )
            for item in resp.get("Items", []):
                subscriptions.append({
                    "user_id": item["user_id"],
                    "email": item["email"],
                    "station_id": item["station_id"],
                    "fuel_type": item.get("fuel_type", "gasoline_95"),
                    "target_price": float(item.get("target_price", 0)),
                })
    else:
        subscriptions = load_subscriptions_local()
        ses = None

    alerts = check_alerts(changes_df, subscriptions)
    sent_count = 0

    for alert in alerts:
        email_content = format_alert_email(alert)
        if config.ENVIRONMENT == "aws" and ses:
            try:
                ses.send_email(
                    Source=os.environ.get("ALERT_SENDER_EMAIL", "alerts@smartfuel.es"),
                    Destination={"ToAddresses": [alert["email"]]},
                    Message={
                        "Subject": {"Data": email_content["subject"], "Charset": "UTF-8"},
                        "Body": {
                            "Text": {"Data": email_content["body_text"], "Charset": "UTF-8"},
                            "Html": {"Data": email_content["body_html"], "Charset": "UTF-8"},
                        },
                    },
                )
                sent_count += 1
            except Exception as e:
                logger.error(f"Failed to send email via SES to {alert['email']}: {e}")
        else:
            logger.info(f"[LOCAL EMAIL] To: {alert['email']} | Subject: {email_content['subject']}")
            sent_count += 1

    return {"statusCode": 200, "alerts_sent": sent_count}
