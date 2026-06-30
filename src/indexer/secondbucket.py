from dataclasses import dataclass
from .metric import METRICS
@dataclass
class SecondBucket:
    timestamp: int = None
    request_count: int = 0
    total_bytes: int = 0

    def __post_init__(self):
        for metric in METRICS.values():
            setattr(self, metric.name, metric.factory())