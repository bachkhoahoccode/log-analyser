from datetime import datetime


class RegexParser:

    def __init__(self, spec):
        self.spec = spec
        self.pattern = spec["regex"]

    def parse_line(self, line):
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
        unix_ts = int(datetime.strptime(event[field], self.spec["time_format"]).timestamp())
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