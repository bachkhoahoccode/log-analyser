import json
import os
import glob
import streamlit as st

CONFIG_DIR = "./config"

DEFAULT_CONFIG = {
    "polling_interval_seconds": 0.2,
    "rolling_window_size":      100,
    "alert_threshold":          10,
    "log_file_path":            "path/to/log.file",
}
# ======================================================================
# FILE HELPERS
# ======================================================================

def _ensure_config_dir():
    os.makedirs(CONFIG_DIR, exist_ok=True)
    if not glob.glob(os.path.join(CONFIG_DIR, "*.json")):
        with open(os.path.join(CONFIG_DIR, "default_config.json"), "w") as f:
            json.dump(DEFAULT_CONFIG, f, indent=4)

def _list_config_files() -> list[str]:
    _ensure_config_dir()
    return [os.path.basename(p) for p in glob.glob(os.path.join(CONFIG_DIR, "*.json"))]

def _load_config(filename: str) -> dict:
    filepath = os.path.join(CONFIG_DIR, filename)
    try:
        with open(filepath, "r") as f:
            data = json.load(f)
        st.session_state.app_config          = data
        st.session_state.current_config_file = filename
        return data
    except (json.JSONDecodeError, FileNotFoundError):
        st.session_state.app_config = DEFAULT_CONFIG.copy()
        return st.session_state.app_config

def _save_config(cfg: dict, filename: str):
    filepath = os.path.join(CONFIG_DIR, filename)
    with open(filepath, "w") as f:
        json.dump(cfg, f, indent=4)

@st.dialog("⚙️ Settings", width="large")
def _settings_dialog():
    config_files = _list_config_files()

    # Initialise session defaults
    if "current_config_file" not in st.session_state:
        st.session_state.current_config_file = config_files[0]
        _load_config(config_files[0])

    # ── Profile selector
    st.subheader("Configuration Profile")
    selected_file = st.selectbox(
        "Active profile",
        options=config_files,
        index=config_files.index(st.session_state.current_config_file),
        key="_settings_profile_select",
    )

    # Reload config when the user switches profiles (without saving first)
    if selected_file != st.session_state.current_config_file:
        _load_config(selected_file)
        st.rerun()

    cfg = st.session_state.app_config
    st.divider()
    st.subheader("Parameters")

    updated: dict = {}

    # Group parameters into two columns for a cleaner settings feel
    keys  = list(cfg.keys())
    left_keys  = keys[:len(keys)//2 + len(keys) % 2]
    right_keys = keys[len(keys)//2 + len(keys) % 2:]

    col_l, col_r = st.columns(2)

    for col, col_keys in ((col_l, left_keys), (col_r, right_keys)):
        with col:
            for key in col_keys:
                value = cfg[key]
                label = key.replace("_", " ").title()
                ui_key = f"_settings_{selected_file}_{key}"

                if isinstance(value, float):
                    updated[key] = st.number_input(
                        label, min_value=0.01, max_value=10.0,
                        step=0.05, value=value, key=ui_key,
                    )
                elif isinstance(value, int):
                    updated[key] = st.number_input(
                        label, min_value=1, max_value=5000,
                        value=value, key=ui_key,
                    )
                else:
                    updated[key] = st.text_input(label, value=value, key=ui_key)

    st.divider()

    # ── Action row ───────────────────────────────────────────────────
    btn_save, btn_cancel = st.columns([1, 1])

    with btn_save:
        if st.button("Save & Reload", type="primary", use_container_width=True):
            st.session_state.app_config = updated
            _save_config(updated, selected_file)
            st.success(f"Saved to {selected_file}")
            st.rerun()

    with btn_cancel:
        if st.button("✕ Cancel", use_container_width=True):
            st.rerun()   # just closes the dialog

def render_sidebar():
    with st.sidebar:
        if st.button("⚙️ Settings", use_container_width=True):
            _settings_dialog()