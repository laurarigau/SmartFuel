"""
Shared configuration for SmartFuel.

When running locally, paths point to the local filesystem.
When running on AWS, S3/DynamoDB references are used instead.
Environment variables override defaults.
"""

import os

# ---------------------------------------------------------------------------
# Environment: "local" or "aws"
# ---------------------------------------------------------------------------
ENVIRONMENT = os.environ.get("SMARTFUEL_ENV", "local")

# ---------------------------------------------------------------------------
# Project paths (local mode)
# ---------------------------------------------------------------------------
PROJECT_ROOT = os.environ.get(
    "SMARTFUEL_PROJECT_ROOT",
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

DATA_DIR = os.path.join(PROJECT_ROOT, "data")
RAW_DIR = os.path.join(DATA_DIR, "raw")
PROCESSED_DIR = os.path.join(DATA_DIR, "processed")
PARQUET_DIR = os.path.join(DATA_DIR, "parquet")
MODELS_DIR = os.path.join(DATA_DIR, "models")
QUARANTINE_DIR = os.path.join(DATA_DIR, "quarantine")

# ---------------------------------------------------------------------------
# AWS resource names (used in aws mode and Terraform)
# ---------------------------------------------------------------------------
AWS_REGION = os.environ.get("AWS_REGION", "eu-west-1")
S3_BUCKET = os.environ.get("SMARTFUEL_S3_BUCKET", "smartfuel-data")
DYNAMODB_STATIONS_TABLE = os.environ.get("SMARTFUEL_DYNAMO_STATIONS", "smartfuel-stations")
DYNAMODB_PRICES_TABLE = os.environ.get("SMARTFUEL_DYNAMO_PRICES", "smartfuel-prices")
DYNAMODB_PREDICTIONS_TABLE = os.environ.get("SMARTFUEL_DYNAMO_PREDICTIONS", "smartfuel-predictions")
DYNAMODB_SUBSCRIPTIONS_TABLE = os.environ.get("SMARTFUEL_DYNAMO_SUBSCRIPTIONS", "smartfuel-subscriptions")
SNS_ALERTS_TOPIC = os.environ.get("SMARTFUEL_SNS_TOPIC", "smartfuel-admin-alerts")
SQS_DLQ_URL = os.environ.get("SMARTFUEL_SQS_DLQ", "")

# ---------------------------------------------------------------------------
# API settings
# ---------------------------------------------------------------------------
API_URL = "https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/PreciosCarburantes/EstacionesTerrestres/"

# ---------------------------------------------------------------------------
# Data schema — columns selected from the raw API response
# ---------------------------------------------------------------------------
RAW_COLUMNS = [
    "IDEESS",
    "Rótulo",
    "Dirección",
    "Municipio",
    "Provincia",
    "C.P.",
    "Latitud",
    "Longitud (WGS84)",
    "Precio Gasolina 95 E5",
    "Precio Gasoleo A",
    "Precio Gasolina 98 E5",
    "Precio Gasoleo Premium",
    "Horario",
    "Tipo Venta",
    "IDCCAA",
]

CLEAN_COLUMNS = [
    "station_id",
    "station_name",
    "address",
    "municipality",
    "province",
    "postal_code",
    "latitude",
    "longitude",
    "gasoline_95_price",
    "diesel_price",
    "gasoline_98_price",
    "diesel_premium_price",
    "schedule",
    "sale_type",
    "region_id",
]

# Mapping from raw Spanish column names to clean English names
COLUMN_MAPPING = dict(zip(RAW_COLUMNS, CLEAN_COLUMNS))

# Columns that hold Spanish-format decimal numbers (comma as separator)
NUMERIC_COLUMNS = [
    "gasoline_95_price",
    "diesel_price",
    "gasoline_98_price",
    "diesel_premium_price",
    "latitude",
    "longitude",
]

# ---------------------------------------------------------------------------
# ML settings
# ---------------------------------------------------------------------------
MODEL_FILENAME = "price_trend_model.joblib"
PREDICTION_HORIZON_DAYS = 3
MIN_HISTORY_DAYS = 7  # Minimum days of data needed to train

# ---------------------------------------------------------------------------
# Validation thresholds
# ---------------------------------------------------------------------------
MIN_EXPECTED_STATIONS = 10000  # API typically returns ~12,000
MAX_PRICE_EUR = 5.0  # Sanity check: no fuel should cost more than this
MIN_PRICE_EUR = 0.5  # Sanity check: no fuel should cost less than this

# ---------------------------------------------------------------------------
# Geohash precision for DynamoDB location queries
# ---------------------------------------------------------------------------
GEOHASH_PRECISION = 5  # ~5 km resolution

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_LEVEL = os.environ.get("SMARTFUEL_LOG_LEVEL", "INFO")
