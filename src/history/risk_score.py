from collections import defaultdict
# ======================================================================
# FINGERPRINT
# ======================================================================

def make_fingerprint(alert_content: dict) -> str:
    ip   = alert_content.get("ip",   "unknown")
    kind = alert_content.get("type", "generic")
    return f"{ip}-{kind}"

# ======================================================================
# SCORING
# ======================================================================
def calculate_severity_score(alert_content: dict) -> int:
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

    def __init__(self):
        # fingerprint -> list of raw alert dicts (preserves insertion order)
        self._groups: dict[str, list[dict]] = defaultdict(list)

    def add(self, raw_alert: dict):
        content     = raw_alert.get("raw_data", {})
        fingerprint = make_fingerprint(content)
        self._groups[fingerprint].append(raw_alert)

    def enriched_alerts(self):
        for fingerprint, occurrences in self._groups.items():
            yield _build_enriched_alert(fingerprint, occurrences)

    def clear(self):
        self._groups.clear()

    def __len__(self):
        return len(self._groups)
    
# ======================================================================
# BUILD ENRICHED ALERT
# ======================================================================
def _build_enriched_alert(fingerprint: str, occurrences: list[dict]) -> dict:
    """
    Merge all occurrences of one fingerprint into a single enriched record.

    Fields added / overwritten versus the raw buffer record:
        score           — highest severity score across all occurrences
        occurrence_count — how many raw events were grouped together
        window          — [window_begin, window_end]
    """
    # Use first occurrence as base
    base    = dict(occurrences[0])
    content = base.get("raw_data", {})
    # Score: take the maximum across all occurrences so the worst-case event drives the risk number
    score = max(calculate_severity_score(o.get("raw_data", {})) for o in occurrences)
    # Time window
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