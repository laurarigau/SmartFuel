"""
Lambda handler for model retraining.

Invoked by the weekly Step Functions retraining workflow.
Supports two actions:
  - "train": reads Athena training data, fits new model, compares against baseline
  - "promote": copies candidate model to production S3 key
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.ml.train import train_and_save
from src.utils import config
from src.utils.logger import get_logger

logger = get_logger("lambda.retrain")


def handler(event, context):
    """
    AWS Lambda entry point for retraining.

    Args:
        event: Dict with action ("train" or "promote") and parameters.
        context: AWS Lambda context.

    Returns:
        dict: Training metrics and model status.
    """
    action = event.get("action", "train")
    logger.info(f"Retrain Lambda invoked with action: {action}")

    if action == "promote":
        candidate_key = event.get("candidate_model_s3_key", "")
        if config.ENVIRONMENT == "aws" and candidate_key:
            import boto3

            s3 = boto3.client("s3")
            prod_key = f"models/{config.MODEL_FILENAME}"
            s3.copy_object(
                Bucket=config.S3_BUCKET,
                CopySource={"Bucket": config.S3_BUCKET, "Key": candidate_key},
                Key=prod_key,
            )
            logger.info(f"Promoted {candidate_key} to {prod_key}")
        return {"statusCode": 200, "status": "promoted"}

    # Default action: train
    try:
        metrics = train_and_save()

        if not metrics:
            return {
                "statusCode": 200,
                "model_is_better": False,
                "reason": "Insufficient data to train",
                "metrics": {},
            }

        candidate_key = f"models/candidate_{config.MODEL_FILENAME}"
        if config.ENVIRONMENT == "aws":
            import boto3

            s3 = boto3.client("s3")
            local_model = os.path.join(config.MODELS_DIR, config.MODEL_FILENAME)
            if os.path.exists(local_model):
                s3.upload_file(local_model, config.S3_BUCKET, candidate_key)

        return {
            "statusCode": 200,
            "model_is_better": metrics.get("model_is_better", False),
            "candidate_model_s3_key": candidate_key,
            "metrics": metrics,
        }

    except Exception as e:
        logger.error(f"Retraining failed: {e}", exc_info=True)
        return {
            "statusCode": 500,
            "model_is_better": False,
            "error": str(e),
        }
