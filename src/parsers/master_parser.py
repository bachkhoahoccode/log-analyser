from abc import ABC, abstractmethod

# Parser interface -- each parser must implement parse_line
class BaseParser(ABC):
    @abstractmethod
    def parse_log(self, file_path: str, limit: int|None = 20) -> dict[int, list]:
        pass


def pick_parser(log_type: str) -> BaseParser:
    # Factory method to select the appropriate parser based on log type
    if log_type == "apache":
        from .apache_parser import ApacheParser
        return ApacheParser()
    elif log_type == "nginx":
        from .nginx_parser import NginxParser
        return NginxParser()
    elif log_type == "auth":
        from .auth_parser import AuthParser
        return AuthParser()
    elif log_type == "cicids":
        from .cicids_parser import CICIDSParser
        return CICIDSParser()
    else:
        raise ValueError(f"Unsupported log type: {log_type}")
    
def parse_logs(file_path: str, parser: BaseParser, out_json: str | None = None, limit:int | None = None) -> dict[int, list]:
    # Delegate parsing to the parser implementation
    logs_by_timestamp = parser.parse_log(file_path, limit=limit)

    if out_json:
        # Write JSON to disk (ensure UTF-8 and pretty print)
        import json
        with open(out_json, 'w', encoding='utf-8') as fh:
            json.dump(logs_by_timestamp, fh, indent=2, ensure_ascii=False)

    return logs_by_timestamp


if __name__ == "__main__":
    def listener():
        return "log_file", "apache"
        # actually not filename but a string snippet of changes in log file.
        # the listener is actually not supposed to be here as well
    parsed = parse_logs(listener()[0], pick_parser(listener()[1]))
    import json
    print(json.dumps(parsed, indent=2, ensure_ascii=False))
    