from dataclasses import dataclass
@dataclass
class WindowRule:
    threshold: int
    risk: int

@dataclass
class RollupDetectorConfig:
    enabled: bool
    metric: str
    short: WindowRule
    medium: WindowRule
    long: WindowRule