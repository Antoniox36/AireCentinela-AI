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
(específicamente 'temperatura' y 'pm25') y determinar de forma autónoma si
la última lectura registrada representa una condición NORMAL (1) o una
ANOMALÍA AMBIENTAL (-1).
=============================================================================
"""

import os
import pandas as pd
from sklearn.ensemble import IsolationForest


# Ruta por defecto al archivo CSV de datos ambientales
# Ubicado en la carpeta ../data/datos_ambientales.csv
RUTA_CSV_DEFAULT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "data", "datos_ambientales.csv")
)


def evaluar_anomalia(ruta_csv=RUTA_CSV_DEFAULT, contamination=0.05):
    """
    Evalúa la condición actual del aire utilizando el historial reciente.

    Parámetros:
    -----------
    ruta_csv : str
        Ruta absoluta o relativa al archivo CSV generado por el backend.
    contamination : float (default=0.05)
        Tasa de sensibilidad de la IA (proporción esperada de anomalías, ej. 5%).
        Si en la feria se generan muchas falsas alarmas, este valor puede reducirse.

    Retorno:
    --------
    int:
         1 -> Estado NORMAL (El aire se comporta según el patrón esperado).
        -1 -> ANOMALÍA DETECTADA (Lectura inusual o sospechosa en temperatura/polvo).
    """

    # 1. VERIFICACIÓN DE EXISTENCIA DEL ARCHIVO
    if not os.path.exists(ruta_csv):
        print(f"[IA Engine] Advertencia: No se encontró el archivo '{ruta_csv}'.")
        # Retorno seguro por defecto: normal (1) para no detener la interfaz
        return 1

    try:
        # 2. MANEJO Y PREPARACIÓN DE DATOS (Librería pandas)
        # Cargamos el archivo CSV en un DataFrame de pandas
        df = pd.read_csv(ruta_csv)

        # Validación: Comprobar que existen las columnas requeridas
        columnas_requeridas = ['temperatura', 'pm25']
        if not all(col in df.columns for col in columnas_requeridas):
            print(f"[IA Engine] Error: El archivo CSV no contiene las columnas necesarias {columnas_requeridas}.")
            return 1

        # Optimización de Memoria: Tomamos únicamente las últimas 150 filas
        df_reciente = df.tail(150)

        # Validación de volumen mínimo de datos para entrenar el modelo
        if len(df_reciente) < 10:
            print(f"[IA Engine] Datos insuficientes ({len(df_reciente)} filas). Se requieren al menos 10 filas.")
            return 1

        # Selección de Variables: Extraer ['temperatura', 'pm25'] como matriz de valores NumPy
        datos = df_reciente[columnas_requeridas].values

        # 3. IMPLEMENTACIÓN DEL MODELO (Librería scikit-learn)
        # Isolation Forest es un algoritmo NO SUPERVISADO.
        # Asume que las anomalías son pocas y con valores aislados.
        # random_state=42 asegura que los resultados sean reproducibles en la demostración.
        modelo = IsolationForest(
            contamination=contamination,
            random_state=42,
            n_estimators=100
        )

        # Entrenamiento: La IA analiza el historial reciente y aprende qué es "normal"
        modelo.fit(datos)

        # Predicción: Califica cada una de las filas (devuelve un array de 1 y -1)
        predicciones = modelo.predict(datos)

        # 4. EXTRACCIÓN DEL RETORNO MATEMÁTICO (El Entregable)
        # Tomamos el último elemento de la lista (índice [-1]), que corresponde a la lectura actual
        ultimo_estado = int(predicciones[-1])

        return ultimo_estado

    except Exception as e:
        print(f"[IA Engine] Excepción al procesar la IA: {e}")
        return 1


def generar_datos_prueba(ruta_destino=RUTA_CSV_DEFAULT, cantidad_filas=150, forzar_anomalia_final=False):
    """
    Genera un archivo CSV con lecturas ambientales sintéticas para pruebas.
    Cumple con el Paso 1 del README:
    "Samuel: Generar datos ficticios en data/datos_ambientales.csv y verificar motor_ia.py".

    Parámetros:
    -----------
    ruta_destino : str
        Ruta donde se guardará el archivo generado.
    cantidad_filas : int
        Número de filas a generar (por defecto 150 para llenar la ventana óptima).
    forzar_anomalia_final : bool
        Si es True, la última fila tendrá valores extremos para probar la detección de anomalía (-1).
    """
    import numpy as np
    from datetime import datetime, timedelta

    # Asegurar que la carpeta destino exista
    os.makedirs(os.path.dirname(ruta_destino), exist_ok=True)

    np.random.seed(42)
    ahora = datetime.now()

    timestamps = []
    temperaturas = []
    humedades = []
    pm25_vals = []
    pm10_vals = []

    # Generar lecturas normales representativas del clima de San Miguel (caluroso)
    # Temperatura típica: 30°C - 34°C
    # Humedad típica: 55% - 65%
    # PM2.5 típico: 12 - 25 µg/m³
    # PM10 típico: 20 - 45 µg/m³
    for i in range(cantidad_filas):
        tiempo = ahora - timedelta(seconds=(cantidad_filas - i) * 2)
        timestamps.append(tiempo.strftime("%Y-%m-%d %H:%M:%S"))

        # Fluctuaciones suaves
        temp = np.random.normal(loc=31.5, scale=1.2)
        hum = np.random.normal(loc=60.0, scale=3.0)
        # En condiciones normales, un leve incremento térmico correlaciona con más polvo en suspensión
        pm25 = np.random.normal(loc=18.0 + (temp - 30.0) * 1.5, scale=2.5)
        pm10 = pm25 * np.random.uniform(1.4, 1.8)

        temperaturas.append(round(temp, 2))
        humedades.append(round(hum, 2))
        pm25_vals.append(round(max(pm25, 2.0), 2))
        pm10_vals.append(round(max(pm10, 5.0), 2))

    # Si se solicita forzar una anomalía en la última lectura:
    if forzar_anomalia_final and cantidad_filas > 0:
        # Por ejemplo: Temperatura baja repentinamente (20°C) pero polvo se dispara (120 µg/m³),
        # un desacoplamiento drástico del patrón aprendido
        temperaturas[-1] = 19.5
        pm25_vals[-1] = 135.0
        pm10_vals[-1] = 210.0

    df_muestra = pd.DataFrame({
        'timestamp': timestamps,
        'temperatura': temperaturas,
        'humedad': humedades,
        'pm25': pm25_vals,
        'pm10': pm10_vals
    })

    df_muestra.to_csv(ruta_destino, index=False)
    print(f"[IA Engine] Archivo de prueba generado exitosamente en: {ruta_destino} ({len(df_muestra)} filas)")


# Bloque de ejecución directa para pruebas de Samuel
if __name__ == "__main__":
    print("=" * 65)
    print(">> EJECUCION DE PRUEBAS DEL MOTOR DE IA -- AIRECENTINELA AI <<")
    print("=" * 65)

    # 1. Comprobar si existe el archivo CSV; si no existe, generarlo
    if not os.path.exists(RUTA_CSV_DEFAULT):
        print("\n[Paso 1] No se encontro 'datos_ambientales.csv'. Generando muestra normal...")
        generar_datos_prueba(RUTA_CSV_DEFAULT, cantidad_filas=150, forzar_anomalia_final=False)

    # 2. Prueba con lecturas normales
    print("\n--- TEST 1: Evaluacion con datos en rango normal ---")
    resultado = evaluar_anomalia(RUTA_CSV_DEFAULT)
    print(f"Resultado obtenido: {resultado}")
    if resultado == 1:
        print("[OK] Diagnostico: ESTADO NORMAL (1). El aire se comporta dentro de lo esperado.")
    else:
        print("[ALERTA] Diagnostico: ANOMALIA DETECTADA (-1).")

    # 3. Prueba forzando una anomalía en la última lectura
    print("\n--- TEST 2: Inyectando anomalia ambiental en la ultima lectura ---")
    generar_datos_prueba(RUTA_CSV_DEFAULT, cantidad_filas=150, forzar_anomalia_final=True)
    resultado_anomalia = evaluar_anomalia(RUTA_CSV_DEFAULT)
    print(f"Resultado obtenido: {resultado_anomalia}")
    if resultado_anomalia == -1:
        print("[OK] Diagnostico: ANOMALIA DETECTADA CON EXITO! (-1). La IA detecto la condicion atipica.")
    else:
        print("[INFO] Diagnostico: Clasificado como normal (1).")

    # 4. Restaurar a datos normales para dejar el sistema listo para Fredy y Gabriel
    print("\n--- Restaurando archivo de datos a condicion normal estandar ---")
    generar_datos_prueba(RUTA_CSV_DEFAULT, cantidad_filas=150, forzar_anomalia_final=False)

    print("\n" + "=" * 65)
    print("[OK] TODAS LAS PRUEBAS COMPLETADAS EXITOSAMENTE")
    print("El modulo 'ia_engine/motor_ia.py' esta listo para ser consumido por Fredy.")
    print("=" * 65)
