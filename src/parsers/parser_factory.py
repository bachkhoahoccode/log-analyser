import json
from .regex_parser import RegexParser

try:
    with open("log_formats.json", "r") as config_file:
        LOG_FORMATS = json.load(config_file)
except FileNotFoundError:
    LOG_FORMATS = {}

class ParserFactory:
    @staticmethod
    def create(format_name):
        # 2. Look up the specifications in the loaded config
        spec = LOG_FORMATS.get(format_name)
        if spec is None:
            raise ValueError(f"Unknown format: {format_name}")

        return RegexParser(spec)
    
if __name__ == "__main__":
    #example logs:

    file_path = input("Enter the path to the log file: ")
    with open(file_path, 'r', encoding='utf-8') as file:
        parsertype = "apache"
        parser = ParserFactory.create(parsertype)
        parsed = parser.parse_line(file)
    print(json.dumps(parsed, indent=2, ensure_ascii=False))
