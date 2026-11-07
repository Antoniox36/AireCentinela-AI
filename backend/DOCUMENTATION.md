# Documentación del backend serial

## Propósito

`backend_serial.py` conecta el firmware de AireCentinela AI con el historial
ambiental del proyecto. Lee líneas del puerto serial, valida cada trama JSON y
agrega las lecturas válidas a `data/datos_ambientales.csv`, que también utiliza
el motor de IA.

## Flujo general

1. `main()` obtiene la configuración de la línea de comandos.
2. `recibir_datos()` abre el puerto serial y permanece leyendo líneas.
3. `validar_trama()` decodifica y valida cada línea como una lectura JSON.
4. `guardar_lectura()` añade una marca de tiempo y escribe la fila en el CSV.
5. Si una trama no es válida, se informa el motivo y se continúa con la
   siguiente, sin guardarla.

El puerto se abre con un tiempo de espera de un segundo por lectura. El proceso
se puede detener con `Ctrl+C`.

## Formato de las tramas

El firmware debe enviar un objeto JSON por línea. Los campos requeridos son:

| Campo | Descripción |
| --- | --- |
| `temperatura` | Temperatura reportada por el sensor BME280. |
| `humedad` | Humedad reportada por el sensor BME280. |
| `presion` | Presión atmosférica en hPa. |
| `eco2` | Concentración equivalente de CO₂ medida por el CCS811, en ppm. |
| `tvoc` | Concentración de compuestos orgánicos volátiles totales medida por el CCS811, en ppb. |

Ejemplo:

```json
{"temperatura":31.5,"humedad":60.0,"presion":1011.2,"eco2":450,"tvoc":12}
```

La trama se acepta únicamente si contiene JSON válido como objeto, incluye
todos los campos requeridos y cada valor es numérico y finito. Los valores
booleanos no se aceptan como números. Los campos adicionales no impiden la
lectura, pero no se agregan al CSV.

## Funciones principales

### `validar_trama(trama)`

Recibe texto o bytes. Si recibe bytes, los decodifica como UTF-8 y luego analiza
el JSON. Devuelve un diccionario con los seis valores numéricos. Ante una
codificación inválida, JSON incorrecto, campos faltantes o valores no
numéricos/no finitos, lanza `ValueError` con el motivo del rechazo.

### `preparar_csv(ruta_csv)`

Crea el directorio de destino si hace falta. Si el CSV no existe o está vacío,
lo inicializa con la cabecera esperada. Si ya tiene datos, compara su cabecera
con el esquema del proyecto y genera un error si no coincide; no sobrescribe un
archivo existente con una estructura diferente.

### `guardar_lectura(lectura, ruta_csv, timestamp)`

Prepara el archivo y añade una fila con la fecha y hora local de la computadora
en formato `AAAA-MM-DD HH:MM:SS`. El argumento opcional `timestamp` permite
proporcionar una marca de tiempo explícita, por ejemplo, durante pruebas.

El orden de columnas del archivo es:

```text
timestamp,temperatura,humedad,presion,eco2,tvoc
```

El archivo se abre en modo de adición, por lo que las lecturas anteriores se
conservan. Después de cada escritura se vacía el búfer para que la lectura
quede registrada sin esperar a que el proceso termine.

### `recibir_datos(port, baudrate, ruta_csv)`

Carga `pyserial` cuando se inicia la recepción y muestra un mensaje claro si no
está instalado. Abre el puerto configurado y procesa cada línea recibida. Las
tramas inválidas se notifican por la salida de errores y se omiten; cada lectura
válida se guarda y se confirma en la salida normal.

### `crear_parser()` y `main()`

`crear_parser()` define las opciones de configuración. `main()` inicia el
receptor y reporta errores de puerto, archivo o configuración. La interrupción
del usuario con `Ctrl+C` cierra la conexión de forma normal.

## Configuración y ejecución

Instala las dependencias del proyecto desde la raíz:

```powershell
python -m pip install -r requirements.txt
```

Ejecuta el backend indicando el puerto COM que corresponde al Arduino:

```powershell
python backend/backend_serial.py --port COM3
```

El firmware de este proyecto utiliza **9600 baudios**, valor predeterminado del
backend. Las opciones disponibles son:

| Opción | Predeterminado | Función |
| --- | --- | --- |
| `--port` | `AIRECENTINELA_PORT` o `COM3` | Puerto serial del dispositivo. |
| `--baudrate` | `9600` | Velocidad de comunicación serial. |
| `--csv` | `data/datos_ambientales.csv` | Ruta del archivo de historial. |

Ejemplo con una ruta de salida personalizada:

```powershell
python backend/backend_serial.py --port COM4 --baudrate 9600 --csv data/prueba.csv
```

También se puede seleccionar el puerto mediante una variable de entorno de
PowerShell:

```powershell
$env:AIRECENTINELA_PORT = "COM4"
python backend/backend_serial.py
```

## Consideraciones de uso

- Cierra el Monitor Serial del IDE de Arduino y cualquier otra aplicación que
  esté usando el puerto antes de iniciar el backend.
- Si el sistema no encuentra el puerto, confirma el nombre en el Administrador
  de dispositivos y pásalo con `--port`.
- El timestamp corresponde al reloj local de la computadora, no al reloj del
  Arduino.
- Si el CSV ya existe, conserva sus datos siempre que su cabecera coincida con
  el esquema requerido. Si no coincide, el backend se detiene y muestra el
  error, en lugar de mezclar formatos.
- Las tramas de error del firmware, como `{"error":"OLED no encontrada"}`, no
  contienen los campos ambientales requeridos y por ello se ignoran.
- El firmware debe transmitir `eco2` y `tvoc` además de las tres mediciones del
  BME280. Si aún envía los campos antiguos de partículas (`pm10`, `pm25`,
  `pm100`), el backend rechazará esas tramas por no incluir los campos CCS811.

## Pruebas

Las pruebas unitarias del backend pueden ejecutarse desde la raíz del proyecto:

```powershell
python -m unittest discover -s tests -v
```

Verifican la validación de tramas, el rechazo de datos inválidos y la creación y
adición de filas con el esquema correcto, sin requerir un Arduino conectado.
