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
    TOPIC: str = os.getenv("MQTT_TOPIC", "sensor/all")
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


# --- STATE MANAGEMENT ---
class MQTTState:
    """Singleton class to hold application state."""

    def __init__(self):
        self.connected: bool = False
        self.history: List[Dict[str, Any]] = []
        self.latest: Dict[str, Any] = {}
        self.previous: Dict[str, Any] = {}
        self.max_history: int = 100


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
        payload = json.loads(msg.payload.decode())

        if userdata.latest:
            userdata.previous = userdata.latest.copy()

        userdata.latest = payload
        userdata.history.append(payload)

        if len(userdata.history) > userdata.max_history:
            userdata.history.pop(0)

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
        # new_max = st.slider(
        #     "Chart History (points)", min_value=50, max_value=500, value=100, step=50
        # )
        # state.max_history = new_max

        st.badge(f"Topic: `{AppConfig.TOPIC}`", color="blue", icon="📓")

        st.divider()

        # st.subheader("🧹 Data Management")

        # left, right = st.columns(2)
        # if left.button("Clear History", width="stretch", icon="🗑️"):
        #     state.history = []
        # if right.button("Clear All Data", width="stretch", icon="🧼"):
        #     state.history = []
        #     state.latest = {}


def calculate_delta(current: float, previous: float) -> Optional[float]:
    """Helper to calculate metric delta."""
    if previous is None:
        return None
    return round(current - previous, 2)


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

    # 3. Create Layout Placeholders
    # Top KPI Row
    st.markdown("### ⏱ Live Telemetry")
    col1_row1, col2_row1, col3_row1, col4_row1, col5_row1, col6_row1 = st.columns(6)
    col1_row2, col2_row2, col3_row2, col4_row2, col5_row2, col6_row2 = st.columns(6)

    with col1_row1:
        metric_temp = st.empty()
    with col2_row1:
        metric_gas = st.empty()
    with col3_row1:
        metric_temp_out = st.empty()
    with col4_row1:
        metric_hum = st.empty()
    with col5_row1:
        metric_motor = st.empty()
    with col6_row1:
        metric_flame = st.empty()

    with col1_row2:
        metric_acc_x = st.empty()
    with col2_row2:
        metric_acc_y = st.empty()
    with col3_row2:
        metric_acc_z = st.empty()
    with col4_row2:
        metric_gyto_x = st.empty()
    with col5_row2:
        metric_gyto_y = st.empty()
    with col6_row2:
        metric_gyto_z = st.empty()

    st.divider()

    # Charts Section
    st.markdown("### 📈 Analytics")
    tab_env, tab_mech = st.tabs(["🌡️ Environmental Data", "⚙️ Mechanical Analysis"])

    with tab_env:
        chart_env_box_temp = st.empty()
        chart_env_box = st.empty()
    with tab_mech:
        chart_mech_box = st.empty()

    while True:
        if state.latest:
            data = state.latest
            prev = state.previous

            # --- METRICS WITH DELTA ---
            # Temperature
            curr_temp = data.get("temperature", 0)
            prev_temp = prev.get("temperature", 0) if prev else 0
            metric_temp.metric(
                label="Temperature",
                value=f"{curr_temp} °C",
                delta=calculate_delta(curr_temp, prev_temp),
                help="Ambient temperature reading",
                border=True,
                chart_data=(
                    pd.DataFrame(state.history)["temperature"]
                    if state.history
                    else None
                ),
            )

            # Gas
            curr_gas = data.get("gas_level", 0)
            prev_gas = prev.get("gas_level", 0) if prev else 0
            gas_mess = (
                f"DANGER"
                if curr_gas > 1500
                else "WARNING" if curr_gas > 1000 else "SAFE"
            )
            gas_mess += f" ({curr_gas} ppm)"
            metric_gas.metric(
                label="Gas Level",
                value=gas_mess,
                delta=calculate_delta(curr_gas, prev_gas),
                delta_color="inverse",  # Higher gas is worse
                help="Gas level",
                border=True,
                chart_data=(
                    pd.DataFrame(state.history)["gas_level"] if state.history else None
                ),
            )

            # Temperature Outside
            curr_temp_out = data.get("temperature_out", 0)
            prev_temp_out = prev.get("temperature_out", 0) if prev else 0
            metric_temp_out.metric(
                label="Temperature Outside",
                value=f"{curr_temp_out} °C",
                delta=calculate_delta(curr_temp_out, prev_temp_out),
                help="Outside temperature reading",
                border=True,
                chart_data=(
                    pd.DataFrame(state.history)["temperature_out"]
                    if state.history
                    else None if state.history else None
                ),
            )

            # Humidity
            curr_hum = data.get("humidity_out", 0)
            prev_hum = prev.get("humidity_out", 0) if prev else 0
            metric_hum.metric(
                label="Humidity",
                value=f"{curr_hum} %",
                delta=calculate_delta(curr_hum, prev_hum),
                help="Ambient humidity level",
                border=True,
                chart_data=(
                    pd.DataFrame(state.history)["humidity_out"]
                    if state.history
                    else None
                ),
            )

            # Motor Status
            motor_status = data.get("motor_adc", 0)
            prev_motor_status = prev.get("motor_adc", 0) if prev else 0
            metric_motor.metric(
                label="Flow",
                value=f"{motor_status}",
                delta=calculate_delta(motor_status, prev_motor_status),
                help="Motor ADC reading indicating flow status",
                border=True,
                chart_data=(
                    pd.DataFrame(state.history)["motor_adc"] if state.history else None
                ),
            )

            # Flame (Critical Logic)
            flame_status = data.get("flame_status", 1)
            metric_flame.metric(
                label="Flame Sensor",
                value="🔥 FIRE" if flame_status == 1 else "✅ Safe",
                help=(
                    "Flame detected! Immediate action required."
                    if flame_status == 1
                    else "No flame detected."
                ),
                border=True,
            )

            # Accelerometer X
            curr_acc_x = data.get("acceleration_x", 0)
            prev_acc_x = prev.get("acceleration_x", 0) if prev else 0
            metric_acc_x.metric(
                label="Accel X",
                value=f"{curr_acc_x} m/s²",
                delta=calculate_delta(curr_acc_x, prev_acc_x),
                help="Acceleration on X-axis",
                border=True,
                chart_data=(
                    pd.DataFrame(state.history)["acceleration_x"]
                    if state.history
                    else None
                ),
            )

            # Accelerometer Y
            curr_acc_y = data.get("acceleration_y", 0)
            prev_acc_y = prev.get("acceleration_y", 0) if prev else 0
            metric_acc_y.metric(
                label="Accel Y",
                value=f"{curr_acc_y} m/s²",
                delta=calculate_delta(curr_acc_y, prev_acc_y),
                help="Acceleration on Y-axis",
                border=True,
                chart_data=(
                    pd.DataFrame(state.history)["acceleration_y"]
                    if state.history
                    else None
                ),
            )

            # Accelerometer Z
            curr_acc_z = data.get("acceleration_z", 0)
            prev_acc_z = prev.get("acceleration_z", 0) if prev else 0
            metric_acc_z.metric(
                label="Accel Z",
                value=f"{curr_acc_z} m/s²",
                delta=calculate_delta(curr_acc_z, prev_acc_z),
                help="Acceleration on Z-axis",
                border=True,
                chart_data=(
                    pd.DataFrame(state.history)["acceleration_z"]
                    if state.history
                    else None
                ),
            )
            # Gyroscope X
            curr_gyro_x = data.get("gyro_x", 0)
            prev_gyro_x = prev.get("gyro_x", 0) if prev else 0
            metric_gyto_x.metric(
                label="Gyro X",
                value=f"{curr_gyro_x} °/s",
                delta=calculate_delta(curr_gyro_x, prev_gyro_x),
                help="Gyroscope on X-axis",
                border=True,
                chart_data=(
                    pd.DataFrame(state.history)["gyro_x"] if state.history else None
                ),
            )
            # Gyroscope Y
            curr_gyro_y = data.get("gyro_y", 0)
            prev_gyro_y = prev.get("gyro_y", 0) if prev else 0
            metric_gyto_y.metric(
                label="Gyro Y",
                value=f"{curr_gyro_y} °/s",
                delta=calculate_delta(curr_gyro_y, prev_gyro_y),
                help="Gyroscope on Y-axis",
                border=True,
                chart_data=(
                    pd.DataFrame(state.history)["gyro_y"] if state.history else None
                ),
            )
            # Gyroscope Z
            curr_gyro_z = data.get("gyro_z", 0)
            prev_gyro_z = prev.get("gyro_z", 0) if prev else 0
            metric_gyto_z.metric(
                label="Gyro Z",
                value=f"{curr_gyro_z} °/s",
                delta=calculate_delta(curr_gyro_z, prev_gyro_z),
                help="Gyroscope on Z-axis",
                border=True,
                chart_data=(
                    pd.DataFrame(state.history)["gyro_z"] if state.history else None
                ),
            )

            # --- CHARTS ---
            if len(state.history) > 1:
                df = pd.DataFrame(state.history)

                with chart_env_box_temp:
                    st.line_chart(
                        df[
                            [
                                "temperature",
                                "temperature_out",
                            ]
                        ],
                        height=300,
                    )
                with chart_env_box:
                    st.line_chart(
                        df[["humidity_out", "gas_level", "motor_adc"]],
                        height=300,
                    )

                with chart_mech_box:
                    st.area_chart(
                        df[
                            [
                                "acceleration_x",
                                "gyro_x",
                                "acceleration_y",
                                "gyro_y",
                                "acceleration_z",
                                "gyro_z",
                            ]
                        ],
                        color=[
                            "#FF5500",
                            "#FFAA00",
                            "#00AAFF",
                            "#0055FF",
                            "#55FF00",
                            "#AAFF00",
                        ],
                        height=300,
                    )

        elif state.connected:
            chart_env_box.info("📡 Waiting for data stream from ESP32...")

        time.sleep(0.05)


if __name__ == "__main__":
    main()
