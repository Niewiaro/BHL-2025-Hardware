import streamlit as st
import pandas as pd
import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion
from dotenv import load_dotenv
import os
import json
import time
from typing import Any, Dict, List, Optional
import logging

# --- LOGGING SETUP ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# --- CONFIG ---
load_dotenv()


class AppConfig:
    """Central configuration class."""

    BROKER: str = os.getenv("MQTT_BROKER", "localhost")
    PORT: int = int(os.getenv("MQTT_PORT", 1883))
    TOPIC: str = os.getenv("MQTT_TOPIC", "sensor/+")
    KEEPALIVE: int = int(os.getenv("MQTT_KEEPALIVE", 60))
    PAGE_TITLE: str = "Industrial IoT Monitor"
    PAGE_ICON: str = "🏭"


# --- STREAMLIT PAGE SETUP ---
st.set_page_config(
    page_title=AppConfig.PAGE_TITLE,
    page_icon=AppConfig.PAGE_ICON,
    layout="wide",
    initial_sidebar_state="expanded",
)


# --- DATA STRUCTURES ---
class DeviceData:
    def __init__(self, name: str):
        self.name = name
        self.history: List[Dict[str, Any]] = []
        self.latest: Dict[str, Any] = {}
        self.previous: Dict[str, Any] = {}
        self.last_update: float = time.time()
        self.max_history: int = 100


class MQTTState:
    def __init__(self):
        self.connected: bool = False
        self.devices: Dict[str, DeviceData] = {}


@st.cache_resource
def get_mqtt_state() -> MQTTState:
    return MQTTState()


# --- MQTT CALLBACKS ---
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
        userdata.connected = True
        client.subscribe(AppConfig.TOPIC)
        logger.info(f"Connected to MQTT Broker: {AppConfig.BROKER}")
    else:
        userdata.connected = False
        logger.error(f"Failed to connect, return code {rc}")


def on_disconnect(
    client: mqtt.Client, userdata: Any, rc: int, properties: Any = None
) -> None:
    """
    Callback function triggered when the client disconnects from the broker.
    """
    userdata.connected = False
    logger.warning("Disconnected from MQTT Broker")


def on_message(client: mqtt.Client, userdata: Any, msg: mqtt.MQTTMessage) -> None:
    """
    Callback function triggered when a message is received.

    Args:
        client: The MQTT client instance.
        userdata: User data (contains the Config object).
        msg: The actual message object containing topic and payload.
    """
    try:
        # 1. Wyciągnij nazwę urządzenia z tematu
        # np. sensor/jadwiga -> jadwiga
        topic_parts = msg.topic.split("/")
        device_name = topic_parts[-1] if len(topic_parts) > 1 else "Unknown"

        # 2. Parsuj JSON
        payload = json.loads(msg.payload.decode())

        # 3. Jeśli to nowe urządzenie, dodaj je do słownika devices
        if device_name not in userdata.devices:
            # Tworzymy nową instancję DeviceData
            userdata.devices[device_name] = DeviceData(device_name)
            logger.info(f"New Device Detected: {device_name}")

        # 4. Pobierz obiekt konkretnego urządzenia
        device = userdata.devices[device_name]

        # 5. Zapisz dane W KONKRETNYM URZĄDZENIU (a nie w userdata.latest!)
        if device.latest:
            device.previous = device.latest.copy()

        device.latest = payload
        device.history.append(payload)
        device.last_update = time.time()

        # Limit historii
        if len(device.history) > device.max_history:
            device.history.pop(0)

    except json.JSONDecodeError:
        logger.error(f"Invalid JSON received: {msg.payload}")
    except Exception as e:
        logger.error(f"Error processing message: {e}")


# --- MQTT CLIENT FACTORY ---
@st.cache_resource
def start_mqtt_client() -> Optional[mqtt.Client]:
    state = get_mqtt_state()
    client = mqtt.Client(
        callback_api_version=CallbackAPIVersion.VERSION2, userdata=state
    )
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message

    try:
        client.connect(AppConfig.BROKER, AppConfig.PORT, AppConfig.KEEPALIVE)
        client.loop_start()
        return client
    except Exception as e:
        logger.critical(f"Could not connect to broker: {e}")
        return None


# --- UI COMPONENTS ---
def render_sidebar(state: MQTTState):
    """Renders the sidebar configuration and status."""
    with st.sidebar:
        st.header(f"{AppConfig.PAGE_ICON} {AppConfig.PAGE_TITLE}")

        st.divider()

        st.subheader("🌐 Network Status")

        # Connection Status Indicator
        if state.connected:
            st.success(f"🟢 Connected: {AppConfig.BROKER}")
        else:
            st.error("🔴 Disconnected")

        st.divider()
        st.subheader("⚙️ Configuration")
        st.info(f"Devices connected: {len(state.devices)}")
        st.badge(f"Topic: `{AppConfig.TOPIC}`", color="blue", icon="📓")
        st.divider()


def calculate_delta(current: float, previous: float) -> Optional[float]:
    """Helper to calculate metric delta."""
    if previous is None:
        return None
    return round(current - previous, 2)


def render_device_tab(device: DeviceData):
    data = device.latest
    prev = device.previous

    st.caption(
        f"Last update: {time.strftime('%H:%M:%S', time.localtime(device.last_update))}"
    )

    # --- KPI METRICS ---
    # Używamy dynamicznego układu - wyświetlamy tylko to, co jest w danych

    # Row 1: Environment & Status
    c1, c2, c3 = st.columns(3)
    c4, c5, c6 = st.columns(3)

    with c1:
        if "temperature" in data:
            val = data["temperature"]
            p_val = prev.get("temperature") if prev else None
            st.metric(
                label="Temp (In)",
                value=f"{val} °C",
                delta=(calculate_delta(val, p_val)),
                help="Ambient temperature reading",
                border=True,
                chart_data=(
                    pd.DataFrame(device.history)["temperature"]
                    if device.history
                    else None
                ),
            )

    with c2:
        if "temperature_out" in data:
            val = data["temperature_out"]
            p_val = prev.get("temperature_out") if prev else None
            st.metric(
                "Temp (Out)",
                f"{val} °C",
                calculate_delta(val, p_val),
                border=True,
                help="Outside temperature reading",
                chart_data=(
                    pd.DataFrame(device.history)["temperature_out"]
                    if device.history
                    else None
                ),
            )

    with c3:
        if "humidity_out" in data:
            val = data["humidity_out"]
            p_val = prev.get("humidity_out") if prev else None
            st.metric(
                "Humidity",
                f"{val} %",
                calculate_delta(val, p_val),
                border=True,
                help="Outside humidity reading",
                chart_data=(
                    pd.DataFrame(device.history)["humidity_out"]
                    if device.history
                    else None
                ),
            )

    with c4:
        if "gas_level" in data:
            val = data["gas_level"]
            p_val = prev.get("gas_level") if prev else None
            status = (
                "⚠️ DANGER" if val > 1000 else "⚠️ WARNING" if val > 700 else "✅ SAFE"
            )
            st.metric(
                "Gas Sensor",
                f"{val} ({status})",
                calculate_delta(val, p_val),
                delta_color="inverse",
                border=True,
                help="Gas concentration level (ppm)",
                chart_data=(
                    pd.DataFrame(device.history)["gas_level"]
                    if device.history
                    else None
                ),
            )

    with c5:
        if "motor_adc" in data:
            val = data["motor_adc"]
            p_val = prev.get("motor_adc") if prev else None
            st.metric(
                "Motor ADC",
                f"{val}",
                calculate_delta(val, p_val),
                border=True,
                help="Motor flow ADC value",
                chart_data=(
                    pd.DataFrame(device.history)["motor_adc"]
                    if device.history
                    else None
                ),
            )

    with c6:
        if "flame_status" in data:
            val = data["flame_status"]
            # 0 zazwyczaj oznacza wykrycie płomienia w tanich czujnikach cyfrowych, ale zależy od konfiguracji
            label = "🔥 FIRE!" if val == 1 else "✅ Safe"
            st.metric("Flame", label, border=True, help="Flame detection status")

    # Row 2: Mechanics (Accel/Gyro)
    # Wyświetlamy tylko jeśli są dane z akcelerometru
    if "acceleration_x" in data:
        st.markdown("##### ⚙️ Motion Data")
        m1, m2, m3, m4, m5, m6 = st.columns(6)

        acc_x = data.get("acceleration_x")
        acc_x_prev = prev.get("acceleration_x") if prev else None
        m1.metric(
            "Acc X",
            acc_x,
            border=True,
            help="Acceleration X-axis",
            delta=calculate_delta(acc_x, acc_x_prev),
            chart_data=(
                pd.DataFrame(device.history)["acceleration_x"]
                if device.history
                else None
            ),
        )
        acc_y = data.get("acceleration_y")
        acc_y_prev = prev.get("acceleration_y") if prev else None
        m2.metric(
            "Acc Y",
            acc_y,
            border=True,
            help="Acceleration Y-axis",
            delta=calculate_delta(acc_y, acc_y_prev),
            chart_data=(
                pd.DataFrame(device.history)["acceleration_y"]
                if device.history
                else None
            ),
        )
        acc_z = data.get("acceleration_z")
        acc_z_prev = prev.get("acceleration_z") if prev else None
        m3.metric(
            "Acc Z",
            acc_z,
            border=True,
            help="Acceleration Z-axis",
            delta=calculate_delta(acc_z, acc_z_prev),
            chart_data=(
                pd.DataFrame(device.history)["acceleration_z"]
                if device.history
                else None
            ),
        )
        gyro_x = data.get("gyro_x")
        gyro_x_prev = prev.get("gyro_x") if prev else None
        m4.metric(
            "Gyro X",
            gyro_x,
            border=True,
            help="Gyroscope X-axis",
            delta=calculate_delta(gyro_x, gyro_x_prev),
            chart_data=(
                pd.DataFrame(device.history)["gyro_x"] if device.history else None
            ),
        )
        gyro_y = data.get("gyro_y")
        gyro_y_prev = prev.get("gyro_y") if prev else None
        m5.metric(
            "Gyro Y",
            gyro_y,
            border=True,
            help="Gyroscope Y-axis",
            delta=calculate_delta(gyro_y, gyro_y_prev),
            chart_data=(
                pd.DataFrame(device.history)["gyro_y"] if device.history else None
            ),
        )
        gyro_z = data.get("gyro_z")
        gyro_z_prev = prev.get("gyro_z") if prev else None
        m6.metric(
            "Gyro Z",
            gyro_z,
            border=True,
            help="Gyroscope Z-axis",
            delta=calculate_delta(gyro_z, gyro_z_prev),
            chart_data=(
                pd.DataFrame(device.history)["gyro_z"] if device.history else None
            ),
        )

    st.divider()

    # --- CHARTS ---
    if len(device.history) > 2:
        df = pd.DataFrame(device.history)

        tab_env, tab_mot = st.tabs(["🌡️ Environment Charts", "⚙️ Mechanical Analysis"])

        with tab_env:
            # Wykres temperatur
            cols_temp = [
                c for c in ["temperature", "temperature_out"] if c in df.columns
            ]
            if cols_temp:
                st.line_chart(df[cols_temp], height=250)

            # Wykres gazu i wilgotności
            c_left, c_right = st.columns(2)
            if "gas_level" in df.columns:
                c_left.area_chart(df["gas_level"], color="#ffaa00", height=200)
            if "humidity_out" in df.columns:
                c_right.line_chart(df["humidity_out"], color="#00aaff", height=200)

        with tab_mot:
            cols_acc = [c for c in df.columns if "acceleration" in c]
            if cols_acc:
                st.line_chart(df[cols_acc], height=300)
            cols_gyro = [c for c in df.columns if "gyro" in c]
            if cols_gyro:
                st.line_chart(df[cols_gyro], height=300)


# --- MAIN LOOP ---
def main():
    st.title("📊 Sensor Live Dashboard")

    # 1. Initialize Backend
    client = start_mqtt_client()
    state = get_mqtt_state()

    # 2. Render Sidebar
    render_sidebar(state)

    if client is None:
        st.error("🚨 Critical Error: MQTT Broker is unreachable. Please check Docker.")
        st.stop()

    if not client:
        st.stop()

    # Dynamic Container
    main_container = st.empty()

    while True:
        with main_container.container():
            if not state.devices:
                st.info(f"📡 Waiting for devices on `{AppConfig.TOPIC}`...")
                st.write("Listening for: `sensor/jadwiga` or similar...")
            else:
                # Sortujemy nazwy, żeby kolejność zakładek nie skakała
                device_names = sorted(list(state.devices.keys()))

                # Tworzymy zakładki dla każdego urządzenia
                # Np. Tab 1: "JADWIGA", Tab 2: "GARAZ"
                tabs = st.tabs([f"📍 {name.upper()}" for name in device_names])

                for i, name in enumerate(device_names):
                    with tabs[i]:
                        render_device_tab(state.devices[name])

        time.sleep(0.5)


if __name__ == "__main__":
    main()
