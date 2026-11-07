# 🧠 Documentación Técnica — Motor de Inteligencia Artificial
**Proyecto:** AireCentinela AI — Estación Ambiental Inteligente  
**Institución:** Universidad Gerardo Barrios (UGB) — Sede San Miguel  
**Responsable del Módulo:** Samuel (Motor de IA)  
**Archivo Principal:** `ia_engine/motor_ia.py`  

---

## 📌 1. Resumen del Módulo
El Motor de Inteligencia Artificial es el componente analítico de AireCentinela AI. Su función es evaluar continuamente las lecturas ambientales recolectadas por los sensores (temperatura y dióxido de carbono equivalente **eCO2**) y determinar de manera autónoma si el estado actual del aire corresponde a una condición **Normal (1)** o a una **Anomalía Ambiental (-1)**.

A diferencia de un sistema convencional basado en reglas fijas (como `if eco2 > 1000`), este motor utiliza Machine Learning **no supervisado** para detectar desacoplamientos inusuales y patrones atípicos multivariables entre el comportamiento térmico y la concentración de gas.

---

## 💻 2. Entorno de Ejecución y Configuración

### Versión de Python Recomendada
* **Python 3.10 a 3.13 (64-bit)**.
* Se recomienda utilizar una versión estable de Python con soporte para ruedas precompiladas (*binary wheels*) en Windows para evitar compilaciones desde código fuente.

### Creación y Activación del Entorno Virtual (Opcional pero Recomendado)
Para aislar las dependencias del proyecto en cualquier computadora:

1. **Crear el entorno virtual en la raíz del proyecto:**
   ```powershell
   py -3.13 -m venv .venv
   ```

2. **Activar el entorno virtual:**
   * En Windows PowerShell:
     ```powershell
     .\.venv\Scripts\Activate.ps1
     ```
   * En Windows CMD:
     ```cmd
     .\.venv\Scripts\activate.bat
     ```

3. **Instalación de todas las dependencias con un solo comando:**
   ```powershell
   pip install -r requirements.txt
   ```

---

## 📦 3. Librerías Utilizadas y Justificación

| Librería | Versión Mínima | Propósito en el Proyecto |
| :--- | :--- | :--- |
| **`pandas`** | `2.2.0` | Ingesta, estructuración y filtrado del historial ambiental desde `data/datos_ambientales.csv`. |
| **`scikit-learn`** | `1.4.0` | Provee la implementación optimizada del algoritmo de Machine Learning `IsolationForest`. |
| **`numpy`** | `1.26.0` | Manejo de matrices numéricas y cálculo de distribuciones estadísticas para la simulación de datos. |

### Dependencias Secundarias (Instaladas automáticamente por `scikit-learn`):
* `scipy`: Cálculos científicos y álgebra lineal subyacente.
* `joblib`: Paralelización y procesamiento eficiente de los árboles de decisión.
* `threadpoolctl`: Control de hilos de ejecución en operaciones numéricas.

---

## 🔍 4. Detalle del Procesamiento de Datos (`pandas`)

En el script `ia_engine/motor_ia.py`, el manejo de datos se estructura en 3 etapas:

1. **Lectura Segura:**  
   `df = pd.read_csv(ruta_csv)`  
   Carga el archivo generado por el backend sin bloquear lecturas concurrentes.

2. **Optimización de Memoria (Ventana Deslizante):**  
   `df_reciente = df.tail(150)`  
   Únicamente se analizan las **últimas 150 filas** registradas. Esto optimiza el consumo de memoria RAM y enfoca el aprendizaje en la dinámica ambiental más reciente (aproximadamente los últimos 5 a 10 minutos de muestreo).

3. **Extracción Multivariable:**  
   `datos = df_reciente[['temperatura', 'eco2']].values`  
   Se seleccionan las dos variables críticas del estudio y se transforman en una matriz bidimensional compatible con scikit-learn.

---

## 🌲 5. Teoría del Algoritmo: Isolation Forest

### ¿Por qué Aprendizaje No Supervisado?
En un entorno real de feria o monitoreo ambiental cerrado, no se cuenta de antemano con millones de ejemplos etiquetados que indiquen qué es peligroso o anómalo. El algoritmo **no supervisado** no requiere entrenamiento previo supervisado; aprende la dinámica intrínseca del lugar a partir de las lecturas observadas.

### Principio de Funcionamiento
* El **Bosque de Aislamiento (Isolation Forest)** construye un conjunto de árboles de decisión binarios generados al azar.
* Para aislar una observación, el algoritmo selecciona aleatoriamente una característica (`temperatura` o `eco2`) y un valor de corte entre los valores mínimo y máximo.
* **Lógica clave:**
  * Los puntos normales (frecuentes y agrupados en rango $400 - 800\text{ ppm}$) requieren muchas particiones para ser aislados.
  * Los puntos anómalos (raros, alejados de la nube central o $> 1200\text{ ppm}$) quedan aislados en muy pocas particiones (recorrido corto en el árbol).

### Parámetros Clave Configurados
* `contamination=0.05`: Indica que el modelo asume que aproximadamente el 5% de las lecturas pueden ser potencialmente anómalas. Este valor define el umbral de decisión. Si en la feria se generan falsas alarmas, puede reducirse a `0.02` o `0.01`.
* `random_state=42`: Semilla fija para garantizar reproducibilidad exacta durante las demostraciones ante los evaluadores.
* `n_estimators=100`: Número de árboles de aislamiento en el ensamble para asegurar estabilidad estadística.

---

## 📤 6. Estructura del Entregable (Retorno Matemático)

### Estructura de Columnas del CSV (`data/datos_ambientales.csv`)
`timestamp,temperatura,humedad,presion,eco2`

El motor de IA extrae automáticamente las columnas requeridas `['temperatura', 'eco2']` para el modelado con Isolation Forest.

La función principal es:
```python
def evaluar_anomalia(ruta_csv=..., contamination=0.05) -> int:
```

### Rangos de Referencia para eCO2:
* **Rango Normal:** $400 - 800\text{ ppm}$
* **Rango de Alerta / Anomalía:** $> 1200\text{ ppm}$

### Significado de los Códigos de Retorno:
* **`1` (Estado Normal):** La última lectura (`temperatura`, `eco2`) coincide con el patrón de agrupamiento aprendido.
* **`-1` (Anomalía Detectada):** La última lectura se desvía drásticamente del comportamiento correlacionado (ejemplo: eCO2 disparado a $1450\text{ ppm}$) o presenta un fallo de hardware.

### Diagnóstico Extendido y Tendencia Histórica:
Para visualizaciones avanzadas o alertas personalizadas, el motor expone:
```python
def obtener_diagnostico_completo(ruta_csv=..., contamination=0.05) -> dict:
```
Retorna un diccionario completo con:
* **`nivel_alerta`:**
  * `'OPTIMO'`: eCO2 $\le 600\text{ ppm}$ y modelo normal.
  * `'ACEPTABLE'`: eCO2 entre $600 - 800\text{ ppm}$ y modelo normal.
  * `'PRECAUCION'`: eCO2 entre $800 - 1200\text{ ppm}$ o acumulación rápida de gas.
  * `'CRITICO'`: eCO2 $> 1200\text{ ppm}$ o anomalía severa.
  * `'FALLO_HARDWARE'`: Sensor desconectado, valores NaN o fuera de escala física.
* **`tendencia`:** Tasa de cambio histórica (`'SUBIENDO_RAPIDO'`, `'SUBIENDO'`, `'ESTABLE'`, `'BAJANDO'`).
* **`delta_ppm`:** Variación numérica en ppm respecto al inicio de la ventana.

### Integración con el Frontend de Fredy (`frontend/app_airecentinela.py`):
```python
from ia_engine.motor_ia import evaluar_anomalia, obtener_diagnostico_completo

# Uso simple (indicador Verde/Rojo):
estado = evaluar_anomalia()

# Uso avanzado (niveles y tendencia):
diagnostico = obtener_diagnostico_completo()
print(diagnostico['nivel_alerta'], diagnostico['tendencia'])
```

---

## 🧪 7. Pruebas y Verificación

Para ejecutar la suite de pruebas locales que valida el modelo, los fallos físicos y las tendencias:

```powershell
py -3.13 ia_engine/motor_ia.py
# (o con tu entorno activo: python ia_engine/motor_ia.py)
```

La suite ejecutará:
1. Comprobación y creación de `data/datos_ambientales.csv` si no existe.
2. **Test 1:** Evaluación con datos en rango normal de eCO2 ($400 - 800\text{ ppm}$) (esperado: `1`).
3. **Test 2:** Inyección de lectura extrema con eCO2 $> 1200\text{ ppm}$ en la última fila (esperado: `-1`).
4. **Test 3:** Simulación de sensor desconectado o trama corrupta (esperado: `-1` con protección activa).
5. **Test 4:** Cálculo de tendencia histórica (`delta_ppm`) y categorización de nivel de alerta.
6. Restauración del CSV a estado normal para que Fredy y Gabriel puedan continuar sus pruebas.
