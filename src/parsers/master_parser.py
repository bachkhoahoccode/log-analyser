from abc import ABC, abstractmethod
from src.indexer.metric import METRICS
from src.indexer.secondbucket import SecondBucket
from src.detectors.master_detector import MasterDetector
import json
from .regex_parser import RegexParser
import asyncio
from path_config import ConfigPaths

class BaseParser(ABC):    
    def __init__(self, spec):
        self.spec = spec
    @abstractmethod
    def parse_line(self, line: str):
        pass

class ParserFactory:
    _formats = None

    @classmethod
    def formats(cls):
        if cls._formats is None:
            with open(ConfigPaths.log_formats, "r") as f:
                cls._formats = json.load(f)
        return cls._formats

    @classmethod
    def create(cls, format_name):  # Truyền cấu hình vào đây
        spec = cls.formats().get(format_name)
        if spec is None:
            raise ValueError(f"Unknown format: {format_name}")
        
        return RegexParser(spec)
    
class MasterParser:
    def __init__(self, format_names, inqueue, outqueue, detector:MasterDetector):
        self.parsers = {}
        self.format_names = format_names
        self.inqueue= inqueue
        self.outqueue = outqueue
        self.detector = detector
        for format in format_names:
            self.parsers[format] = ParserFactory.create(format)
    async def parse_logs(self):
        while self.queue:
            line = await self.inqueue.get()
            format = line["format"]
            content = line["raw_line"]
            raw_event = self.parsers[format].parse_line(content)
            asyncio.create_task(self.detector.detect_event_if_idle(list(raw_event)))
            event = self.build(raw_event)
            await self.outqueue.put(event)

    def build(self, event):
        bucket = SecondBucket(event[0])
        bucket.request_count = 1
        bucket.total_bytes = event[1].get("bytes", 0)
        for metric in METRICS.values():
            value = metric.extractor(event[1])
            if value is None:
                continue
            storage = getattr(bucket, metric.name)
            if metric.method == "direct":
                key, amount = value
                if key is not None:
                    storage[key] += amount
            else:
                outer, inner, amount = value
                if outer is not None and inner is not None:
                    storage[outer][inner] += amount
        return bucket
    
def build(event):
    # event[0] là timestamp, event[1] là dict chứa data của log đó
    timestamp, event_data = event[0], event[1]

    bucket = SecondBucket(timestamp)
    bucket.request_count = 1
    bucket.total_bytes = event_data.get("bytes", 0)
    
    for metric in METRICS.values():
        value = metric.extractor(event_data)
        if value is None:
            continue
        storage = getattr(bucket, metric.name) #empty dict 
        if metric.method == "direct":
            if isinstance(value, tuple) and len(value) == 2:
                key, amount = value
                if key is not None:
                    storage[key] = amount
            else:
                print(f"WARNING: Metric {metric.name} (direct) trả về sai tuple 2 phần tử: {value}")
        elif metric.method == "nested":
            if isinstance(value, tuple) and len(value) == 3:
                outer, inner, amount = value
                if outer is not None and inner is not None:
                    if outer not in storage:
                        storage[outer] = {}
                    storage[outer][inner] = amount
            else:
                print(f"WARNING: Metric {metric.name} (nested) trả về sai tuple 3 phần tử: {value}")
    return bucket



if __name__ == "__main__":
    try:
        with open(ConfigPaths.log_formats, "r") as config_file:
            RLOG_FORMATS = json.load(config_file)
    except FileNotFoundError:
        RLOG_FORMATS = {}

    ParserFactory.create('apache', RLOG_FORMATS)