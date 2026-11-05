# 📡 Documentación Técnica del Firmware — AireCentinela AI

**Archivo:** `firmware_airecentinela.ino`  
**Placa:** Arduino Uno R3 (ATmega328P)  
**Entorno de Compilación:** Arduino IDE / VS Code (compilador AVR `avr-g++`)

---

## 📌 Descripción General

El firmware está diseñado para capturar datos ambientales y de calidad del aire en tiempo real mediante dos sensores principales (BME280 y PMS5003), desplegarlos localmente en una pantalla OLED SSD1306 de 0.96", gestionar alertas audibles/visuales locales y emitir una trama en formato **JSON** a través del puerto serial (USB) cada 3 segundos hacia el servidor backend.

---

## 🛠️ Conexiones y Mapeo de Hardware

| Componente | Tipo de Interfaz | Pines del Arduino Uno | Notas |
| :--- | :--- | :--- | :--- |
| **BME280** (Temp, Hum, Presión) | I2C | `A4` (SDA), `A5` (SCL) | Dirección I2C: `0x76` o `0x77` (3.3V) |
| **OLED SSD1306** (128x64) | I2C | `A4` (SDA), `A5` (SCL) | Dirección I2C: `0x3C` (5V) |
| **PMS5003** (Polvo PM1.0/2.5/10) | UART (SoftwareSerial) | `Pin 2` (RX), `Pin 3` (TX) | **Atención:** Las líneas TX/RX del PMS5003 operan a 3.3V (Usar convertidor de nivel) |
| **Buzzer Activo** | Salida Digital | `Pin 8` | Alerta audible |
| **Puerto Serial USB** | UART Hardware | `Pin 0` (RX), `Pin 1` (TX) | 9600 Baudios (Exclusivo para la PC) |

---

## ⚙️ Librerías C++ Utilizadas

1. `Adafruit_BME280` y `Adafruit_Sensor`: Lectura de temperatura (°C), humedad (%) y presión (hPa).
2. `Adafruit_SSD1306` y `Adafruit_GFX`: Renderizado de gráficos e interfaz local OLED.
3. `SoftwareSerial`: Creación de un puerto serial por software en los pines 2 y 3 para no interferir con la comunicación USB con Python.
4. `ArduinoJson` (v7): Serialización ligera de los datos en formato JSON para transmisión por USB.

---

## 🔄 Flujo de Funcionamiento (`loop`)

1. **Lectura Ambiental:** Lee la temperatura, humedad y presión del sensor BME280.
2. **Procesamiento de Trama PMS5003:** 
   - Valida la cabecera del sensor (`0x42 0x4D`).
   - Lee el buffer de 32 bytes y calcula el *Checksum* para prevenir datos corruptos.
   - Extrae las concentraciones de material particulado (`PM1.0`, `PM2.5`, `PM10.0`).
3. **Interfaz Local OLED:** Actualiza la pantalla en tiempo real mostrando métricas climáticas y resaltando el valor de `PM2.5`.
4. **Alerta Crítica Local:** Si el valor de `PM2.5` supera los **35 µg/m³**, la pantalla invierte sus colores (efecto visual de advertencia) y el Buzzer emite un pulso audible.
5. **Transmisión JSON a Python (Cada 3000 ms):**  
   Envía la siguiente estructura por el puerto serial para que el módulo backend (`backend_serial.py`) la capture y procese:

```json
{
  "temperatura": 28.5,
  "humedad": 65.0,
  "presion": 1013.25,
  "pm10": 12,
  "pm25": 38,
  "pm100": 45
}