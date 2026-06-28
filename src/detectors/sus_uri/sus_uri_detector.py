import json
from pathlib import Path
RULE = json.loads((Path(__file__).parent/"rules.json").read_text())

def detect(tsevent):
    ts, event = tsevent
    path = str(event.get(RULE["field"])).lower()
    for target in RULE["watchlist"]:
        if target in path:
            return [{
                "timestamp" : ts,
                "type": "suspicious_uri",
                "ip": event['ip'],
                "risk": RULE["risk"],
                "evidence": {
                    "path": path,
                    "matched": target
                }
            }]
    return []