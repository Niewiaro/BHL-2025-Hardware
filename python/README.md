# MQTT Sensor Logger 📡

A lightweight Python application that subscribes to an MQTT topic and displays real-time telemetry data from ESP32 sensors (Temperature, Flame, Smoke, Sound, Vibration).

## 📋 Prerequisites

* **Python 3.10+** (Recommended: 3.12 or 3.13)
* A running MQTT Broker (e.g., Mosquitto via Docker)

## 🚀 Installation

1.  **Navigate to the python directory:**
    ```bash
    cd python
    ```

2.  **Create and activate a virtual environment (optional but recommended):**
    ```bash
    python -m venv .venv
    # Windows:
    .\.venv\Scripts\Activate
    # Mac/Linux:
    source .venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    *(Note: This project requires `paho-mqtt` and `python-dotenv`)*

## ⚙️ Configuration

Create a `.env` file in the root of the `python` directory and configure your MQTT settings:

```ini
# .env file
MQTT_BROKER=localhost
MQTT_PORT=1883
MQTT_TOPIC=sensor/all
````

## ▶️ Usage

Run the main script:

```bash
python main.py
```

## 📊 Example Output

When the connection is established and data starts flowing, you will see:

```text
⚙️  Loaded configuration: Config(broker=localhost, port=1883, topic=sensor/all)
⏳ Connecting to localhost:1883...
✅ Connected to MQTT Broker!
📡 Subscribed to topic: sensor/all

========================================
📥 Received data from: sensor/all
----------------------------------------
🌡️  Temperature : 32 °C
🔥 Flame       : Safe
💨 Smoke Level : 85 %
🔊 Sound       : 283 dB
📳 Vibration   : 20 Hz
========================================
```

## 🛠 Troubleshooting

  * **Connection Refused:** Ensure your Docker container for Mosquitto is running (`docker ps`).
  * **No Data:** Check if ESP32 and the Computer are on the same network (Hotspot/WiFi) and the IP in ESP32 code matches your computer's IP.
