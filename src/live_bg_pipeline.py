import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from path_config import StorageConfig, ConfigPaths
from utils.listener import LogListener
from indexer.aggregator import AggregatorCache
from parsers.master_parser import MasterParser
from history.history_processor import historical_processor_loop
from detectors.master_detector import MasterDetector

import json

listener_to_parser_queue = asyncio.Queue()
parser_to_cache_queue    = asyncio.Queue()
shared_alert_event       = asyncio.Event()

ROLLING_WINDOW_SIZE = 300  # keep in sync with app_config default in app.py


def _load_log_sources() -> list[dict]:
    if not ConfigPaths.files_monitored.exists():
        print(f"[Pipeline] WARNING: {ConfigPaths.files_monitored} not found. "
              "No log sources to monitor — pipeline will idle.")
        return []
    with open(ConfigPaths.files_monitored, "r", encoding="utf-8") as f:
        config = json.load(f)
    return config.get("log_sources", [])


async def launch_system():
    live_storage = StorageConfig(mode="live")
    live_storage.ensure_dirs()

    print(f"[Pipeline] Writing live data to: {live_storage.base_dir.resolve()}")

    detector_instance = MasterDetector(
        alert_trigger_event=shared_alert_event,
        buffer_file_path=str(live_storage.alerts_buffer),
    )
    target_path = _load_log_sources()
    listener    = LogListener(target_path, listener_to_parser_queue)
    formats     = listener.formats
    parser      = MasterParser(
        formats, listener_to_parser_queue, parser_to_cache_queue,
        detector=detector_instance,
    )
    cache = AggregatorCache(
        parser_to_cache_queue,
        detector=detector_instance,
        history_path=str(live_storage.metrics_history),
    )

    await asyncio.gather(
        listener.start_live_listening(),
        parser.parse_logs(),
        cache.ingest_event(ROLLING_WINDOW_SIZE),
        historical_processor_loop(
            alert_trigger_event=shared_alert_event,
            buffer_path=str(live_storage.alerts_buffer),
            history_path=str(live_storage.alerts_history),
            hourly_path=str(live_storage.hourly_history),
            daily_path=str(live_storage.daily_history),
        ),
    )

if __name__ == "__main__":
    print("[Pipeline] Starting live log-analysis pipeline. Ctrl+C to stop.")
    try:
        asyncio.run(launch_system())
    except KeyboardInterrupt:
        print("\n[Pipeline] Stopped by user.")