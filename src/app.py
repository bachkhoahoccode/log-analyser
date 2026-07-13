import json
from collections import deque
from pathlib import Path
import streamlit as st

from path_config import StorageConfig
from dashboard.config_sidebar import render_sidebar
from dashboard.charts import render_charts
from dashboard.file_loader import render_file_loader

# =====================================================================
# PAGE CONFIG
# =====================================================================
st.set_page_config(page_title="Log Analytics Engine", page_icon="🛡️", layout="wide")

# =====================================================================
# SYSTEM INITIALIZATION & STATE ENGINE
# =====================================================================
if "app_config" not in st.session_state:
    st.session_state.app_config = {
        "rolling_window_size": 300,
        "alert_threshold": 50,
    }

if "current_tab" not in st.session_state:
    st.session_state.current_tab = "Live Dashboard"

if "batch_data" not in st.session_state:
    st.session_state.batch_data = None

if "sliding_window" not in st.session_state:
    st.session_state.sliding_window = deque(maxlen=st.session_state.app_config.get("rolling_window_size", 300))

sliding_window = st.session_state.sliding_window
ROLLING_WINDOW_SIZE = st.session_state.app_config.get("rolling_window_size", 300)

def _read_jsonl_history(path) -> list[dict]:
#Read a JSONL history file into a list of dicts. Returns [] if missing
    if not path or not Path(path).exists():
        return []
    snapshots = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                snapshots.append(json.loads(line))
    return snapshots

# =====================================================================
# SIDEBAR
# =====================================================================
def build_sidebar():
    st.sidebar.title("🛡️ SOC Aggregator")
    st.session_state.current_tab = st.sidebar.radio(
        "Mode",
        ["Live Dashboard", "Batch Dashboard", "Historical Trends"],
        index=["Live Dashboard", "Batch Dashboard", "Historical Trends"].index(
            st.session_state.current_tab
        ),
    )
    st.sidebar.markdown("---")
    render_sidebar()


# =====================================================================
# LIVE TAB
# =====================================================================
def render_live_tab():
    st.title("🔴 Live Streaming Telemetry Engine")
    st.caption(
        "Reads from data/live/*.jsonl"
    )

    live_storage = StorageConfig(mode="live")

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Max Pipeline Capacity", value=ROLLING_WINDOW_SIZE)
    with col2:
        if st.button("🔄 Refresh now"):
            st.rerun()

    live_metrics = _read_jsonl_history(live_storage.metrics_history)
    live_alerts  = _read_jsonl_history(live_storage.alerts_history)

    if not live_metrics:
        st.info(
            "No live data yet. Make sure live_bg_pipeline.py is running "
            f"in a separate terminal, and writing to {live_storage.base_dir}."
        )
        return

    st.markdown("---")
    render_charts(live_metrics, live_alerts)


# =====================================================================
# BATCH TAB
# =====================================================================
def render_batch_tab():

    if st.session_state.batch_data is None:
        render_file_loader()
        return

    st.title("📊 Historical Batch Analytics")

    col_back, _ = st.columns([1.5, 4.5])
    with col_back:
        if st.button("🔄 Upload Different File", use_container_width=True):
            st.session_state.batch_data = None
            st.rerun()

    st.markdown("---")

    batch_metrics = st.session_state.batch_data.get("metrics", [])
    batch_alerts  = st.session_state.batch_data.get("alerts",  [])
    render_charts(batch_metrics, batch_alerts)

# =====================================================================
# HISTORICAL TRENDS TAB  (hourly / daily rollups)
# =====================================================================
def render_historical_tab():
    st.title("📅 Historical Trends — Hourly & Daily Rollups")
    st.caption("Reads from the hourly/daily history files written by live_bg_pipeline.py.")

    live_storage = StorageConfig(mode="live")

    period = st.radio("Granularity", ["Hourly", "Daily"], horizontal=True)
    path   = live_storage.hourly_history if period == "Hourly" else live_storage.daily_history

    snapshots = _read_jsonl_history(path)
    alerts_in_history = [s for s in snapshots if s.get("type")]  # enriched alert records

    if not snapshots:
        st.info(
            f"No {period.lower()} history yet at {path}. "
            "Make sure live_bg_pipeline.py is running."
        )
        return

    render_charts(snapshots, alerts_in_history)
 
# =====================================================================
# MAIN
# =====================================================================
def run_ui():
    build_sidebar()

    if st.session_state.current_tab == "Live Dashboard":
        render_live_tab()
    elif st.session_state.current_tab == "Batch Dashboard":
        render_batch_tab()
    else:
        render_historical_tab()


if __name__ == "__main__":
    run_ui()