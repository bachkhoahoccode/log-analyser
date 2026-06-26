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

def find_timestamp_format(ts_str: str) -> str:

     # ISO Z fix
    if ts_str.endswith("Z"):
        ts_str = ts_str.replace("Z", "+00:00")

    # raw unix timestamp
    if ts_str.isdigit():
        length = len(ts_str)

        if length == 10:
            return "unix_seconds"
        elif length == 13:
            return "unix_milliseconds"
        elif length == 16:
            return "unix_microseconds"
        elif length == 19:
            return "unix_nanoseconds"

        return "unix_unknown"

    for fmt in KNOWN_FORMATS:
        try:
            dt = datetime.strptime(ts_str, fmt)
            return fmt
        except ValueError:
            continue
    raise ValueError(f"Unrecognized timestamp format: {ts_str}")