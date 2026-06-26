"""                
                # Apply your "Detector" logic on the specific field
                if data['status'] == '401':
                    print(f"Alert: Potential unauthorized access to {data['url']} from {data['ip']}")
                    # Trigger your graph/alerting layer here

"""

import time
from parsers.master_parser import pick_parser, parse_logs
from threading import Thread

Thread(target=log_maker, daemon=True).start()
Thread(target=listener, daemon=True).start()

input("Press Enter to quit\n")
last_position = 0

#def process(new_lines):


while True:
    with open("access.log") as f:
        f.seek(last_position)

        new_lines = f.readlines()

        last_position = f.tell()

    #process(new_lines)
    parse_logs(new_lines, pick_parser("apache"))
    time.sleep(1)



from cache import AggregatorCache
from detectors import AttackDetector

cache = AggregatorCache()
detector = AttackDetector(cache)

def process_log_stream(line_iterator):
    for line in line_iterator:
        event = parse_to_event_dict(line) # Extract timestamp, ip, etc.
        
        # Ingest updates the clock and the buckets automatically
        cache.ingest_event(event)
        
        # Check if this line triggered an alert based on the updated time state
        alerts = detector.evaluate_ip(event["ip"])
        for alert in alerts:
            print(f"[ALERT] Timestamp: {event['timestamp']} | {alert}")

# SCENARIO 1: Manual File Upload
with open("historical_access.log", "r") as f:
    process_log_stream(f)

# SCENARIO 2: Real-time Live Tail (e.g., listening to Nginx log pipe)
# process_log_stream(tail_live_stream())