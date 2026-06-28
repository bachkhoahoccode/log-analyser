import json
from pathlib import Path

RULE = json.loads((Path(__file__).parent / "rules.json").read_text())

METRIC = RULE["metric"]
RULES = RULE["rules"]


def detect(bucket, frame):
    rule = RULES.get(frame)
    if rule is None:
        return []

    metric = getattr(bucket, METRIC)

    alerts = []

    for ip, count in metric.items():

        if count < rule["threshold"]:
            continue

        alerts.append({
            "timestamp" : bucket.timestamp,
            "type": "flood",
            "window": frame,
            "risk": rule["risk"],
            "evidence": {
                "requests": count
            }
        })

    return alerts