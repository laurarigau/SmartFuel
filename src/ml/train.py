"""
Model training module for SmartFuel ML.

Trains a gradient-boosting classifier to predict short-term fuel-price
trends, evaluates against a majority-class baseline, and persists the
model artefact alongside its metrics.
"""

import json
import os
from typing import Any

try:
    import joblib
except ImportError:
    joblib = None
import pickle
import numpy as np
import pandas as pd
try:
    from sklearn.ensemble import GradientBoostingClassifier
    from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
    from sklearn.model_selection import train_test_split
except ImportError:
    class SimpleTrendClassifier:  # type: ignore[no-redef]
        """Lightweight numpy-based trend classifier used when scikit-learn is not available."""
        def __init__(self, **kwargs):
            self.weights = None
            self.bias = 0.0
            self.feature_importances_ = None

        def fit(self, X, y):
            X_mat = np.nan_to_num(np.asarray(X, dtype=np.float64))
            y_vec = np.asarray(y, dtype=np.float64)
            n, d = X_mat.shape
            self.weights = np.zeros(d)
            for _ in range(150):
                p = 1.0 / (1.0 + np.exp(-np.clip(X_mat @ self.weights + self.bias, -20, 20)))
                self.weights -= 0.05 * ((X_mat.T @ (p - y_vec)) / n + 0.01 * self.weights)
                self.bias -= 0.05 * np.mean(p - y_vec)
            abs_w = np.abs(self.weights)
            self.feature_importances_ = abs_w / (np.sum(abs_w) or 1.0)
            return self

        def predict_proba(self, X):
            X_mat = np.nan_to_num(np.asarray(X, dtype=np.float64))
            p1 = 1.0 / (1.0 + np.exp(-np.clip(X_mat @ self.weights + self.bias, -20, 20)))
            return np.column_stack([1.0 - p1, p1])

        def predict(self, X):
            return (self.predict_proba(X)[:, 1] >= 0.5).astype(int)

    GradientBoostingClassifier = SimpleTrendClassifier  # type: ignore[misc]

    def accuracy_score(y_true, y_pred):
        return float(np.mean(np.asarray(y_true) == np.asarray(y_pred)))

    def precision_score(y_true, y_pred, zero_division=0):
        y_t, y_p = np.asarray(y_true) == 1, np.asarray(y_pred) == 1
        tp = np.sum(y_t & y_p)
        fp = np.sum(~y_t & y_p)
        return float(tp / (tp + fp)) if (tp + fp) > 0 else float(zero_division)

    def recall_score(y_true, y_pred, zero_division=0):
        y_t, y_p = np.asarray(y_true) == 1, np.asarray(y_pred) == 1
        tp = np.sum(y_t & y_p)
        fn = np.sum(y_t & ~y_p)
        return float(tp / (tp + fn)) if (tp + fn) > 0 else float(zero_division)

    def f1_score(y_true, y_pred, zero_division=0):
        p = precision_score(y_true, y_pred, zero_division)
        r = recall_score(y_true, y_pred, zero_division)
        return float(2 * p * r / (p + r)) if (p + r) > 0 else float(zero_division)

    def train_test_split(X, y, test_size=0.2, random_state=42, **kwargs):
        np.random.seed(random_state)
        n = len(X)
        indices = np.random.permutation(n)
        split_idx = int(n * (1 - test_size))
        train_idx, test_idx = indices[:split_idx], indices[split_idx:]
        if hasattr(X, "iloc"):
            return X.iloc[train_idx], X.iloc[test_idx], y.iloc[train_idx], y.iloc[test_idx]
        return X[train_idx], X[test_idx], y[train_idx], y[test_idx]

from src.ml.features import build_training_data, load_price_history
from src.utils.config import MODEL_FILENAME, MODELS_DIR
from src.utils.logger import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Hyper-parameters (sensible defaults for a small tabular dataset)
# ---------------------------------------------------------------------------
_TEST_SIZE: float = 0.20
_RANDOM_STATE: int = 42
_N_ESTIMATORS: int = 200
_MAX_DEPTH: int = 4
_LEARNING_RATE: float = 0.1
_MIN_SAMPLES_SPLIT: int = 10


def train_model(
    X: pd.DataFrame,
    y: pd.Series,
) -> dict[str, Any]:
    """Train a GradientBoostingClassifier and return performance metrics.

    Args:
        X: Feature matrix.
        y: Binary target vector (1 = price goes UP).

    Returns:
        Dictionary with keys:
            - ``model`` – the fitted sklearn estimator.
            - ``accuracy`` (*float*)
            - ``precision`` (*float*)
            - ``recall`` (*float*)
            - ``f1`` (*float*)
            - ``feature_importances`` (*dict[str, float]*) – mapping from
              feature name to importance score.
    """
    logger.info("Splitting data: %.0f%% train, %.0f%% test", (1 - _TEST_SIZE) * 100, _TEST_SIZE * 100)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=_TEST_SIZE, random_state=_RANDOM_STATE, stratify=y
    )

    logger.info(
        "Training GradientBoostingClassifier (n_estimators=%d, max_depth=%d)",
        _N_ESTIMATORS,
        _MAX_DEPTH,
    )
    model = GradientBoostingClassifier(
        n_estimators=_N_ESTIMATORS,
        max_depth=_MAX_DEPTH,
        learning_rate=_LEARNING_RATE,
        min_samples_split=_MIN_SAMPLES_SPLIT,
        random_state=_RANDOM_STATE,
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)

    accuracy = float(accuracy_score(y_test, y_pred))
    precision = float(precision_score(y_test, y_pred, zero_division=0))
    recall_val = float(recall_score(y_test, y_pred, zero_division=0))
    f1_val = float(f1_score(y_test, y_pred, zero_division=0))

    importances: dict[str, float] = {
        col: round(float(imp), 6)
        for col, imp in zip(X.columns, model.feature_importances_)
    }

    baseline_result = evaluate_against_baseline(y_test, pd.Series(y_pred))

    logger.info(
        "Model metrics — Accuracy: %.4f  Precision: %.4f  Recall: %.4f  F1: %.4f",
        accuracy,
        precision,
        recall_val,
        f1_val,
    )
    logger.info(
        "Baseline comparison — Model better: %s (model=%.4f vs baseline=%.4f)",
        baseline_result["model_is_better"],
        baseline_result["model_accuracy"],
        baseline_result["baseline_accuracy"],
    )

    return {
        "model": model,
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall_val,
        "f1": f1_val,
        "feature_importances": importances,
    }


def evaluate_against_baseline(
    y_test: pd.Series,
    y_pred: pd.Series,
) -> dict[str, Any]:
    """Compare model predictions against a naïve baseline.

    The baseline strategy is *"predict 0 (price stays the same or drops)"*
    for every observation, reflecting the fact that prices don't change on
    most days.

    Args:
        y_test: True labels.
        y_pred: Model predictions.

    Returns:
        Dictionary with ``model_accuracy``, ``baseline_accuracy``, and
        ``model_is_better`` (bool).
    """
    y_test_arr = np.asarray(y_test)
    baseline_pred = np.zeros_like(y_test_arr)

    model_accuracy = float(accuracy_score(y_test_arr, np.asarray(y_pred)))
    baseline_accuracy = float(accuracy_score(y_test_arr, baseline_pred))

    return {
        "model_accuracy": model_accuracy,
        "baseline_accuracy": baseline_accuracy,
        "model_is_better": model_accuracy > baseline_accuracy,
    }


def save_model(
    model: Any,
    metrics: dict[str, Any],
    output_dir: str | None = None,
) -> str:
    """Persist the trained model and its metrics to disk.

    The model is saved with *joblib*; the metrics are saved as a companion
    JSON file with the same basename.

    Args:
        model: Fitted sklearn estimator.
        metrics: Dictionary of evaluation metrics (must be JSON-serialisable
            after removing the ``model`` key).
        output_dir: Target directory. Defaults to ``config.MODELS_DIR``.

    Returns:
        Absolute path of the saved model file.
    """
    output_dir = output_dir or MODELS_DIR
    os.makedirs(output_dir, exist_ok=True)

    model_path = os.path.join(output_dir, MODEL_FILENAME)
    if joblib is not None:
        joblib.dump(model, model_path)
    else:
        with open(model_path, "wb") as f:
            pickle.dump(model, f)
    logger.info("Model saved to %s", model_path)

    # Save metrics alongside the model
    metrics_to_save = {k: v for k, v in metrics.items() if k != "model"}
    metrics_filename = MODEL_FILENAME.replace(".joblib", "_metrics.json")
    metrics_path = os.path.join(output_dir, metrics_filename)

    with open(metrics_path, "w", encoding="utf-8") as fh:
        json.dump(metrics_to_save, fh, indent=2, ensure_ascii=False)
    logger.info("Metrics saved to %s", metrics_path)

    return model_path


def train_and_save() -> dict[str, Any]:
    """Orchestrate the full training pipeline: load → features → train → save.

    Returns:
        Dictionary of model metrics (same as ``train_model`` output, minus
        the ``model`` key, plus the ``model_path``).
    """
    logger.info("Starting full training pipeline")

    history_df = load_price_history()
    X, y = build_training_data(history_df)

    if X.empty:
        logger.error("No training data available — aborting")
        return {"error": "No training data available"}

    result = train_model(X, y)
    model_path = save_model(result["model"], result)

    # Build a JSON-safe return dict
    output: dict[str, Any] = {k: v for k, v in result.items() if k != "model"}
    output["model_path"] = model_path

    logger.info("Training pipeline complete: %s", output)
    return output
