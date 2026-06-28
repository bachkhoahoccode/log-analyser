import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# ======================================================================
# PUBLIC ENTRY POINT
# ======================================================================

def render_charts(metrics: dict, alerts: list):
    _render_kpi_row(metrics, alerts)
    st.markdown("---")
    _render_alert_queue(alerts)
    st.markdown("---")
    _render_metric_charts(metrics)
    st.markdown("---")
    _render_investigation_tables(metrics)

# ======================================================================
# SECTION: KPI ROW
# ======================================================================

def _render_kpi_row(metrics: dict, alerts: list):
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Window Total Requests",
                  value=f"{metrics.get('request_count', 0):,}")
    with col2:
        raw_bytes = metrics.get("total_bytes", 0)
        st.metric("Network Outbound",
                  value=f"{raw_bytes / (1024 * 1024):.2f} MB")
    with col3:
        st.metric("Active Alerts",
                  value=len(alerts),
                  delta="Action Required" if alerts else None,
                  delta_color="inverse")
    with col4:
        vhosts = metrics.get("virtual_host_counts", {})
        st.metric("Active Host Environments", value=len(vhosts))

    ts = metrics.get("timestamp")
    if ts:
        readable = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
        st.caption(f"Snapshot timestamp: {readable}")


# ======================================================================
# SECTION: ALERT QUEUE
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
# SECTION: METRIC CHARTS
# ======================================================================

def _render_metric_charts(metrics: dict):
    st.header("📊 Aggregated Metric Insights")
    left, right = st.columns(2)

    with left:
        # Bandwidth by IP
        bytes_by_ip = metrics.get("total_bytes_by_ip", {})
        if bytes_by_ip:
            df = pd.DataFrame(bytes_by_ip.items(), columns=["Source IP", "Bytes"])
            df["MB"] = (df["Bytes"] / (1024 * 1024)).round(2)
            df = df.sort_values("MB")
            fig = px.bar(df, x="MB", y="Source IP", orientation="h",
                         title="Source Node Bandwidth Footprint (MB)",
                         color_discrete_sequence=["#4A90E2"])
            st.plotly_chart(fig, use_container_width=True)

        # URI hits
        uri_counts = metrics.get("uri_counts", {})
        if uri_counts:
            df = pd.DataFrame(uri_counts.items(), columns=["URI", "Hits"]).sort_values("Hits")
            fig = px.bar(df, x="Hits", y="URI", orientation="h",
                         title="Top Visited Resource Paths",
                         color_discrete_sequence=["#6C757D"])
            st.plotly_chart(fig, use_container_width=True)

        # Failed logins
        failed = metrics.get("failed_login_by_ip", {})
        if failed:
            df = pd.DataFrame(failed.items(), columns=["Source IP", "Failures"]).sort_values("Failures")
            fig = px.bar(df, x="Failures", y="Source IP", orientation="h",
                         title="Failed Login Counts by IP",
                         color_discrete_sequence=["#E24A4A"])
            st.plotly_chart(fig, use_container_width=True)

    with right:
        # HTTP status donut
        status_counts = metrics.get("status_counts", {})
        if status_counts:
            df = pd.DataFrame(status_counts.items(), columns=["HTTP Status", "Hits"])
            fig = px.pie(df, values="Hits", names="HTTP Status", hole=0.4,
                         title="HTTP Response States",
                         color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig, use_container_width=True)

        # 404 targets
        not_found = metrics.get("not_found_urls", {})
        if not_found:
            df = pd.DataFrame(not_found.items(), columns=["Missing Endpoint", "Hits"]).sort_values("Hits")
            fig = px.bar(df, x="Hits", y="Missing Endpoint", orientation="h",
                         title="Directory Traversal Footprint (404 Targets)",
                         color_discrete_sequence=["#F5A623"])
            st.plotly_chart(fig, use_container_width=True)

        # User agents
        ua_counts = metrics.get("user_agent_counts", {})
        if ua_counts:
            df = pd.DataFrame(ua_counts.items(), columns=["User Agent", "Hits"]).sort_values("Hits")
            fig = px.bar(df, x="Hits", y="User Agent", orientation="h",
                         title="Identified Software Fingerprints")
            st.plotly_chart(fig, use_container_width=True)


# ======================================================================
# SECTION: NESTED DRILL-DOWN TABLES
# ======================================================================

def _render_investigation_tables(metrics: dict):
    st.header("🔍 Cross-Reference Investigation Tables")
    st.markdown("> Nested bucket data: `ip → key → count`")

    tab_status, tab_uri, tab_ua = st.tabs([
        "IP × Status Matrix",
        "IP × URI Matrix",
        "IP × User-Agent Profiles",
    ])

    with tab_status:
        rows = [
            {"IP Address": ip, "HTTP Status": status, "Hits": count}
            for ip, statuses in metrics.get("status_by_ip", {}).items()
            for status, count in statuses.items()
        ]
        st.dataframe(pd.DataFrame(rows) if rows else pd.DataFrame(), use_container_width=True)

    with tab_uri:
        rows = [
            {"IP Address": ip, "Endpoint": path, "Hits": count}
            for ip, uris in metrics.get("uri_by_ip", {}).items()
            for path, count in uris.items()
        ]
        st.dataframe(pd.DataFrame(rows) if rows else pd.DataFrame(), use_container_width=True)

    with tab_ua:
        rows = [
            {"IP Address": ip, "User Agent": ua, "Hits": count}
            for ip, uas in metrics.get("user_agent_by_ip", {}).items()
            for ua, count in uas.items()
        ]
        st.dataframe(pd.DataFrame(rows) if rows else pd.DataFrame(), use_container_width=True)