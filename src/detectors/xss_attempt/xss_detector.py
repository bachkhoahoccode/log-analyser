import json
from pathlib import Path

RULE = json.loads((Path(__file__).parent/"rules.json").read_text())


def detect(tsevent):
    ts, event = tsevent
    text = str(event.get(RULE["field"])).lower()
    for pattern in RULE["patterns"]:
        if pattern.lower() in text:
            return [{
                "timestamp": ts,
                "type": "xss_attempt",
                "ip": event['ip'],
                "risk": RULE["risk"],
                "evidence": {
                    "pattern": pattern,
                    "request": text
                }
            }]

    return []