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
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        metric_temp = st.empty()
    with col2:
        metric_smoke = st.empty()
    with col3:
        metric_sound = st.empty()
    with col4:
        metric_vib = st.empty()
    with col5:
        metric_flame = st.empty()

    st.divider()

    # Charts Section
    st.markdown("### 📈 Analytics")
    tab_env, tab_mech = st.tabs(["🌡️ Environmental Data", "⚙️ Mechanical Analysis"])

    with tab_env:
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

            # Smoke
            curr_smoke = data.get("smoke", 0)
            prev_smoke = prev.get("smoke", 0) if prev else 0
            metric_smoke.metric(
                label="Smoke",
                value=f"{curr_smoke} %",
                delta=calculate_delta(curr_smoke, prev_smoke),
                delta_color="inverse",  # Higher smoke is worse
                help="Smoke level percentage",
                border=True,
                chart_data=(
                    pd.DataFrame(state.history)["smoke"] if state.history else None
                ),
            )

            # Sound
            curr_sound = data.get("sound", 0)
            prev_sound = prev.get("sound", 0) if prev else 0
            metric_sound.metric(
                label="Sound",
                value=f"{curr_sound} dB",
                delta=calculate_delta(curr_sound, prev_sound),
                help="Ambient sound level in decibels",
                border=True,
                chart_data=(
                    pd.DataFrame(state.history)["sound"] if state.history else None
                ),
            )

            # Vibration
            curr_vib = data.get("vibration", 0)
            prev_vib = prev.get("vibration", 0) if prev else 0
            metric_vib.metric(
                label="Vibration",
                value=f"{curr_vib} Hz",
                delta=calculate_delta(curr_vib, prev_vib),
                help="Vibration frequency in Hertz",
                border=True,
                chart_data=(
                    pd.DataFrame(state.history)["vibration"] if state.history else None
                ),
            )

            # Flame (Critical Logic)
            flame_val = data.get("flame", 1)
            metric_flame.metric(
                label="Flame Sensor",
                value="🔥 FIRE" if flame_val == 1 else "✅ Safe",
                help=(
                    "Flame detected! Immediate action required."
                    if flame_val == 1
                    else "No flame detected."
                ),
                border=True,
            )

            # --- CHARTS ---
            if len(state.history) > 1:
                df = pd.DataFrame(state.history)

                # Dynamiczne wykresy
                with chart_env_box:
                    st.line_chart(df[["temperature", "smoke"]], height=300)

                with chart_mech_box:
                    st.area_chart(
                        df[["vibration", "sound"]],
                        color=["#FF5500", "#00AA00"],
                        height=300,
                    )

        elif state.connected:
            chart_env_box.info("📡 Waiting for data stream from ESP32...")

        time.sleep(0.05)


if __name__ == "__main__":
    main()
