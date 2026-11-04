# 🍃 AireCentinela AI — Estación Ambiental Inteligente

**Universidad Gerardo Barrios (UGB) — Sede San Miguel**  
*Proyecto para el Concurso de Hardware y Automatización*

---

## 📌 Descripción General
AireCentinela AI es una estación ambiental de monitoreo en tiempo real basada en **Arduino Uno R3**, procesada mediante un backend en **Python** y analizada por un motor de Inteligencia Artificial no supervisado (**Isolation Forest**). Los datos y alertas visuales se despliegan en un dashboard interactivo en modo oscuro desarrollado con **PyQt6**.

---

## 👥 Equipo de Trabajo y Roles

| Integrante | Rol Principal | Módulo Asignado |
| :--- | :--- | :--- |
| **Antonio** | Liderazgo y Firmware C++ | `firmware/firmware_airecentinela/` |
| **Pablo** | Hardware y Esquemáticos | `docs/mapa_conexiones.md` |
| **Gabriel** | Backend e Ingeniería de Datos | `backend/backend_serial.py` |
| **Samuel** | Motor de Inteligencia Artificial | `ia_engine/motor_ia.py` |
| **Fredy** | Frontend y Dashboard Visual | `frontend/app_airecentinela.py` |

---

## 🛠️ Arquitectura del Sistema

1. **Hardware / Captura:** Lectura de sensores de temperatura/humedad (BME280) y partículas suspendidas (PMS5003), despliegue local en pantalla OLED 0.96" y emisión en formato JSON por puerto USB.
2. **Backend:** Script `backend_serial.py` que captura la trama JSON e incrementa el archivo `datos_ambientales.csv` con estampa de tiempo.
3. **Motor de IA:** Modelo `IsolationForest` que evalúa las lecturas del CSV y detecta anomalías ambientales.
4. **Dashboard GUI:** Panel visual en PyQt6 con gráficas dinámicas de `matplotlib` e indicadores reactivos de alerta.

---

## 🚀 Flujo de Ejecución (Orden de Pruebas)

1. **Samuel:** Generar datos ficticios en `data/datos_ambientales.csv` y verificar `motor_ia.py`.
2. **Gabriel:** Ejecutar `backend_serial.py` para verificar la lectura continua del puerto COM.
3. **Fredy:** Ejecutar `app_airecentinela.py` para visualizar gráficas e indicadores.
4. **Antonio & Pablo:** Cargar el firmware en el Arduino Uno una vez ensamblado el hardware.