from datetime import datetime, timezone

KNOWN_FORMATS = [
    "%Y-%m-%dT%H:%M:%S.%f%z",
    "%Y-%m-%dT%H:%M:%S%z",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y-%m-%d %H:%M:%S,%f",
    "%d/%b/%Y:%H:%M:%S %z",
    "%b %d %H:%M:%S",
    "%a, %d %b %Y %H:%M:%S %z",
    "%Y/%m/%d %H:%M:%S",
    "%Y%m%d%H%M%S",
]

def parse_timestamp(ts_str: str) -> int:

     # ISO Z fix
    if timestamp_str.endswith("Z"):
        timestamp_str = timestamp_str.replace("Z", "+00:00")

    # raw unix timestamp
    if timestamp_str.isdigit():
        return parse_unix_number(timestamp_str)
    
    for fmt in KNOWN_FORMATS:
        try:
            dt = datetime.strptime(ts_str, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return int(dt.timestamp())
        except ValueError:
            continue
    raise ValueError(f"Unrecognized timestamp format: {ts_str}")