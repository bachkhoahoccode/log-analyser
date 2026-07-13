from dataclasses import dataclass
from pathlib import Path

@dataclass
class StorageConfig:
    mode: str  # "live" or "batch"
    session_id: str = ""  # e.g. timestamp or uploaded filename slug

    @property
    def base_dir(self) -> Path:
        if self.mode == "live":
            return Path("data/live")
        return Path(f"data/batch/{self.session_id}")
    @property
    def alerts_buffer(self) -> Path:
        return self.base_dir / "alerts_buffer.jsonl"
    @property
    def alerts_history(self) -> Path:
        return self.base_dir / "history_final.jsonl"
    @property
    def hourly_history(self) -> Path:
        return self.base_dir / "history_hourly.jsonl"
    @property
    def daily_history(self) -> Path:
        return self.base_dir / "history_daily.jsonl"
    @property
    def metrics_history(self) -> Path:
        return self.base_dir / "metrics_history.jsonl"
    @property
    def log_formats_config(self) -> Path:
        return Path("config/regex_log_formats.json") 
    def ensure_dirs(self):
        self.base_dir.mkdir(parents=True, exist_ok=True)
 
ROOT = Path(__file__).parent.parent   # points to project root
 
class ConfigPaths:
    log_formats = ROOT / "config" / "regex_log_formats.json"
    system      = ROOT / "config" / "system.json"
    files_monitored = ROOT / "config" / "files_monitored.json"