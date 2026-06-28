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
    for ip, agents in metric.items():
        distinct = len(agents)
        if distinct < rule["distinct_threshold"]:
            continue

        alerts.append({
            "timestamp" : bucket.timestamp,
            "type": "ua_switching",
            "window": frame,
            "ip": ip,
            "risk": rule["risk"],
            "evidence": {
                "distinct_user_agents": distinct
            }
        })

    return alerts