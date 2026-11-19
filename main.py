"""Orquestador principal de AireCentinela AI: inicia backend serial y dashboard visual."""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

RAIZ_PROYECTO = Path(__file__).resolve().parent
SCRIPT_BACKEND = RAIZ_PROYECTO / "backend" / "backend_serial.py"
SCRIPT_FRONTEND = RAIZ_PROYECTO / "frontend" / "app_airecentinela.py"
RUTA_CSV_DEFAULT = RAIZ_PROYECTO / "data" / "datos_ambientales.csv"


def crear_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Inicia la estación ambiental completa AireCentinela AI."
    )
    parser.add_argument(
        "--port",
        default=os.environ.get("AIRECENTINELA_PORT", "COM6"),
        help="Puerto serial del Arduino Uno R3 (predeterminado: COM6).",
    )
    parser.add_argument(
        "--baudrate",
        type=int,
        default=9600,
        help="Velocidad serial en baudios (predeterminado: 9600).",
    )
    parser.add_argument(
        "--limpiar",
        action="store_true",
        help="Limpia el historial CSV antes de iniciar la captura en vivo.",
    )
    parser.add_argument(
        "--sin-hardware",
        action="store_true",
        help="Abre únicamente el dashboard con el historial existente sin conectar COM.",
    )
    return parser


def detener_proceso(proceso: subprocess.Popen | None) -> None:
    """Termina el subproceso del backend de forma limpia para liberar el puerto COM."""
    if proceso is None or proceso.poll() is not None:
        return
    proceso.terminate()
    try:
        proceso.wait(timeout=3)
    except subprocess.TimeoutExpired:
        proceso.kill()


def main() -> int:
    args = crear_parser().parse_args()
    proceso_backend: subprocess.Popen | None = None

    print("=" * 60)
    print("  AireCentinela AI | Iniciando Estación Ambiental")
    print("=" * 60)

    try:
        if not args.sin_hardware:
            cmd_backend = [
                sys.executable,
                str(SCRIPT_BACKEND),
                "--port",
                args.port,
                "--baudrate",
                str(args.baudrate),
                "--csv",
                str(RUTA_CSV_DEFAULT),
            ]
            if args.limpiar:
                cmd_backend.append("--limpiar")

            print(f"[Main] Lanzando backend serial en {args.port} ({args.baudrate} baudios)...")
            proceso_backend = subprocess.Popen(cmd_backend, cwd=str(RAIZ_PROYECTO))

            # Dar tiempo a que el Arduino reinicie y abra el puerto serial
            time.sleep(2.0)
            if proceso_backend.poll() is not None:
                print(
                    f"[Main] Error: el backend se detuvo al intentar abrir {args.port}. "
                    "Verifica que el Monitor Serial esté cerrado y el cable conectado.",
                    file=sys.stderr,
                )
                return 1

        print("[Main] Abriendo interfaz gráfica PyQt6 + Motor IA...")
        resultado_frontend = subprocess.run(
            [sys.executable, str(SCRIPT_FRONTEND)],
            cwd=str(RAIZ_PROYECTO),
            check=False,
        )
        return resultado_frontend.returncode

    except KeyboardInterrupt:
        print("\n[Main] Ejecución interrumpida por el usuario.")
        return 0
    finally:
        detener_proceso(proceso_backend)
        print("[Main] Sistema cerrado y puerto serial liberado.")


if __name__ == "__main__":
    raise SystemExit(main())