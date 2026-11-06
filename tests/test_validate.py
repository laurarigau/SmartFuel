"""Tests for the data validation module using unittest."""

import json
import os
import tempfile
import unittest

os.environ["SMARTFUEL_ENV"] = "local"

from src.pipeline.validate import validate_raw_file, quarantine_file, validate_and_quarantine


def _make_valid_data(station_count=12000):
    stations = []
    for i in range(station_count):
        stations.append({
            "IDEESS": str(1000 + i),
            "Rótulo": f"Station {i}",
            "Dirección": f"Street {i}",
            "Municipio": "Madrid",
            "Provincia": "MADRID",
            "C.P.": "28001",
            "Latitud": "40,416775",
            "Longitud (WGS84)": "-3,703790",
            "Precio Gasolina 95 E5": "1,699",
            "Precio Gasoleo A": "1,839",
            "Precio Gasolina 98 E5": "",
            "Precio Gasoleo Premium": "",
            "Horario": "L-D: 24H",
            "Tipo Venta": "P",
            "IDCCAA": "13",
        })
    return {
        "Fecha": "04/11/2026 13:25:51",
        "ListaEESSPrecio": stations,
        "ResultadoConsulta": "OK",
    }


class TestValidateRawFile(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_valid_file_passes(self):
        path = os.path.join(self.temp_dir.name, "valid.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(_make_valid_data(), f)

        result = validate_raw_file(path)
        self.assertTrue(result["valid"])
        self.assertEqual(result["station_count"], 12000)
        self.assertEqual(len(result["errors"]), 0)

    def test_too_few_stations_fails(self):
        path = os.path.join(self.temp_dir.name, "few.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(_make_valid_data(station_count=100), f)

        result = validate_raw_file(path)
        self.assertFalse(result["valid"])
        self.assertTrue(any("station" in e.lower() for e in result["errors"]))

    def test_missing_keys_fails(self):
        path = os.path.join(self.temp_dir.name, "bad_keys.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"bad": "keys"}, f)

        result = validate_raw_file(path)
        self.assertFalse(result["valid"])

    def test_invalid_json_fails(self):
        path = os.path.join(self.temp_dir.name, "not_json.json")
        with open(path, "w") as f:
            f.write("not json {{{")

        result = validate_raw_file(path)
        self.assertFalse(result["valid"])


class TestQuarantineFile(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_moves_file_to_quarantine(self):
        path = os.path.join(self.temp_dir.name, "bad.json")
        with open(path, "w") as f:
            f.write("{}")

        quarantine_dir = os.path.join(self.temp_dir.name, "quarantine")
        new_path = quarantine_file(path, quarantine_dir=quarantine_dir)
        self.assertTrue(os.path.exists(new_path))
        self.assertFalse(os.path.exists(path))
        self.assertIn("quarantine", new_path)


if __name__ == "__main__":
    unittest.main()
