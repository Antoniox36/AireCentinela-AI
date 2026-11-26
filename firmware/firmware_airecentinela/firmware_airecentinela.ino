#include <Wire.h>
#include <SoftwareWire.h>
#include <Adafruit_CCS811.h>
#include <ArduinoJson.h>

#define BUZZER_PIN 8
#define BME280_ADDR 0x76

#define BUZZER_ON  LOW
#define BUZZER_OFF HIGH

SoftwareWire busBME(A2, A3); // SDA = A2, SCL = A3
Adafruit_CCS811 ccs;         // SDA = A4, SCL = A5

uint16_t dig_T1;
int16_t  dig_T2, dig_T3;
uint16_t dig_P1;
int16_t  dig_P2, dig_P3, dig_P4, dig_P5, dig_P6, dig_P7, dig_P8, dig_P9;
uint8_t  dig_H1, dig_H3;
int16_t  dig_H2, dig_H4, dig_H5;
int8_t   dig_H6;
int32_t  t_fine;

float temperatura = 0.0;
float humedad = 0.0;
float presion = 1013.25;
uint16_t eco2 = 400;
uint16_t tvoc = 0;

bool bmeOk = false;
bool ccsOk = false;
bool ccsListo = false;

// 0 = Silencio, 1 = Pulso lento, 2 = Pulso rápido, 3 = Continuo
uint8_t nivelAlarmaIA = 0;
unsigned long ultimaOrdenIA = 0;
unsigned long ultimoEnvioJSON = 0;
const unsigned long INTERVALO_ENVIO_MS = 1000;

unsigned long ultimoCambioBuzzer = 0;
bool estadoBuzzerActivo = false;

bool iniciarBME280();
void leerBME280();
void leerComandosIA();
void gestionarAlarmaSonora();
void enviarTramaJSON();

void setup() {
  digitalWrite(BUZZER_PIN, BUZZER_OFF);
  pinMode(BUZZER_PIN, OUTPUT);
  digitalWrite(BUZZER_PIN, BUZZER_OFF);

  Serial.begin(9600);
  Serial.setTimeout(20);

  Wire.begin();
  busBME.begin();
  busBME.setClock(50000L);
  delay(300);

  for (int i = 0; i < 5 && !bmeOk; i++) {
    bmeOk = iniciarBME280();
    if (!bmeOk) delay(250);
  }

  for (int i = 0; i < 5 && !ccsOk; i++) {
    ccsOk = ccs.begin(0x5A);
    if (!ccsOk) delay(250);
  }
}

void loop() {
  leerComandosIA();

  if (!bmeOk) bmeOk = iniciarBME280();
  if (!ccsOk) ccsOk = ccs.begin(0x5A);

  if (!bmeOk || !ccsOk) {
    digitalWrite(BUZZER_PIN, BUZZER_OFF);
    Serial.print(F("{\"error\":\"Esperando sensores -> BME280:"));
    Serial.print(bmeOk ? F("OK") : F("FALLO"));
    Serial.print(F(" CCS811:"));
    Serial.print(ccsOk ? F("OK") : F("FALLO"));
    Serial.println(F("\"}"));
    delay(1500);
    return;
  }

  leerBME280();

  if (ccs.available()) {
    if (!ccs.readData()) {
      uint16_t lecturaCO2 = ccs.geteCO2();
      if (lecturaCO2 >= 400) {
        eco2 = lecturaCO2;
        tvoc = ccs.getTVOC();
        ccsListo = true;
      }
    }
  }

  gestionarAlarmaSonora();

  if (ccsListo && (millis() - ultimoEnvioJSON >= INTERVALO_ENVIO_MS)) {
    enviarTramaJSON();
    ultimoEnvioJSON = millis();
  }

  delay(20);
}

void leerComandosIA() {
  while (Serial.available() > 0) {
    char c = (char)Serial.read();
    if (c >= '0' && c <= '3') {
      nivelAlarmaIA = (uint8_t)(c - '0');
      ultimaOrdenIA = millis();
    }
  }
  if (nivelAlarmaIA > 0 && (millis() - ultimaOrdenIA > 6000)) {
    nivelAlarmaIA = 0;
  }
}

void gestionarAlarmaSonora() {
  if (!ccsListo || nivelAlarmaIA == 0) {
    estadoBuzzerActivo = false;
    digitalWrite(BUZZER_PIN, BUZZER_OFF);
    return;
  }

  if (nivelAlarmaIA >= 3) {
    estadoBuzzerActivo = true;
    digitalWrite(BUZZER_PIN, BUZZER_ON);
    return;
  }

  unsigned long intervaloSilencioMs = (nivelAlarmaIA == 2) ? 300 : 1200;
  const unsigned long DURACION_PITIDO_MS = 80;
  unsigned long ahora = millis();

  if (estadoBuzzerActivo) {
    if (ahora - ultimoCambioBuzzer >= DURACION_PITIDO_MS) {
      estadoBuzzerActivo = false;
      digitalWrite(BUZZER_PIN, BUZZER_OFF);
      ultimoCambioBuzzer = ahora;
    }
  } else {
    if (ahora - ultimoCambioBuzzer >= intervaloSilencioMs) {
      estadoBuzzerActivo = true;
      digitalWrite(BUZZER_PIN, BUZZER_ON);
      ultimoCambioBuzzer = ahora;
    }
  }
}

uint8_t leerReg8(uint8_t reg) {
  busBME.beginTransmission(BME280_ADDR);
  busBME.write(reg);
  busBME.endTransmission();
  busBME.requestFrom((uint8_t)BME280_ADDR, (uint8_t)1);
  return busBME.read();
}

uint16_t leerReg16LE(uint8_t reg) {
  busBME.beginTransmission(BME280_ADDR);
  busBME.write(reg);
  busBME.endTransmission();
  busBME.requestFrom((uint8_t)BME280_ADDR, (uint8_t)2);
  uint16_t lo = busBME.read();
  uint16_t hi = busBME.read();
  return (hi << 8) | lo;
}

void escribirReg8(uint8_t reg, uint8_t val) {
  busBME.beginTransmission(BME280_ADDR);
  busBME.write(reg);
  busBME.write(val);
  busBME.endTransmission();
}

bool iniciarBME280() {
  busBME.beginTransmission(BME280_ADDR);
  if (busBME.endTransmission() != 0) return false;

  uint8_t chipID = leerReg8(0xD0);
  if (chipID != 0x60 && chipID != 0x58) return false;

  dig_T1 = leerReg16LE(0x88);
  dig_T2 = (int16_t)leerReg16LE(0x8A);
  dig_T3 = (int16_t)leerReg16LE(0x8C);

  dig_P1 = leerReg16LE(0x8E);
  dig_P2 = (int16_t)leerReg16LE(0x90);
  dig_P3 = (int16_t)leerReg16LE(0x92);
  dig_P4 = (int16_t)leerReg16LE(0x94);
  dig_P5 = (int16_t)leerReg16LE(0x96);
  dig_P6 = (int16_t)leerReg16LE(0x98);
  dig_P7 = (int16_t)leerReg16LE(0x9A);
  dig_P8 = (int16_t)leerReg16LE(0x9C);
  dig_P9 = (int16_t)leerReg16LE(0x9E);

  dig_H1 = leerReg8(0xA1);
  dig_H2 = (int16_t)leerReg16LE(0xE1);
  dig_H3 = leerReg8(0xE3);
  dig_H4 = ((int16_t)leerReg8(0xE4) << 4) | (leerReg8(0xE5) & 0x0F);
  dig_H5 = ((int16_t)leerReg8(0xE6) << 4) | (leerReg8(0xE5) >> 4);
  dig_H6 = (int8_t)leerReg8(0xE7);

  escribirReg8(0xF2, 0x01);
  escribirReg8(0xF4, 0x27);
  escribirReg8(0xF5, 0xA0);
  delay(50);
  return true;
}

void leerBME280() {
  busBME.beginTransmission(BME280_ADDR);
  busBME.write(0xF7);
  busBME.endTransmission();
  busBME.requestFrom((uint8_t)BME280_ADDR, (uint8_t)8);

  int32_t adc_P = ((uint32_t)busBME.read() << 12) | ((uint32_t)busBME.read() << 4) | (busBME.read() >> 4);
  int32_t adc_T = ((uint32_t)busBME.read() << 12) | ((uint32_t)busBME.read() << 4) | (busBME.read() >> 4);
  int32_t adc_H = ((uint32_t)busBME.read() << 8)  | (uint32_t)busBME.read();

  int32_t var1 = ((((adc_T >> 3) - ((int32_t)dig_T1 << 1))) * ((int32_t)dig_T2)) >> 11;
  int32_t var2 = (((((adc_T >> 4) - ((int32_t)dig_T1)) * ((adc_T >> 4) - ((int32_t)dig_T1))) >> 12) * ((int32_t)dig_T3)) >> 14;
  t_fine = var1 + var2;
  temperatura = ((t_fine * 5 + 128) >> 8) / 100.0F;

  int64_t p_var1 = ((int64_t)t_fine) - 128000;
  int64_t p_var2 = p_var1 * p_var1 * (int64_t)dig_P6;
  p_var2 = p_var2 + ((p_var1 * (int64_t)dig_P5) << 17);
  p_var2 = p_var2 + (((int64_t)dig_P4) << 35);
  p_var1 = ((p_var1 * p_var1 * (int64_t)dig_P3) >> 8) + ((p_var1 * (int64_t)dig_P2) << 12);
  p_var1 = (((((int64_t)1) << 47) + p_var1)) * ((int64_t)dig_P1) >> 33;
  if (p_var1 != 0) {
    int64_t p = 1048576 - adc_P;
    p = (((p << 31) - p_var2) * 3125) / p_var1;
    p_var1 = (((int64_t)dig_P9) * (p >> 13) * (p >> 13)) >> 25;
    p_var2 = (((int64_t)dig_P8) * p) >> 19;
    p = ((p + p_var1 + p_var2) >> 8) + (((int64_t)dig_P7) << 4);
    presion = (float)p / 25600.0F;
  }

  if (adc_H == 0x8000) {
    humedad = 0.0;
  } else {
    int32_t v_x1_u32r = (t_fine - ((int32_t)76800));
    v_x1_u32r = (((((adc_H << 14) - (((int32_t)dig_H4) << 20) - (((int32_t)dig_H5) * v_x1_u32r)) + ((int32_t)16384)) >> 15) *
                 (((((((v_x1_u32r * ((int32_t)dig_H6)) >> 10) * (((v_x1_u32r * ((int32_t)dig_H3)) >> 11) + ((int32_t)32768))) >> 10) + ((int32_t)2097152)) *
                   ((int32_t)dig_H2) + 8192) >> 14));
    v_x1_u32r = (v_x1_u32r - (((((v_x1_u32r >> 15) * (v_x1_u32r >> 15)) >> 7) * ((int32_t)dig_H1)) >> 4));
    v_x1_u32r = (v_x1_u32r < 0 ? 0 : v_x1_u32r);
    v_x1_u32r = (v_x1_u32r > 419430400 ? 419430400 : v_x1_u32r);
    humedad = (float)(v_x1_u32r >> 12) / 1024.0F;
  }
}

void enviarTramaJSON() {
  JsonDocument doc;
  doc["temperatura"] = round(temperatura * 100.0) / 100.0;
  doc["humedad"]     = round(humedad * 100.0) / 100.0;
  doc["presion"]     = round(presion * 100.0) / 100.0;
  doc["eco2"]        = eco2;
  doc["tvoc"]        = tvoc;

  serializeJson(doc, Serial);
  Serial.println();
}
