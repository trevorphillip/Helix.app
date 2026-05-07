from __future__ import annotations

import json
import time
from typing import Callable

import streamlit as st

from helix_core.db import list_sessions, load_session, save_session
from helix_apps.crispr_sandbox.services import apply_session_snapshot


def render_session_controls(username: str, snapshot_fn: Callable[[], dict]) -> None:
    st.download_button(
        "💾 Save session",
        data=json.dumps(snapshot_fn(), indent=2).encode("utf-8"),
        file_name=f"helix_session_{int(time.time())}.json",
        mime="application/json",
        use_container_width=True,
        key="save_session_btn"
    )

    session_name = st.text_input("Session name", value="Sandbox session", key="session_name")
    if st.button("Save session to PC", use_container_width=True, key="save_session_db_btn"):
        session_id = save_session(
            snapshot_fn(),
            username=username or "anonymous",
            session_name=session_name.strip() or "Sandbox session",
            mode="sandbox",
        )
        st.success(f"Saved session #{session_id} to helix.db")

    saved_sessions = list_sessions(username=username or None, mode="sandbox", limit=10)
    session_options = {
        f"#{row['id']} · {row['session_name']} · {row['created_at']}": row["id"]
        for row in saved_sessions
    }
    selected_saved_session = st.selectbox(
        "Restore saved PC session",
        ["None"] + list(session_options.keys()),
        key="saved_session_pick",
    )
    if selected_saved_session != "None" and st.button("Load saved session", use_container_width=True, key="load_saved_session_btn"):
        saved = load_session(session_options[selected_saved_session])
        restored = apply_session_snapshot(dict(st.session_state), saved["payload"])
        for key, value in restored.items():
            st.session_state[key] = value
        st.success(f"Loaded session #{saved['id']}")
        st.rerun()

    up_sess = st.file_uploader("Restore session (.json)", type=["json"], key="sessup")
    if up_sess:
        try:
            S = json.loads(up_sess.read().decode("utf-8"))
            restored = apply_session_snapshot(dict(st.session_state), S)
            for key, value in restored.items():
                st.session_state[key] = value
            st.rerun()
        except Exception as e:
            st.error(f"Could not load session: {e}")
