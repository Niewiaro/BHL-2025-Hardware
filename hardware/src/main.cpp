#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>

#include "secrets.h"

const char *ssid = WIFI_SSID;
const char *password = WIFI_PASSWORD;
const char *mqtt_server = MQTT_SERVER_IP;

const char *topic = "sensor/all";

WiFiClient espClient;
PubSubClient client(espClient);
long lastMsg = 0;
int value = 0;

void setup_wifi()
{
  delay(10);
  Serial.println();
  Serial.print("Connecting to WiFi: ");
  Serial.println(ssid);

  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED)
  {
    delay(500);
    Serial.print(".");
  }

  Serial.println("");
  Serial.println("WiFi connected");
  Serial.println("ESP32 IP Address: ");
  Serial.println(WiFi.localIP());
}

void reconnect()
{
  // Loop to reconnect to MQTT
  while (!client.connected())
  {
    Serial.print("Connecting to MQTT...");
    // Trying to connect with ID "ESP32Client"
    if (client.connect("ESP32Client"))
    {
      Serial.println("connected!");
    }
    else
    {
      Serial.print("error, rc=");
      Serial.print(client.state());
      Serial.println(" trying again in 5 seconds");
      delay(5000);
    }
  }
}

void setup()
{
  Serial.begin(115200);
  setup_wifi();
  client.setServer(mqtt_server, 1883);
}

void loop()
{
  if (!client.connected())
  {
    reconnect();
  }
  client.loop();

  long now = millis();
  if (now - lastMsg > 2000)
  {
    lastMsg = now;
    value++;

    int temp = 20 + (value % 15);
    int flame = value % 2;
    int smoke = (value * 5) % 100;
    int sound = (value * 3) % 1024;
    int vibration = (value * 10) % 50;

    char msg[256];
    snprintf(msg, 256,
             "{\"temperature\":%d,\"flame\":%d,\"smoke\":%d,\"sound\":%d,\"vibration\":%d}",
             temp, flame, smoke, sound, vibration);

    Serial.print("Sending JSON: ");
    Serial.println(msg);

    client.publish(topic, msg);
  }
}
