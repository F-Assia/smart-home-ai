#include <Arduino.h>
#include <ArduinoJson.h>
#include <DHT.h>
#include <ESP32Servo.h>
#include <HTTPClient.h>
#include <WiFi.h>

const char *WIFI_SSID = "Wokwi-GUEST";
const char *WIFI_PASSWORD = "";

// URL de votre serveur Flask (mettez bien l'IP ou l'URL fonctionnelle qui a débloqué le DHT22)
const char *FLASK_BASE_URL = "http://192.168.0.108:5000";

const int DHT_PIN = 4;
const int LED_PIN = 13;
const int SERVO_PIN = 18;

DHT dht(DHT_PIN, DHT22);
Servo fanServo;

unsigned long lastSync = 0;
const unsigned long SYNC_INTERVAL_MS = 3000;

void connectWiFi()
{
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED)
  {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected");
}

String url(const String &path)
{
  return String(FLASK_BASE_URL) + path;
}

void postTemperatureAndSync(float temperature) {
  if (WiFi.status() != WL_CONNECTED) return;

  HTTPClient http;
  http.begin(url("/api/temperature"));
  http.addHeader("Content-Type", "application/json");

  StaticJsonDocument<128> body;
  body["temperature"] = temperature;
  String payload;
  serializeJson(body, payload);

  int code = http.POST(payload);
  Serial.printf("POST /api/temperature -> %d\n", code);

  if (code == 200) {
    String responsePayload = http.getString();
    
    // Le JSON étant désormais ultra-léger, 256 ou 512 octets suffisent largement !
    StaticJsonDocument<512> doc; 
    DeserializationError error = deserializeJson(doc, responsePayload);

    if (!error) {
      if (doc.containsKey("state")) {
        JsonObject state = doc["state"];
        
        bool light = state["light"] | false;
        int fan = state["fan"] | 0;
        fan = constrain(fan, 0, 100);

        // Application physique immédiate sur les broches de la carte
        digitalWrite(LED_PIN, light ? HIGH : LOW);

        int angle = map(fan, 0, 100, 0, 180);
        fanServo.write(angle);

        Serial.printf("✨ Synchro OK ! LED=%s | Fan=%d%% (Angle: %d°)\n", 
                      light ? "ON" : "OFF", fan, angle);
      }
    } else {
      Serial.printf("❌ Erreur décodage JSON : %s\n", error.c_str());
    }
  } else {
    Serial.printf("❌ Erreur backend. Code HTTP: %d\n", code);
  }

  http.end();
}

void setup()
{
  Serial.begin(115200);
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW); // Éteinte par défaut au démarrage

  dht.begin();

  // Configuration propre du Servo pour Wokwi (min/max en microsecondes)
  fanServo.attach(SERVO_PIN, 500, 2400);
  fanServo.write(0); // Position 0° au démarrage

  connectWiFi();
}

void loop()
{
  if (millis() - lastSync >= SYNC_INTERVAL_MS)
  {
    lastSync = millis();

    float tempReading = dht.readTemperature();
    if (!isnan(tempReading))
    {
      Serial.printf("Temperature lue: %.2f C\n", tempReading);
      // Envoie la température ET récupère immédiatement les ordres pour la LED et le Servo
      postTemperatureAndSync(tempReading);
    }
    else
    {
      Serial.println("Échec de lecture du capteur DHT22 !");
    }
  }
}