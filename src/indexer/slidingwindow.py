from collections import deque
from .secondbucket import SecondBucket
from .metric import METRICS


class SlidingWindowTracker:
    def __init__(self, window_seconds: int, export_history :bool = False):
        self.window_seconds = window_seconds
        # This tracker maintains its own private history segment
        self.history = deque(maxlen=window_seconds)
        self.export_history = export_history
        self.summary = SecondBucket()

    def update_on_rollup(self, newest_bucket):
        oldest_bucket = SecondBucket()
        if len(self.history) == self.history.maxlen:
            oldest_bucket = self.history[0]
        self.history.append(newest_bucket)
        self.summary.timestamp = newest_bucket.timestamp
        self.summary.request_count = self.summary.request_count + newest_bucket.request_count - oldest_bucket.request_count
        self.summary.total_bytes = self.summary.total_bytes + newest_bucket.total_bytes - oldest_bucket.total_bytes
        for metric in METRICS.values():
            metric.aggregate_metric(self.summary.__dict__, oldest_bucket.__dict__, delta = -1)
            metric.aggregate_metric(self.summary.__dict__, newest_bucket.__dict__)
    def summarize(self):
        self.summary.__init__() # reset data
        for bucket in self.history:
            self.summary.request_count += bucket.request_count
            self.summary.total_bytes += bucket.total_bytes
            for metric in METRICS.values():
                metric.aggregate_metric(getattr(self.summary, metric.name), getattr(bucket, metric.name))