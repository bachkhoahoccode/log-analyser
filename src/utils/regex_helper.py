import re
from collections import defaultdict
PATTERNS = {
    "apache": re.compile(
        r'(?P<ip>\S+) '
        r'(?P<identd>\S+) '
        r'(?P<userid>\S+) '
        r'\[(?P<timestamp>[^\]]+)\] '
        r'"(?P<request>[^\"]*)" '
        r'(?P<status>\d{3}) '
        r'(?P<size>\S+)'
        r'(?: "(?P<referer>[^"]*)" "(?P<user_agent>[^"]*)")?'
        ),
    "nginx": re.compile(r'(?P<ip>\S+) '
        r'(?P<identd>\S+) '
        r'(?P<userid>\S+) '
        r'\[(?P<timestamp>[^\]]+)\] '
        r'"(?P<request>[^\"]*)" '
        r'(?P<status>\d{3}) '
        r'(?P<size>\S+)'
        r'(?: "(?P<referer>[^"]*)" "(?P<user_agent>[^"]*)")?'
        )
}


def detect_log_format(lines, formats, sample_size=100):
    scores = defaultdict(int)
    first_match = {}
    total = 0
    for line in lines:
        line = line.strip()
        if not line:
            continue
        total += 1
        for name, spec in formats.items():
            m = re.match(spec["regex"], line)
            if m:
                scores[name] += 1
                if name not in first_match:
                    first_match[name] = (spec["time_format"], m)
        if total >= sample_size:
            break

    if not scores:
        return None
    best = max(scores, key=scores.get)
    return {
        "name": best,
        "timestamp" : first_match[best][1].group(formats[best]["time_field"]),
    }