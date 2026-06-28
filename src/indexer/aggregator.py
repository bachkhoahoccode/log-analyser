import asyncio
import json
from .metric import METRICS
from .slidingwindow import SlidingWindowTracker
from .secondbucket import SecondBucket
from src.detectors.master_detector import MasterDetector


class AggregatorCache:
    def __init__(self, inqueue, detector: MasterDetector):
        self.current_event_time = 0
        self.current_bucket = None
        self.detector = detector
        self.inqueue = inqueue
        self.windows = {
            "short": SlidingWindowTracker(window_seconds=WINDOWS.get("short_window_seconds")),
            "medium": SlidingWindowTracker(window_seconds=WINDOWS.get("medium_window_seconds"), export_history = True),
            "long": SlidingWindowTracker(window_seconds=WINDOWS.get("long_window_seconds"))
        }

    async def ingest_event(self, max_window):
        while self.inqueue:
            event = await self.inqueue.get()
            event_sec = event["timestamp"]

            # corrupted ts in flow
            if self.current_event_time - event_sec > max_window:
                return
            # Handle chronological progression
            if event_sec > self.current_event_time:
                if self.current_bucket is not None:
                    self._rollup_to_all_windows(self.current_bucket)
                    asyncio.create_task(self.detector.detect_rollup_if_idle(list(self.windows)))
                self.current_event_time = event_sec
                self.current_bucket = SecondBucket(event_sec)
            # active second bucket
            if event_sec == self.current_event_time:
                
                self.aggregate(self.current_bucket, event)
            else:
                # out-of-order data, recalculate summary
                for window in self.windows.values():
                    for bucket in window.history:
                        if bucket.timestamp == event_sec:
                            self.aggregate(bucket, event)
                            window.summarize()
                            break
    
    def _rollup_to_all_windows(self, closed_bucket):
        for window_name, window_tracker in self.windows.items():
            window_tracker.update_on_rollup(closed_bucket)
        if closed_bucket.timestamp % LADDER_EXPORT_INTERVAL == 0:
            self._write_window_to_history()

    def aggregate(self, bucket, event):
        bucket.request_count += 1
        bucket.total_bytes += event["bytes"]
        for metric in METRICS.values():
            metric.aggregate_event(bucket, event)

    def _write_window_to_history(self):
        history_window = next((w for w in self.windows.values() if w.export_history), None)
        if history_window:
            payload = {
                "timestamp": self.current_event_time,
                "metrics": dict(history_window.summary) # Cast defaultdict to plain dict
            }
            
            print(f"[LADDER] Minute boundary reached. Exporting '1m' window state...")
            with open("data/history/metrics_history.json", "a") as f:
                f.write(json.dumps(payload) + "\n")

if __name__ == "__main__":
    line = []
    
try:
    with open ('config/system.json', 'r') as s:
        system = json.load(s)
        WINDOWS = system.get("window")
        MAX_WINDOW = int(WINDOWS.get("max window"))
        LADDER_EXPORT_INTERVAL = int(system["storage"].get("ladder_export_interval"))
except FileNotFoundError:
    WINDOWS = {}
    LADDER_EXPORT_INTERVAL = 0
