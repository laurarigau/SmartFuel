"""
Data validation module for SmartFuel.

Validates raw JSON snapshot files against expected schema and data-quality
rules.  Invalid files are moved to a quarantine directory for manual review.
"""

import json
import os
import shutil
from typing import Any

from src.utils.config import MIN_EXPECTED_STATIONS, QUARANTINE_DIR
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Required top-level keys in a valid API response
_REQUIRED_TOP_KEYS: list[str] = ["Fecha", "ListaEESSPrecio"]

# Required keys in every station record (spot-check)
_REQUIRED_STATION_KEYS: list[str] = ["IDEESS", "Latitud", "Longitud (WGS84)"]

# Number of stations to spot-check
_SPOT_CHECK_COUNT: int = 100


def validate_raw_file(file_path: str) -> dict[str, Any]:
    """Load a raw JSON file and run a suite of data-quality checks.

    Checks performed:
        1. File contains valid JSON.
        2. Top-level object has *Fecha* and *ListaEESSPrecio* keys.
        3. Number of stations is at least ``config.MIN_EXPECTED_STATIONS``.
        4. The first 100 stations all contain *IDEESS*, *Latitud*, and
           *Longitud (WGS84)*.

    Args:
        file_path: Path to the raw JSON file to validate.

    Returns:
        A dictionary with keys:
            - ``valid`` (*bool*) – overall pass/fail.
            - ``errors`` (*list[str]*) – human-readable error messages.
            - ``station_count`` (*int*) – number of stations found.
            - ``snapshot_date`` (*str*) – value of the *Fecha* field.
    """
    errors: list[str] = []
    station_count: int = 0
    snapshot_date: str = ""

    # ---- Check 1: Valid JSON ------------------------------------------------
    try:
        with open(file_path, "r", encoding="utf-8") as fh:
            data: dict[str, Any] = json.load(fh)
    except (json.JSONDecodeError, OSError) as exc:
        errors.append(f"File is not valid JSON or cannot be read: {exc}")
        return {
            "valid": False,
            "errors": errors,
            "station_count": station_count,
            "snapshot_date": snapshot_date,
        }

    # ---- Check 2: Required top-level keys -----------------------------------
    for key in _REQUIRED_TOP_KEYS:
        if key not in data:
            errors.append(f"Missing required top-level key: '{key}'")

    if errors:
        return {
            "valid": False,
            "errors": errors,
            "station_count": station_count,
            "snapshot_date": snapshot_date,
        }

    snapshot_date = data.get("Fecha", "")
    stations: list[dict[str, Any]] = data.get("ListaEESSPrecio", [])
    station_count = len(stations)

    # ---- Check 3: Minimum station count -------------------------------------
    if station_count < MIN_EXPECTED_STATIONS:
        errors.append(
            f"Station count {station_count} is below minimum threshold "
            f"of {MIN_EXPECTED_STATIONS}"
        )

    # ---- Check 4: Spot-check required station fields ------------------------
    check_up_to = min(_SPOT_CHECK_COUNT, station_count)
    for idx in range(check_up_to):
        station = stations[idx]
        for key in _REQUIRED_STATION_KEYS:
            if key not in station:
                errors.append(
                    f"Station at index {idx} is missing required key '{key}'"
                )

    valid = len(errors) == 0
    if valid:
        logger.info(
            "Validation passed for %s (%d stations, date=%s)",
            file_path,
            station_count,
            snapshot_date,
        )
    else:
        logger.warning(
            "Validation FAILED for %s with %d error(s): %s",
            file_path,
            len(errors),
            "; ".join(errors),
        )

    return {
        "valid": valid,
        "errors": errors,
        "station_count": station_count,
        "snapshot_date": snapshot_date,
    }


def quarantine_file(file_path: str, quarantine_dir: str | None = None) -> str:
    """Move a file to the quarantine directory.

    Args:
        file_path: Absolute path of the file to quarantine.
        quarantine_dir: Optional override for the quarantine directory.

    Returns:
        New absolute path inside the quarantine directory.
    """
    target_dir = quarantine_dir or QUARANTINE_DIR
    os.makedirs(target_dir, exist_ok=True)
    filename = os.path.basename(file_path)
    dest = os.path.join(target_dir, filename)
    shutil.move(file_path, dest)
    logger.info("Quarantined %s → %s", file_path, dest)
    return dest


def validate_and_quarantine(file_path: str, quarantine_dir: str | None = None) -> dict[str, Any]:
    """Validate a raw file and quarantine it if invalid.

    Args:
        file_path: Path to the raw JSON file.
        quarantine_dir: Optional override for quarantine directory.

    Returns:
        The validation result dict, augmented with a ``quarantined_path``
        key if the file was quarantined.
    """
    result = validate_raw_file(file_path)

    if not result["valid"]:
        quarantined_path = quarantine_file(file_path, quarantine_dir=quarantine_dir)
        result["quarantined_path"] = quarantined_path
        logger.warning("File quarantined at %s", quarantined_path)
    else:
        result["quarantined_path"] = None

    return result
