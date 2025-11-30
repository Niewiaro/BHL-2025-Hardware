#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>

#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <Wire.h>
#include "DHTesp.h"

#include "secrets.h"

#define DEBUG true
#define FLAME_PIN 12 // flame sensor - digital
#define GAS_PIN 34   // MQ gas - analog
#define DHT_PIN 33   // DHT22 sensor pin
#define ADC_PIN 32   // motor current sensor - analog

// --- WiFi and MQTT Variables ---
const char *ssid = WIFI_SSID;
const char *password = WIFI_PASSWORD;
const char *mqtt_server = MQTT_SERVER_IP;

const char *topic = "sensor/all";

WiFiClient espClient;
PubSubClient client(espClient);
long lastMsg = 0;

// --- MPU6050 Variables ---
Adafruit_MPU6050 mpu;
int acceleration_x, acceleration_y, acceleration_z;
int gyro_x, gyro_y, gyro_z;
int temperature;

// --- Flame Sensor Variables ---
int flame_status = 1;

// --- Gas Sensor Variables ---
int gas_level = 0;

// --- DHT22 Variables ---
DHTesp dht;
float dht_temperature = 0;
float dht_humidity = 0;

// --- Mototr Current Sensor Variables ---
int motor_adc_value = 0;

void setup_wifi()
{
  delay(10);

  if (DEBUG)
  {
    Serial.println();
    Serial.print("Connecting to WiFi: ");
    Serial.println(ssid);
  }

  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED)
  {
    delay(500);
    if (DEBUG)
    {
      Serial.print(".");
    }
  }

  if (DEBUG)
  {
    Serial.println("");
    Serial.println("WiFi connected");
    Serial.println("ESP32 IP Address: ");
    Serial.println(WiFi.localIP());
  }
}

void reconnect()
{
  // Loop to reconnect to MQTT
  while (!client.connected())
  {
    if (DEBUG)
    {
      Serial.print("Connecting to MQTT...");
    }
    // Trying to connect with ID "ESP32Client"
    if (client.connect("ESP32Client"))
    {
      if (DEBUG)
      {
        Serial.println("connected!");
      }
    }
    else
    {
      if (DEBUG)
      {
        Serial.print("error, rc=");
        Serial.print(client.state());
        Serial.println(" trying again in 5 seconds");
      }
      // Wait 5 seconds before retrying
      delay(5000);
    }
  }
}

void setup()
{
  if (DEBUG)
  {
    Serial.begin(115200);
    while (!Serial)
    {
      delay(10);
    }
  }

  setup_wifi();
  client.setServer(mqtt_server, 1883);

  // --- MPU6050 Setup ---
  if (!mpu.begin())
  {
    Serial.println("Failed to find MPU6050 chip");
    while (1)
    {
      delay(10);
    }
  }
  if (DEBUG)
  {
    Serial.println("MPU6050 Found!");
  }

  // setupt motion detection
  mpu.setHighPassFilter(MPU6050_HIGHPASS_0_63_HZ);
  mpu.setMotionDetectionThreshold(1);
  mpu.setMotionDetectionDuration(20);
  mpu.setInterruptPinLatch(true); // Keep it latched.  Will turn off when reinitialized.
  mpu.setInterruptPinPolarity(true);
  mpu.setMotionInterrupt(true);

  // Digital sensors
  pinMode(FLAME_PIN, INPUT);

  // Analog sensors
  pinMode(14, INPUT);

  dht.setup(DHT_PIN, DHTesp::DHT22);
  pinMode(ADC_PIN, INPUT);
  analogSetPinAttenuation(ADC_PIN, ADC_0db);
}

void get_mpu_data()
{
  /* Get new sensor events with the readings */
  sensors_event_t a, g, temp;
  mpu.getEvent(&a, &g, &temp);

  acceleration_x = a.acceleration.x;
  acceleration_y = a.acceleration.y;
  acceleration_z = a.acceleration.z;

  gyro_x = g.gyro.x;
  gyro_y = g.gyro.y;
  gyro_z = g.gyro.z;

  temperature = temp.temperature;

  if (DEBUG)
  {
    Serial.print("Acceleration X: ");
    Serial.print(acceleration_x);
    Serial.print(", Y: ");
    Serial.print(acceleration_y);
    Serial.print(", Z: ");
    Serial.print(acceleration_z);
    Serial.println(" m/s^2");

    Serial.print("Rotation X: ");
    Serial.print(gyro_x);
    Serial.print(", Y: ");
    Serial.print(gyro_y);
    Serial.print(", Z: ");
    Serial.print(gyro_z);
    Serial.println(" rad/s");

    Serial.print("Temperature: ");
    Serial.print(temperature);
    Serial.println(" degC");
    Serial.println("");
  }
}

void get_flame_data()
{
  flame_status = digitalRead(FLAME_PIN);

  if (DEBUG)
  {
    if (flame_status)
    {
      Serial.println("🔥🔥🔥 FIRE DETECTED! 🔥🔥🔥");
    }
    else
    {
      Serial.println("Safe: No flame detected.");
    }
  }
}

void get_gas_data()
{
  gas_level = analogRead(GAS_PIN); // 0–4095 na ESP32
  if (DEBUG)
  {
    Serial.print("Gas Level: ");
    Serial.println(gas_level);
  }
}

void get_dht_data()
{
  TempAndHumidity data = dht.getTempAndHumidity();
  if (isnan(data.temperature) || isnan(data.humidity))
  {
    if (DEBUG)
    {
      Serial.println("Failed to read from DHT sensor!");
    }
  }
  else
  {
    dht_humidity = data.humidity;
    dht_temperature = data.temperature;
    if (DEBUG)
    {
      Serial.print("Temperature (°C): ");
      Serial.println(dht_temperature, 1);
      Serial.print("Humidity (%): ");
      Serial.println(dht_humidity, 1);
    }
  }
}

void get_motor_current_data()
{
  motor_adc_value = analogRead(ADC_PIN);
  if (DEBUG)
  {
    Serial.print("Motor: ");
    Serial.println(motor_adc_value);
  }
}

void loop()
{
  if (!client.connected())
  {
    reconnect();
  }
  client.loop();

  long now = millis();

  if (now - lastMsg > 1000)
  {
    lastMsg = now;

    // if (mpu.getMotionInterruptStatus())
    // {
    //   get_mpu_data();
    // }
    get_mpu_data();
    get_flame_data();
    get_gas_data();
    get_dht_data();
    get_motor_current_data();

    char msg[256];
    snprintf(msg, 256,
             "{\"acceleration_x\":%d,\"acceleration_y\":%d,\"acceleration_z\":%d,"
             "\"gyro_x\":%d,\"gyro_y\":%d,\"gyro_z\":%d,"
             "\"temperature\":%d,"
             "\"flame_status\":%d,"
             "\"gas_level\":%d,"
             "\"temperature_out\":%.2f,"
             "\"humidity_out\":%.2f,"
             "\"motor_adc\":%d"
             "}",
             acceleration_x, acceleration_y, acceleration_z,
             gyro_x, gyro_y, gyro_z,
             temperature,
             flame_status,
             gas_level,
             dht_temperature,
             dht_humidity,
             motor_adc_value);

    if (DEBUG)
    {
      Serial.print("Sending JSON: ");
      Serial.println(msg);
    }

    client.publish(topic, msg);
  }
}
