# storage.py
import streamlit as st
from db import Project, save_project, list_projects, get_project, delete_project

def project_sidebar(username: str, seq: str, start_pos: int, end_pos: int,
                    enzyme: str, pam: str, pam_side: str, guide_len: int):
    st.sidebar.markdown("### Project")
    pname = st.sidebar.text_input("Name", value=f"Run @ {start_pos}-{end_pos}")
    colA, colB = st.sidebar.columns(2)
    if colA.button("💾 Save", use_container_width=True):
        pid = save_project(Project(
            owner=username, name=pname, sequence=seq,
            win_start=start_pos, win_end=end_pos,
            enzyme=enzyme, pam=pam, pam_side=pam_side, guide_len=guide_len
        ))
        st.sidebar.success(f"Saved as #{pid}")
    projs = list_projects(username)
    if projs:
        label_to_id = {f"#{p.id} • {p.name}": p.id for p in projs}
        pick = st.sidebar.selectbox("Load", list(label_to_id.keys()))
        pid = label_to_id[pick]
        if colB.button("📂 Load", use_container_width=True):
            p = get_project(username, pid)
            if p:
                st.session_state.sequence = p.sequence
                st.session_state.win = (p.win_start, p.win_end)
                st.session_state["enzyme"] = p.enzyme
                st.sidebar.success(f"Loaded #{pid} → {p.name}")
                st.rerun()
        if st.sidebar.button("🗑️ Delete selected"):
            if delete_project(username, pid):
                st.sidebar.success(f"Deleted #{pid}")
                st.rerun()
