import csv
import json
import tempfile
import unittest
from pathlib import Path

from backend.backend_serial import COLUMNAS_CSV, guardar_lectura, validar_trama


LECTURA = {
    "temperatura": 31.5,
    "humedad": 60,
    "presion": 1011.2,
    "pm10": 10,
    "pm25": 18,
    "pm100": 30,
}


class ValidarTramaTests(unittest.TestCase):
    def test_valida_json_del_firmware_en_bytes(self) -> None:
        resultado = validar_trama(json.dumps(LECTURA).encode("utf-8"))

        self.assertEqual(resultado, {clave: float(valor) for clave, valor in LECTURA.items()})

    def test_rechaza_json_invalido_y_campos_ausentes(self) -> None:
        with self.assertRaisesRegex(ValueError, "JSON válido"):
            validar_trama("{")
        with self.assertRaisesRegex(ValueError, "pm100"):
            validar_trama(json.dumps({"temperatura": 30}))

    def test_rechaza_valores_no_numericos_y_no_finitos(self) -> None:
        for valor in (True, "30", float("nan"), float("inf")):
            with self.subTest(valor=valor):
                trama = {**LECTURA, "temperatura": valor}
                with self.assertRaises(ValueError):
                    validar_trama(json.dumps(trama))


class GuardarLecturaTests(unittest.TestCase):
    def test_crea_csv_con_esquema_compartido_y_agrega_lecturas(self) -> None:
        with tempfile.TemporaryDirectory() as directorio:
            ruta_csv = Path(directorio) / "subdirectorio" / "datos.csv"

            guardar_lectura(
                validar_trama(json.dumps(LECTURA)),
                ruta_csv,
                timestamp="2026-11-06 12:00:00",
            )
            guardar_lectura(
                validar_trama(json.dumps(LECTURA)),
                ruta_csv,
                timestamp="2026-11-06 12:00:03",
            )

            with ruta_csv.open(newline="", encoding="utf-8") as archivo:
                filas = list(csv.DictReader(archivo))

            self.assertEqual(tuple(filas[0].keys()), COLUMNAS_CSV)
            self.assertEqual(len(filas), 2)
            self.assertEqual(filas[0]["timestamp"], "2026-11-06 12:00:00")
            self.assertEqual(filas[1]["pm25"], "18.0")

    def test_rechaza_csv_con_cabecera_incompatible(self) -> None:
        with tempfile.TemporaryDirectory() as directorio:
            ruta_csv = Path(directorio) / "datos.csv"
            ruta_csv.write_text("timestamp,temperatura,pm25\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "cabecera esperada"):
                guardar_lectura(LECTURA, ruta_csv)

            self.assertEqual(
                ruta_csv.read_text(encoding="utf-8"),
                "timestamp,temperatura,pm25\n",
            )


if __name__ == "__main__":
    unittest.main()
