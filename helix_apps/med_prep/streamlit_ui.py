from __future__ import annotations

import streamlit as st


def render_medprep() -> None:
    st.title("Med-Prep")
    st.caption("Boards-style study tools, question banks, spaced repetition, and review planning.")
    st.info("This area is ready for question banks, spaced repetition, and track-based study flows.")

    c1, c2, c3 = st.columns(3)
    c1.metric("Tracks", 1)
    c2.metric("Due Cards", 0)
    c3.metric("Study Streak", 0)

    st.subheader("Next additions")
    st.write("- Track/module browser")
    st.write("- Due-card queue")
    st.write("- Progress persistence by user")
