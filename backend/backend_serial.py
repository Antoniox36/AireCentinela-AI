"""Receptor serial del firmware de AireCentinela AI."""

import argparse
import csv
import importlib
import json
import math
import os
import sys
from datetime import datetime
from pathlib import Path

COLUMNAS_CSV = (
    "timestamp",
    "temperatura",
    "humedad",
    "presion",
    "pm10",
    "pm25",
    "pm100",
)
VARIABLES_AMBIENTALES = COLUMNAS_CSV[1:]
BAUD_RATE_DEFAULT = 9600
RUTA_CSV_DEFAULT = (
    Path(__file__).resolve().parent.parent / "data" / "datos_ambientales.csv"
)


def validar_trama(trama: bytes | str) -> dict[str, float]:
    """Decodifica y valida una línea JSON enviada por el firmware."""
    try:
        texto = trama.decode("utf-8") if isinstance(trama, bytes) else trama
    except UnicodeDecodeError as error:
        raise ValueError("la trama no contiene texto UTF-8 válido") from error

    try:
        datos = json.loads(texto)
    except json.JSONDecodeError as error:
        raise ValueError("la trama no contiene JSON válido") from error

    if not isinstance(datos, dict):
        raise ValueError("el JSON debe ser un objeto")

    faltantes = [campo for campo in VARIABLES_AMBIENTALES if campo not in datos]
    if faltantes:
        raise ValueError(f"faltan campos requeridos: {', '.join(faltantes)}")

    lectura: dict[str, float] = {}
    for campo in VARIABLES_AMBIENTALES:
        valor = datos[campo]
        if isinstance(valor, bool) or not isinstance(valor, (int, float)):
            raise ValueError(f"'{campo}' debe ser un número")
        try:
            valor_numerico = float(valor)
        except OverflowError as error:
            raise ValueError(f"'{campo}' está fuera del rango permitido") from error
        if not math.isfinite(valor_numerico):
            raise ValueError(f"'{campo}' debe ser un número finito")
        lectura[campo] = valor_numerico

    return lectura


def preparar_csv(ruta_csv: Path) -> None:
    """Crea el directorio y cabecera, o verifica el esquema del CSV existente."""
    ruta_csv.parent.mkdir(parents=True, exist_ok=True)
    if not ruta_csv.exists() or ruta_csv.stat().st_size == 0:
        with ruta_csv.open("w", newline="", encoding="utf-8") as salida:
            csv.writer(salida).writerow(COLUMNAS_CSV)
        return

    with ruta_csv.open("r", newline="", encoding="utf-8") as entrada:
        cabecera = next(csv.reader(entrada), [])
    if tuple(cabecera) != COLUMNAS_CSV:
        raise ValueError(
            f"el CSV existente '{ruta_csv}' no tiene la cabecera esperada: "
            f"{','.join(COLUMNAS_CSV)}"
        )


def guardar_lectura(
    lectura: dict[str, float],
    ruta_csv: Path = RUTA_CSV_DEFAULT,
    timestamp: str | None = None,
) -> None:
    """Agrega una lectura validada al historial ambiental."""
    preparar_csv(ruta_csv)
    fila = {
        "timestamp": timestamp or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        **lectura,
    }
    with ruta_csv.open("a", newline="", encoding="utf-8") as salida:
        escritor = csv.DictWriter(salida, fieldnames=COLUMNAS_CSV)
        escritor.writerow(fila)
        salida.flush()


def recibir_datos(port: str, baudrate: int, ruta_csv: Path) -> None:
    """Escucha el puerto serial y persiste las tramas JSON válidas."""
    try:
        serial = importlib.import_module("serial")
    except ModuleNotFoundError as error:
        if error.name != "serial":
            raise
        raise RuntimeError(
            "Falta pyserial; instálalo con 'python -m pip install pyserial'."
        ) from error

    print(f"[Backend] Escuchando {port} a {baudrate} baudios.")
    print(f"[Backend] Historial: {ruta_csv}")

    with serial.Serial(port=port, baudrate=baudrate, timeout=1) as conexion:
        while True:
            trama = conexion.readline()
            if not trama:
                continue
            try:
                lectura = validar_trama(trama)
            except ValueError as error:
                print(f"[Backend] Trama ignorada: {error}.", file=sys.stderr)
                continue

            guardar_lectura(lectura, ruta_csv)
            print("[Backend] Lectura guardada.")


def crear_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Recibe lecturas JSON del Arduino y las guarda en un CSV."
    )
    parser.add_argument(
        "--port",
        default=os.environ.get("AIRECENTINELA_PORT", "COM4"),
        help="Puerto serial del Arduino (predeterminado: COM4 o AIRECENTINELA_PORT).",
    )
    parser.add_argument(
        "--baudrate",
        type=int,
        default=BAUD_RATE_DEFAULT,
        help=f"Velocidad serial en baudios (predeterminado: {BAUD_RATE_DEFAULT}).",
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=RUTA_CSV_DEFAULT,
        help=f"Ruta del historial CSV (predeterminada: {RUTA_CSV_DEFAULT}).",
    )
    return parser


def main() -> int:
    args = crear_parser().parse_args()
    try:
        recibir_datos(args.port, args.baudrate, args.csv)
    except KeyboardInterrupt:
        print("\n[Backend] Recepción detenida por el usuario.")
        return 0
    except (OSError, RuntimeError, ValueError) as error:
        print(f"[Backend] Error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())