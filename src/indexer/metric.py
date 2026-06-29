from collections import defaultdict
class Metric:
    def __init__(self, name, method, factory, extractor):
        self.name = name
        self.method = method
        self.factory = factory
        self.extractor = extractor
    def aggregate_metric(self, dest, src, delta=1):

        if self.method == "direct":
            for key, value in src[self.name].items():
                dest[self.name][key] += delta * value
                if dest[self.name][key] <= 0:
                    del dest[self.name][key]
        elif self.method == "nested":
            for outer_key, inner_key in src[self.name].items():
                for inner_key, value in src[self.name][outer_key].items():
                    dest[self.name][outer_key][inner_key] += delta * value
                    if dest[self.name][outer_key][inner_key] <= 0:
                        del dest[self.name][outer_key][inner_key]

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
        lambda e: (e.get("path"), 1) #will deal with different name for "path" in near future
    ),
    "status_by_ip": Metric(
        "status_by_ip",
        "nested",
        lambda: defaultdict(lambda: defaultdict(int)),
        lambda e: (e.get("ip"), e.get("status"), 1)
    ),
    "not_found_urls": Metric(
        "not_found_urls",
        "direct",
        lambda: defaultdict(int),
        lambda e: (e.get("path"), 1) if e.get("status") == 404 else {}
    ),
    "failed_login_by_ip": Metric(
        "failed_login_by_ip",
        "direct",
        lambda: defaultdict(int),
        lambda e:
            (e.get("ip"), 1) if e.get("path") == "/login" 
            and e.get("status") in (401,403) else {}
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