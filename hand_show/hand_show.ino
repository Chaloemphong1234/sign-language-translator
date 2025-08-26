#include <WiFi.h>
#include <PubSubClient.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>

// ================= LCD =================
LiquidCrystal_I2C lcd(0x3F, 16, 2);

// ================= WiFi =================
const char* ssid = "KeeMeo";
const char* password = "Aemmy1515";

// ================= MQTT =================
const char* mqtt_server = "broker.hivemq.com";
const int mqtt_port = 1883;
const char* mqtt_topic = "hand_sign/translation";

WiFiClient espClient;
PubSubClient client(espClient);

// ================= LED =================
#define LED_WIFI 2
#define LED_MQTT 4
#define LED_CHANGE 5  // LED แจ้งเปลี่ยนคำแปล

String lastPrediction = "";             // เก็บคำแปลล่าสุด
unsigned long changeLedTime = 0;       // เวลาเริ่มติด LED_CHANGE
const unsigned long changeLedDuration = 800; // 2 วินาที

// ================= Setup WiFi =================
void setup_wifi() {
  Serial.print("Connecting to WiFi");
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  digitalWrite(LED_WIFI, HIGH); // ติดค้างเมื่อเชื่อม WiFi สำเร็จ
  Serial.println("\n✅ WiFi connected");
  Serial.print("IP: "); Serial.println(WiFi.localIP());

  lcd.clear();
  lcd.setCursor(0,0);
  lcd.print("HAND TRANSLATION:");
  lcd.setCursor(0,1);
  lcd.print("Connecting...");
}

// ================= MQTT Callback =================
void callback(char* topic, byte* payload, unsigned int length) {
  String predictedText = "";
  for (unsigned int i = 0; i < length; i++) predictedText += (char)payload[i];

  Serial.print("📩 MQTT Message: "); Serial.println(predictedText);

  // ถ้าคำเปลี่ยน → ติด LED_CHANGE 2 วินาที
  if (predictedText != lastPrediction) {
    lastPrediction = predictedText;
    digitalWrite(LED_CHANGE, HIGH);
    changeLedTime = millis();
  }

  // แสดงผลบน LCD (บรรทัดสอง)
  lcd.setCursor(0,1);
  lcd.print("                "); // เคลียร์บรรทัด
  lcd.setCursor(0,1);
  lcd.print(predictedText.substring(0, min(16, (int)predictedText.length())));
}

// ================= MQTT Reconnect =================
void reconnect() {
  while (!client.connected()) {
    Serial.print("Connecting MQTT...");
    if (client.connect("ESP32Client")) {
      client.subscribe(mqtt_topic);
      digitalWrite(LED_MQTT, HIGH); // ติดค้างเมื่อ MQTT connected
      Serial.println("✅ MQTT connected");
      lcd.setCursor(0,0);
      lcd.print("HAND TRANSLATION:");
    } else {
      Serial.print("❌ failed, rc=");
      Serial.println(client.state());
      delay(4000);
    }
  }
}

// ================= Setup =================
void setup() {
  Serial.begin(115200);

  pinMode(LED_WIFI, OUTPUT);
  pinMode(LED_MQTT, OUTPUT);
  pinMode(LED_CHANGE, OUTPUT);
  digitalWrite(LED_WIFI, LOW);
  digitalWrite(LED_MQTT, LOW);
  digitalWrite(LED_CHANGE, LOW);

  lcd.init();
  lcd.backlight();

  setup_wifi();
  client.setServer(mqtt_server, mqtt_port);
  client.setCallback(callback);
}

// ================= Loop =================
void loop() {
  if (!client.connected()) reconnect();
  client.loop();

  // ปิด LED_CHANGE หลัง 2 วินาที โดยไม่บล็อค
  if (digitalRead(LED_CHANGE) == HIGH && (millis() - changeLedTime >= changeLedDuration)) {
    digitalWrite(LED_CHANGE, LOW);
  }

  // เช็ค WiFi
  if (WiFi.status() != WL_CONNECTED) {
    digitalWrite(LED_WIFI, LOW);
    digitalWrite(LED_MQTT, LOW);
    lcd.clear();
    lcd.setCursor(0,0);
    lcd.print("WiFi Lost!");
    setup_wifi();
  }
}
