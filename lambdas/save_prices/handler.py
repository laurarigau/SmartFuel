"""
Lambda handler for saving changed prices to DynamoDB.

Runs in parallel with the predict step in the Step Functions workflow.
Only writes prices that have actually changed, keeping DynamoDB write costs minimal.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.utils import config
from src.utils.logger import get_logger

logger = get_logger("lambda.save_prices")


def handler(event, context):
    """
    AWS Lambda entry point for saving changed prices to DynamoDB.

    Args:
        event: Dict with changes_s3_key and timestamp from the clean step.
        context: AWS Lambda context.

    Returns:
        dict: Count of records written to DynamoDB.
    """
    logger.info(f"Saving changed prices to DynamoDB: {event}")

    changes_s3_key = event.get("changes_s3_key", "")
    timestamp = event.get("timestamp", "")

    if config.ENVIRONMENT == "aws" and changes_s3_key:
        import boto3
        import pandas as pd
        import tempfile

        s3 = boto3.client("s3")
        dynamodb = boto3.resource("dynamodb")
        prices_table = dynamodb.Table(config.DYNAMODB_PRICES_TABLE)
        stations_table = dynamodb.Table(config.DYNAMODB_STATIONS_TABLE)

        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
            try:
                s3.download_fileobj(config.S3_BUCKET, changes_s3_key, tmp)
                tmp.close()
                df = pd.read_csv(tmp.name)
            except Exception as e:
                logger.info(f"No changes file found or empty ({e}), 0 records to write.")
                return {"statusCode": 200, "records_written": 0}
            finally:
                if os.path.exists(tmp.name):
                    os.remove(tmp.name)

        written = 0
        with prices_table.batch_writer() as batch:
            for _, row in df.iterrows():
                item = {
                    "station_id": str(row["station_id"]),
                    "snapshot_date": timestamp,
                    "fuel_type": str(row["fuel_type"]),
                    "price": str(row["new_price"]),
                    "old_price": str(row["old_price"]),
                    "price_change": str(row["price_change"]),
                    "pct_change": str(row["pct_change"]),
                }
                batch.put_item(Item=item)
                written += 1

        logger.info(f"Successfully wrote {written} changed price records to DynamoDB")
        return {"statusCode": 200, "records_written": written}

    else:
        # Local mode: log and return
        logger.info(f"Local mode: simulated DynamoDB batch write for timestamp {timestamp}")
        return {"statusCode": 200, "records_written": 0, "mode": "local"}
