import json
import os
from collections import defaultdict
from datetime import datetime, timezone

from indexer.metric import METRICS   # your existing Metric registry

def _hour_key(ts: float) -> str:
    dt = datetime.fromtimestamp(ts, tz=timezone.utc)
    return dt.strftime("%Y-%m-%dT%H")

def _day_key(ts: float) -> str:
    dt = datetime.fromtimestamp(ts, tz=timezone.utc)
    return dt.strftime("%Y-%m-%d")

class _ResolutionAggregator:

    def __init__(self, key_fn, output_path: str):
        self._key_fn     = key_fn          # ts -> bucket key string
        self._output_path = output_path
        self._current_key: str | None = None
        self._bucket: dict = {}            # metric_name -> defaultdict

    def ingest(self, event: dict, ts: float):

        bucket_key = self._key_fn(ts)

        # Roll over when we enter a new period
        if bucket_key != self._current_key:
            if self._current_key is not None:
                self._flush(self._current_key)
            self._current_key = bucket_key
            self._bucket = self._fresh_bucket()

        self._apply_event(event)

    def flush_all(self):
        if self._current_key and self._bucket:
            self._flush(self._current_key)

    def _fresh_bucket(self) -> dict:
        return {name: metric.factory() for name, metric in METRICS.items()}

    def _apply_event(self, event: dict):
        for name, metric in METRICS.items():
            extracted = metric.extractor(event)
            if extracted is None:
                continue

            if metric.method == "direct":
                key, value = extracted
                if key is None:
                    continue
                src = {key: value}
                metric.aggregate_metric(self._bucket[name], src)

            elif metric.method == "nested":
                # extractor returns (outer_key, inner_key, value)
                if len(extracted) == 3:
                    outer_key, inner_key, value = extracted
                else:
                    outer_key, inner_key = extracted
                    value = 1
                if outer_key is None or inner_key is None:
                    continue
                src = {outer_key: {inner_key: value}}
                metric.aggregate_metric(self._bucket[name], src)

    def _flush(self, bucket_key: str):
        """Serialise the closed bucket and append it to the output file."""
        record = {
            "bucket":      bucket_key,
            "flushed_at":  datetime.isoformat(),
            "metrics":     _serialise_bucket(self._bucket),
        }
        os.makedirs(os.path.dirname(self._output_path) or ".", exist_ok=True)
        with open(self._output_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

        print(f"  [TemporalAgg] Flushed {bucket_key} → {self._output_path} "
              f"({record['metrics'].get('request_count', '?')} reqs)")

class TemporalAggregator:
    def __init__(
        self,
        hourly_path: str = None,
        daily_path:  str = None,
    ):
        self._hourly = _ResolutionAggregator(_hour_key, hourly_path)
        self._daily  = _ResolutionAggregator(_day_key,  daily_path)

    def ingest(self, event: dict, ts: float):
        self._hourly.ingest(event, ts)
        self._daily.ingest(event, ts)

    def flush_all(self):
        self._hourly.flush_all()
        self._daily.flush_all()

def _serialise_bucket(bucket: dict) -> dict:
    out = {}
    for k, v in bucket.items():
        if isinstance(v, defaultdict):
            out[k] = {
                ok: (dict(ov) if isinstance(ov, defaultdict) else ov)
                for ok, ov in v.items()
            }
        else:
            out[k] = v
    return out