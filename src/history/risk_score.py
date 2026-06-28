"""
risk_scoring.py — Alert enrichment and aggregation engine.

Responsibilities:
  - Score an individual alert payload
  - Accumulate repeated alerts (same fingerprint) into a group
  - Derive the begin/end time window from a group
  - Produce the final enriched dict that history_processor writes to disk

history_processor.py is the only caller; it owns I/O and dedup state.
"""

from collections import defaultdict


# ======================================================================
# FINGERPRINT  (shared key format — import this wherever you need it)
# ======================================================================

def make_fingerprint(alert_content: dict) -> str:
    """Stable string key that identifies a logical alert, not an individual event."""
    ip   = alert_content.get("ip",   "unknown")
    kind = alert_content.get("type", "generic")
    return f"{ip}-{kind}"


# ======================================================================
# SCORING
# ======================================================================

def calculate_severity_score(alert_content: dict) -> int:
    """
    Derive a 0-100 risk score from a single alert payload.
    Extend the rules here without touching the processor loop.
    """
    score = 10  # baseline

    if "critical" in str(alert_content).lower():
        score += 50

    if "failed_attempts" in alert_content:
        score += min(alert_content["failed_attempts"] * 5, 40)

    return min(score, 100)


# ======================================================================
# GROUP ACCUMULATOR
# ======================================================================

class AlertGroupAccumulator:
    """
    Tracks every occurrence of each fingerprint seen in the current
    processor wake cycle so we can derive begin/end windows and a
    consolidated score across repeated events.

    Typical lifecycle (one wake cycle):
        acc = AlertGroupAccumulator()
        for raw_alert in buffered_alerts:
            acc.add(raw_alert)
        for enriched in acc.enriched_alerts():
            write_to_file(enriched)
        acc.clear()
    """

    def __init__(self):
        # fingerprint -> list of raw alert dicts (preserves insertion order)
        self._groups: dict[str, list[dict]] = defaultdict(list)

    def add(self, raw_alert: dict):
        """Register one buffered alert record."""
        content     = raw_alert.get("raw_data", {})
        fingerprint = make_fingerprint(content)
        self._groups[fingerprint].append(raw_alert)

    def enriched_alerts(self):
        """
        Yield one enriched dict per unique fingerprint.
        The dict is ready to be serialised and appended to history.
        """
        for fingerprint, occurrences in self._groups.items():
            yield _build_enriched_alert(fingerprint, occurrences)

    def clear(self):
        self._groups.clear()

    def __len__(self):
        return len(self._groups)


# ======================================================================
# INTERNAL: BUILD ENRICHED ALERT
# ======================================================================

def _build_enriched_alert(fingerprint: str, occurrences: list[dict]) -> dict:
    """
    Merge all occurrences of one fingerprint into a single enriched record.

    Fields added / overwritten versus the raw buffer record:
        score           — highest severity score across all occurrences
        occurrence_count — how many raw events were grouped together
        window_begin    — earliest timestamp seen
        window_end      — latest timestamp seen
        window          — [window_begin, window_end] (matches charts.py alert shape)
    """
    # Use the first occurrence as the base (has type, ip, raw_data, etc.)
    base    = dict(occurrences[0])
    content = base.get("raw_data", {})

    # Score: take the maximum across all occurrences so the worst-case
    # event drives the risk number, not whichever happened to arrive first.
    score = max(calculate_severity_score(o.get("raw_data", {})) for o in occurrences)

    # Time window: collect all timestamps, sort, take first and last.
    timestamps = sorted(
        o.get("timestamp") or o.get("raw_data", {}).get("timestamp")
        for o in occurrences
        if (o.get("timestamp") or o.get("raw_data", {}).get("timestamp"))
    )

    window_begin = timestamps[0]  if timestamps else None
    window_end   = timestamps[-1] if timestamps else None

    base.update({
        "score":            score,
        "occurrence_count": len(occurrences),
        "window_begin":     window_begin,
        "window_end":       window_end,
        "window":           [window_begin, window_end],  # charts.py alert shape
        "fingerprint":      fingerprint,
    })

    return base