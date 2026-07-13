import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st
from datetime import datetime, timezone

st.set_page_config(page_title="Charts smoke-test", page_icon="🧪", layout="wide")

# ── Fake metrics dict────────

fake_metrics = {
    "timestamp": int(datetime.now(timezone.utc).timestamp()),
    "request_count": 18_432,
    "total_bytes": 94_371_840,   # ~90 MB

    # KPI: virtual hosts
    "virtual_host_counts": {
        "api.example.com": 9_200,
        "static.example.com": 5_100,
        "admin.example.com": 4_132,
    },

    # Chart: bandwidth by IP
    "total_bytes_by_ip": {
        "203.0.113.42":  41_943_040,   # ~40 MB — suspicious outlier
        "198.51.100.17": 20_971_520,
        "192.168.1.55":  15_728_640,
        "10.0.0.8":       8_388_608,
        "172.16.0.99":    4_194_304,
        "198.51.100.3":   3_145_728,
    },

    # Chart: URI hits
    "uri_counts": {
        "/api/v1/products":  4_210,
        "/api/v1/users":     3_890,
        "/static/main.js":   2_540,
        "/healthz":          1_980,
        "/api/v1/orders":    1_430,
        "/admin/dashboard":    892,
        "/.env":               341,   # sus
        "/.git/config":        198,   # sus
        "/wp-admin/":           87,   # sus
    },

    # Chart: failed logins
    "failed_login_by_ip": {
        "203.0.113.42": 142,
        "198.51.100.17": 38,
        "10.0.0.8":       6,
    },

    # Chart: HTTP status donut
    "status_counts": {
        "200": 12_810,
        "304":  2_100,
        "404":  1_892,
        "401":    980,
        "403":    420,
        "500":    230,
    },

    # Chart: 404 targets
    "not_found_urls": {
        "/.env":              341,
        "/.git/config":       198,
        "/wp-admin/":          87,
        "/phpmyadmin/":        54,
        "/backup.zip":         32,
        "/config.php":         21,
    },

    # Chart: user agents
    "user_agent_counts": {
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124":  8_200,
        "Mozilla/5.0 (Macintosh) Safari/537.36":                  4_100,
        "python-requests/2.31.0":                                  2_890,   # bot
        "curl/7.88.1":                                               540,
        "Googlebot/2.1":                                             320,
        "sqlmap/1.7.8#stable":                                       182,   # scanner
        "Nikto/2.1.6":                                                98,   # scanner
    },

    # Table: IP × Status
    "status_by_ip": {
        "203.0.113.42":  {"401": 142, "403": 28, "200": 310, "404": 890},
        "198.51.100.17": {"200": 4200, "304": 890, "500": 42},
        "192.168.1.55":  {"200": 3100, "304": 420},
        "10.0.0.8":      {"200": 1800, "401": 6, "403": 2},
        "172.16.0.99":   {"200": 980, "404": 12},
    },

    # Table: IP × URI
    "uri_by_ip": {
        "203.0.113.42": {
            "/.env": 341, "/.git/config": 198, "/wp-admin/": 87,
            "/phpmyadmin/": 54, "/admin/dashboard": 210,
        },
        "198.51.100.17": {
            "/api/v1/products": 2100, "/api/v1/users": 1800,
            "/api/v1/orders": 900,
        },
        "192.168.1.55":  {"/static/main.js": 1200, "/healthz": 980},
        "10.0.0.8":      {"/api/v1/products": 800, "/api/v1/users": 620},
    },

    # Table: IP × User-Agent
    "user_agent_by_ip": {
        "203.0.113.42": {
            "sqlmap/1.7.8#stable": 182,
            "Nikto/2.1.6": 98,
            "python-requests/2.31.0": 420,
            "Mozilla/5.0 (Windows NT 10.0) Chrome/124": 310,
        },
        "198.51.100.17": {
            "Mozilla/5.0 (Windows NT 10.0) Chrome/124": 3200,
            "Mozilla/5.0 (Macintosh) Safari/537.36": 1000,
        },
        "192.168.1.55":  {"Mozilla/5.0 (Macintosh) Safari/537.36": 1800},
        "10.0.0.8":      {"python-requests/2.31.0": 1200, "curl/7.88.1": 300},
    },
}

# ── Fake alerts list

fake_alerts = [
    {
        "type":      "brute_force",
        "ip":        "203.0.113.42",
        "riskscore": 92,
        "score":     92,
        "time":      "14:32:17",
        "window":    "14:32:00 → 14:32:17",
        "evidence":  "142 failed /login attempts in 5s window (threshold: 8)",
        "fingerprint": "203.0.113.42-brute_force",
        "occurrence_count": 3,
    },
    {
        "type":      "xss_attempt",
        "ip":        "203.0.113.42",
        "riskscore": 65,
        "score":     65,
        "time":      "14:31:54",
        "window":    "14:31:54 → 14:31:54",
        "evidence":  "XSS payload in URI: /search?q=<script>alert(1)</script>",
        "fingerprint": "203.0.113.42-xss_attempt",
        "occurrence_count": 1,
    },
    {
        "type":      "directory_scanner",
        "ip":        "203.0.113.42",
        "riskscore": 48,
        "score":     48,
        "time":      "14:30:02",
        "window":    "14:30:00 → 14:30:05",
        "evidence":  "890 × 404 across 12 unique URIs in 5s (thresholds: 10 errors, 15 URIs)",
        "fingerprint": "203.0.113.42-directory_scanner",
        "occurrence_count": 7,
    },
    {
        "type":      "suspicious_uri",
        "ip":        "198.51.100.17",
        "riskscore": 22,
        "score":     22,
        "time":      "14:28:41",
        "window":    "14:28:41 → 14:28:41",
        "evidence":  "Request to watchlisted path: /.env",
        "fingerprint": "198.51.100.17-suspicious_uri",
        "occurrence_count": 1,
    },
]

# ── Run ───────────────────────────────────────────────────────────────

st.title("🧪 Charts smoke-test — fake data")
st.caption("Verifying charts.py renders correctly before wiring live/batch producers.")

st.markdown("---")

from dashboard.charts import render_charts
render_charts(fake_metrics, fake_alerts)
