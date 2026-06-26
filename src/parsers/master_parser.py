from abc import ABC, abstractmethod
import json

# Parser interface -- each parser must implement parse_line
class BaseParser(ABC):    
    @abstractmethod
    def _parse_log_line(self, line: str):
        pass


def pick_parser(log_type: str) -> BaseParser:
    # Factory method to select the appropriate parser based on log type
    if log_type == "apache":
        from .apache.access_parser import ApacheParser
        return ApacheParser()
    elif log_type == "nginx":
        from .Nginx.access_parser import NginxParser
        return NginxParser()
    elif log_type == "auth":
        from .auth_parser import AuthParser
        return AuthParser()
    elif log_type == "cicids":
        from .cicids_parser import CICIDSParser
        return CICIDSParser()
    else:
        raise ValueError(f"Unsupported log type: {log_type}")
    
def parse_logs(log_lines: str, parser: BaseParser, out_json: str | None = None, limit:int | None = None) -> dict[int, list]:
    # Delegate parsing to the parser implementation
    
    logs_by_timestamp = {}
    i = 0
    for line in log_lines:
        if limit is not None and i >= limit:
            break
        i += 1
        result = parser._parse_log_line(line)
        if result:
            
            unix_ts, parsed_data = result
            if unix_ts not in logs_by_timestamp:
                logs_by_timestamp[unix_ts] = []
            logs_by_timestamp[unix_ts].append(parsed_data)
    if out_json:
        # Write JSON to disk (ensure UTF-8 and pretty print)
        with open(out_json, 'w', encoding='utf-8') as fh:
            json.dump(logs_by_timestamp, fh, indent=2, ensure_ascii=False)
    return logs_by_timestamp


if __name__ == "__main__":
    #example logs:

    file_path = input("Enter the path to the log file: ")
    with open(file_path, 'r', encoding='utf-8') as file:
        parsed = parse_logs(file, default_parser = pick_parser("apache"))
    print(json.dumps(parsed, indent=2, ensure_ascii=False))
    