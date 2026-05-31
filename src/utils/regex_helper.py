import re
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