"""Tests for the data ingestion module using unittest."""

import json
import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock

os.environ["SMARTFUEL_ENV"] = "local"

from src.pipeline.ingest import fetch_fuel_data, save_raw_json


class TestIngest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.sample_response = {
            "Fecha": "04/11/2026 13:25:51",
            "ListaEESSPrecio": [
                {
                    "IDEESS": "4375",
                    "Rótulo": "TEST",
                    "Dirección": "TEST",
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
            ],
            "ResultadoConsulta": "OK",
        }

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_save_raw_json(self):
        path = save_raw_json(self.sample_response, output_dir=self.temp_dir.name)
        self.assertTrue(os.path.exists(path))
        self.assertIn("fuel_prices_2026-11-04_1325", os.path.basename(path))

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["Fecha"], "04/11/2026 13:25:51")

    def test_fetch_fuel_data(self):
        from unittest.mock import patch, MagicMock
        import io
        import json

        mock_data = json.dumps(self.sample_response).encode("utf-8")
        mock_resp = MagicMock()
        mock_resp.__enter__.return_value = io.BytesIO(mock_data)

        with patch("urllib.request.urlopen", return_value=mock_resp.__enter__.return_value):
            data = fetch_fuel_data()
            self.assertIn("Fecha", data)
            self.assertIn("ListaEESSPrecio", data)


if __name__ == "__main__":
    unittest.main()
