import asyncio
import json
import time
import streamlit as st
from . import ALL_DETECTORS

class MasterDetector:

    def __init__(self, alert_trigger_event, buffer_file_path=None):
        self.event_detectors = []
        self.rollup_detectors = []
        self.event_busy = False  
        self.rollup_busy = False  
        
        self.alert_trigger_event = alert_trigger_event
        self.buffer_file_path = buffer_file_path

        for detector in ALL_DETECTORS:
            if not detector.RULE["enabled"]:
                continue
            trigger = detector.RULE["trigger"]
            if trigger == "event":
                self.event_detectors.append(detector)
            elif trigger == "rollup":
                self.rollup_detectors.append(detector)
            else:
                raise ValueError(
                    f"Unknown trigger '{trigger}' in detector '{detector.__name__}'"
                )

    async def detect_event_if_idle(self, event):
        if self.event_busy:
            return  
        
        self.event_busy = True
        try:
            results = await asyncio.gather(
                *(detector.detect(event) for detector in self.event_detectors),
                return_exceptions=True
            )
            await self._process_detection_results(results, "event")
        finally:
            self.event_busy = False

    async def detect_rollup_if_idle(self, windows):
        if self.rollup_busy:
            return  
        
        self.rollup_busy = True
        for window in windows:
            bucket = window.summary
            frame = window.window_seconds
            try:
                results = await asyncio.gather(
                    *(detector.detect(bucket, frame) for detector in self.rollup_detectors),
                    return_exceptions=True
                )
            
                await self._process_detection_results(results, "rollup")

            finally:
                self.rollup_busy = False


    async def _process_detection_results(self, results, trigger_type):
        for res in results:
            # Skip empty results or detector crashes
            if not res or isinstance(res, Exception):
                continue
            
            # 1. Print the immediate alert to console
            # 1. Inside your MasterDetector rule check:
            print(f"\n🚨 [ALERT] Triggered by {trigger_type} detector: {res}")

            # Sneak the message directly into Streamlit's global session memory

            if "latest_alert" in st.session_state:
                st.session_state.latest_alert = f"🚨 {trigger_type.upper()}: {res}"
            
            # 2. Package the raw alert metadata
            alert_payload = {
                "timestamp": time.time(),
                "trigger": trigger_type,
                "raw_data": res
            }
            # 3. Fast boundary write: Append to buffer file using a background thread
            await asyncio.to_thread(self._write_to_buffer, alert_payload)
        self.alert_trigger_event.set()

    def _write_to_buffer(self, payload):
        if self.buffer_file_path is None:
            return
        else:
            with open(self.buffer_file_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(payload) + "\n")