# 📡 Documentación Técnica del Firmware — AireCentinela AI

**Archivo:** `firmware_airecentinela.ino`  
**Placa:** Arduino Uno R3 (ATmega328P)  
**Entorno de Compilación:** Arduino IDE / VS Code (compilador AVR `avr-g++`)

---

## 📌 Descripción General

El firmware implementa la capa de captura física y control de actuadores para **AireCentinela AI**. Gestiona de forma síncrona la lectura de dos buses $I^2C$ aislados (hardware y software), procesa comandos de alarma bidireccionales emitidos por el motor de Inteligencia Artificial desde Python y transmite las mediciones ambientales en formato **JSON** cada segundo (1000 ms) a través del puerto serie USB (`COM6` a 9600 baudios).

---

## 🛠️ Conexiones y Mapeo de Hardware

| Componente | Tipo de Interfaz | Pines del Arduino Uno | Alimentación / Notas Técnicas |
| :--- | :--- | :--- | :--- |
| **CCS811** (eCO2 y TVOC) | $I^2C$ Hardware (`Wire`) | `A4` (SDA), `A5` (SCL) | Dirección `0x5A` (o `0x5B`), alimentación 5V, pin `WAK` a `GND` |
| **HW-611 / BME280** (Clima) | $I^2C$ Software (`SoftwareWire`) | `A2` (SDA), `A3` (SCL) | Dirección `0x76`, reloj `50 kHz`, lectura por registros directos |
| **Buzzer Activo** | Salida Digital | `Pin 8` | Lógica invertida (`Active-LOW`: enciende en `LOW`, apaga en `HIGH`) |
| **Puerto Serial USB** | UART Hardware | `Pin 0` (RX), `Pin 1` (TX) | Comunicación bidireccional a 9600 baudios con el backend en Python |

---

## ⚙️ Librerías C++ Utilizadas

1. `Wire`: Bus $I^2C$ por hardware nativo para el sensor de calidad del aire CCS811.
2. `SoftwareWire`: Emulación de bus $I^2C$ por software en los pines analógicos `A2` y `A3` para aislar el sensor BME280 y evitar interferencias por *clock stretching*.
3. `Adafruit_CCS811`: Inicialización, calibración y extracción de $e\text{CO}_2$ (ppm) y $TVOC$ (ppb).
4. `ArduinoJson` (v7): Serialización compacta y eficiente de tramas JSON enviadas por USB.

---

## 🔄 Flujo de Funcionamiento del Firmware

### 1. Inicialización (`setup`):
- Configuración preventiva del `Pin 8` en nivel `HIGH` (`BUZZER_OFF`) para evitar pitidos durante el encendido.
- Inicio del puerto serie a 9600 baudios con *timeout* de lectura de 20 ms.
- Inicialización de los buses $I^2C$ (`Wire.begin()` y `busBME.begin()` a 50 kHz).
- Rutina de verificación reentrante (hasta 5 intentos) para `BME280` y `CCS811`.

### 2. Ciclo Continuo (`loop`):
- **Recepción de órdenes IA (`leerComandosIA`):** Lee continuamente por el puerto serial caracteres del `'0'` al `'3'` enviados por el backend según el nivel de riesgo detectado. Si pasan más de 6 segundos sin órdenes, la alarma se silencia automáticamente por seguridad.
- **Gestión de Alarma Sonora (`gestionarAlarmaSonora`):**
  - **Nivel 0:** Silencio total (`BUZZER_OFF`).
  - **Nivel 1 (Precaución):** Pulso audible lento (80 ms pitido cada 1200 ms de silencio).
  - **Nivel 2 (Alerta elevada):** Pulso audible rápido (80 ms pitido cada 300 ms de silencio).
  - **Nivel 3 (Crítico):** Alarma continua sostenida (`BUZZER_ON`).
- **Lectura de BME280 (`leerBME280`):** Lectura por registros de fábrica y compensación directa matemática en enteros de 32/64 bits para temperatura (°C), presión (hPa) y humedad (%).
- **Lectura de CCS811:** Lectura de $e\text{CO}_2$ (validando valores $\ge 400\text{ ppm}$) y $TVOC$ (ppb).
- **Emisión JSON periódica (`enviarTramaJSON`):** Cada 1000 ms emite una trama JSON por el puerto serie USB:

```json
{
  "temperatura": 28.52,
  "humedad": 65.14,
  "presion": 1013.25,
  "eco2": 450,
  "tvoc": 12
}
```
