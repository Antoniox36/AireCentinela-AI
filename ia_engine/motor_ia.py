"""Motor de Inteligencia Artificial no supervisada (Isolation Forest) para AireCentinela AI."""

import os
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

RUTA_CSV_DEFAULT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "data", "datos_ambientales.csv")
)
FEATURES_IA = ["temperatura", "humedad", "presion", "eco2", "tvoc"]

# Márgenes estándar relativos sobre la línea base aprendida de cada zona (en ppm)
MARGEN_PRECAUCION_PPM = 200.0
MARGEN_ALERTA_PPM = 450.0
MARGEN_CRITICO_PPM = 800.0


def calcular_tendencia_eco2(serie_eco2: pd.Series) -> dict:
    """Calcula la variación de eCO2 entre el inicio y el final de la ventana reciente."""
    if len(serie_eco2) < 15:
        return {"tendencia": "INSUFICIENTE", "delta_ppm": 0.0}

    valores = serie_eco2.values
    n_bloque = max(3, len(valores) // 5)
    promedio_inicial = valores[:n_bloque].mean()
    promedio_final = valores[-n_bloque:].mean()
    delta = round(float(promedio_final - promedio_inicial), 2)

    if delta > 200.0:
        tendencia = "SUBIENDO_RAPIDO"
    elif delta > 75.0:
        tendencia = "SUBIENDO"
    elif delta < -75.0:
        tendencia = "BAJANDO"
    else:
        tendencia = "ESTABLE"

    return {"tendencia": tendencia, "delta_ppm": delta}


def obtener_diagnostico_completo(
    ruta_csv: str = RUTA_CSV_DEFAULT, contamination: float = 0.05
) -> dict:
    """Evalúa el estado ambiental combinando Isolation Forest y márgenes relativos sobre la línea base."""
    if not os.path.exists(ruta_csv):
        return {
            "estado_ia": 1,
            "nivel_alerta": "SIN_DATOS",
            "mensaje": f"No se encontró el archivo '{ruta_csv}'",
            "temperatura": None,
            "eco2": None,
            "tendencia": "DESCONOCIDA",
            "delta_ppm": 0.0,
            "comando_arduino": b"0\n",
        }

    try:
        df = pd.read_csv(ruta_csv)
        if not all(col in df.columns for col in FEATURES_IA):
            return {
                "estado_ia": 1,
                "nivel_alerta": "ERROR_ESQUEMA",
                "mensaje": f"Faltan columnas requeridas {FEATURES_IA}",
                "temperatura": None,
                "eco2": None,
                "tendencia": "DESCONOCIDA",
                "delta_ppm": 0.0,
                "comando_arduino": b"0\n",
            }

        if df.empty:
            return {
                "estado_ia": 1,
                "nivel_alerta": "SIN_DATOS",
                "mensaje": "Esperando primeras tramas del sensor",
                "temperatura": None,
                "eco2": None,
                "tendencia": "DESCONOCIDA",
                "delta_ppm": 0.0,
                "comando_arduino": b"0\n",
            }

        df_reciente = df.tail(150).copy()
        for col in FEATURES_IA:
            df_reciente[col] = pd.to_numeric(df_reciente[col], errors="coerce")

        ultima_temp = df_reciente["temperatura"].iloc[-1]
        ultimo_eco2 = df_reciente["eco2"].iloc[-1]

        if (
            pd.isna(ultima_temp)
            or pd.isna(ultimo_eco2)
            or ultima_temp < -40.0
            or ultima_temp > 85.0
            or ultimo_eco2 <= 0.0
            or ultimo_eco2 > 20000.0
        ):
            return {
                "estado_ia": -1,
                "nivel_alerta": "FALLO_HARDWARE",
                "mensaje": "Desconexión o lectura física fuera de rango",
                "temperatura": ultima_temp,
                "eco2": ultimo_eco2,
                "tendencia": "ERROR",
                "delta_ppm": 0.0,
                "comando_arduino": b"0\n",
            }

        df_limpio = df_reciente[FEATURES_IA].dropna().copy()

        if len(df_limpio) < 15:
            return {
                "estado_ia": 1,
                "nivel_alerta": "CALIBRANDO",
                "mensaje": f"Aprendiendo línea base de la zona ({len(df_limpio)}/15)",
                "temperatura": float(ultima_temp),
                "eco2": float(ultimo_eco2),
                "tendencia": "CALIBRANDO",
                "delta_ppm": 0.0,
                "comando_arduino": b"0\n",
            }

        matriz_features = df_limpio[FEATURES_IA].values
        modelo = IsolationForest(
            contamination=contamination, random_state=42, n_estimators=100
        )
        modelo.fit(matriz_features)

        estado_ia = int(modelo.predict(matriz_features)[-1])
        eco2_actual = float(ultimo_eco2)
        mediana_zona = float(df_limpio["eco2"].median())
        exceso_sobre_base = eco2_actual - mediana_zona

        info_tendencia = calcular_tendencia_eco2(df_limpio["eco2"])
        tendencia = info_tendencia["tendencia"]
        delta_ppm = info_tendencia["delta_ppm"]

        # Escala progresiva estándar relativa a la línea base de la zona + veredicto IA
        if exceso_sobre_base >= MARGEN_CRITICO_PPM:
            nivel = "CRITICO"
            comando = b"3\n"  # Pitido continuo
            mensaje = (
                f"CRÍTICO: {eco2_actual:.0f} ppm (+{exceso_sobre_base:.0f} sobre base {mediana_zona:.0f})"
            )
        elif exceso_sobre_base >= MARGEN_ALERTA_PPM and estado_ia == -1:
            nivel = "CRITICO"
            comando = b"2\n"  # Pulso rápido
            mensaje = (
                f"Anomalía alta: {eco2_actual:.0f} ppm (base {mediana_zona:.0f} ppm)"
            )
        elif exceso_sobre_base >= MARGEN_PRECAUCION_PPM or (
            estado_ia == -1 and exceso_sobre_base > 100.0
        ):
            nivel = "PRECAUCION"
            comando = b"1\n"  # Pulso lento
            mensaje = (
                f"Precaución: {eco2_actual:.0f} ppm (+{exceso_sobre_base:.0f} sobre base)"
            )
        else:
            nivel = "OPTIMO"
            comando = b"0\n"  # Silencio
            mensaje = (
                f"Patrón normal de la zona (base ~{mediana_zona:.0f} ppm)"
            )

        return {
            "estado_ia": estado_ia,
            "nivel_alerta": nivel,
            "mensaje": mensaje,
            "temperatura": float(ultima_temp),
            "eco2": eco2_actual,
            "tendencia": tendencia,
            "delta_ppm": delta_ppm,
            "comando_arduino": comando,
        }

    except Exception as error:
        return {
            "estado_ia": 1,
            "nivel_alerta": "ERROR_SISTEMA",
            "mensaje": str(error),
            "temperatura": None,
            "eco2": None,
            "tendencia": "DESCONOCIDA",
            "delta_ppm": 0.0,
            "comando_arduino": b"0\n",
        }


def evaluar_anomalia(
    ruta_csv: str = RUTA_CSV_DEFAULT, contamination: float = 0.05
) -> int:
    """Devuelve 1 si la última lectura coincide con el patrón de la zona o -1 si es anómala."""
    return obtener_diagnostico_completo(ruta_csv, contamination)["estado_ia"]


def generar_datos_prueba(
    ruta_destino: str = RUTA_CSV_DEFAULT,
    cantidad_filas: int = 150,
    forzar_anomalia_final: bool = False,
) -> None:
    """Genera lecturas sintéticas respetando el esquema de 6 columnas del proyecto."""
    os.makedirs(os.path.dirname(ruta_destino), exist_ok=True)
    np.random.seed(42)
    ahora = datetime.now()

    timestamps, temperaturas, humedades, presiones, eco2_vals, tvoc_vals = (
        [],
        [],
        [],
        [],
        [],
        [],
    )

    for i in range(cantidad_filas):
        tiempo = ahora - timedelta(seconds=(cantidad_filas - i))
        timestamps.append(tiempo.strftime("%Y-%m-%d %H:%M:%S"))

        temp = np.random.normal(loc=32.0, scale=0.3)
        hum = np.random.normal(loc=60.6, scale=1.0)
        pres = np.random.normal(loc=998.2, scale=0.4)

        eco2 = float(np.clip(np.random.normal(loc=850.0, scale=40.0), 750.0, 950.0))
        tvoc = float(max(0.0, round((eco2 - 400.0) * 0.16 + np.random.normal(0, 3), 0)))

        temperaturas.append(round(float(temp), 2))
        humedades.append(round(float(hum), 2))
        presiones.append(round(float(pres), 2))
        eco2_vals.append(round(eco2, 0))
        tvoc_vals.append(tvoc)

    if forzar_anomalia_final and cantidad_filas >= 1:
        eco2_vals[-1] = 2400.0
        tvoc_vals[-1] = 320.0

    df_muestra = pd.DataFrame(
        {
            "timestamp": timestamps,
            "temperatura": temperaturas,
            "humedad": humedades,
            "presion": presiones,
            "eco2": eco2_vals,
            "tvoc": tvoc_vals,
        }
    )
    df_muestra.to_csv(ruta_destino, index=False)


if __name__ == "__main__":
    generar_datos_prueba(RUTA_CSV_DEFAULT, cantidad_filas=150, forzar_anomalia_final=False)
    assert evaluar_anomalia(RUTA_CSV_DEFAULT) == 1, "Fallo en Test 1 (Línea base de 850 ppm)"

    generar_datos_prueba(RUTA_CSV_DEFAULT, cantidad_filas=150, forzar_anomalia_final=True)
    assert evaluar_anomalia(RUTA_CSV_DEFAULT) == -1, "Fallo en Test 2 (Anomalía sostenida)"

    df_fallo = pd.read_csv(RUTA_CSV_DEFAULT)
    df_fallo.loc[df_fallo.index[-1], "eco2"] = -999.0
    df_fallo.to_csv(RUTA_CSV_DEFAULT, index=False)
    assert evaluar_anomalia(RUTA_CSV_DEFAULT) == -1, "Fallo en Test 3 (Fallo Hardware)"

    generar_datos_prueba(RUTA_CSV_DEFAULT, cantidad_filas=150, forzar_anomalia_final=False)
    diag = obtener_diagnostico_completo(RUTA_CSV_DEFAULT)
    print(f"[OK] Pruebas IA adaptativa superadas -> {diag['nivel_alerta']} | {diag['mensaje']}")

    with open(RUTA_CSV_DEFAULT, "w", encoding="utf-8", newline="") as f:
        f.write("timestamp,temperatura,humedad,presion,eco2,tvoc\n")