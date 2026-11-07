#include <Wire.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BME280.h>
#include <Adafruit_CCS811.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <ArduinoJson.h>

// --- CONFIGURACIÓN DE PINES Y PANTALLA OLED ---
#define BUZZER_PIN 8
#define ANCHO_PANTALLA 128
#define ALTO_PANTALLA 64
#define OLED_RESET -1

// Instancia de la Pantalla OLED 0.96" I2C (Dirección habitual: 0x3C)
Adafruit_SSD1306 display(ANCHO_PANTALLA, ALTO_PANTALLA, &Wire, OLED_RESET);

// Instancias de los Sensores I2C
Adafruit_BME280 bme;
Adafruit_CCS811 ccs;

// --- VARIABLES GLOBALES DE TIEMPO Y LECTURA ---
float temperatura = 0.0;
float humedad = 0.0;
float presion = 0.0;
uint16_t eco2 = 400;
uint16_t tvoc = 0;

unsigned long ultimoEnvioJSON = 0;
const unsigned long INTERVALO_ENVIO_MS = 3000; // Enviar trama cada 3 segundos

// --- PROTOTIPOS DE FUNCIONES ---
void actualizarOLED();
void enviarTramaJSON();

void setup() {
  // 1. Comunicación USB Serial con la PC
  Serial.begin(9600);

  // 2. Configuración del Buzzer
  pinMode(BUZZER_PIN, OUTPUT);
  digitalWrite(BUZZER_PIN, LOW);

  // 3. Inicialización de la Pantalla OLED
  if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    Serial.println(F("{\"error\":\"OLED no encontrada\"}"));
    while (true);
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

  // 4. Inicialización del BME280 (I2C: 0x76 o 0x77)
  if (!bme.begin(0x76, &Wire)) {
    if (!bme.begin(0x77, &Wire)) {
      display.clearDisplay();
      display.setCursor(10, 25);
      display.println(F("Error: BME280"));
      display.display();
      while (true);
    }
  }

  // 5. Inicialización del CCS811 (I2C: 0x5A por defecto)
  if (!ccs.begin(0x5A)) {
    if (!ccs.begin(0x5B)) { // Probar dirección alternativa
      display.clearDisplay();
      display.setCursor(10, 25);
      display.println(F("Error: CCS811"));
      display.display();
      while (true);
    }
  }

  // Esperar a que el CCS811 esté listo para medir
  while (!ccs.available());

  delay(2000);
}

void loop() {
  // 1. Leer sensor climático BME280
  temperatura = bme.readTemperature();
  humedad = bme.readHumidity();
  presion = bme.readPressure() / 100.0F; // Convertir a hPa

  // 2. Leer sensor de gas CCS811 si hay datos disponibles
  if (ccs.available()) {
    if (!ccs.readData()) {
      eco2 = ccs.geteCO2();
      tvoc = ccs.getTVOC();
    }
  }

  // 3. Actualizar la interfaz gráfica de la pantalla OLED local
  actualizarOLED();

  // 4. Alerta audible rápida local si el eCO2 supera 1000 ppm
  if (eco2 > 1000) {
    digitalWrite(BUZZER_PIN, HIGH);
    delay(80);
    digitalWrite(BUZZER_PIN, LOW);
  }

  // 5. Enviar JSON estructurado por Serial cada 3 segundos
  if (millis() - ultimoEnvioJSON >= INTERVALO_ENVIO_MS) {
    enviarTramaJSON();
    ultimoEnvioJSON = millis();
  }

  delay(100);
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
  display.setCursor(0, 14);
  display.print(F("Temp: "));
  display.print(temperatura, 1);
  display.print(F(" C"));

  display.setCursor(0, 24);
  display.print(F("Hum:  "));
  display.print(humedad, 0);
  display.print(F(" %"));

  // Separador Central
  display.drawLine(0, 34, 128, 34, SSD1306_WHITE);

  // Lectura Destacada de eCO2 (Parte Inferior)
  display.setCursor(0, 38);
  display.print(F("eCO2: "));
  display.print(eco2);
  display.print(F(" ppm"));

  display.setCursor(0, 52);
  display.print(F("TVOC: "));
  display.print(tvoc);
  display.print(F(" ppb"));

  // Inversión visual en caso de alerta elevada (eCO2 > 1000 ppm)
  if (eco2 > 1000) {
    display.invertDisplay(true);
  } else {
    display.invertDisplay(false);
  }

  display.display();
}

// --- FUNCIÓN DE SERIALIZACIÓN JSON A PUERTO USB ---
void enviarTramaJSON() {
  JsonDocument doc;
  
  doc["temperatura"] = temperatura;
  doc["humedad"]     = humedad;
  doc["presion"]     = presion;
  doc["eco2"]        = eco2;
  doc["tvoc"]        = tvoc;

  serializeJson(doc, Serial);
  Serial.println(); // Delimitador de nueva línea para separador de lecturas
}