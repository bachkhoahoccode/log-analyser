from collections import deque, defaultdict
from typing import Dict, Optional
import json

try:
    with open ('config/system.json', 'r') as s:
        system = json.load(s)
        WINDOWS = system.get("window")
        LADDER_EXPORT_INTERVAL = int(system["storage"].get("ladder_export_interval"))
except FileNotFoundError:
    WINDOWS = {}
    LADDER_EXPORT_INTERVAL = 0

class Metric:
    def __init__(self, name, method, factory):
        self.name = name
        self.method = method
        self.factory = factory
    def aggregate_metric(self, dest, src, delta=1):

        if self.method == "direct":
            for key, value in src.items():
                dest[key] += delta * value
                if dest[key] <= 0:
                    del dest[key]

        elif self.method == "nested":
            for outer_key, inner_dict in src.items():
                for inner_key, value in inner_dict.items():
                    dest[outer_key][inner_key] += delta * value

                    if dest[outer_key][inner_key] <= 0:
                        del dest[outer_key][inner_key]

                if not dest[outer_key]:
                    del dest[outer_key]

METRICS = {
    "ip_counts": Metric(
        "ip_counts",
        "direct",
        lambda: defaultdict(int)
    ),

    "total_bytes_by_ip": Metric(
        "total_bytes_by_ip",
        "direct",
        lambda: defaultdict(int)
    ),

    "method_counts": Metric(
        "method_counts",
        "direct",
        lambda: defaultdict(int)
    ),

    "status_counts": Metric(
        "status_counts",
        "direct",
        lambda: defaultdict(int)
    ),

    "user_agent_counts": Metric(
        "user_agent_counts",
        "direct",
        lambda: defaultdict(int)
    ),

    "uri_counts": Metric(
        "uri_counts",
        "direct",
        lambda: defaultdict(int)
    ),

    "uri_by_ip": Metric(
        "uri_by_ip",
        "nested",
        lambda: defaultdict(lambda: defaultdict(int))
    ),

    "status_by_ip": Metric(
        "status_by_ip",
        "nested",
        lambda: defaultdict(lambda: defaultdict(int))
    ),

    "not_found_urls": Metric(
        "not_found_urls",
        "direct",
        lambda: defaultdict(int)
    ),

    "virtual_host_counts": Metric(
        "virtual_host_counts",
        "direct",
        lambda: defaultdict(int)
    ),
}

class SecondBucket:
    def __init__(self, timestamp = None):
        self.timestamp = timestamp

        self.request_count = 0
        self.total_bytes = 0
        self.unique_ips = set()
        # create every metric automatically
        for metric in METRICS.values():
            setattr(self, metric.name, metric.factory())

class SlidingWindowTracker:
    def __init__(self, window_seconds: int, export_history :bool = False):
        self.window_seconds = window_seconds
        # This tracker maintains its own private history segment
        self.history = deque(maxlen=window_seconds)
        self.export_history = export_history
        self.summary = SecondBucket()

    def update_on_rollup(self, newest_bucket):
        if len(self.history) == self.history.maxlen:
            oldest_bucket = self.history[0]
        self.history.append(newest_bucket)

        self.summary.request_count = self.summary.request_count + newest_bucket.request_count - oldest_bucket.request_count
        self.summary.total_bytes = self.summary.total_bytes + newest_bucket.total_bytes - oldest_bucket.total_bytes
        for metric in METRICS.values():
            metric.aggregate_metric(getattr(self.summary, metric.name), getattr(oldest_bucket, metric.name), delta = -1)
            metric.aggregate_metric(getattr(self.summary, metric.name), getattr(newest_bucket, metric.name))
    
class AggregatorCache:
    def __init__(self):
        self.current_event_time = 0
        self.current_bucket = None
        
        # Define all your window requirements dynamically here
        self.windows = {
            "5s": SlidingWindowTracker(window_seconds=5),
            "1m": SlidingWindowTracker(window_seconds=60, export_history = True),
            "5m": SlidingWindowTracker(window_seconds=300)
        }

    def ingest_event(self, event):
        event_sec = event["timestamp"]

        # Handle chronological progression
        if event_sec > self.current_event_time:
            if self.current_bucket is not None:
                self._rollup_to_all_windows(self.current_bucket)
            self.current_event_time = event_sec
            self.current_bucket = SecondBucket(event_sec)

        # Ingest into the active second bucket
        if event_sec == self.current_event_time:
            self.aggregate(self.current_bucket, event)
        else:
            # Handle out-of-order data by updating the specific window histories directly
            for window in self.windows.values():
                for bucket in window.history:
                    if bucket.timestamp == event_sec:
                        self.aggregate(bucket, event)
                        window.summary()
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
        
        # Find the 1m window dynamically by its flag
        history_window = next((w for w in self.windows.values() if w.export_history), None)
        if history_window:
            # Capturing the state is simple and O(1) because the window already calculated it!
            payload = {
                "timestamp": self.current_event_time,
                "metrics": dict(history_window.live_ip_counts) # Cast defaultdict to plain dict
            }
            
            # Append seamlessly to your JSON line file for graph plotting later
            print(f"[LADDER] Minute boundary reached. Exporting '1m' window state...")
            with open("data/history/metrics_history.json", "a") as f:
                f.write(json.dumps(payload) + "\n")