import streamlit as st
from parsers.master_parser import ParserFactory, build
from indexer.aggregator import AggregatorCache
from indexer.secondbucket import SecondBucket
from detectors.master_detector import MasterDetector
from indexer.metric import METRICS

def process_batch_file(uploaded_file, format):
    detector = MasterDetector(None, "data/batch.jsonl")
    parser = ParserFactory.create(format)
    cache = AggregatorCache([], detector)
    uploaded_file.seek(0)
    try:
        raw_lines = uploaded_file.read().decode("utf-8").splitlines()
    except Exception as e:
        st.error(f"Failed to read file encoding: {e}")
        return None
    alerts = []
    metrics = []
    for line in raw_lines:
        if not line.strip():
            continue
        parsed = parser.parse_line(line)#parsed is tuple
        for detective in detector.event_detectors:
            event_alert = detective.detect(parsed)
            if event_alert: alerts += event_alert
        roll_alert, roll_metrics = ingest_event(cache, parsed)
        if roll_alert: alerts += roll_alert
        if roll_metrics: metrics.append(roll_metrics)
    return metrics, alerts

def ingest_event(cache, tsevent):
    event_sec = tsevent[0]
    event = build(tsevent)
    alerts = []
    metrics = None
    # Handle chronological progression
    if event_sec > cache.current_event_time:
        if cache.current_bucket is not None:
            cache._rollup_to_all_windows(cache.current_bucket)
            if cache.current_event_time % 60 == 0:
                metrics = cache.windows["medium"].summary
            for window in cache.windows.values():
                bucket = window.summary
                frame = window.window_seconds
                for detective in cache.detector.rollup_detectors:
                    alert = detective.detect(bucket, frame)
                    if alert: alerts.append(alert)
        cache.current_event_time = event_sec
        cache.current_bucket = SecondBucket(event_sec)
    # active second bucket
    if event_sec == cache.current_event_time:
        cache.current_bucket.request_count += 1
        cache.current_bucket.total_bytes += event.total_bytes
        for metric in METRICS.values():
            metric.aggregate_metric(cache.current_bucket.__dict__, event.__dict__)
    return alerts, metrics