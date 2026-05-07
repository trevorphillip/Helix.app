from __future__ import annotations

import streamlit as st

from helix_core.crisprutils import PAM_SEQUENCES, PAM_SIDE, GUIDE_LENGTHS
from helix_desktop.ui import command_palette, handle_command


def render_sidebar(seq: str) -> dict:
    with st.sidebar:
        st.markdown("""
<style>
section[data-testid="stSidebar"] {
    background: #111318 !important;
}
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 {
    color: #5F5E5A !important;
    font-size: 10px !important;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] .stCheckbox span {
    font-size: 10px !important;
    color: #5F5E5A !important;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}
section[data-testid="stSidebar"] [data-baseweb="select"] > div {
    background: #1a1f2e !important;
    border-color: #1e2130 !important;
    color: #EF9F27 !important;
}
section[data-testid="stSidebar"] [data-baseweb="select"] span {
    color: #EF9F27 !important;
}
section[data-testid="stSidebar"] [data-testid="stSlider"] div[role="slider"] {
    background: #EF9F27 !important;
    border-color: #EF9F27 !important;
}
section[data-testid="stSidebar"] [data-testid="stSlider"] div[data-testid="stTickBarMin"],
section[data-testid="stSidebar"] [data-testid="stSlider"] div[data-testid="stTickBarMax"] {
    color: #5F5E5A !important;
}
</style>
""", unsafe_allow_html=True)
        st.header("Controls")
        enzyme = st.selectbox("Enzyme", list(PAM_SEQUENCES.keys()), index=0, key="enzyme")
        pam_pattern = PAM_SEQUENCES[enzyme]
        pam_side = PAM_SIDE[enzyme]
        guide_len = GUIDE_LENGTHS[enzyme]
        scan_reverse = st.checkbox("Scan reverse complement (− strand)", value=False, key="scan_rc")

        st.markdown("### Display / realism")
        hyper = st.checkbox(
            "Hyper-realistic mode", value=False,
            help="More physically-faithful visuals (B-DNA), glossy protein surfaces, and NN Tm for primers.",
            key="hyper_mode"
        )

        if st.session_state.get("win_pending") is not None:
            st.session_state.win = st.session_state.win_pending
            st.session_state.win_pending = None

        w_min, w_max = 0, len(seq)
        def_win = st.session_state.win
        win = st.slider("Window (bp)", min_value=w_min, max_value=w_max, value=(def_win[0], def_win[1]), key="win")
        start_pos, end_pos = win

        cmd = command_palette()
        if cmd:
            handle_command(cmd, seq, start_pos, end_pos)
            st.rerun()

        st.caption(f"PAM: **{pam_pattern}** • PAM side: **{pam_side}** • Guide: **{guide_len} nt**")

    return {
        "enzyme": enzyme,
        "pam_pattern": pam_pattern,
        "pam_side": pam_side,
        "guide_len": guide_len,
        "scan_reverse": scan_reverse,
        "hyper": hyper,
        "start_pos": start_pos,
        "end_pos": end_pos,
    }
