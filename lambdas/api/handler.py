"""
Lambda handler for the SmartFuel HTTP API (API Gateway).

Routes requests to the appropriate handler:
  GET    /stations         - List stations with optional geohash/radius filter
  GET    /stations/{id}    - Get single station details
  GET    /prices/{id}      - Get price history for a station
  GET    /predictions      - Get all current predictions
  POST   /subscriptions    - Create a price alert subscription (auth required)
  DELETE /subscriptions/{id}- Delete a subscription (auth required)
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.utils import config
from src.utils.logger import get_logger

logger = get_logger("lambda.api")

CORS_HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type,Authorization",
    "Access-Control-Allow-Methods": "GET,POST,DELETE,OPTIONS",
}


def _response(status_code: int, body: dict | list) -> dict:
    return {
        "statusCode": status_code,
        "headers": CORS_HEADERS,
        "body": json.dumps(body, ensure_ascii=False),
    }


def handler(event, context):
    """
    Main API Gateway Lambda router.
    """
    http_method = event.get("requestContext", {}).get("http", {}).get("method") or event.get("httpMethod", "GET")
    route_key = event.get("routeKey", "")
    path = event.get("rawPath") or event.get("path", "")
    path_params = event.get("pathParameters") or {}
    query_params = event.get("queryStringParameters") or {}

    logger.info(f"{http_method} {path} (route: {route_key})")

    # Handle OPTIONS preflight
    if http_method == "OPTIONS":
        return _response(200, {"message": "OK"})

    try:
        # Route dispatch
        if http_method == "GET" and (path == "/stations" or route_key == "GET /stations"):
            return handle_get_stations(query_params)

        elif http_method == "GET" and path.startswith("/stations/"):
            station_id = path_params.get("id") or path.split("/")[-1]
            return handle_get_station(station_id)

        elif http_method == "GET" and path.startswith("/prices/"):
            station_id = path_params.get("id") or path.split("/")[-1]
            return handle_get_prices(station_id)

        elif http_method == "GET" and (path == "/predictions" or route_key == "GET /predictions"):
            return handle_get_predictions()

        elif http_method == "POST" and (path == "/subscriptions" or route_key == "POST /subscriptions"):
            body = json.loads(event.get("body", "{}"))
            user_id = _extract_user_id(event)
            return handle_create_subscription(body, user_id)

        elif http_method == "DELETE" and path.startswith("/subscriptions/"):
            sub_id = path_params.get("id") or path.split("/")[-1]
            user_id = _extract_user_id(event)
            return handle_delete_subscription(sub_id, user_id)

        else:
            return _response(404, {"error": "Not Found", "path": path})

    except Exception as e:
        logger.error(f"API Error on {path}: {e}", exc_info=True)
        return _response(500, {"error": str(e)})


def _extract_user_id(event: dict) -> str:
    """Extract authenticated user ID from Cognito JWT authorizer claims."""
    claims = event.get("requestContext", {}).get("authorizer", {}).get("jwt", {}).get("claims", {})
    return claims.get("sub", "anonymous")


def handle_get_stations(params: dict) -> dict:
    """Return stations, optionally filtered by geohash or bounding box."""
    if config.ENVIRONMENT == "aws":
        import boto3

        dynamodb = boto3.resource("dynamodb")
        table = dynamodb.Table(config.DYNAMODB_STATIONS_TABLE)

        geohash_prefix = params.get("geohash")
        if geohash_prefix:
            resp = table.query(
                IndexName="geohash-index",
                KeyConditionExpression="geohash = :gh",
                ExpressionAttributeValues={":gh": geohash_prefix},
                Limit=100,
            )
            return _response(200, resp.get("Items", []))
        else:
            resp = table.scan(Limit=50)
            return _response(200, resp.get("Items", []))
    else:
        # Local mode: read from processed CSV
        import glob
        import pandas as pd

        csv_files = glob.glob(os.path.join(config.PROCESSED_DIR, "fuel_prices_*.csv"))
        if not csv_files:
            return _response(200, [])

        df = pd.read_csv(max(csv_files))
        limit = int(params.get("limit", 100))
        records = df.head(limit).to_dict(orient="records")
        return _response(200, records)


def handle_get_station(station_id: str) -> dict:
    """Return single station by ID."""
    if config.ENVIRONMENT == "aws":
        import boto3

        dynamodb = boto3.resource("dynamodb")
        table = dynamodb.Table(config.DYNAMODB_STATIONS_TABLE)
        resp = table.get_item(Key={"station_id": station_id})
        item = resp.get("Item")
        if not item:
            return _response(404, {"error": "Station not found"})
        return _response(200, item)
    else:
        import glob
        import pandas as pd

        csv_files = glob.glob(os.path.join(config.PROCESSED_DIR, "fuel_prices_*.csv"))
        if not csv_files:
            return _response(404, {"error": "No data available"})

        df = pd.read_csv(max(csv_files))
        match = df[df["station_id"].astype(str) == str(station_id)]
        if match.empty:
            return _response(404, {"error": "Station not found"})
        return _response(200, match.iloc[0].to_dict())


def handle_get_prices(station_id: str) -> dict:
    """Return price history for a station."""
    if config.ENVIRONMENT == "aws":
        import boto3
        from boto3.dynamodb.conditions import Key

        dynamodb = boto3.resource("dynamodb")
        table = dynamodb.Table(config.DYNAMODB_PRICES_TABLE)
        resp = table.query(
            KeyConditionExpression=Key("station_id").eq(station_id),
            ScanIndexForward=False,
            Limit=30,
        )
        return _response(200, resp.get("Items", []))
    else:
        # Mock price history for demo
        import numpy as np

        np.random.seed(int(station_id) if station_id.isdigit() else 42)
        base = 1.65
        history = []
        for d in range(14, 0, -1):
            history.append({
                "date": f"2026-10-{d:02d}",
                "gasoline_95": round(base + np.random.normal(0, 0.02), 3),
                "diesel": round(base + 0.12 + np.random.normal(0, 0.02), 3),
            })
        return _response(200, history)


def handle_get_predictions() -> dict:
    """Return all latest predictions."""
    if config.ENVIRONMENT == "aws":
        import boto3

        dynamodb = boto3.resource("dynamodb")
        table = dynamodb.Table(config.DYNAMODB_PREDICTIONS_TABLE)
        resp = table.scan(Limit=100)
        return _response(200, resp.get("Items", []))
    else:
        from src.ml.predict import run_predictions

        try:
            preds = run_predictions()
            return _response(200, preds[:100])
        except Exception:
            return _response(200, [])


def handle_create_subscription(body: dict, user_id: str) -> dict:
    """Create a price alert subscription."""
    station_id = body.get("station_id")
    fuel_type = body.get("fuel_type", "gasoline_95")
    target_price = body.get("target_price")
    email = body.get("email")

    if not all([station_id, target_price, email]):
        return _response(400, {"error": "Missing station_id, target_price, or email"})

    if config.ENVIRONMENT == "aws":
        import boto3

        dynamodb = boto3.resource("dynamodb")
        table = dynamodb.Table(config.DYNAMODB_SUBSCRIPTIONS_TABLE)
        item = {
            "user_id": user_id,
            "station_fuel": f"{station_id}#{fuel_type}",
            "station_id": station_id,
            "fuel_type": fuel_type,
            "target_price": str(target_price),
            "email": email,
        }
        table.put_item(Item=item)
        return _response(201, item)
    else:
        # Local mock
        return _response(201, {
            "user_id": user_id,
            "station_id": station_id,
            "fuel_type": fuel_type,
            "target_price": target_price,
            "email": email,
            "status": "created (local mock)",
        })


def handle_delete_subscription(sub_id: str, user_id: str) -> dict:
    """Delete a price alert subscription."""
    if config.ENVIRONMENT == "aws":
        import boto3

        dynamodb = boto3.resource("dynamodb")
        table = dynamodb.Table(config.DYNAMODB_SUBSCRIPTIONS_TABLE)
        table.delete_item(Key={"user_id": user_id, "station_fuel": sub_id})
        return _response(200, {"message": "Subscription deleted"})
    else:
        return _response(200, {"message": "Subscription deleted (local mock)"})
