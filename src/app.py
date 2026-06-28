import asyncio
from collections import deque
import streamlit as st

# Custom module injections
from utils.listener import LogListener
from indexer.aggregator import AggregatorCache
from parsers.master_parser import MasterParser
from history.history_processor import historical_processor_loop
from dashboard.config_sidebar import render_sidebar
from dashboard.charts import render_charts          # ← shared chart engine
from dashboard.file_loader import render_file_loader
from detectors.master_detector import MasterDetector

# =====================================================================
# PAGE CONFIG  (must be first Streamlit call)
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

# batch_data holds either None (no file loaded) or the aggregated metrics
# dict returned by your real parser — same shape charts.py expects.
if "batch_data" not in st.session_state:
    st.session_state.batch_data = None     # {"metrics": {...}, "alerts": [...]}

ROLLING_WINDOW_SIZE = st.session_state.app_config.get("rolling_window_size", 300)
sliding_window = deque(maxlen=ROLLING_WINDOW_SIZE)

listener_to_parser_queue = asyncio.Queue()
parser_to_cache_queue    = asyncio.Queue()
shared_alert_event       = asyncio.Event()


async def launch_system():
    detector_instance = MasterDetector(alert_trigger_event=shared_alert_event)
    target_path       = st.session_state.app_config.get("log_sources")
    listener          = LogListener(target_path, listener_to_parser_queue)
    formats           = listener.formats
    parser            = MasterParser(
        formats, listener_to_parser_queue, parser_to_cache_queue,
        detector=detector_instance,
    )
    cache = AggregatorCache(parser_to_cache_queue, detector=detector_instance)
    await asyncio.gather(
        listener.start_live_listening(),
        parser.parse_logs(),
        cache.ingest_event(ROLLING_WINDOW_SIZE),
        historical_processor_loop(alert_trigger_event=shared_alert_event),
    )


# =====================================================================
# SIDEBAR
# =====================================================================
def build_sidebar():
    st.sidebar.title("🛡️ SOC Aggregator")
    st.session_state.current_tab = st.sidebar.radio(
        "Mode",
        ["Live Dashboard", "Batch Dashboard"],
        index=0 if st.session_state.current_tab == "Live Dashboard" else 1,
    )
    st.sidebar.markdown("---")
    render_sidebar()   # ⚙️ settings modal button lives here


# =====================================================================
# LIVE TAB
# =====================================================================
def render_live_tab():
    st.title("🔴 Live Streaming Telemetry Engine")
    st.caption("Active pipelines consuming records via background execution loops.")

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Buffered Window Items",    value=len(sliding_window))
    with col2:
        st.metric("Max Pipeline Capacity",    value=ROLLING_WINDOW_SIZE)

    # Pull aggregated snapshot + alerts from your live cache.
    # Replace the two lines below with your real cache read once wired up.
    live_metrics = st.session_state.get("live_metrics")   # set by cache layer
    live_alerts  = st.session_state.get("live_alerts", [])

    if live_metrics:
        st.markdown("---")
        render_charts(live_metrics, live_alerts)
    else:
        st.info("System operational — waiting for the first aggregation window to complete.")


# =====================================================================
# BATCH TAB
# =====================================================================
def render_batch_tab():
    # ── No file loaded yet ──────────────────────────────────────────
    if st.session_state.batch_data is None:
        render_file_loader()
        return

    # ── File loaded — show analytics ────────────────────────────────
    st.title("📊 Historical Batch Analytics")

    col_back, _ = st.columns([1.5, 4.5])
    with col_back:
        if st.button("🔄 Upload Different File", use_container_width=True):
            st.session_state.batch_data = None
            st.rerun()

    st.markdown("---")

    # batch_data is {"metrics": <aggregated dict>, "alerts": <list>}
    batch_metrics = st.session_state.batch_data.get("metrics", {})
    batch_alerts  = st.session_state.batch_data.get("alerts",  [])
    render_charts(batch_metrics, batch_alerts)


# =====================================================================
# MAIN
# =====================================================================
def run_ui():
    build_sidebar()

    # Global toast dispatcher
    if st.session_state.get("latest_alert"):
        st.toast(st.session_state.latest_alert, icon="⚠️")
        st.session_state.latest_alert = None

    if st.session_state.current_tab == "Live Dashboard":
        render_live_tab()
    else:
        render_batch_tab()


if __name__ == "__main__":
    run_ui()