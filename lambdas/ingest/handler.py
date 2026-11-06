"""
Lambda handler for data ingestion.

Triggered 4 times a day by EventBridge schedule.
Calls the Spanish Ministry API and writes the raw JSON snapshot to S3.
"""

import json
import os
import sys

# Ensure src is on Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.pipeline.ingest import fetch_fuel_data, save_raw_json
from src.utils import config
from src.utils.logger import get_logger

logger = get_logger("lambda.ingest")


def handler(event, context):
    """
    AWS Lambda entry point for ingestion.

    Args:
        event: EventBridge scheduled event payload.
        context: AWS Lambda context.

    Returns:
        dict: Status and details about the ingested snapshot.
    """
    logger.info("Starting fuel data ingestion...")

    try:
        data = fetch_fuel_data()
        station_count = len(data.get("ListaEESSPrecio", []))
        snapshot_date = data.get("Fecha", "unknown")

        if config.ENVIRONMENT == "aws":
            import boto3
            from datetime import datetime

            s3 = boto3.client("s3")

            # Parse date to build S3 key
            try:
                dt = datetime.strptime(snapshot_date, "%d/%m/%Y %H:%M:%S")
                timestamp = dt.strftime("%Y-%m-%d_%H%M")
            except (ValueError, TypeError):
                timestamp = datetime.utcnow().strftime("%Y-%m-%d_%H%M")

            s3_key = f"raw/fuel_prices_{timestamp}.json"
            s3.put_object(
                Bucket=config.S3_BUCKET,
                Key=s3_key,
                Body=json.dumps(data, ensure_ascii=False).encode("utf-8"),
                ContentType="application/json",
            )
            logger.info(f"Saved raw snapshot to s3://{config.S3_BUCKET}/{s3_key}")
            file_ref = f"s3://{config.S3_BUCKET}/{s3_key}"
        else:
            # Local mode: save to disk
            file_ref = save_raw_json(data)
            logger.info(f"Saved raw snapshot locally: {file_ref}")

        return {
            "statusCode": 200,
            "body": {
                "message": "Data ingested successfully",
                "file": file_ref,
                "station_count": station_count,
                "snapshot_date": snapshot_date,
            },
        }

    except Exception as e:
        logger.error(f"Ingestion failed: {e}", exc_info=True)
        return {
            "statusCode": 500,
            "body": {"error": str(e)},
        }
