# 🍃 Aire Centinela AI — Estación Ambiental Inteligente

> **Universidad Gerardo Barrios (UGB) — Sede San Miguel**  
> *Facultad de Ciencia y Tecnología*  
> *Proyecto de Monitoreo Ambiental con Hardware e Inteligencia Artificial*

---

## 📌 Descripción General

**Aire Centinela AI** es una estación de monitoreo ambiental inteligente en tiempo real diseñada para la captura, almacenamiento, interpretación y análisis autónomo de la calidad del aire interior y microclimas.

El sistema integra un microcontrolador **Arduino Uno R3** con buses $I^2C$ aislados para los sensores **CCS811** (`eCO2` y `TVOC`) y **HW-611 / BME280** (temperatura, humedad relativa y presión atmosférica), enviando tramas **JSON** cada segundo a través de USB (`COM6` a `9600` baudios).

El backend en **Python** valida y registra las lecturas en `data/datos_ambientales.csv`, ejecuta en tiempo real un modelo no supervisado **Isolation Forest** (`scikit-learn`) que aprende la línea base de cada entorno y envía de vuelta al Arduino órdenes de alerta sonora progresiva para el **Buzzer Activo**. Por su parte, la interfaz gráfica en **PyQt6** y **Matplotlib** incluye auditoría inicial de hardware, traducción en lenguaje natural para perfiles sectoriales (**Oficina / Escuela**, **Agricultura / Cultivo**, **Hogar / Salud**) y registro verificable con comparativa por ubicación (`data/sesiones_ubicaciones.json`).

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
│   ├── motor_ia.py                        # Isolation Forest adaptativo + perfiles sectoriales
│   └── DOCUMENTACION.md
├── frontend/
│   └── app_airecentinela.py               # Dashboard PyQt6 (Auditoría, Perfiles y Evidencia)
├── data/
│   ├── datos_ambientales.csv              # Historial ambiental continuo (6 columnas)
│   └── sesiones_ubicaciones.json          # Registro auditado de snapshots por ubicación
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
        ├─────────────────────────────────────────────┐
        ▼                                             ▼
[ IA ENGINE — ia_engine/motor_ia.py ]        [ FRONTEND — frontend/app_airecentinela.py ]
 ├── Ventana deslizante (150 lecturas)         ├── Auditoría de arranque (Sensores, CSV, GPS e IA)
 ├── Línea base adaptativa por zona            ├── Monitor en vivo + banda normal sombreada
 ├── Isolation Forest (scikit-learn)           ├── Diagnóstico por sector (Agro, Aula, Hogar)
 └── Traducción humana de variables físicas    └── Evidencia y comparativa por ubicación
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

## ✨ Funcionalidades Clave de la Plataforma

* **Auditoría Previa de Componentes:** Pantalla inicial que verifica el estado del canal serial, respuesta de los sensores `CCS811` y `HW-611 / BME280`, punto geográfico en San Miguel y calibración del modelo antes de abrir el panel principal.
* **Interpretación Humana en Tiempo Real:** Cada tarjeta de medición traduce el valor numérico a un diagnóstico inmediato comprensible para cualquier usuario, acompañado de una banda sombreada en la gráfica que delimita la zona normal aprendida por la IA.
* **Adaptabilidad por Perfil de Uso:** Cambia dinámicamente las recomendaciones según el entorno de aplicación (**Oficina / Escuela**, **Agricultura / Cultivo** u **Hogar / Salud**) e incluye fichas técnicas de referencia rápida.
* **Evidencia y Comparativa por Ubicación:** Permite guardar snapshots completos por punto de medición (`data/sesiones_ubicaciones.json`), reconstruir su última gráfica/veredicto al seleccionarlo y compararlo frente a las lecturas actuales en vivo.

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
   * `python main.py --sin-hardware`: Abre el dashboard para revisar datos guardados o demostrar la interfaz sin Arduino conectado.

3. **Ejecutar pruebas individuales:**
   ```powershell
   python -m unittest discover -s tests -v
   python ia_engine/motor_ia.py
   ```