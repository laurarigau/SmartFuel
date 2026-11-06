"""
Lambda handler for running ML price trend predictions.

Runs in parallel with the save_prices step in the Step Functions workflow.
Loads the trained model from S3/disk and saves predictions to DynamoDB.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.ml.predict import run_predictions
from src.utils import config
from src.utils.logger import get_logger

logger = get_logger("lambda.predict")


def handler(event, context):
    """
    AWS Lambda entry point for predictions.

    Args:
        event: Dict with parquet_s3_key and timestamp from the clean step.
        context: AWS Lambda context.

    Returns:
        dict: Summary of predictions generated.
    """
    logger.info(f"Running predictions: {event}")

    timestamp = event.get("timestamp", "")

    try:
        predictions = run_predictions()

        if not predictions:
            logger.info("No predictions generated (insufficient history or missing model).")
            return {
                "statusCode": 200,
                "predictions_count": 0,
                "message": "Model not available or insufficient data",
            }

        up_count = sum(1 for p in predictions if p.get("prediction") == "UP")
        down_or_stable = len(predictions) - up_count

        if config.ENVIRONMENT == "aws":
            import boto3

            dynamodb = boto3.resource("dynamodb")
            pred_table = dynamodb.Table(config.DYNAMODB_PREDICTIONS_TABLE)

            with pred_table.batch_writer() as batch:
                for pred in predictions:
                    item = {
                        "station_id": str(pred["station_id"]),
                        "prediction_date": timestamp,
                        "prediction": pred["prediction"],
                        "probability": str(pred.get("probability", 0.5)),
                        "features_date": pred.get("features_date", timestamp),
                    }
                    batch.put_item(Item=item)

            logger.info(f"Wrote {len(predictions)} predictions to DynamoDB")

        return {
            "statusCode": 200,
            "predictions_count": len(predictions),
            "up_count": up_count,
            "down_or_stable_count": down_or_stable,
        }

    except Exception as e:
        logger.error(f"Prediction failed: {e}", exc_info=True)
        return {
            "statusCode": 500,
            "error": str(e),
        }
