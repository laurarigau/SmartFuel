#!/usr/bin/env python3
"""
SmartFuel — Local Pipeline Orchestrator

Simulates the full AWS pipeline locally:
  1. Ingest raw data from the Ministry API
  2. Validate the downloaded file
  3. Clean and convert to Parquet
  4. Detect price changes
  5. Run predictions (if model exists)
  6. Check price alerts (if subscriptions exist)

Usage:
    python run_pipeline.py                  # Run full pipeline
    python run_pipeline.py --step ingest    # Run only ingestion
    python run_pipeline.py --step validate  # Validate latest raw file
    python run_pipeline.py --step clean     # Clean latest raw file
    python run_pipeline.py --step changes   # Detect price changes
    python run_pipeline.py --step predict   # Run predictions
    python run_pipeline.py --step train     # Train/retrain model
    python run_pipeline.py --skip-ingest    # Run pipeline using existing data
"""

import argparse
import json
import os
import sys
import traceback

# Ensure the project root is on the path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

os.environ.setdefault("SMARTFUEL_ENV", "local")

from src.utils.logger import get_logger
from src.utils import config

logger = get_logger("pipeline")


def step_ingest():
    """Step 1: Download raw data from the Ministry API."""
    from src.pipeline.ingest import ingest

    logger.info("=== STEP 1: INGEST ===")
    file_path = ingest()
    logger.info(f"Raw data saved to: {file_path}")
    return file_path


def step_validate(file_path: str = None):
    """Step 2: Validate the raw JSON file."""
    from src.pipeline.validate import validate_and_quarantine

    logger.info("=== STEP 2: VALIDATE ===")

    if file_path is None:
        file_path = _find_latest_raw_file()

    result = validate_and_quarantine(file_path)
    if result["valid"]:
        logger.info(
            f"Validation PASSED — {result['station_count']} stations, "
            f"snapshot: {result['snapshot_date']}"
        )
    else:
        logger.error(f"Validation FAILED — errors: {result['errors']}")
        if "quarantined_path" in result:
            logger.error(f"File quarantined to: {result['quarantined_path']}")

    return result


def step_clean(file_path: str = None):
    """Step 3: Clean raw data → Parquet + CSV."""
    from src.pipeline.clean import clean_raw_file

    logger.info("=== STEP 3: CLEAN ===")

    if file_path is None:
        file_path = _find_latest_raw_file()

    result = clean_raw_file(file_path)
    logger.info(
        f"Cleaned {result['row_count']} rows — "
        f"Parquet: {result['parquet_path']}, CSV: {result['csv_path']}"
    )
    return result


def step_changes(file_path: str = None):
    """Step 4: Detect price changes vs previous snapshot."""
    from src.pipeline.changes import find_price_changes

    logger.info("=== STEP 4: DETECT CHANGES ===")

    if file_path is None:
        file_path = _find_latest_raw_file()

    result = find_price_changes(file_path)
    logger.info(f"Found {result['changes_count']} price changes")

    if result["changes_count"] > 0:
        changes_df = result["changes"]
        # Show top 10 biggest drops
        if not changes_df.empty and "price_change" in changes_df.columns:
            biggest_drops = changes_df.nsmallest(10, "price_change")
            logger.info("Top 10 biggest price drops:")
            for _, row in biggest_drops.iterrows():
                logger.info(
                    f"  {row.get('station_name', 'N/A')} ({row.get('municipality', 'N/A')}): "
                    f"{row.get('fuel_type', 'N/A')} "
                    f"{row.get('old_price', 'N/A'):.3f} → {row.get('new_price', 'N/A'):.3f} "
                    f"({row.get('price_change', 0):+.3f})"
                )

    return result


def step_predict():
    """Step 5: Run predictions using the trained model."""
    from src.ml.predict import run_predictions

    logger.info("=== STEP 5: PREDICT ===")

    model_path = os.path.join(config.MODELS_DIR, config.MODEL_FILENAME)
    if not os.path.exists(model_path):
        logger.warning(
            "No trained model found. Run 'python run_pipeline.py --step train' first."
        )
        return []

    predictions = run_predictions()
    logger.info(f"Generated {len(predictions)} predictions")

    if predictions:
        up_count = sum(1 for p in predictions if p["prediction"] == "UP")
        stable_count = len(predictions) - up_count
        logger.info(f"  ↑ UP: {up_count}  |  ↓ STABLE/DOWN: {stable_count}")

    return predictions


def step_train():
    """Train or retrain the ML model."""
    from src.ml.train import train_and_save

    logger.info("=== TRAINING MODEL ===")

    import glob

    data_files = []
    if os.path.exists(config.PARQUET_DIR):
        data_files.extend(glob.glob(os.path.join(config.PARQUET_DIR, "fuel_prices_*.parquet")))
    if os.path.exists(config.PROCESSED_DIR):
        data_files.extend(glob.glob(os.path.join(config.PROCESSED_DIR, "fuel_prices_*.csv")))

    if len(data_files) < 2:
        logger.warning(
            f"Only {len(data_files)} snapshot(s) available. "
            f"Need at least {config.MIN_HISTORY_DAYS} days of data for training. "
            f"Keep collecting data and try again later."
        )
        return {}

    metrics = train_and_save()
    logger.info(f"Model trained — metrics: {json.dumps(metrics, indent=2)}")
    return metrics


def step_alerts(changes_result: dict = None):
    """Step 6: Check and send price alerts."""
    from src.alerts.alerts import check_alerts, load_subscriptions_local, format_alert_email

    logger.info("=== STEP 6: CHECK ALERTS ===")

    subscriptions = load_subscriptions_local()
    if not subscriptions:
        logger.info("No subscriptions found — skipping alerts.")
        return []

    if changes_result is None or changes_result.get("changes_count", 0) == 0:
        logger.info("No price changes — no alerts to send.")
        return []

    alerts = check_alerts(changes_result["changes"], subscriptions)
    logger.info(f"Generated {len(alerts)} alerts")

    for alert in alerts:
        email = format_alert_email(alert)
        logger.info(
            f"  ALERT → {alert['email']}: {email['subject']}"
        )

    return alerts


def run_full_pipeline(skip_ingest: bool = False):
    """Run the complete pipeline end-to-end."""
    logger.info("=" * 60)
    logger.info("SmartFuel Pipeline — Starting Full Run")
    logger.info("=" * 60)

    # Step 1: Ingest
    if skip_ingest:
        logger.info("Skipping ingestion (--skip-ingest)")
        file_path = _find_latest_raw_file()
    else:
        try:
            file_path = step_ingest()
        except Exception as e:
            logger.error(f"Ingestion failed: {e}")
            logger.info("Falling back to latest existing raw file...")
            file_path = _find_latest_raw_file()

    if file_path is None:
        logger.error("No raw data files found. Cannot continue.")
        return

    # Step 2: Validate
    validation = step_validate(file_path)
    if not validation["valid"]:
        logger.error("Pipeline stopped — invalid data file.")
        return

    # Step 3: Clean
    clean_result = step_clean(file_path)

    # Step 4: Changes
    changes_result = step_changes(file_path)

    # Step 5: Predict
    step_predict()

    # Step 6: Alerts
    step_alerts(changes_result)

    logger.info("=" * 60)
    logger.info("SmartFuel Pipeline — Complete!")
    logger.info("=" * 60)


def _find_latest_raw_file() -> str | None:
    """Find the most recent raw JSON file."""
    import glob

    pattern = os.path.join(config.RAW_DIR, "fuel_prices_*.json")
    files = glob.glob(pattern)
    if not files:
        return None
    return max(files)


def main():
    parser = argparse.ArgumentParser(
        description="SmartFuel Local Pipeline Orchestrator"
    )
    parser.add_argument(
        "--step",
        choices=["ingest", "validate", "clean", "changes", "predict", "train"],
        help="Run only a specific pipeline step",
    )
    parser.add_argument(
        "--skip-ingest",
        action="store_true",
        help="Skip data ingestion (use existing raw files)",
    )
    parser.add_argument(
        "--file",
        type=str,
        help="Path to a specific raw JSON file to process",
    )

    args = parser.parse_args()

    try:
        if args.step:
            if args.step == "ingest":
                step_ingest()
            elif args.step == "validate":
                step_validate(args.file)
            elif args.step == "clean":
                step_clean(args.file)
            elif args.step == "changes":
                step_changes(args.file)
            elif args.step == "predict":
                step_predict()
            elif args.step == "train":
                step_train()
        else:
            run_full_pipeline(skip_ingest=args.skip_ingest)
    except KeyboardInterrupt:
        logger.info("Pipeline interrupted by user.")
        sys.exit(1)
    except Exception:
        logger.error(f"Pipeline failed:\n{traceback.format_exc()}")
        sys.exit(1)


if __name__ == "__main__":
    main()
