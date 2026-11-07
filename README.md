# 🍃 AireCentinela AI — Estación Ambiental Inteligente

> **Universidad Gerardo Barrios (UGB) — Sede San Miguel**  
> *Facultad de Ciencia y Tecnología*  
> *Proyecto para el Concurso de Hardware y Automatización*

---

## 📌 Descripción General

**AireCentinela AI** es una estación de monitoreo ambiental inteligente en tiempo real diseñada para la medición, ingesta y análisis continuo de la calidad del aire. 

El sistema integra un microcontrolador **Arduino Uno R3** encargado de la captura multisensorial (temperatura, humedad, presión atmosférica y material particulado fino $PM_{1.0}$, $PM_{2.5}$, $PM_{10.0}$), transmitiendo las lecturas serializadas en formato JSON mediante USB hacia un backend en **Python**. 

Un motor analítico no supervisado basado en el algoritmo **Isolation Forest** evalúa los datos y detecta patrones anómalos o picos atípicos de contaminación de forma autónoma. Los diagnósticos e indicadores de alerta se presentan en un dashboard interactivo desarrollado en **PyQt6** y **Matplotlib**.

---

## 👥 Equipo de Trabajo y Roles

| Integrante | Rol Principal | Módulo Asignado |
| :--- | :--- | :--- |
| **Oscar Antonio Ramos Carbajal** | Liderazgo y Firmware C++ | `firmware/firmware_airecentinela/` |
| **Pedro Pablo Trejo Guevara** | Hardware y Esquemáticos | `docs/mapa_conexiones.md` |
| **Gabriel Alejandro Ramírez Segovia** | Backend e Ingeniería de Datos | `backend/backend_serial.py` |
| **Samuel Alexander Aguilar Salamanca** | Motor de Inteligencia Artificial | `ia_engine/motor_ia.py` |
| **Fredy Alexander Rivas Loza** | Frontend y Dashboard Visual | `frontend/app_airecentinela.py` |

---

## 🛠️ Arquitectura del Sistema

```text
[ SENSORES FÍSICOS ]
 ├── BME280 (I2C)         ──► Temp, Humedad, Presión
 └── PMS5003 (UART/3.3V)  ──► Partículas PM1.0 / PM2.5 / PM10.0
        │
        ▼
[ HARDWARE / FIRMWARE ]
 └── Arduino Uno R3 (ATmega328P)
      ├── Pantalla OLED 0.96" SSD1306 (Lectura Local)
      ├── Buzzer Activo (Alerta Audible Local)
      └── Serialización ArduinoJson v7 (USB @ 9600 Baudios)
        │
        ▼  Trama JSON
[ BACKEND SERIAL ]
 └── backend/backend_serial.py (Puerto por defecto: COM4)
      ├── Validación de tipos numéricos finitos
      ├── Esquema y persistencia continua con flush
      └── Registro local: data/datos_ambientales.csv
        │
        ├─────────────────────────────────────────┐
        ▼                                         ▼
[ IA ENGINE ]                            [ FRONTEND DASHBOARD ]
 └── ia_engine/motor_ia.py                └── frontend/app_airecentinela.py
      ├── Ventana deslizante (150 filas)          ├── PyQt6 (Modo Oscuro)
      ├── Isolation Forest (scikit-learn)         ├── Curvas dinámicas (Matplotlib)
      └── Retorno: 1 (Normal) / -1 (Anomalía)    └── Indicadores de Alerta Reactivos
```

---

## 🔌 Mapeo de Hardware (Arduino Uno R3)

| Componente | Tipo de Interfaz | Pines Arduino Uno | Notas Técnicas |
| :--- | :--- | :--- | :--- |
| **BME280** | I2C | `A4` (SDA), `A5` (SCL) | Temperatura, Humedad y Presión (3.3V) |
| **OLED SSD1306** | I2C | `A4` (SDA), `A5` (SCL) | Display local 128x64 px (`0x3C` / 5V) |
| **PMS5003** | SoftwareSerial | `Pin 2` (RX), `Pin 3` (TX) | Partículas en suspensión (Convertidor 3.3V-5V) |
| **Buzzer Activo** | Digital Output | `Pin 8` | Alerta audible ($PM_{2.5} > 35\ \mu\text{g/m}^3$) |
| **Puerto Serie USB** | Hardware Serial | `Pin 0` (RX), `Pin 1` (TX) | Transmisión JSON a 9600 Baudios hacia la PC |

---

## 🧪 Pruebas y Verificación Módulo por Módulo

El repositorio incluye herramientas y suites de prueba automatizadas para la verificación individual de los componentes:

1. **Motor de Inteligencia Artificial:** Generación sintética y test de detección de anomalías:
   ```powershell
   python ia_engine/motor_ia.py
   ```

2. **Backend Serial:** Ejecución de la suite de pruebas unitarias automatizadas (`unittest`):
   ```powershell
   python -m unittest discover -s tests -v
   ```

3. **Frontend Dashboard:** Prueba de la interfaz gráfica y renderizado visual:
   ```powershell
   python frontend/app_airecentinela.py
   ```

4. **Firmware & Hardware:** Carga del bosquejo C++ al Arduino Uno R3 desde Arduino IDE o VS Code tras la conexión física.