import asyncio
import json
import os

from scoring.risk_score import AlertGroupAccumulator, make_fingerprint

def read_and_clear_buffer(path: str) -> list[str]:
    """Read all lines from the buffer file and wipe it atomically."""
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
    buffer_path:  str = "alerts_buffer.jsonl",
    history_path: str = "history_final.jsonl",
):
    print("[Processor] Active — sleeping until alert_trigger_event fires.")
    seen_fingerprints: set[str] = set()

    try:
        while True:
            # 0 % CPU sleep: wakes only when master_detector calls event.set()
            await alert_trigger_event.wait()
            alert_trigger_event.clear()

            raw_lines = await asyncio.to_thread(read_and_clear_buffer, buffer_path)
            if not raw_lines:
                continue

            # ── Parse & deduplicate ──────────────────────────────────
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

            # ── Enrich & write ───────────────────────────────────────
            for enriched in accumulator.enriched_alerts():
                fp = enriched["fingerprint"]
                seen_fingerprints.add(fp)

                await asyncio.to_thread(append_to_history, history_path, enriched)
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
            alert = json.loads(line)
            if make_fingerprint(alert.get("raw_data", {})) not in seen_fingerprints:
                flush_acc.add(alert)

        for enriched in flush_acc.enriched_alerts():
            append_to_history(history_path, enriched)

        print("[Processor] Buffer flushed. Engine offline.")