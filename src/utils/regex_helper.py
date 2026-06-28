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
    total_lines = 0
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        total_lines += 1
        for name, spec in formats.items():
            regex = spec["regex"]
            if re.match(regex,line):
                scores[name] += 1
        if total_lines >= sample_size:
            break

    if total_lines == 0:
        return None

    best_format = max(scores, key=scores.get, default=None)
    if best_format is None:
        return None
    return best_format
    '''return {
        "format": best_format,
        "confidence": scores[best_format] / total_lines,
        "matches": dict(scores)
    }'''