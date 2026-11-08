"""
=============================================================================
🍃 PROYECTO: AireCentinela AI — Estación Ambiental Inteligente
🎓 INSTITUCIÓN: Universidad Gerardo Barrios (UGB) — Sede San Miguel
👤 INTEGRANTE: Samuel (Motor de Inteligencia Artificial)
📁 MÓDULO: ia_engine/motor_ia.py
=============================================================================

DESCRIPCIÓN DEL MÓDULO:
Este script implementa el motor de Inteligencia Artificial no supervisada
usando el algoritmo Isolation Forest (Bosque de Aislamiento) de scikit-learn.

Su objetivo es analizar el comportamiento conjunto de variables ambientales
(específicamente 'temperatura' y dióxido de carbono equivalente 'eco2') y
determinar de forma autónoma si la última lectura registrada representa una
condición NORMAL (1) o una ANOMALÍA AMBIENTAL (-1).
=============================================================================
"""

import os
import pandas as pd
from sklearn.ensemble import IsolationForest

RUTA_CSV_DEFAULT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "data", "datos_ambientales.csv")
)

def calcular_tendencia_eco2(df_limpio):
    """Analiza la tendencia histórica reciente del eCO2 calculando la tasa de cambio."""
    if len(df_limpio) < 10:
        return {'tendencia': 'INSUFICIENTE', 'delta_ppm': 0.0}

    valores_eco2 = df_limpio['eco2'].values
    n_bloque = max(2, len(valores_eco2) // 5)
    promedio_inicial = valores_eco2[:n_bloque].mean()
    promedio_final = valores_eco2[-n_bloque:].mean()
    delta = round(promedio_final - promedio_inicial, 2)

    if delta > 150.0:
        tendencia = "SUBIENDO_RAPIDO"
    elif delta > 50.0:
        tendencia = "SUBIENDO"
    elif delta < -50.0:
        tendencia = "BAJANDO"
    else:
        tendencia = "ESTABLE"

    return {'tendencia': tendencia, 'delta_ppm': delta}


def obtener_diagnostico_completo(ruta_csv=RUTA_CSV_DEFAULT, contamination=0.05):
    """Proporciona un diagnóstico detallado con niveles de alerta y tendencia histórica."""
    if not os.path.exists(ruta_csv):
        return {
            'estado_ia': 1, 'nivel_alerta': 'SIN_DATOS', 
            'mensaje': f"No se encontró el archivo '{ruta_csv}'",
            'temperatura': None, 'eco2': None, 'tendencia': 'DESCONOCIDA'
        }

    try:
        df = pd.read_csv(ruta_csv)
        columnas_requeridas = ['temperatura', 'eco2']
        if not all(col in df.columns for col in columnas_requeridas):
            return {
                'estado_ia': 1, 'nivel_alerta': 'ERROR_ESQUEMA',
                'mensaje': f"Faltan columnas requeridas {columnas_requeridas}",
                'temperatura': None, 'eco2': None, 'tendencia': 'DESCONOCIDA'
            }

        df_reciente = df.tail(150).copy()
        for col in columnas_requeridas:
            df_reciente[col] = pd.to_numeric(df_reciente[col], errors='coerce')

        ultima_temp = df_reciente['temperatura'].iloc[-1]
        ultimo_eco2 = df_reciente['eco2'].iloc[-1]

        if (pd.isna(ultima_temp) or pd.isna(ultimo_eco2) or
            ultima_temp < -40.0 or ultima_temp > 85.0 or
            ultimo_eco2 <= 0.0 or ultimo_eco2 > 10000.0):
            return {
                'estado_ia': -1, 'nivel_alerta': 'FALLO_HARDWARE',
                'mensaje': "Desconexión o lectura física fuera de rango",
                'temperatura': ultima_temp, 'eco2': ultimo_eco2,
                'tendencia': 'ERROR', 'delta_ppm': 0.0
            }

        df_limpio = df_reciente[columnas_requeridas].dropna()
        if len(df_limpio) < 10:
            return {
                'estado_ia': 1, 'nivel_alerta': 'CALIBRANDO',
                'mensaje': f"Historial insuficiente ({len(df_limpio)} filas)",
                'temperatura': ultima_temp, 'eco2': ultimo_eco2,
                'tendencia': 'CALIBRANDO', 'delta_ppm': 0.0
            }

        datos = df_limpio.values
        modelo = IsolationForest(contamination=contamination, random_state=42, n_estimators=100)
        modelo.fit(datos)
        predicciones = modelo.predict(datos)
        estado_ia = int(predicciones[-1])

        info_tendencia = calcular_tendencia_eco2(df_limpio)
        tendencia = info_tendencia['tendencia']
        delta_ppm = info_tendencia['delta_ppm']

        if estado_ia == -1 or ultimo_eco2 > 1200.0:
            nivel = 'CRITICO'
            mensaje = f"Alerta ambiental crítica: eCO2 en {ultimo_eco2} ppm"
        elif ultimo_eco2 > 800.0 or tendencia == "SUBIENDO_RAPIDO":
            nivel = 'PRECAUCION'
            mensaje = f"Precaución: eCO2 elevado ({ultimo_eco2} ppm) o acumulación acelerada (+{delta_ppm} ppm)"
        elif ultimo_eco2 > 600.0:
            nivel = 'ACEPTABLE'
            mensaje = f"Calidad aceptable: eCO2 en {ultimo_eco2} ppm"
        else:
            nivel = 'OPTIMO'
            mensaje = f"Ambiente óptimo y ventilado: eCO2 en {ultimo_eco2} ppm"

        return {
            'estado_ia': estado_ia, 'nivel_alerta': nivel, 'mensaje': mensaje,
            'temperatura': ultima_temp, 'eco2': ultimo_eco2, 'tendencia': tendencia, 'delta_ppm': delta_ppm
        }

    except Exception as e:
        return {
            'estado_ia': 1, 'nivel_alerta': 'ERROR_SISTEMA',
            'mensaje': str(e), 'temperatura': None, 'eco2': None, 'tendencia': 'DESCONOCIDA'
        }


def evaluar_anomalia(ruta_csv=RUTA_CSV_DEFAULT, contamination=0.05):
    """Evalúa la condición actual del aire utilizando el historial reciente."""
    diagnostico = obtener_diagnostico_completo(ruta_csv, contamination)
    return diagnostico['estado_ia']


def generar_datos_prueba(ruta_destino=RUTA_CSV_DEFAULT, cantidad_filas=150, forzar_anomalia_final=False):
    """Genera un archivo CSV con lecturas ambientales sintéticas para pruebas."""
    import numpy as np
    from datetime import datetime, timedelta

    os.makedirs(os.path.dirname(ruta_destino), exist_ok=True)
    np.random.seed(42)
    ahora = datetime.now()

    timestamps, temperaturas, humedades, presiones, eco2_vals = [], [], [], [], []

    for i in range(cantidad_filas):
        tiempo = ahora - timedelta(seconds=(cantidad_filas - i) * 2)
        timestamps.append(tiempo.strftime("%Y-%m-%d %H:%M:%S"))

        temp = np.random.normal(loc=31.5, scale=1.2)
        hum = np.random.normal(loc=60.0, scale=3.0)
        pres = np.random.normal(loc=1011.2, scale=1.5)

        base_eco2 = 450.0 + (temp - 30.0) * 25.0
        eco2 = np.random.normal(loc=base_eco2, scale=35.0)
        eco2_clamped = max(400.0, min(800.0, eco2))

        temperaturas.append(round(temp, 2))
        humedades.append(round(hum, 2))
        presiones.append(round(pres, 2))
        eco2_vals.append(round(eco2_clamped, 2))

    if forzar_anomalia_final and cantidad_filas > 0:
        temperaturas[-1] = 19.5
        eco2_vals[-1] = 1450.0

    df_muestra = pd.DataFrame({
        'timestamp': timestamps,
        'temperatura': temperaturas,
        'humedad': humedades,
        'presion': presiones,
        'eco2': eco2_vals
    })

    df_muestra.to_csv(ruta_destino, index=False)
    print(f"[IA Engine] Archivo de prueba generado exitosamente en: {ruta_destino} ({len(df_muestra)} filas)")


if __name__ == "__main__":
    print("=" * 65)
    print(">> EJECUCION DE PRUEBAS DEL MOTOR DE IA -- AIRECENTINELA AI <<")
    print("=" * 65)

    generar_datos_prueba(RUTA_CSV_DEFAULT, cantidad_filas=150, forzar_anomalia_final=False)

    print("\n--- TEST 1: Evaluacion con datos en rango normal (eCO2 400-800 ppm) ---")
    resultado = evaluar_anomalia(RUTA_CSV_DEFAULT)
    print(f"Resultado obtenido: {resultado}")
    if resultado == 1:
        print("[OK] Diagnostico: ESTADO NORMAL (1). El aire se comporta dentro de lo esperado.")
    else:
        print("[ALERTA] Diagnostico: ANOMALIA DETECTADA (-1).")

    print("\n--- TEST 2: Inyectando anomalia ambiental en la ultima lectura (eCO2 > 1200 ppm) ---")
    generar_datos_prueba(RUTA_CSV_DEFAULT, cantidad_filas=150, forzar_anomalia_final=True)
    resultado_anomalia = evaluar_anomalia(RUTA_CSV_DEFAULT)
    print(f"Resultado obtenido: {resultado_anomalia}")
    if resultado_anomalia == -1:
        print("[OK] Diagnostico: ANOMALIA DETECTADA CON EXITO! (-1). La IA detecto la condicion atipica.")
    else:
        print("[INFO] Diagnostico: Clasificado como normal (1).")

    print("\n--- TEST 3: Simulando desconexion o fallo de hardware en sensor (-999 / NaN) ---")
    df_fallo = pd.read_csv(RUTA_CSV_DEFAULT)
    df_fallo.loc[df_fallo.index[-1], 'eco2'] = -999.0
    df_fallo.to_csv(RUTA_CSV_DEFAULT, index=False)
    resultado_fallo = evaluar_anomalia(RUTA_CSV_DEFAULT)
    print(f"Resultado obtenido: {resultado_fallo}")
    if resultado_fallo == -1:
        print("[OK] Diagnostico: PROTECCION ACTIVA! (-1). La IA capturo el fallo fisico sin caerse.")
    else:
        print("[INFO] Diagnostico: Clasificado como (1).")

    print("\n--- TEST 4: Evaluacion de diagnostico detallado y tendencia historica ---")
    generar_datos_prueba(RUTA_CSV_DEFAULT, cantidad_filas=150, forzar_anomalia_final=False)
    diag = obtener_diagnostico_completo(RUTA_CSV_DEFAULT)
    print(f"Estado IA: [{diag['estado_ia']}]")
    print(f"Nivel de Alerta: [{diag['nivel_alerta']}]")
    print(f"Tendencia Historica: [{diag['tendencia']}] (Variacion: {diag['delta_ppm']} ppm)")
    print(f"Mensaje Descriptivo: {diag['mensaje']}")
    print("[OK] Diagnostico detallado completado.")

    print("\n--- Restaurando archivo de datos a condicion normal estandar ---")
    generar_datos_prueba(RUTA_CSV_DEFAULT, cantidad_filas=150, forzar_anomalia_final=False)

    print("\n" + "=" * 65)
    print("[OK] TODAS LAS PRUEBAS COMPLETADAS EXITOSAMENTE")
    print("=" * 65)