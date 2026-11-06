"""
Data ingestion module for SmartFuel.

Fetches fuel price data from the Spanish Ministry of Energy API and saves
the raw JSON response to disk with a timestamp-derived filename.
"""

import json
import os
import time
from datetime import datetime
from typing import Any

import ssl
import urllib.request

from src.utils.config import API_URL, RAW_DIR
from src.utils.logger import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Retry settings
# ---------------------------------------------------------------------------
MAX_RETRIES: int = 3
INITIAL_BACKOFF_SECONDS: float = 1.0
BACKOFF_MULTIPLIER: float = 2.0
REQUEST_TIMEOUT_SECONDS: int = 30


def _create_ssl_context() -> ssl.SSLContext:
    """Create an SSL context compatible with the Spanish Ministry's TLS 1.2 server."""
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.load_default_certs()
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    ctx.maximum_version = ssl.TLSVersion.TLSv1_2
    try:
        ctx.set_ciphers("AES256-GCM-SHA384:HIGH:!aNULL:!kEDH")
    except ssl.SSLError:
        pass
    return ctx


def fetch_fuel_data() -> dict[str, Any]:
    """Call the Spanish Ministry API and return the parsed JSON.

    Uses exponential backoff with up to MAX_RETRIES attempts and a custom TLS 1.2
    SSLContext required by the Spanish Ministry's servers.
    """
    ssl_context = _create_ssl_context()
    backoff = INITIAL_BACKOFF_SECONDS

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info("Fetching fuel data from API (attempt %d/%d)", attempt, MAX_RETRIES)
            req = urllib.request.Request(
                API_URL,
                headers={"User-Agent": "curl/7.88.1 (SmartFuel/1.0)"},
            )
            with urllib.request.urlopen(req, context=ssl_context, timeout=REQUEST_TIMEOUT_SECONDS) as resp:
                data: dict[str, Any] = json.loads(resp.read().decode("utf-8"))

            station_count = len(data.get("ListaEESSPrecio", []))
            logger.info(
                "Successfully fetched fuel data: %d stations, date=%s",
                station_count,
                data.get("Fecha", "unknown"),
            )
            return data
        except Exception as exc:
            logger.warning(
                "API request failed on attempt %d/%d: %s", attempt, MAX_RETRIES, exc
            )
            if attempt == MAX_RETRIES:
                logger.error("All %d API retries exhausted", MAX_RETRIES)
                raise
            logger.info("Retrying in %.1f seconds…", backoff)
            time.sleep(backoff)
            backoff *= BACKOFF_MULTIPLIER

    raise RuntimeError("Unexpected end of retry loop")


def save_raw_json(data: dict[str, Any], output_dir: str | None = None) -> str:
    """Persist raw API response as a timestamped JSON file.

    The timestamp is extracted from ``data["Fecha"]`` which has the format
    ``%d/%m/%Y %H:%M:%S``.

    Args:
        data: Parsed JSON from the Ministry API.
        output_dir: Directory to write the file to.  Defaults to
            ``config.RAW_DIR``.

    Returns:
        Absolute path of the saved JSON file.
    """
    output_dir = output_dir or RAW_DIR
    os.makedirs(output_dir, exist_ok=True)

    fecha_str: str = data.get("Fecha", "")
    try:
        snapshot_dt = datetime.strptime(fecha_str, "%d/%m/%Y %H:%M:%S")
    except (ValueError, TypeError):
        logger.warning(
            "Could not parse Fecha '%s'; falling back to current UTC time", fecha_str
        )
        snapshot_dt = datetime.utcnow()

    filename = f"fuel_prices_{snapshot_dt.strftime('%Y-%m-%d_%H%M')}.json"
    file_path = os.path.join(output_dir, filename)

    with open(file_path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False)

    logger.info("Saved raw JSON to %s", file_path)
    return file_path


def ingest() -> str:
    """Orchestrate fetch → save and return the saved file path.

    Returns:
        Absolute path of the saved JSON file.
    """
    logger.info("Starting ingestion pipeline")
    data = fetch_fuel_data()
    path = save_raw_json(data)
    logger.info("Ingestion complete: %s", path)
    return path
