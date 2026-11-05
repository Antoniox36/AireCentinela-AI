#include <Wire.h>
#include <SoftwareSerial.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BME280.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <ArduinoJson.h>

// --- CONFIGURACIÓN DE PINES Y PANTALLA OLED ---
#define BUZZER_PIN 8
#define ANCHO_PANTALLA 128
#define ALTO_PANTALLA 64
#define OLED_RESET -1 // Comparte el pin de reset del Arduino

// Instancia de la Pantalla OLED 0.96" I2C (Dirección habitual: 0x3C)
Adafruit_SSD1306 display(ANCHO_PANTALLA, ALTO_PANTALLA, &Wire, OLED_RESET);

// SoftwareSerial para el sensor PMS5003 (Pin 2 = RX, Pin 3 = TX)
SoftwareSerial pmsSerial(2, 3);

// Instancia del Sensor Ambiental BME280 (I2C)
Adafruit_BME280 bme;

// --- ESTRUCTURA DE DATOS PARA EL PMS5003 ---
struct PMSData {
  uint16_t pm10_env;
  uint16_t pm25_env;
  uint16_t pm100_env;
};

PMSData pms;

// --- VARIABLES GLOBALES DE TIEMPO Y LECTURA ---
float temperatura = 0.0;
float humedad = 0.0;
float presion = 0.0;
unsigned long ultimoEnvioJSON = 0;
const unsigned long INTERVALO_ENVIO_MS = 3000; // Enviar trama cada 3 segundos

// --- PROTOTIPOS DE FUNCIONES ---
bool leerPMS5003(PMSData *data);
void actualizarOLED();
void enviarTramaJSON();

void setup() {
  // 1. Comunicación USB Serial con la PC
  Serial.begin(9600);
  
  // 2. Comunicación Serial por Software con el PMS5003
  pmsSerial.begin(9600);

  // 3. Configuración del Buzzer
  pinMode(BUZZER_PIN, OUTPUT);
  digitalWrite(BUZZER_PIN, LOW);

  // 4. Inicialización de la Pantalla OLED
  if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    Serial.println(F("{\"error\":\"OLED no encontrada\"}"));
    while (true); // Detención de seguridad
  }

  // Pantalla de Inicio / Splashscreen
  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);
  display.setCursor(15, 20);
  display.println(F("AireCentinela AI"));
  display.setCursor(18, 38);
  display.println(F("Iniciando..."));
  display.display();

  // 5. Inicialización del BME280 (Prueba direcciones I2C 0x76 y 0x77)
  if (!bme.begin(0x76, &Wire)) {
    if (!bme.begin(0x77, &Wire)) {
      display.clearDisplay();
      display.setCursor(10, 25);
      display.println(F("Error: BME280"));
      display.display();
      while (true); // Detención de seguridad
    }
  }

  delay(2000); // Pausa de estabilización inicial
}

void loop() {
  // 1. Leer sensor climático BME280
  temperatura = bme.readTemperature();
  humedad = bme.readHumidity();
  presion = bme.readPressure() / 100.0F; // Convertir a hPa

  // 2. Leer sensor de partículas PMS5003
  bool pmsExitoso = leerPMS5003(&pms);

  // 3. Actualizar la interfaz gráfica de la pantalla OLED local
  actualizarOLED();

  // 4. Alerta audible rápida local si el polvo PM2.5 supera 35 µg/m³
  if (pmsExitoso && pms.pm25_env > 35) {
    digitalWrite(BUZZER_PIN, HIGH);
    delay(80);
    digitalWrite(BUZZER_PIN, LOW);
  }

  // 5. Enviar JSON estructurado por Serial cada 3 segundos exactos
  if (millis() - ultimoEnvioJSON >= INTERVALO_ENVIO_MS) {
    enviarTramaJSON();
    ultimoEnvioJSON = millis();
  }

  delay(100);
}

// --- FUNCIÓN PARA PROCESAR LA TRAMA DE 32 BYTES DEL PMS5003 ---
bool leerPMS5003(PMSData *data) {
  if (!pmsSerial.available()) return false;

  // Buscar el byte de cabecera 0x42
  if (pmsSerial.peek() != 0x42) {
    pmsSerial.read();
    return false;
  }

  if (pmsSerial.available() < 32) return false;

  uint8_t buffer[32];
  pmsSerial.readBytes(buffer, 32);

  // Validar cabecera 0x42 0x4D
  if (buffer[0] != 0x42 || buffer[1] != 0x4D) return false;

  // Verificación de Checksum
  uint16_t checksumCalculado = 0;
  for (int i = 0; i < 30; i++) {
    checksumCalculado += buffer[i];
  }

  uint16_t checksumRecibido = (buffer[30] << 8) | buffer[31];
  if (checksumCalculado != checksumRecibido) return false;

  // Extraer valores ambientales (PM1.0, PM2.5, PM10)
  data->pm10_env  = (buffer[10] << 8) | buffer[11];
  data->pm25_env  = (buffer[12] << 8) | buffer[13];
  data->pm100_env = (buffer[14] << 8) | buffer[15];

  return true;
}

// --- FUNCIÓN DE DIBUJO EN PANTALLA OLED 0.96" ---
void actualizarOLED() {
  display.clearDisplay();
  
  // Encabezado
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);
  display.setCursor(15, 0);
  display.println(F("AireCentinela AI"));
  display.drawLine(0, 10, 128, 10, SSD1306_WHITE);

  // Datos Climáticos (Parte Superior)
  display.setCursor(0, 15);
  display.print(F("Temp: "));
  display.print(temperatura, 1);
  display.print(F(" C"));

  display.setCursor(0, 26);
  display.print(F("Hum:  "));
  display.print(humedad, 0);
  display.print(F(" %"));

  // Separador Central
  display.drawLine(0, 37, 128, 37, SSD1306_WHITE);

  // Lectura Destacada de PM2.5 (Parte Inferior)
  display.setCursor(0, 43);
  display.print(F("PM2.5: "));
  
  display.setTextSize(2);
  display.print(pms.pm25_env);

  // Inversión visual en caso de alerta elevada
  if (pms.pm25_env > 35) {
    display.invertDisplay(true);
  } else {
    display.invertDisplay(false);
  }

  display.display();
}

// --- FUNCIÓN DE SERIALIZACIÓN JSON A PUERTO USB ---
void enviarTramaJSON() {
  // En ArduinoJson v7 se usa JsonDocument directamente
  JsonDocument doc;
  
  doc["temperatura"] = temperatura;
  doc["humedad"]     = humedad;
  doc["presion"]     = presion;
  doc["pm10"]        = pms.pm10_env;
  doc["pm25"]        = pms.pm25_env;
  doc["pm100"]       = pms.pm100_env;

  // Imprimir JSON hacia el puerto serial
  serializeJson(doc, Serial);
  Serial.println(); // Delimitador de nueva línea
}