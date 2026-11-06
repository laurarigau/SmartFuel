"""Tests for the data cleaning module using unittest."""

import json
import os
import tempfile
import unittest
import pandas as pd

os.environ["SMARTFUEL_ENV"] = "local"

from src.pipeline.clean import (
    convert_spanish_decimal,
    clean_dataframe,
    save_parquet,
    save_csv,
    clean_raw_file,
)

SAMPLE_STATION = {
    "IDEESS": "4375",
    "Rótulo": "TEST STATION",
    "Dirección": "CALLE TEST, 1",
    "Municipio": "Madrid",
    "Provincia": "MADRID",
    "C.P.": "28001",
    "Latitud": "40,416775",
    "Longitud (WGS84)": "-3,703790",
    "Precio Gasolina 95 E5": "1,699",
    "Precio Gasoleo A": "1,839",
    "Precio Gasolina 98 E5": "1,899",
    "Precio Gasoleo Premium": "1,939",
    "Horario": "L-D: 24H",
    "Tipo Venta": "P",
    "IDCCAA": "13",
}


class TestClean(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.sample_data = {
            "Fecha": "04/11/2026 13:25:51",
            "ListaEESSPrecio": [SAMPLE_STATION.copy() for _ in range(5)],
        }
        self.sample_df = pd.DataFrame([SAMPLE_STATION.copy() for _ in range(5)])

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_convert_spanish_decimal(self):
        self.assertAlmostEqual(convert_spanish_decimal("1,699"), 1.699)
        self.assertAlmostEqual(convert_spanish_decimal("1.699"), 1.699)
        self.assertIsNone(convert_spanish_decimal(""))
        self.assertIsNone(convert_spanish_decimal(None))

    def test_clean_dataframe(self):
        cleaned = clean_dataframe(self.sample_df, snapshot_date=self.sample_data["Fecha"])
        self.assertIn("station_id", cleaned.columns)
        self.assertIn("station_name", cleaned.columns)
        self.assertIn("gasoline_95_price", cleaned.columns)
        self.assertIn("diesel_price", cleaned.columns)
        self.assertEqual(len(cleaned), 5)

    def test_clean_raw_file(self):
        raw_path = os.path.join(self.temp_dir.name, "raw.json")
        with open(raw_path, "w", encoding="utf-8") as f:
            json.dump(self.sample_data, f)

        result = clean_raw_file(
            raw_path,
            parquet_dir=self.temp_dir.name,
            csv_dir=self.temp_dir.name,
        )
        self.assertEqual(result["row_count"], 5)
        if result["parquet_path"]:
            self.assertTrue(os.path.exists(result["parquet_path"]))
        self.assertTrue(os.path.exists(result["csv_path"]))


if __name__ == "__main__":
    unittest.main()
