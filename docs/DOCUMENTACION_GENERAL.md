# 📚 Índice Maestro y Documentación Consolidada — AireCentinela AI

**Proyecto:** AireCentinela AI — Estación Ambiental Inteligente  
**Institución:** Universidad Gerardo Barrios (UGB) — Sede San Miguel  
**Facultad:** Ciencia y Tecnología  
**Versión del Sistema:** 2.0 (Arquitectura Unificada con CCS811 y Buses Aislados)  

---

## 🧭 1. Directorio y Mapa de Toda la Documentación

El proyecto cuenta con documentación técnica especializada en cada nivel de su arquitectura:

| Nivel / Módulo | Archivo de Documentación | Responsable | Propósito Principal |
| :--- | :--- | :--- | :--- |
| **Global / Raíz** | [`README.md`](file:///d:/prueba_git/AireCentinela-AI-1/README.md) | Todo el equipo | Visión general, arquitectura del sistema, instalación rápida y comandos de ejecución. |
| **Hardware** | [`docs/mapa_conexiones.md`](file:///d:/prueba_git/AireCentinela-AI-1/docs/mapa_conexiones.md) | Pedro Pablo Trejo | Diagrama esquemático, tabla de pines de Arduino Uno R3, voltajes y aislamiento de buses $I^2C$. |
| **Firmware C++** | [`DOCUMENTACION_FIRMWARE.md`](file:///d:/prueba_git/AireCentinela-AI-1/firmware/firmware_airecentinela/DOCUMENTACION_FIRMWARE.md) | Oscar Antonio Ramos | Firmware C++, lectura de registros BME280 por `SoftwareWire`, CCS811, buzzer activo y JSON serial. |
| **Backend Serial** | [`backend/DOCUMENTATION.md`](file:///d:/prueba_git/AireCentinela-AI-1/backend/DOCUMENTATION.md) | Gabriel Alejandro Ramírez | Ingesta de puerto COM, validación estricta de tramas JSON, persistencia CSV y control de búfer. |
| **Motor de IA** | [`ia_engine/DOCUMENTACION.md`](file:///d:/prueba_git/AireCentinela-AI-1/ia_engine/DOCUMENTACION.md) | Samuel Alexander Aguilar | Isolation Forest adaptativo, 5 variables (`eCO2`, `TVOC`, etc.), perfiles sectoriales y diagnósticos. |
| **Índice Maestro** | [`docs/DOCUMENTACION_GENERAL.md`](file:///d:/prueba_git/AireCentinela-AI-1/docs/DOCUMENTACION_GENERAL.md) | Todo el equipo | Consolidación, interconexión de módulos, protocolo de datos y flujo de extremo a extremo. |

---

## 🛠️ 2. Arquitectura de Hardware y Sensores

```text
[ ENTORNO AMBIENTAL ]
        │
        ├── BME280 (HW-611) ────────► Temperatura (°C), Humedad (%), Presión (hPa)
        │                             [Bus I2C Software: Pines A2 (SDA), A3 (SCL) @ 50 kHz]
        │
        └── CCS811 ─────────────────► eCO2 (ppm), TVOC (ppb)
                                      [Bus I2C Hardware: Pines A4 (SDA), A5 (SCL), WAK a GND]
                                      │
                                      ▼
                        [ ARDUINO UNO R3 (ATmega328P) ]
                                      │
          ▲                           ├── Actuador: Buzzer Activo en Pin Digital 8 (Active-LOW)
          │ Comandos IA ('0'..'3')    └── Serial USB: 9600 Baudios (Trama JSON cada 1 s)
          │                                   │
          └───────────────────────────────────┤
                                              ▼
                                 [ PC / BACKEND EN PYTHON ]
```

### Justificación Técnica del Aislamiento de Buses:
El sensor `CCS811` utiliza *clock stretching* a nivel de hardware, lo que ocasionaba colisiones y bloqueos eléctricos cuando compartía el bus $I^2C$ nativo con el `BME280`. La solución definitiva implementada aísla el `BME280` en los pines `A2/A3` mediante la librería `SoftwareWire` a 50 kHz, garantizando una lectura limpia y estable sin congelamientos.

---

## 🔄 3. Protocolo de Comunicación y Flujo de Datos

### 3.1. Trama JSON de Sensores (Arduino ➡️ Backend en Python):
Cada segundo (1000 ms), el firmware transmite una línea JSON con las 5 variables ambientales:

```json
{
  "temperatura": 28.52,
  "humedad": 65.14,
  "presion": 1013.25,
  "eco2": 450,
  "tvoc": 12
}
```

### 3.2. Formato del Historial CSV (`data/datos_ambientales.csv`):
El backend valida que todos los valores sean numéricos y finitos, agrega una estampa de tiempo local y escribe en el archivo:
```text
timestamp,temperatura,humedad,presion,eco2,tvoc
2026-11-25 20:30:00,28.52,65.14,1013.25,450,12
```

### 3.3. Comandos de Control de Alarma (Backend IA ➡️ Arduino):
El backend consulta el diagnóstico del motor de IA y envía un carácter ASCII de vuelta por el puerto serial para modular la alarma sonora del Buzzer en el Arduino:

| Comando | Nivel de Riesgo | Comportamiento del Buzzer en Arduino |
| :---: | :--- | :--- |
| `'0'` | Normal / Silencio | Buzzer apagado continuamente (`HIGH`). |
| `'1'` | Precaución | Pulso audible lento (pitido de 80 ms cada 1200 ms). |
| `'2'` | Alerta Elevada | Pulso audible rápido (pitido de 80 ms cada 300 ms). |
| `'3'` | Crítico / Peligro | Pitido continuo sostenido (`LOW`). |

*(Mecanismo de seguridad:* si pasan más de 6 segundos sin recibir órdenes de la PC, el Arduino apaga la alarma automáticamente).*

---

## 🧠 4. Motor de Inteligencia Artificial (Isolation Forest)

El motor de IA analiza una ventana deslizante de las **últimas 150 lecturas** para aprender dinámicamente la línea base del lugar.

- **Variables analizadas:** `['temperatura', 'humedad', 'presion', 'eco2', 'tvoc']`.
- **Algoritmo:** `IsolationForest(contamination=0.05, random_state=42, n_estimators=100)`.
- **Perfiles sectoriales:**
  - **Oficina / Escuela:** Alertas centradas en somnolencia, ventilación y concentración de $e\text{CO}_2$.
  - **Agricultura / Cultivo:** Alertas enfocadas en estrés térmico, humedad relativa y transpiración vegetal.
  - **Hogar / Salud:** Alertas de acumulación de compuestos volátiles ($TVOC$) y calidad de aire nocturno.

---

## 🖥️ 5. Frontend y Orquestación (`main.py`)

El sistema cuenta con un ejecutor central [`main.py`](file:///d:/prueba_git/AireCentinela-AI-1/main.py) que inicia:
1. **Auditoría Inicial:** Verificación previa de conexión serial, estado de sensores, GPS simulado de San Miguel y calibración de IA.
2. **Dashboard Interactivo PyQt6:** Gráficas en tiempo real de Matplotlib con bandas sombreadas normales aprendidas por la IA, tarjetas de diagnóstico en lenguaje natural y registro de snapshots por ubicación en `data/sesiones_ubicaciones.json`.

---

## 🚀 6. Guía Rápida de Verificación y Pruebas

```powershell
# 1. Ejecutar la suite de pruebas unitarias del backend:
python -m unittest discover -s tests -v

# 2. Ejecutar la verificación directa del motor de IA:
python ia_engine/motor_ia.py

# 3. Iniciar el sistema completo en modo demostración (sin hardware conectado):
python main.py --sin-hardware

# 4. Iniciar el sistema en producción conectado al Arduino:
python main.py --port COM6
```
