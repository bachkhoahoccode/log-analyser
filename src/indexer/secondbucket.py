from .metric import METRICS

class SecondBucket:
    def __init__(self, timestamp = None):
        self.timestamp = timestamp

        self.request_count = 0
        self.total_bytes = 0
        # create every metric automatically
        for metric in METRICS.values():
            setattr(self, metric.name, metric.factory())