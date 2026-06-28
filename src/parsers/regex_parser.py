from typing import Optional, Tuple, Dict, Any
from datetime import datetime
import json
import re

try:
    with open("log_formats.json", "r") as config_file:
        LOG_FORMATS = json.load(config_file)
except FileNotFoundError:
    LOG_FORMATS = {}


class RegexParser:

    def __init__(self, spec):
        self.spec = spec
        self.pattern = re.compile(spec["regex"])

    def parse_line(self, line)-> Optional[Tuple[int, Dict[str, Any]]]:
        match = self.pattern.match(line)
        if not match:
            return None
        event = match.groupdict()
        unix_ts = self._parse_timestamp(event)
        self._convert_numeric_fields(event)
        self._normalize_optional_fields(event)
        self._split_request(event)
        return unix_ts, event

    def _parse_timestamp(self, event):
        field = self.spec["time_field"]
        format = self.spec["time_format"]
        unix = int(datetime.strptime(event[field], format).timestamp())
        unix_ts = unix // 10**(len(str(unix))-10)

        del event[field]
        return unix_ts

    def _convert_numeric_fields(self, event):
        for field in self.spec.get("numeric_fields", []):
            if field not in event:
                continue
            if (field in self.spec.get("dash_as_zero", []) and event[field] == "-"):
                event[field] = 0
            else:
                event[field] = int(event[field])

    def _normalize_optional_fields(self,event):
        for field in self.spec.get("optional_fields",[]):
            event[field] = (event.get(field) or "")

    def _split_request(self,event):
        request_field = (self.spec.get("request_field"))
        request = event.get(request_field)
        if not request:
            return
        parts = request.split(maxsplit=2)
        if len(parts) != 3:
            return
        event["method"] = parts[0]
        event["path"] = parts[1]
        event["protocol"] = parts[2]

if __name__ == "__main__":
    #example logs:

    file_path = input("Enter the path to the log file: ")
    with open(file_path, 'r', encoding='utf-8') as file:
        parsertype = "apache"
        parser = RegexParser("apache") #not working, placeholder
        parsed = parser.parse_line(file)
    print(json.dumps(parsed, indent=2, ensure_ascii=False))
