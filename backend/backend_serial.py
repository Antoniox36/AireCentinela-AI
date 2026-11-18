"""Receptor serial bidireccional del firmware de AireCentinela AI."""

import argparse
import csv
import importlib
import json
import math
import os
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from ia_engine.motor_ia import obtener_diagnostico_completo

COLUMNAS_CSV = (
    "timestamp",
    "temperatura",
    "humedad",
    "presion",
    "eco2",
    "tvoc",
)
VARIABLES_AMBIENTALES = COLUMNAS_CSV[1:]
BAUD_RATE_DEFAULT = 9600
PUERTO_DEFAULT = "COM6"
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

    if "error" in datos:
        raise ValueError(f"reporte del firmware: {datos['error']}")

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


def preparar_csv(ruta_csv: Path, reiniciar: bool = False) -> None:
    """Crea o reinicia el CSV con la cabecera oficial del proyecto."""
    ruta_csv.parent.mkdir(parents=True, exist_ok=True)
    if reiniciar or not ruta_csv.exists() or ruta_csv.stat().st_size == 0:
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


def _cargar_pyserial():
    try:
        return importlib.import_module("serial")
    except ModuleNotFoundError as error:
        if error.name != "serial":
            raise
        raise RuntimeError(
            "Falta pyserial; instálalo con 'python -m pip install pyserial'."
        ) from error


def verificar_sensores(port: str, baudrate: int, timeout_segundos: int = 10) -> bool:
    """Comprueba que el Arduino responde con al menos una trama válida de ambos sensores."""
    serial = _cargar_pyserial()
    print(f"[Verificación] Conectando a {port} ({baudrate} baudios)...")
    inicio = time.monotonic()

    with serial.Serial(port=port, baudrate=baudrate, timeout=1) as conexion:
        while time.monotonic() - inicio < timeout_segundos:
            trama = conexion.readline()
            if not trama:
                continue
            try:
                lectura = validar_trama(trama)
                print(f"[OK] Sensores activos y respondiendo: {lectura}")
                return True
            except ValueError as error:
                print(f"[Espera] {error}")

    print(
        "[ERROR] Tiempo agotado sin recibir datos válidos de los sensores.",
        file=sys.stderr,
    )
    return False


def recibir_datos(
    port: str, baudrate: int, ruta_csv: Path, limpiar_csv: bool = False
) -> None:
    """Escucha el puerto serial, persiste las tramas y envía al Arduino el veredicto de la IA."""
    serial = _cargar_pyserial()
    preparar_csv(ruta_csv, reiniciar=limpiar_csv)

    print(f"[Backend] Escuchando {port} a {baudrate} baudios (control bidireccional IA activo).")
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
            diagnostico = obtener_diagnostico_completo(str(ruta_csv))
            comando = diagnostico.get("comando_arduino", b"0\n")
            conexion.write(comando)
            conexion.flush()

            print(
                f"[Backend] [{datetime.now().strftime('%H:%M:%S')}] "
                f"T={lectura['temperatura']}°C | H={lectura['humedad']}% | "
                f"P={lectura['presion']}hPa | eCO2={lectura['eco2']:.0f}ppm | "
                f"TVOC={lectura['tvoc']:.0f}ppb -> IA: {diagnostico['nivel_alerta']} "
                f"(CMD: {comando.decode().strip()})"
            )


def crear_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Recibe lecturas JSON del Arduino y coordina alertas con el Motor IA."
    )
    parser.add_argument(
        "--port",
        default=os.environ.get("AIRECENTINELA_PORT", PUERTO_DEFAULT),
        help=f"Puerto serial del Arduino (predeterminado: {PUERTO_DEFAULT}).",
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
    parser.add_argument(
        "--verificar",
        action="store_true",
        help="Verifica durante 10s que los sensores envían tramas válidas y sale.",
    )
    parser.add_argument(
        "--limpiar",
        action="store_true",
        help="Borra lecturas anteriores del CSV antes de comenzar a grabar.",
    )
    return parser


def main() -> int:
    args = crear_parser().parse_args()
    try:
        if args.verificar:
            return 0 if verificar_sensores(args.port, args.baudrate) else 1
        recibir_datos(args.port, args.baudrate, args.csv, limpiar_csv=args.limpiar)
    except KeyboardInterrupt:
        print("\n[Backend] Recepción detenida por el usuario.")
        return 0
    except (OSError, RuntimeError, ValueError) as error:
        print(f"[Backend] Error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())