import json
import os
import streamlit as st


# ======================================================================
# HELPERS
# ======================================================================

def _load_available_formats(config_path: str = "data/regex_log_formats.json") -> dict:
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_formats(formats: dict, config_path: str = "data/regex_log_formats.json"):
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(formats, f, indent=4)


def _dispatch_to_parser(uploaded_file, format_name: str) -> dict:
    from utils.process_batch_file import process_batch_file   
    with st.spinner("Processing batch log files..."): 
        result = process_batch_file(uploaded_file, format_name)       

    if "metrics" not in result:
        result = {"metrics": result, "alerts": []}
    return result


# ======================================================================
# PUBLIC ENTRY POINT
# ======================================================================

def render_file_loader():
    st.title("📂 Historical Batch File Loader")
    st.write("Upload an offline log file to run it through the aggregation engine.")

    formats_dict   = _load_available_formats()
    format_options = ["Auto-Detect & Verify"] + list(formats_dict.keys())

    uploaded_file  = st.file_uploader(
        "Drop your log file here (.txt, .csv, .log, .jsonl)",
        type=["txt", "csv", "log", "jsonl"],
    )
    selected_format = st.selectbox("Expected log format:", options=format_options)

    if uploaded_file is None:
        return

    if not st.button("Validate & Process", type="primary"):
        return

    # ── Read preview lines for format detection ──────────────────────
    uploaded_file.seek(0)
    preview_lines = []
    for _ in range(10):
        line_bytes = uploaded_file.readline()
        if not line_bytes:
            break
        preview_lines.append(line_bytes.decode("utf-8", errors="ignore").strip())
    uploaded_file.seek(0)   # reset for the real parse

    if not preview_lines:
        st.error("The uploaded file appears to be empty.")
        return

    # ── Format detection ─────────────────────────────────────────────
    from utils.regex_helper import detect_log_format
    from utils.time_helper  import find_timestamp_format, KNOWN_FORMATS
    sample_line    = preview_lines[:10]
    result  = detect_log_format(sample_line, formats_dict)
    if result is None:
        st.error("Unknown log structure.")
        return
    detected_format = result["name"]
    ts = result["timestamp"]
    try:
        detected_time  = find_timestamp_format(ts, KNOWN_FORMATS)
    except ValueError:
        st.error(
                    "File refused: could not isolate recognisable log syntax "
                    "or timestamp markers."
                )
    resolved_format = None   # will be set if validation passes

    if selected_format != "Auto-Detect & Verify":
        # User picked a specific format — verify it matches
        expected = formats_dict.get(selected_format, {})
        if (detected_format == selected_format and
                detected_time == expected.get("time_format")):
            st.success(f"✅ Verified — file matches '{selected_format}'.")
            resolved_format = selected_format
        else:
            st.error(
                f"Validation failed: file structure doesn't match "
                f"'{selected_format}'. Try Auto-Detect."
            )
            return

    else:
        # Auto-detect: try to match against known formats
        cfg = formats_dict[detected_format]
        if cfg.get("time_format") == detected_time:
            st.success(f"✅ Auto-detected format: '{detected_format}'")
            resolved_format = detected_format

        if resolved_format is None:
            if detected_format and detected_time:
                # New combination — ask the user to name it
                st.warning(
                    "Structure recognised, but this Regex + Timestamp "
                    "combination is not yet registered."
                )
                st.session_state._pending_format = {
                    "regex":       formats_dict[detected_format]["regex"],
                    "time_format": detected_time,
                    "file":        uploaded_file,    # keep reference
                }
            else:
                st.error(
                    "File refused: could not isolate recognisable log syntax "
                    "or timestamp markers."
                )
            return

    # ── Dispatch to real parser ───────────────────────────────────────
    if resolved_format:
        with st.spinner("Parsing and aggregating…"):
            result = _dispatch_to_parser(uploaded_file, resolved_format)
        st.session_state.batch_data = result
        st.rerun()


    # ── Handle pending new-format registration ────────────────────────
    if "_pending_format" in st.session_state:
        with st.form("new_format_form"):
            st.info("Give this format layout a name to register it:")
            new_name = st.text_input("Format name", placeholder="e.g. custom_nginx_v2")
            submitted = st.form_submit_button("Save & Process")

            if submitted:
                if not new_name.strip():
                    st.error("Please enter a valid format name.")
                else:
                    pending = st.session_state._pending_format
                    formats_dict[new_name] = {
                        "regex":       pending["regex"],
                        "time_format": pending["time_format"],
                    }
                    _save_formats(formats_dict)

                    with st.spinner("Parsing and aggregating…"):
                        result = _dispatch_to_parser(pending["file"], new_name)

                    del st.session_state._pending_format
                    st.session_state.batch_data = result
                    st.rerun()