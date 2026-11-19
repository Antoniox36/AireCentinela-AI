# 🍃 AireCentinela AI — Estación Ambiental Inteligente

> **Universidad Gerardo Barrios (UGB) — Sede San Miguel**  
> *Facultad de Ciencia y Tecnología*  
> *Proyecto de Monitoreo Ambiental con Hardware e Inteligencia Artificial*

---

## 📌 Descripción General

**AireCentinela AI** es una estación de monitoreo ambiental inteligente en tiempo real diseñada para la captura, almacenamiento y análisis autónomo de la calidad del aire interior.

El sistema integra un microcontrolador **Arduino Uno R3** con buses $I^2C$ aislados para los sensores **CCS811** (`eCO2` y `TVOC`) y **HW-611 / BME280** (temperatura, humedad relativa y presión atmosférica), enviando tramas **JSON** cada segundo a través de USB (`COM6` a `9600` baudios).

El backend en **Python** valida y registra las lecturas en `data/datos_ambientales.csv`, ejecuta en tiempo real un modelo no supervisado **Isolation Forest** (`scikit-learn`) que aprende la línea base de cada habitación y envía de vuelta al Arduino órdenes de alerta sonora progresiva para el **Buzzer Activo**, mientras un dashboard en **PyQt6** y **Matplotlib** visualiza métricas, curvas históricas y diagnósticos en vivo.

---

## 👥 Equipo de Trabajo y Roles

| Integrante | Rol Principal | Módulo Asignado |
| :--- | :--- | :--- |
| **Oscar Antonio Ramos Carbajal** | Liderazgo, Orquestación y Firmware C++ | `main.py`, `firmware/firmware_airecentinela/` |
| **Pedro Pablo Trejo Guevara** | Hardware y Esquemáticos | `docs/mapa_conexiones.md` |
| **Gabriel Alejandro Ramírez Segovia** | Backend e Ingeniería de Datos | `backend/backend_serial.py` |
| **Samuel Alexander Aguilar Salamanca** | Motor de Inteligencia Artificial | `ia_engine/motor_ia.py` |
| **Fredy Alexander Rivas Loza** | Frontend y Dashboard Visual | `frontend/app_airecentinela.py` |

---

## 🛠️ Arquitectura del Sistema

```text
AireCentinela-AI/
├── main.py                                # Orquestador principal (Backend + Frontend)
├── firmware/
│   └── firmware_airecentinela/
│       └── firmware_airecentinela.ino     # Firmware C++ Arduino Uno R3 (Buses I2C aislados)
├── backend/
│   ├── backend_serial.py                  # Receptor/emisor serial bidireccional (COM6)
│   └── DOCUMENTATION.md
├── ia_engine/
│   ├── motor_ia.py                        # Isolation Forest adaptativo + márgenes relativos
│   └── DOCUMENTACION.md
├── frontend/
│   └── app_airecentinela.py               # Dashboard PyQt6 + Matplotlib en tiempo real
├── data/
│   └── datos_ambientales.csv              # Historial ambiental (6 columnas)
├── docs/
│   └── mapa_conexiones.md                 # Diagrama y tabla de pines físicos
├── tests/
│   └── test_backend_serial.py             # Pruebas unitarias del backend
└── requirements.txt
```

### Flujo Bidireccional en Tiempo Real

```text
[ SENSORES FÍSICOS ]
 ├── CCS811 (I2C Hardware A4/A5)  ──► eCO2 (ppm), TVOC (ppb)
 └── HW-611 BME280 (I2C A2/A3)    ──► Temperatura (°C), Humedad (%), Presión (hPa)
        │
        ▼
[ ARDUINO UNO R3 @ COM6 / 9600 baudios ] ◄── Órdenes IA: 0 (Silencio) | 1..3 (Pulsos Buzzer)
        │
        ▼  Trama JSON (cada 1 s)
[ BACKEND SERIAL — backend/backend_serial.py ]
 ├── Validación estricta de tipos numéricos finitos
 ├── Persistencia continua en data/datos_ambientales.csv
 └── Consulta en vivo al Motor IA y retorno de comando al Arduino
        │
        ├─────────────────────────────────────────┐
        ▼                                         ▼
[ IA ENGINE — ia_engine/motor_ia.py ]    [ FRONTEND — frontend/app_airecentinela.py ]
 ├── Ventana deslizante (150 lecturas)     ├── Tarjetas métricas en vivo (refresco 1 s)
 ├── Línea base adaptativa por zona        ├── Gráfica histórica dinámica de eCO2
 └── Isolation Forest (scikit-learn)       └── Semáforo de diagnóstico y tendencia
```

---

## 🔌 Mapeo de Hardware (Arduino Uno R3)

| Componente | Interfaz | Pines Arduino Uno | Notas Técnicas |
| :--- | :--- | :--- | :--- |
| **CCS811** (Calidad de aire) | $I^2C$ Hardware (`Wire`) | `A4` (SDA), `A5` (SCL) | Dirección `0x5A`, `VCC` a `3.3V`, `WAK` a `GND` |
| **HW-611 / BME280** (Clima) | $I^2C$ Software (`SoftwareWire`) | `A2` (SDA), `A3` (SCL) | Dirección `0x76`, `VCC` a `3.3V`, reloj `50 kHz` |
| **Buzzer Activo** | Salida Digital | `Pin 8` | Lógica invertida (`Active-LOW`), controlado por IA |
| **Puerto Serie USB** | UART Hardware | `Pin 0` (RX), `Pin 1` (TX) | Comunicación bidireccional `COM6` a `9600` baudios |

---

## 🚀 Instalación y Ejecución Rápida

1. **Activar el entorno virtual e instalar dependencias:**
   ```powershell
   .\venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Ejecutar el sistema completo con un solo comando:**
   ```powershell
   python main.py
   ```
   *Opciones útiles de `main.py`:*
   * `python main.py --limpiar`: Borra el historial CSV anterior antes de iniciar una nueva sesión.
   * `python main.py --port COM6`: Especifica manualmente el puerto serial.
   * `python main.py --sin-hardware`: Abre el dashboard para revisar datos guardados sin Arduino conectado.

3. **Ejecutar pruebas individuales:**
   ```powershell
   python -m unittest discover -s tests -v
   python ia_engine/motor_ia.py
   ```