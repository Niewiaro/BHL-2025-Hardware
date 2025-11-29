import os
import json
import sys
from typing import Any, Dict

import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """
    Configuration class to handle environment variables and settings.
    """

    def __init__(self):
        """
        Initializes configuration by reading from environment variables.
        Falls back to default values if .env is missing specific keys.
        """
        self.broker = os.getenv("MQTT_BROKER", "localhost")
        self.port = int(os.getenv("MQTT_PORT", 1883))
        self.topic = os.getenv("MQTT_TOPIC", "sensor/all")

    def __repr__(self):
        return f"Config(broker={self.broker}, port={self.port}, topic={self.topic})"


def on_connect(
    client: mqtt.Client, userdata: Any, flags: Dict, rc: int, properties: Any = None
) -> None:
    """
    Callback function triggered when the client connects to the broker.

    Args:
        client: The MQTT client instance.
        userdata: User data defined in Client().
        flags: Response flags sent by the broker.
        rc: Connection result code (0 = success).
        properties: MQTT v5.0 properties (optional).
    """
    if rc == 0:
        print(f"✅ Connected to MQTT Broker!")
        # Subscribing in on_connect ensures we resubscribe if connection is lost
        client.subscribe(userdata.topic)
        print(f"📡 Subscribed to topic: {userdata.topic}")
    else:
        print(f"⚠️ Connection failed with code: {rc}")


def on_message(client: mqtt.Client, userdata: Any, msg: mqtt.MQTTMessage):
    """
    Callback function triggered when a message is received.

    Args:
        client: The MQTT client instance.
        userdata: User data (contains the Config object).
        msg: The actual message object containing topic and payload.
    """
    try:
        # 1. Decode payload
        payload_str = msg.payload.decode()

        # 2. Parse JSON
        data = json.loads(payload_str)

        # 3. specific display logic
        print("\n" + "=" * 40)
        print(f"📥 Received data from: {msg.topic}")
        print("-" * 40)
        print(f"🌡️  Temperature : {data.get('temperature', 'N/A')} °C")
        print(
            f"🔥 Flame       : {'DETECTED' if data.get('flame') == 0 else 'Safe'}"
        )  # Assuming 0 is detected
        print(f"💨 Smoke Level : {data.get('smoke', 0)} %")
        print(f"🔊 Sound       : {data.get('sound', 0)} dB")
        print(f"📳 Vibration   : {data.get('vibration', 0)} Hz")
        print("=" * 40)

    except json.JSONDecodeError:
        print(f"⚠️ Failed to decode JSON: {msg.payload}")
    except Exception as e:
        print(f"❌ Error processing message: {e}")


def main():
    """
    Main execution function.
    Sets up the MQTT client, loads config, and starts the loop.
    """
    # 1. Load Configuration
    try:
        config = Config()
        print(f"⚙️  Loaded configuration: {config}")
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        sys.exit(1)

    # 2. Initialize MQTT Client (using protocol v2.x standards)
    # We pass 'config' as userdata so callbacks can access it if needed
    client = mqtt.Client(
        callback_api_version=CallbackAPIVersion.VERSION2, userdata=config
    )

    # 3. Assign Callbacks
    client.on_connect = on_connect
    client.on_message = on_message

    # 4. Connect to Broker
    print(f"⏳ Connecting to {config.broker}:{config.port}...")
    try:
        client.connect(config.broker, config.port, 60)
    except Exception as e:
        print(f"❌ Could not connect to broker: {e}")
        print("   Is Docker running? Is the IP correct?")
        sys.exit(1)

    # 5. Start the Loop (Blocking)
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("\n🛑 Disconnected by user. Exiting...")
        client.disconnect()


if __name__ == "__main__":
    main()
