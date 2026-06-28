from collections import defaultdict
class Metric:
    def __init__(self, name, method, factory, extractor):
        self.name = name
        self.method = method
        self.factory = factory
        self.extractor = extractor
    def aggregate_metric(self, dest, src, delta=1):

        if self.method == "direct":
            for key, value in src.items():
                dest[key] += delta * value
                if dest[key] <= 0:
                    del dest[key]

        elif self.method == "nested":
            for outer_key, inner_dict in src.items():
                for inner_key, value in inner_dict.items():
                    dest[outer_key][inner_key] += delta * value

                    if dest[outer_key][inner_key] <= 0:
                        del dest[outer_key][inner_key]

                if not dest[outer_key]:
                    del dest[outer_key]

METRICS = {
    "total_bytes_by_ip": Metric(
        "total_bytes_by_ip",
        "direct",
        lambda: defaultdict(int),
        lambda e: (e.get("ip"), e.get("bytes", 0))
    ),
    "method_counts": Metric(
        "method_counts",
        "direct",
        lambda: defaultdict(int),
        lambda e: (e.get("method"), 1)
    ),
    "user_agent_counts": Metric(
        "user_agent_counts",
        "direct",
        lambda: defaultdict(int),
        lambda e: (e.get("user_agent"), 1)
    ),
    "uri_counts": Metric(
        "uri_counts",
        "direct",
        lambda: defaultdict(int),
        lambda e: (e.get("path"), 1)
    ),
    "status_by_ip": Metric(
        "status_by_ip",
        "nested",
        lambda: defaultdict(lambda: defaultdict(int)),
        lambda e: (e.get("ip"), e.get("status"))
    ),
    "not_found_urls": Metric(
        "not_found_urls",
        "direct",
        lambda: defaultdict(int),
        lambda e: (e["path"], 1) if e.get("status") == 404 else None
    ),
    "failed_login_by_ip": Metric(
        "failed_login_by_ip",
        "direct",
        lambda: defaultdict(int),
        lambda e:
            (e.get("ip"), 1) if e.get("path") == "/login" 
            and e.get("status") in (401,403) else None
    ),
    "virtual_host_counts": Metric(
        "virtual_host_counts",
        "direct",
        lambda: defaultdict(int),
        lambda e: (e.get("virtual_host"), 1)
    ),
    "ip_counts": Metric(
        "ip_counts",
        "direct",
        lambda: defaultdict(int),
        lambda e: (e.get("ip"), 1)
    ),
    "status_counts": Metric(
        "status_counts",
        "direct",
        lambda: defaultdict(int),
        lambda e: (e.get("status"), 1)
    ),
    "uri_by_ip": Metric(
        "uri_by_ip",
        "nested",
        lambda: defaultdict(lambda: defaultdict(int)),
        lambda e: (e.get("ip"), e.get("path"), 1)
    ),
    "user_agent_by_ip": Metric(
        "user_agent_by_ip",
        "nested",
        lambda: defaultdict(lambda: defaultdict(int)),
        lambda e: (e.get("ip"), e.get("user_agent"), 1)
    ),
}