"""Motor de Inteligencia Artificial no supervisada (Isolation Forest) para Aire Centinela AI."""

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

PERFILES_USO = ("Oficina / Escuela", "Agricultura / Cultivo", "Hogar / Salud")


def interpretar_variables(
    temp: float, hum: float, pres: float, eco2: float, tvoc: float
) -> dict[str, str]:
    """Traduce cada magnitud física a una explicación clara para cualquier usuario."""
    if temp < 20.0:
        txt_temp = "Ambiente fresco · Baja carga térmica"
    elif temp <= 28.0:
        txt_temp = "Confort térmico ideal para personas y equipos"
    elif temp <= 33.0:
        txt_temp = "Ambiente cálido · Conviene ventilación cruzada"
    else:
        txt_temp = "Estrés térmico alto · Riesgo de fatiga o deshidratación"

    if hum <= 0.5:
        txt_hum = "Sensor en modo presión/temperatura (sin lectura RH)"
    elif hum < 35.0:
        txt_hum = "Aire muy seco · Puede irritar vías respiratorias"
    elif hum <= 65.0:
        txt_hum = "Humedad equilibrada · Rango saludable (35–65 %)"
    elif hum <= 80.0:
        txt_hum = "Humedad elevada · Sensación bochornosa"
    else:
        txt_hum = "Humedad crítica · Riesgo de condensación y hongos"

    if pres < 990.0:
        txt_pres = "Baja presión relativa · Posible inestabilidad climática"
    elif pres <= 1018.0:
        txt_pres = "Presión atmosférica estable · Sin cambios bruscos"
    else:
        txt_pres = "Alta presión atmosférica · Tiempo despejado y estable"

    if eco2 < 650.0:
        txt_eco2 = "Aire limpio y bien oxigenado (< 650 ppm)"
    elif eco2 < 1000.0:
        txt_eco2 = "Concentración moderada · Aire interior aceptable"
    elif eco2 < 1500.0:
        txt_eco2 = "Aire viciado · Reduce concentración y produce somnolencia"
    else:
        txt_eco2 = "Acumulación crítica de CO2 · Ventilar de inmediato"

    if tvoc < 50.0:
        txt_tvoc = "Aire puro · Libre de compuestos volátiles o humo"
    elif tvoc < 220.0:
        txt_tvoc = "Presencia leve de vapores, perfumes o limpieza"
    else:
        txt_tvoc = "Alta carga química/humo · Posible irritación"

    return {
        "temperatura": txt_temp,
        "humedad": txt_hum,
        "presion": txt_pres,
        "eco2": txt_eco2,
        "tvoc": txt_tvoc,
    }


def generar_consejos_por_perfil(
    temp: float, hum: float, pres: float, eco2: float, tvoc: float, nivel: str
) -> dict[str, dict[str, str]]:
    """Genera diagnósticos y recomendaciones adaptadas a cada sector productivo o cotidiano."""
    # 1. Perfil Oficina / Escuela
    if eco2 >= 1000.0 or nivel == "CRITICO":
        titulo_edu = "Alerta de Fatiga Cognitiva"
        detalle_edu = (
            f"Con {eco2:.0f} ppm de eCO2 la atención y retención caen hasta un 15 %. "
            "Abra puertas o active extracción durante 5 minutos."
        )
    elif eco2 >= 750.0 or nivel == "PRECAUCION":
        titulo_edu = "Ventilación Preventiva Recomendada"
        detalle_edu = (
            f"El CO2 empieza a acumularse ({eco2:.0f} ppm) a {temp:.1f} °C. "
            "Permita circulación de aire antes de que afecte el rendimiento."
        )
    else:
        titulo_edu = "Entorno Óptimo para Aprendizaje y Trabajo"
        detalle_edu = (
            f"Calidad de aire limpia ({eco2:.0f} ppm) y TVOC controlado ({tvoc:.0f} ppb). "
            "Condiciones ideales para concentración continua."
        )

    # 2. Perfil Agricultura / Cultivo (Invernadero o bodega agrícola)
    if hum > 78.0:
        titulo_agro = "Riesgo Fitosanitario por Humedad Alta"
        detalle_agro = (
            f"Humedad del {hum:.1f} % con {temp:.1f} °C favorece hongos foliares (mildiu/botritis). "
            "Incremente ventilación y reduzca riego foliar."
        )
    elif temp > 33.0 and (hum > 0.5 and hum < 45.0):
        titulo_agro = "Estrés Hídrico y Déficit de Presión de Vapor"
        detalle_agro = (
            f"Calor alto ({temp:.1f} °C) y aire seco ({hum:.1f} %) cierran estomas y frenan el crecimiento. "
            "Active nebulización o sombreado."
        )
    elif eco2 >= 600.0 and eco2 <= 1300.0:
        titulo_agro = "Microclima Favorable para Fotosíntesis"
        detalle_agro = (
            f"Nivel de CO2 ({eco2:.0f} ppm) y presión ({pres:.1f} hPa) estimulan actividad fotosintética "
            "sin estrés térmico severo."
        )
    else:
        titulo_agro = "Condiciones Agronómicas Estables"
        detalle_agro = (
            f"Temperatura ({temp:.1f} °C) y atmósfera ({pres:.1f} hPa) dentro de parámetros seguros "
            "para cultivo protegido o almacenamiento de granos."
        )

    # 3. Perfil Hogar / Salud Respiratoria
    if tvoc >= 180.0 or nivel == "CRITICO":
        titulo_hogar = "Presencia de Gases o Vapores Irritantes"
        detalle_hogar = (
            f"TVOC elevado ({tvoc:.0f} ppb) y eCO2 en {eco2:.0f} ppm. "
            "Puede deberse a humo de cocina, aerosoles o falta de aire fresco; ventile la habitación."
        )
    elif eco2 >= 800.0 or nivel == "PRECAUCION":
        titulo_hogar = "Renovación de Aire Sugerida"
        detalle_hogar = (
            f"El aire interior supera la línea base habitual ({eco2:.0f} ppm). "
            "Ventilar mejora el descanso y reduce dolor de cabeza."
        )
    else:
        titulo_hogar = "Aire Interior Saludable y Seguro"
        detalle_hogar = (
            f"Sin acumulación de gases ({eco2:.0f} ppm) ni compuestos volátiles ({tvoc:.0f} ppb). "
            "Ambiente apto para niños, adultos mayores y personas sensibles."
        )

    return {
        "Oficina / Escuela": {"titulo": titulo_edu, "detalle": detalle_edu},
        "Agricultura / Cultivo": {"titulo": titulo_agro, "detalle": detalle_agro},
        "Hogar / Salud": {"titulo": titulo_hogar, "detalle": detalle_hogar},
    }


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
    respuesta_base = {
        "estado_ia": 1,
        "nivel_alerta": "SIN_DATOS",
        "mensaje": "Esperando primeras tramas del sensor",
        "temperatura": None,
        "humedad": None,
        "presion": None,
        "eco2": None,
        "tvoc": None,
        "base_eco2": 450.0,
        "limite_normal_eco2": 650.0,
        "tendencia": "DESCONOCIDA",
        "delta_ppm": 0.0,
        "comando_arduino": b"0\n",
        "interpretaciones": {},
        "perfiles": {},
        "muestras_analizadas": 0,
    }

    if not os.path.exists(ruta_csv):
        respuesta_base["mensaje"] = f"No se encontró el archivo '{ruta_csv}'"
        return respuesta_base

    try:
        df = pd.read_csv(ruta_csv)
        if not all(col in df.columns for col in FEATURES_IA):
            respuesta_base["nivel_alerta"] = "ERROR_ESQUEMA"
            respuesta_base["mensaje"] = f"Faltan columnas requeridas {FEATURES_IA}"
            return respuesta_base

        if df.empty:
            return respuesta_base

        df_reciente = df.tail(150).copy()
        for col in FEATURES_IA:
            df_reciente[col] = pd.to_numeric(df_reciente[col], errors="coerce")

        ultima_temp = df_reciente["temperatura"].iloc[-1]
        ultima_hum = df_reciente["humedad"].iloc[-1]
        ultima_pres = df_reciente["presion"].iloc[-1]
        ultimo_eco2 = df_reciente["eco2"].iloc[-1]
        ultimo_tvoc = df_reciente["tvoc"].iloc[-1]

        if (
            pd.isna(ultima_temp)
            or pd.isna(ultimo_eco2)
            or ultima_temp < -40.0
            or ultima_temp > 85.0
            or ultimo_eco2 <= 0.0
            or ultimo_eco2 > 20000.0
        ):
            respuesta_base.update(
                {
                    "estado_ia": -1,
                    "nivel_alerta": "FALLO_HARDWARE",
                    "mensaje": "Desconexión o lectura física fuera de rango",
                    "temperatura": ultima_temp,
                    "eco2": ultimo_eco2,
                    "tendencia": "ERROR",
                }
            )
            return respuesta_base

        temp_f = float(ultima_temp)
        hum_f = float(ultima_hum) if not pd.isna(ultima_hum) else 0.0
        pres_f = float(ultima_pres) if not pd.isna(ultima_pres) else 1013.25
        eco2_f = float(ultimo_eco2)
        tvoc_f = float(ultimo_tvoc) if not pd.isna(ultimo_tvoc) else 0.0

        interpretaciones = interpretar_variables(temp_f, hum_f, pres_f, eco2_f, tvoc_f)
        df_limpio = df_reciente[FEATURES_IA].dropna().copy()
        n_muestras = len(df_limpio)

        if n_muestras < 15:
            perfiles = generar_consejos_por_perfil(
                temp_f, hum_f, pres_f, eco2_f, tvoc_f, "CALIBRANDO"
            )
            return {
                "estado_ia": 1,
                "nivel_alerta": "CALIBRANDO",
                "mensaje": f"Aprendiendo línea base de la zona ({n_muestras}/15)",
                "temperatura": temp_f,
                "humedad": hum_f,
                "presion": pres_f,
                "eco2": eco2_f,
                "tvoc": tvoc_f,
                "base_eco2": eco2_f,
                "limite_normal_eco2": eco2_f + MARGEN_PRECAUCION_PPM,
                "tendencia": "CALIBRANDO",
                "delta_ppm": 0.0,
                "comando_arduino": b"0\n",
                "interpretaciones": interpretaciones,
                "perfiles": perfiles,
                "muestras_analizadas": n_muestras,
            }

        matriz_features = df_limpio[FEATURES_IA].values
        modelo = IsolationForest(
            contamination=contamination, random_state=42, n_estimators=100
        )
        modelo.fit(matriz_features)

        estado_ia = int(modelo.predict(matriz_features)[-1])
        mediana_zona = float(df_limpio["eco2"].median())
        exceso_sobre_base = eco2_f - mediana_zona

        info_tendencia = calcular_tendencia_eco2(df_limpio["eco2"])
        tendencia = info_tendencia["tendencia"]
        delta_ppm = info_tendencia["delta_ppm"]

        if exceso_sobre_base >= MARGEN_CRITICO_PPM:
            nivel = "CRITICO"
            comando = b"3\n"
            mensaje = (
                f"CRÍTICO: {eco2_f:.0f} ppm (+{exceso_sobre_base:.0f} sobre base {mediana_zona:.0f})"
            )
        elif exceso_sobre_base >= MARGEN_ALERTA_PPM and estado_ia == -1:
            nivel = "CRITICO"
            comando = b"2\n"
            mensaje = (
                f"Anomalía alta: {eco2_f:.0f} ppm (base {mediana_zona:.0f} ppm)"
            )
        elif exceso_sobre_base >= MARGEN_PRECAUCION_PPM or (
            estado_ia == -1 and exceso_sobre_base > 100.0
        ):
            nivel = "PRECAUCION"
            comando = b"1\n"
            mensaje = (
                f"Precaución: {eco2_f:.0f} ppm (+{exceso_sobre_base:.0f} sobre base)"
            )
        else:
            nivel = "OPTIMO"
            comando = b"0\n"
            mensaje = (
                f"Patrón normal de la zona (base ~{mediana_zona:.0f} ppm)"
            )

        perfiles = generar_consejos_por_perfil(
            temp_f, hum_f, pres_f, eco2_f, tvoc_f, nivel
        )

        return {
            "estado_ia": estado_ia,
            "nivel_alerta": nivel,
            "mensaje": mensaje,
            "temperatura": temp_f,
            "humedad": hum_f,
            "presion": pres_f,
            "eco2": eco2_f,
            "tvoc": tvoc_f,
            "base_eco2": round(mediana_zona, 1),
            "limite_normal_eco2": round(mediana_zona + MARGEN_PRECAUCION_PPM, 1),
            "tendencia": tendencia,
            "delta_ppm": delta_ppm,
            "comando_arduino": comando,
            "interpretaciones": interpretaciones,
            "perfiles": perfiles,
            "muestras_analizadas": n_muestras,
        }

    except Exception as error:
        respuesta_base["nivel_alerta"] = "ERROR_SISTEMA"
        respuesta_base["mensaje"] = str(error)
        return respuesta_base


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
    assert "perfiles" in diag and "interpretaciones" in diag
    print(f"[OK] Pruebas IA adaptativa superadas -> {diag['nivel_alerta']} | {diag['mensaje']}")

    with open(RUTA_CSV_DEFAULT, "w", encoding="utf-8", newline="") as f:
        f.write("timestamp,temperatura,humedad,presion,eco2,tvoc\n")