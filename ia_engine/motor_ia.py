"""Motor de Inteligencia Artificial no supervisada (Isolation Forest) para AireCentinela AI."""

import os
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

RUTA_CSV_DEFAULT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "data", "datos_ambientales.csv")
)


def calcular_tendencia_eco2(df_limpio: pd.DataFrame) -> dict:
    """Calcula la variación de eCO2 entre el inicio y el final de la ventana reciente."""
    if len(df_limpio) < 10:
        return {"tendencia": "INSUFICIENTE", "delta_ppm": 0.0}

    valores_eco2 = df_limpio["eco2"].values
    n_bloque = max(2, len(valores_eco2) // 5)
    promedio_inicial = valores_eco2[:n_bloque].mean()
    promedio_final = valores_eco2[-n_bloque:].mean()
    delta = round(float(promedio_final - promedio_inicial), 2)

    if delta > 150.0:
        tendencia = "SUBIENDO_RAPIDO"
    elif delta > 50.0:
        tendencia = "SUBIENDO"
    elif delta < -50.0:
        tendencia = "BAJANDO"
    else:
        tendencia = "ESTABLE"

    return {"tendencia": tendencia, "delta_ppm": delta}


def obtener_diagnostico_completo(
    ruta_csv: str = RUTA_CSV_DEFAULT, contamination: float = 0.03
) -> dict:
    """Evalúa la última lectura con Isolation Forest y devuelve nivel de alerta y tendencia."""
    if not os.path.exists(ruta_csv):
        return {
            "estado_ia": 1,
            "nivel_alerta": "SIN_DATOS",
            "mensaje": f"No se encontró el archivo '{ruta_csv}'",
            "temperatura": None,
            "eco2": None,
            "tendencia": "DESCONOCIDA",
            "delta_ppm": 0.0,
        }

    try:
        df = pd.read_csv(ruta_csv)
        columnas_requeridas = ["temperatura", "eco2"]
        if not all(col in df.columns for col in columnas_requeridas):
            return {
                "estado_ia": 1,
                "nivel_alerta": "ERROR_ESQUEMA",
                "mensaje": f"Faltan columnas requeridas {columnas_requeridas}",
                "temperatura": None,
                "eco2": None,
                "tendencia": "DESCONOCIDA",
                "delta_ppm": 0.0,
            }

        if df.empty:
            return {
                "estado_ia": 1,
                "nivel_alerta": "SIN_DATOS",
                "mensaje": "El archivo CSV aún no contiene lecturas",
                "temperatura": None,
                "eco2": None,
                "tendencia": "DESCONOCIDA",
                "delta_ppm": 0.0,
            }

        df_reciente = df.tail(150).copy()
        for col in columnas_requeridas:
            df_reciente[col] = pd.to_numeric(df_reciente[col], errors="coerce")

        ultima_temp = df_reciente["temperatura"].iloc[-1]
        ultimo_eco2 = df_reciente["eco2"].iloc[-1]

        if (
            pd.isna(ultima_temp)
            or pd.isna(ultimo_eco2)
            or ultima_temp < -40.0
            or ultima_temp > 85.0
            or ultimo_eco2 <= 0.0
            or ultimo_eco2 > 10000.0
        ):
            return {
                "estado_ia": -1,
                "nivel_alerta": "FALLO_HARDWARE",
                "mensaje": "Desconexión o lectura física fuera de rango",
                "temperatura": ultima_temp,
                "eco2": ultimo_eco2,
                "tendencia": "ERROR",
                "delta_ppm": 0.0,
            }

        df_limpio = df_reciente[columnas_requeridas].dropna()
        if len(df_limpio) < 10:
            return {
                "estado_ia": 1,
                "nivel_alerta": "CALIBRANDO",
                "mensaje": f"Calibrando modelo ({len(df_limpio)}/10 lecturas)",
                "temperatura": float(ultima_temp),
                "eco2": float(ultimo_eco2),
                "tendencia": "CALIBRANDO",
                "delta_ppm": 0.0,
            }

        datos = df_limpio.values
        modelo = IsolationForest(
            contamination=contamination, random_state=42, n_estimators=100
        )
        modelo.fit(datos)
        estado_ia = int(modelo.predict(datos)[-1])

        info_tendencia = calcular_tendencia_eco2(df_limpio)
        tendencia = info_tendencia["tendencia"]
        delta_ppm = info_tendencia["delta_ppm"]

        if ultimo_eco2 > 1000.0 or (estado_ia == -1 and ultimo_eco2 > 800.0):
            nivel = "CRITICO"
            mensaje = f"Alerta ambiental crítica: eCO2 en {ultimo_eco2:.0f} ppm"
        elif (
            ultimo_eco2 > 750.0
            or tendencia == "SUBIENDO_RAPIDO"
            or (estado_ia == -1 and ultimo_eco2 > 550.0)
        ):
            nivel = "PRECAUCION"
            mensaje = (
                f"Precaución: variación atípica o acumulación ({ultimo_eco2:.0f} ppm)"
            )
        elif ultimo_eco2 > 600.0:
            nivel = "ACEPTABLE"
            mensaje = f"Calidad aceptable: eCO2 en {ultimo_eco2:.0f} ppm"
        else:
            nivel = "OPTIMO"
            mensaje = f"Ambiente óptimo y ventilado: eCO2 en {ultimo_eco2:.0f} ppm"

        return {
            "estado_ia": estado_ia,
            "nivel_alerta": nivel,
            "mensaje": mensaje,
            "temperatura": float(ultima_temp),
            "eco2": float(ultimo_eco2),
            "tendencia": tendencia,
            "delta_ppm": delta_ppm,
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
        }


def evaluar_anomalia(
    ruta_csv: str = RUTA_CSV_DEFAULT, contamination: float = 0.03
) -> int:
    """Devuelve 1 si la última lectura es normal o -1 si es anómala."""
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

        temp = np.random.normal(loc=31.0, scale=0.8)
        hum = np.random.normal(loc=63.0, scale=2.5)
        pres = np.random.normal(loc=999.0, scale=1.0)

        base_eco2 = 430.0 + (temp - 30.0) * 20.0
        eco2 = float(np.clip(np.random.normal(loc=base_eco2, scale=25.0), 400.0, 800.0))
        tvoc = float(max(0.0, round((eco2 - 400.0) * 0.15 + np.random.normal(0, 2), 0)))

        temperaturas.append(round(float(temp), 2))
        humedades.append(round(float(hum), 2))
        presiones.append(round(float(pres), 2))
        eco2_vals.append(round(eco2, 0))
        tvoc_vals.append(tvoc)

    if forzar_anomalia_final and cantidad_filas > 0:
        temperaturas[-1] = 21.0
        eco2_vals[-1] = 1450.0
        tvoc_vals[-1] = 185.0

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
    assert evaluar_anomalia(RUTA_CSV_DEFAULT) == 1, "Fallo en Test 1 (Normal)"

    generar_datos_prueba(RUTA_CSV_DEFAULT, cantidad_filas=150, forzar_anomalia_final=True)
    assert evaluar_anomalia(RUTA_CSV_DEFAULT) == -1, "Fallo en Test 2 (Anomalía)"

    df_fallo = pd.read_csv(RUTA_CSV_DEFAULT)
    df_fallo.loc[df_fallo.index[-1], "eco2"] = -999.0
    df_fallo.to_csv(RUTA_CSV_DEFAULT, index=False)
    assert evaluar_anomalia(RUTA_CSV_DEFAULT) == -1, "Fallo en Test 3 (Fallo Hardware)"

    generar_datos_prueba(RUTA_CSV_DEFAULT, cantidad_filas=150, forzar_anomalia_final=False)
    diag = obtener_diagnostico_completo(RUTA_CSV_DEFAULT)
    print(f"[OK] Pruebas IA superadas -> Estado: {diag['nivel_alerta']} | {diag['mensaje']}")

    with open(RUTA_CSV_DEFAULT, "w", encoding="utf-8", newline="") as f:
        f.write("timestamp,temperatura,humedad,presion,eco2,tvoc\n")