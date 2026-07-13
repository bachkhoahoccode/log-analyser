import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# ======================================================================
# PUBLIC ENTRY POINT
# ======================================================================

def render_charts(metrics: list[dict], alerts: list[dict]):
    """
    metrics: list of per-window snapshot dicts, each shaped like the old
             single `metrics` dict but with a "timestamp" key.
             Example: [{"timestamp": 1717200000, "request_count": 12, ...}, ...]
    alerts:  list of alert dicts (unchanged shape).
    """
    if not metrics:
        st.info("No metric snapshots in this analysis frame yet.")
        return

    latest = metrics[-1]
    summed = _sum_snapshots(metrics)

    _render_kpi_row(summed, latest, alerts)
    st.markdown("---")
    _render_alert_queue(alerts)
    st.markdown("---")
    _render_metric_charts(latest)          # per-IP/per-URI charts
    st.markdown("---")
    _render_investigation_tables(latest)   # drill-down tables
    st.markdown("---")
    _render_time_series(metrics)           # multi-chart grid over time


# ======================================================================
# HELPERS — combining the list of snapshots
# ======================================================================

# Keys that should be summed across all snapshots for the KPI row.
# (Per-IP/per-URI dict metrics are intentionally excluded — those use
# the "latest snapshot only" path per product decision.)
_SUMMABLE_SCALAR_KEYS = ["request_count", "total_bytes"]

def _sum_snapshots(metrics: list[dict]) -> dict:
    """Sum scalar KPI fields across every snapshot in the list."""
    summed = {key: 0 for key in _SUMMABLE_SCALAR_KEYS}
    vhost_union: dict[str, int] = {}

    for snap in metrics:
        for key in _SUMMABLE_SCALAR_KEYS:
            summed[key] += snap.get(key, 0)

        for host, count in snap.get("virtual_host_counts", {}).items():
            vhost_union[host] = vhost_union.get(host, 0) + count

    summed["virtual_host_counts"] = vhost_union
    return summed


def _metrics_to_dataframe(metrics: list[dict], keys: list[str]) -> pd.DataFrame:
    """
    Build a tidy DataFrame with one row per snapshot, columns = timestamp + keys.
    Missing keys default to 0. Used by the time-series tab.
    """
    rows = []
    for snap in metrics:
        ts = snap.get("timestamp")
        row = {"timestamp": datetime.fromtimestamp(ts) if ts else None}
        for key in keys:
            value = snap.get(key, 0)
            # scalar metrics go straight in; dict metrics get summed to a single number
            row[key] = sum(value.values()) if isinstance(value, dict) else value
        rows.append(row)
    return pd.DataFrame(rows)

# ======================================================================
# SECTION: KPI ROW
# ======================================================================

def _render_kpi_row(summed: dict, latest: dict, alerts: list):
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Requests (frame)",
                  value=f"{summed.get('request_count', 0):,}")
    with col2:
        raw_bytes = summed.get("total_bytes", 0)
        st.metric("Network Outbound (frame)",
                  value=f"{raw_bytes / (1024 * 1024):.2f} MB")
    with col3:
        st.metric("Active Alerts",
                  value=len(alerts),
                  delta="Action Required" if alerts else None,
                  delta_color="inverse")
    with col4:
        vhosts = summed.get("virtual_host_counts", {})
        st.metric("Active Host Environments (frame)", value=len(vhosts))

    ts = latest.get("timestamp")
    if ts:
        readable = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
        st.caption(f"Latest snapshot timestamp: {readable}")

# ======================================================================
# SECTION: ALERT QUEUE  (unchanged — alerts shape didn't change)
# ======================================================================

def _render_alert_queue(alerts: list):
    st.header("🚨 Incident Response & Real-Time Alert Triage")

    if not alerts:
        st.success("No alerts in the current analysis frame.")
        return

    for alert in alerts:
        color = "crimson" if alert.get("riskscore", 0) >= 80 else "darkorange"
        st.markdown(
            f"""
            <div style="
                border: 1px solid #ddd;
                padding: 15px;
                border-radius: 8px;
                margin-bottom: 12px;
                border-left: 6px solid {color};
                background-color: #fdfdfd;
            ">
                <span style="float:right; font-weight:bold; color:{color}; font-size:1.1em;">
                    Risk Score: {alert.get('riskscore','—')}
                </span>
                <h4 style="margin:0; color:#333;">
                    [{alert.get('time','—')}] {alert.get('type','Unknown')}
                </h4>
                <p style="margin:5px 0 2px 0; font-size:0.95em;">
                    <b>Source IP:</b> <code>{alert.get('ip','—')}</code>
                    &nbsp;|&nbsp;
                    <b>Window:</b> {alert.get('window','—')}
                </p>
                <p style="margin:0; font-size:0.9em; color:#555;">
                    <b>Evidence:</b> {alert.get('evidence','—')}
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

# ======================================================================
# SECTION: METRIC CHARTS  (latest snapshot only, per product decision)
# ======================================================================

def _render_metric_charts(latest: dict):
    st.header("📊 Current Snapshot — Metric Insights")
    st.caption("Per-IP / per-URI breakdowns reflect the most recent snapshot only.")
    left, right = st.columns(2)

    with left:
        bytes_by_ip = latest.get("total_bytes_by_ip", {})
        if bytes_by_ip:
            df = pd.DataFrame(bytes_by_ip.items(), columns=["Source IP", "Bytes"])
            df["MB"] = (df["Bytes"] / (1024 * 1024)).round(2)
            df = df.sort_values("MB")
            fig = px.bar(df, x="MB", y="Source IP", orientation="h",
                         title="Source Node Bandwidth Footprint (MB)",
                         color_discrete_sequence=["#4A90E2"])
            st.plotly_chart(fig, use_container_width=True)

        uri_counts = latest.get("uri_counts", {})
        if uri_counts:
            df = pd.DataFrame(uri_counts.items(), columns=["URI", "Hits"]).sort_values("Hits")
            fig = px.bar(df, x="Hits", y="URI", orientation="h",
                         title="Top Visited Resource Paths",
                         color_discrete_sequence=["#6C757D"])
            st.plotly_chart(fig, use_container_width=True)

        failed = latest.get("failed_login_by_ip", {})
        if failed:
            df = pd.DataFrame(failed.items(), columns=["Source IP", "Failures"]).sort_values("Failures")
            fig = px.bar(df, x="Failures", y="Source IP", orientation="h",
                         title="Failed Login Counts by IP",
                         color_discrete_sequence=["#E24A4A"])
            st.plotly_chart(fig, use_container_width=True)

    with right:
        status_counts = latest.get("status_counts", {})
        if status_counts:
            df = pd.DataFrame(status_counts.items(), columns=["HTTP Status", "Hits"])
            fig = px.pie(df, values="Hits", names="HTTP Status", hole=0.4,
                         title="HTTP Response States",
                         color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig, use_container_width=True)

        not_found = latest.get("not_found_urls", {})
        if not_found:
            df = pd.DataFrame(not_found.items(), columns=["Missing Endpoint", "Hits"]).sort_values("Hits")
            fig = px.bar(df, x="Hits", y="Missing Endpoint", orientation="h",
                         title="Directory Traversal Footprint (404 Targets)",
                         color_discrete_sequence=["#F5A623"])
            st.plotly_chart(fig, use_container_width=True)

        ua_counts = latest.get("user_agent_counts", {})
        if ua_counts:
            df = pd.DataFrame(ua_counts.items(), columns=["User Agent", "Hits"]).sort_values("Hits")
            fig = px.bar(df, x="Hits", y="User Agent", orientation="h",
                         title="Identified Software Fingerprints")
            st.plotly_chart(fig, use_container_width=True)


# ======================================================================
# SECTION: NESTED DRILL-DOWN TABLES  (latest snapshot only)
# ======================================================================

def _render_investigation_tables(latest: dict):
    st.header("🔍 Cross-Reference Investigation Tables")
    st.markdown("> Nested bucket data: `ip → key → count` — most recent snapshot only.")

    tab_status, tab_uri, tab_ua = st.tabs([
        "IP × Status Matrix",
        "IP × URI Matrix",
        "IP × User-Agent Profiles",
    ])

    with tab_status:
        rows = [
            {"IP Address": ip, "HTTP Status": status, "Hits": count}
            for ip, statuses in latest.get("status_by_ip", {}).items()
            for status, count in statuses.items()
        ]
        st.dataframe(pd.DataFrame(rows) if rows else pd.DataFrame(), use_container_width=True)

    with tab_uri:
        rows = [
            {"IP Address": ip, "Endpoint": path, "Hits": count}
            for ip, uris in latest.get("uri_by_ip", {}).items()
            for path, count in uris.items()
        ]
        st.dataframe(pd.DataFrame(rows) if rows else pd.DataFrame(), use_container_width=True)

    with tab_ua:
        rows = [
            {"IP Address": ip, "User Agent": ua, "Hits": count}
            for ip, uas in latest.get("user_agent_by_ip", {}).items()
            for ua, count in uas.items()
        ]
        st.dataframe(pd.DataFrame(rows) if rows else pd.DataFrame(), use_container_width=True)

# ======================================================================
# SECTION: TIME SERIES  (new — multi-chart grid, one chart per metric)
# ======================================================================

_TIME_SERIES_KEYS = [
    "request_count",
    "total_bytes",
    "failed_login_by_ip",
    "not_found_urls",
    "status_counts",
    "uri_counts",
]

_TIME_SERIES_LABELS = {
    "request_count":      "Requests per Window",
    "total_bytes":        "Bandwidth per Window (bytes)",
    "failed_login_by_ip": "Failed Logins per Window",
    "not_found_urls":     "404 Hits per Window",
    "status_counts":      "Total Status Hits per Window",
    "uri_counts":         "Total URI Hits per Window",
}

def _render_time_series(metrics: list[dict]):
    st.header("📈 Trend Analysis — Metrics Over Time")

    if len(metrics) < 2:
        st.info("Need at least 2 snapshots to draw a trend. Currently have "
                f"{len(metrics)}.")
        return
    df = _metrics_to_dataframe(metrics, _TIME_SERIES_KEYS)
    cols = st.columns(2)
    for i, key in enumerate(_TIME_SERIES_KEYS):
        with cols[i % 2]:
            fig = px.line(df, x="timestamp", y=key,
                          title=_TIME_SERIES_LABELS.get(key, key),
                          markers=True)
            fig.update_layout(margin=dict(l=10, r=10, t=40, b=10), height=280)
            st.plotly_chart(fig, use_container_width=True)