# 🔌 Mapa de Conexiones Físicas — AireCentinela AI

**Placa:** Arduino Uno R3 (ATmega328P)  
**Arquitectura $I^2C$:** Buses aislados por hardware (`Wire`) y software (`SoftwareWire`) para evitar colisiones de dirección y problemas eléctricos en protoboard.  
**Comunicación Serial:** Puerto USB (`COM6` a `9600` baudios).

---

## 📋 Tabla de Cableado por Componente

| Módulo / Componente | Pin del Módulo | Pin en Arduino Uno | Alimentación / Notas Técnicas |
| :--- | :--- | :--- | :--- |
| **Sensor CCS811** (eCO2 y TVOC) | `VCC` | `3.3V` | **No conectar a 5V** (opera estrictamente a 3.3V) |
| **Sensor CCS811** (eCO2 y TVOC) | `GND` | `GND` | Tierra común |
| **Sensor CCS811** (eCO2 y TVOC) | `SDA` | `A4` | Bus $I^2C$ Hardware (`0x5A`) |
| **Sensor CCS811** (eCO2 y TVOC) | `SCL` | `A5` | Bus $I^2C$ Hardware (`0x5A`) |
| **Sensor CCS811** (eCO2 y TVOC) | `WAK` | `GND` | Mantiene el sensor activo en modo lectura continua |
| **Sensor HW-611 / BME280** (Clima) | `VCC` | `3.3V` | Alimentación regulada 3.3V |
| **Sensor HW-611 / BME280** (Clima) | `GND` | `GND` | Tierra común |
| **Sensor HW-611 / BME280** (Clima) | `SDA` | `A2` | Bus $I^2C$ Software (`0x76` / `0x77` a 50 kHz) |
| **Sensor HW-611 / BME280** (Clima) | `SCL` | `A3` | Bus $I^2C$ Software (`0x76` / `0x77` a 50 kHz) |
| **Buzzer Activo** (Alarma Sonora) | `VCC` / `+` | `5V` | Alimentación directa 5V |
| **Buzzer Activo** (Alarma Sonora) | `GND` / `-` | `GND` | Tierra común |
| **Buzzer Activo** (Alarma Sonora) | `I/O` / `S` | `Pin Digital 8` | Lógica invertida (`Active-LOW`: pita en `LOW`, calla en `HIGH`) |

---

## 📐 Diagrama Esquemático de Distribución

```text
                    +-----------------------+
                    |    ARDUINO UNO R3     |
                    |                       |
   [CCS811 0x5A]    |                       |    [HW-611 / BME280 0x76]
   SDA ─────────────┼─ A4               A2 ─┼───────────── SDA
   SCL ─────────────┼─ A5               A3 ─┼───────────── SCL
   WAK ───┐         |                       |
   GND ───┴─────────┼─ GND              D8 ─┼───────────── I/O [Buzzer Activo]
   VCC ─────────────┼─ 3.3V             5V ─┼───────────── VCC [Buzzer Activo]
                    |                       |
                    |  USB (Pin 0/1) ───────┼──► PC (COM6 @ 9600 baudios)
                    +-----------------------+
```

---

## ⚠️ Notas Importantes de Montaje

1. **Aislamiento de Buses $I^2C$:** El sensor `CCS811` utiliza el bus $I^2C$ nativo (`A4`/`A5`) mientras que el `HW-611 (BME280)` opera sobre un bus $I^2C$ por software (`A2`/`A3` mediante la librería `SoftwareWire` a 50 kHz). Esto evita que el *clock stretching* del CCS811 interfiera con las lecturas climáticas.
2. **Pin `WAK` del CCS811:** Debe permanecer conectado directamente a `GND`. Si queda flotando, el sensor entra en reposo y deja de responder en la dirección `0x5A`.
3. **Lógica del Buzzer Activo:** El módulo buzzer utilizado se activa en bajo (`LOW`). El firmware inicializa el `Pin 8` en `HIGH` desde el arranque para evitar pitidos accidentales al energizar la placa y modula la frecuencia de pulsos según los comandos (`0` a `3`) enviados por el motor de Inteligencia Artificial desde Python.