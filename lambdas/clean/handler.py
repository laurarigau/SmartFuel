"""
Lambda handler for data cleaning and change detection.

Second step of the Step Functions processing workflow.
Converts valid raw JSON to Parquet and detects price changes since the last snapshot.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.pipeline.clean import clean_raw_file
from src.pipeline.changes import find_price_changes
from src.utils import config
from src.utils.logger import get_logger

logger = get_logger("lambda.clean")


def handler(event, context):
    """
    AWS Lambda entry point for data cleaning.

    Args:
        event: Dict with S3 bucket and key from the validate step.
        context: AWS Lambda context.

    Returns:
        dict: Cleaned Parquet S3 key, changes count, and change details.
    """
    logger.info(f"Cleaning data: {event}")

    s3_bucket = event.get("s3_bucket", config.S3_BUCKET)
    s3_key = event.get("s3_key", "")
    local_path = event.get("file_path", "")

    if config.ENVIRONMENT == "aws" and s3_key:
        import boto3
        import tempfile

        s3 = boto3.client("s3")

        # Download raw file
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            s3.download_fileobj(s3_bucket, s3_key, tmp)
            tmp_path = tmp.name

        try:
            with tempfile.TemporaryDirectory() as out_dir:
                clean_result = clean_raw_file(tmp_path, parquet_dir=out_dir, csv_dir=out_dir)

                # Upload Parquet to S3
                parquet_key = f"clean/parquet/{os.path.basename(clean_result['parquet_path'])}"
                s3.upload_file(clean_result["parquet_path"], s3_bucket, parquet_key)

                # Find price changes
                changes_result = find_price_changes(tmp_path)

                # Upload changes CSV to S3
                changes_key = f"clean/changes/changes_{clean_result['timestamp']}.csv"
                if not changes_result["changes"].empty:
                    changes_tmp = os.path.join(out_dir, "changes.csv")
                    changes_result["changes"].to_csv(changes_tmp, index=False)
                    s3.upload_file(changes_tmp, s3_bucket, changes_key)

                return {
                    "statusCode": 200,
                    "s3_bucket": s3_bucket,
                    "parquet_s3_key": parquet_key,
                    "changes_s3_key": changes_key,
                    "row_count": clean_result["row_count"],
                    "changes_count": changes_result["changes_count"],
                    "timestamp": clean_result["timestamp"],
                }
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    else:
        # Local mode
        target = local_path or s3_key
        clean_result = clean_raw_file(target)
        changes_result = find_price_changes(target)

        return {
            "statusCode": 200,
            "parquet_path": clean_result["parquet_path"],
            "csv_path": clean_result["csv_path"],
            "row_count": clean_result["row_count"],
            "changes_count": changes_result["changes_count"],
            "timestamp": clean_result["timestamp"],
        }
