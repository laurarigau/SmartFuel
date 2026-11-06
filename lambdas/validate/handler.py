"""
Lambda handler for raw data validation.

First step of the Step Functions processing workflow.
Validates the raw JSON schema and station count.
Moves invalid files to quarantine and triggers SNS admin notification.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.pipeline.validate import validate_raw_file, validate_and_quarantine
from src.utils import config
from src.utils.logger import get_logger

logger = get_logger("lambda.validate")


def handler(event, context):
    """
    AWS Lambda entry point for validation.

    Args:
        event: Dict with S3 bucket and key, or local file path.
        context: AWS Lambda context.

    Returns:
        dict: Validation results used by Step Functions Choice state.
    """
    logger.info(f"Validating file: {event}")

    s3_bucket = event.get("s3_bucket", config.S3_BUCKET)
    s3_key = event.get("s3_key", "")
    local_path = event.get("file_path", "")

    if config.ENVIRONMENT == "aws" and s3_key:
        import boto3
        import tempfile

        s3 = boto3.client("s3")
        sns = boto3.client("sns")

        # Download S3 object to temp file
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            s3.download_fileobj(s3_bucket, s3_key, tmp)
            tmp_path = tmp.name

        try:
            result = validate_raw_file(tmp_path)

            if not result["valid"]:
                # Move to quarantine prefix
                quarantine_key = s3_key.replace("raw/", "quarantine/")
                s3.copy_object(
                    Bucket=s3_bucket,
                    CopySource={"Bucket": s3_bucket, "Key": s3_key},
                    Key=quarantine_key,
                )
                s3.delete_object(Bucket=s3_bucket, Key=s3_key)
                result["quarantined_path"] = f"s3://{s3_bucket}/{quarantine_key}"

                # Send SNS alert
                sns.publish(
                    TopicArn=config.SNS_ALERTS_TOPIC,
                    Subject="SmartFuel: Raw Data Validation Failed",
                    Message=json.dumps(result, indent=2),
                )
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    else:
        # Local mode
        target = local_path or s3_key
        result = validate_and_quarantine(target)

    # Pass through S3 details for downstream Step Functions states
    result["s3_bucket"] = s3_bucket
    result["s3_key"] = s3_key
    return result
