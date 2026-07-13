import asyncio
import json
import os

from .risk_score import AlertGroupAccumulator, make_fingerprint
from .temporal_aggregator import TemporalAggregator

def read_and_clear_buffer(path: str) -> list[str]:
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return []
    with open(path, "r+", encoding="utf-8") as f:
        lines = f.readlines()
        f.seek(0)
        f.truncate()
    return lines


def append_to_history(path: str, data: dict):
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(data) + "\n")

async def historical_processor_loop(
    alert_trigger_event,
    buffer_path:  str = None,
    history_path: str = None,
    hourly_path:  str = None,
    daily_path:   str = None,
):
    if buffer_path is None:
        return
    print("[Processor] Active — sleeping until alert_trigger_event fires.")

    seen_fingerprints: set[str] = set()

    # One TemporalAggregator lives for the lifetime of this coroutine
    # buckets accumulate correctly across multiple wake cycles.
    temporal = TemporalAggregator(
        hourly_path=hourly_path,
        daily_path=daily_path,
    )

    try:
        while True:
            await alert_trigger_event.wait()
            alert_trigger_event.clear()

            raw_lines = await asyncio.to_thread(read_and_clear_buffer, buffer_path)
            if not raw_lines:
                continue
            accumulator = AlertGroupAccumulator()

            for line in raw_lines:
                if not line.strip():
                    continue

                alert   = json.loads(line)
                content = alert.get("raw_data", {})
                fp      = make_fingerprint(content)

                if fp in seen_fingerprints:
                    print(f"  [Processor] Skipping duplicate: {fp}")
                    continue

                accumulator.add(alert)
                ts = (
                    alert.get("timestamp")
                    or content.get("timestamp")
                )
                if ts:
                    temporal.ingest(content, float(ts))

            # Enrich grouped alerts and write to history
            for enriched in accumulator.enriched_alerts():
                fp = enriched["fingerprint"]
                seen_fingerprints.add(fp)
                if history_path is not None:
                    await asyncio.to_thread(append_to_history, history_path, enriched)
                if hourly_path is not None:
                    await asyncio.to_thread(append_to_history, hourly_path, enriched)
                if daily_path is not None:
                    await asyncio.to_thread(append_to_history, daily_path, enriched)
                print(
                    f"  [Processor] Saved: {fp} | "
                    f"occurrences={enriched['occurrence_count']} | "
                    f"score={enriched['score']} | "
                    f"window={enriched['window']}"
                )

    except asyncio.CancelledError:
        print("[Processor] Shutdown — flushing remaining buffer.")

        leftover = read_and_clear_buffer(buffer_path)
        flush_acc = AlertGroupAccumulator()

        for line in leftover:
            if not line.strip():
                continue
            alert   = json.loads(line)
            content = alert.get("raw_data", {})
            fp      = make_fingerprint(content)

            if fp not in seen_fingerprints:
                flush_acc.add(alert)

            ts = alert.get("timestamp") or content.get("timestamp")
            if ts:
                temporal.ingest(content, float(ts))

        for enriched in flush_acc.enriched_alerts():
            if history_path is not None:
                append_to_history(history_path, enriched)
            if hourly_path is not None:
                append_to_history(hourly_path, enriched)
            if daily_path is not None:
                append_to_history(daily_path, enriched)

        temporal.flush_all()
        print("[Processor] Buffer and temporal buckets flushed. Engine offline.")