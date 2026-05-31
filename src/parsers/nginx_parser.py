import re
from datetime import datetime
from parsers.master_parser import BaseParser
from utils.regex_helper import PATTERNS

class NginxParser(BaseParser):
    # Combined Log Format regex as a class-level compiled pattern so it's
    # compiled once and shared across instances.
    _log_pattern = PATTERNS["nginx"]

    def _parse_log_line(self, line: str):
        
        match = self._log_pattern.match(line)
        if not match:
            return None

        event = match.groupdict()
        unix_ts = int(datetime.strptime(
            event["timestamp"],
            "%d/%b/%Y:%H:%M:%S %z"
        ).timestamp())

        del event["timestamp"]

        # Convert numbers
        event["status"] = int(event["status"])
        if event["size"] == "-":
            event["size"] = 0
        else:
            event["size"] = int(event["size"])

        # Normalise optional fields (referer and user_agent may be missing)
        if event.get("referer") is None:
            event["referer"] = ""
        if event.get("user_agent") is None:
            event["user_agent"] = ""

        # Split request
        request_parts = event["request"].split()
        if len(request_parts) == 3:
            event["method"] = request_parts[0]
            event["path"] = request_parts[1]
            event["protocol"] = request_parts[2]

        return unix_ts, event

    def parse_log(self, file_path: str, limit:int = 20):
        logs_by_timestamp = {}
        with open(file_path, 'r', encoding='utf-8') as file:
            i = 0
            for line in file:
                if limit is not None and i >= limit:
                    break
                i += 1
                result = self._parse_log_line(line)
                if result:
                    unix_ts, parsed_data = result
                    if unix_ts not in logs_by_timestamp:
                        logs_by_timestamp[unix_ts] = []
                    logs_by_timestamp[unix_ts].append(parsed_data)

        return logs_by_timestamp
if __name__ == "__main__":
     parsed = NginxParser().parse_log('data/sample_datasets/sample_nginx_access.log', limit=20)
     import json
     print(json.dumps(parsed, indent=2, ensure_ascii=False))
