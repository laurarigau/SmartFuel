"""
Prediction module for SmartFuel ML.

Loads a persisted model and produces per-station price-trend forecasts
using the latest available features.
"""

import json
import os
from typing import Any

try:
    import joblib
except ImportError:
    joblib = None
import pickle
import pandas as pd

from src.ml.features import (
    _get_feature_columns,
    build_station_features,
    load_price_history,
)
from src.utils.config import MIN_HISTORY_DAYS, MODEL_FILENAME, MODELS_DIR
from src.utils.logger import get_logger

logger = get_logger(__name__)


def load_model(model_dir: str | None = None) -> tuple[Any, dict[str, Any]]:
    """Load the trained model and its companion metrics from disk.

    Args:
        model_dir: Directory containing the model artefact.  Defaults to
            ``config.MODELS_DIR``.

    Returns:
        Tuple of ``(model, metrics_dict)``.

    Raises:
        FileNotFoundError: If the model file does not exist.
    """
    model_dir = model_dir or MODELS_DIR
    model_path = os.path.join(model_dir, MODEL_FILENAME)

    if not os.path.isfile(model_path):
        raise FileNotFoundError(f"Model not found at {model_path}")

    if joblib is not None:
        model = joblib.load(model_path)
    else:
        with open(model_path, "rb") as f:
            model = pickle.load(f)
    logger.info("Model loaded from %s", model_path)

    metrics: dict[str, Any] = {}
    metrics_filename = MODEL_FILENAME.replace(".joblib", "_metrics.json")
    metrics_path = os.path.join(model_dir, metrics_filename)
    if os.path.isfile(metrics_path):
        with open(metrics_path, "r", encoding="utf-8") as fh:
            metrics = json.load(fh)
        logger.info("Metrics loaded from %s", metrics_path)

    return model, metrics


def predict_station(
    model: Any,
    history_df: pd.DataFrame,
    station_id: str,
) -> dict[str, Any]:
    """Generate a price-trend prediction for a single station.

    Builds the latest feature row from historical data and runs the model.

    Args:
        model: Fitted sklearn estimator.
        history_df: Full price history DataFrame (all stations).
        station_id: Identifier of the station to predict for.

    Returns:
        Dictionary with keys:
            - ``station_id`` (*str*)
            - ``prediction`` (*str*) – ``"UP"`` or ``"DOWN_OR_STABLE"``
            - ``probability`` (*float*) – model confidence for the predicted
              class.
            - ``features_date`` (*str*) – date of the most recent feature row.
    """
    station_features = build_station_features(history_df, station_id)

    if station_features.empty:
        return {
            "station_id": station_id,
            "prediction": "INSUFFICIENT_DATA",
            "probability": 0.0,
            "features_date": "",
        }

    feature_cols = _get_feature_columns()

    # Drop rows with NaN features, then take the last (most recent) row
    valid_features = station_features.dropna(subset=feature_cols)

    if valid_features.empty:
        return {
            "station_id": station_id,
            "prediction": "INSUFFICIENT_DATA",
            "probability": 0.0,
            "features_date": "",
        }

    latest = valid_features.iloc[[-1]]
    X_latest = latest[feature_cols]

    prediction_label: int = int(model.predict(X_latest)[0])
    probabilities = model.predict_proba(X_latest)[0]

    # probability of the predicted class
    probability = float(probabilities[prediction_label])

    prediction_str = "UP" if prediction_label == 1 else "DOWN_OR_STABLE"

    features_date = str(latest["date"].iloc[0]) if "date" in latest.columns else ""

    return {
        "station_id": station_id,
        "prediction": prediction_str,
        "probability": round(probability, 4),
        "features_date": features_date,
    }


def predict_all_stations(
    model: Any,
    history_df: pd.DataFrame,
) -> list[dict[str, Any]]:
    """Run predictions for every station that has enough history.

    Args:
        model: Fitted sklearn estimator.
        history_df: Full price history DataFrame (all stations).

    Returns:
        List of prediction dictionaries (one per eligible station).
    """
    station_ids = history_df["station_id"].unique()
    logger.info("Running predictions for %d stations", len(station_ids))

    predictions: list[dict[str, Any]] = []

    for sid in station_ids:
        station_data = history_df[history_df["station_id"] == sid]
        if "snapshot_date" in station_data.columns:
            n_days = station_data["snapshot_date"].dt.date.nunique()
        else:
            n_days = len(station_data)

        if n_days < MIN_HISTORY_DAYS:
            continue

        pred = predict_station(model, history_df, sid)
        if pred["prediction"] != "INSUFFICIENT_DATA":
            predictions.append(pred)

    logger.info("Generated %d predictions", len(predictions))
    return predictions


def run_predictions() -> list[dict[str, Any]]:
    """Orchestrate the full prediction pipeline.

    Loads the model, loads price history, and runs predictions for all
    eligible stations.

    Returns:
        List of prediction dicts.
    """
    logger.info("Starting prediction pipeline")
    model, metrics = load_model()
    history_df = load_price_history()
    predictions = predict_all_stations(model, history_df)
    logger.info("Prediction pipeline complete: %d predictions", len(predictions))
    return predictions
