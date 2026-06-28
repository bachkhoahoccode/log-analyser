import json
from pathlib import Path

RULE = json.loads((Path(__file__).parent / "rules.json").read_text())

METRICS = RULE["metrics"]
RULES = RULE["rules"]


def detect(bucket, frame):
    rule = RULES.get(frame)
    if rule is None:
        return []

    uri_metric = getattr(bucket, METRICS["uri"])
    status_metric = getattr(bucket, METRICS["status"])

    alerts = []

    for ip, uris in uri_metric.items():

        unique_uri = len(uris)

        not_found = status_metric.get(ip, {}).get(404, 0)

        if unique_uri < rule["unique_uri_threshold"]:
            continue

        if not_found < rule["404_threshold"]:
            continue

        alerts.append({
            "timestamp" : bucket.timestamp,
            "type": "directory_scanner",
            "window": frame,
            "ip": ip,
            "risk": rule["risk"],
            "evidence": {
                "unique_uri": unique_uri,
                "404": not_found
            }
        })

    return alerts