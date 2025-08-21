import streamlit as st
from crisprutils import (
    load_example_sequences, find_pam_sites, find_grnas,
    gc_track, annotate_grnas
)
from visuals import (
    plot_overview_minimap, plot_detail_map,
    plot_double_helix_windowed
)
import pandas as pd

st.set_page_config(layout="wide")
st.title("🧬 CRISPR gRNA Finder — Pro Map")
st.caption("Clean tracks • GC% overview • Windowed 3D helix")

# ---- Input ----
examples = load_example_sequences()
mode = st.radio("Input mode", ["From the lab (examples)", "Enter your own DNA"], horizontal=True)
if mode == "From the lab (examples)":
    name = st.selectbox("Choose example", list(examples.keys()))
    seq = examples[name]
    with st.expander("Show sequence"):
        st.code(seq)
else:
    seq = st.text_area("Paste your DNA (5' → 3')", height=180)

if not seq:
    st.stop()

seq = seq.strip().upper()
st.success(f"✅ Loaded {len(seq)} bp")

# ---- Analysis ----
pam_sites = find_pam_sites(seq)     # default SpCas9 (NGG)
grnas_raw = find_grnas(seq)         # list[(guide20, pos)]
grnas_annot = annotate_grnas(seq, grnas_raw)

c1, c2, c3 = st.columns(3)
c1.metric("PAM sites (NGG)", len(pam_sites))
c2.metric("gRNA candidates", len(grnas_raw))
c3.metric("Length (bp)", len(seq))

# ---- View Toggle + Window ----
view = st.radio("Visualization", ["2D Tracks", "3D Helix"], horizontal=True)
default_end = min(600, len(seq))
start_pos, end_pos = st.slider(
    "Window (bp)",
    min_value=0, max_value=len(seq),
    value=(0, default_end)
)

if view == "2D Tracks":
    # Overview (minimap) with GC% + PAM/gRNA rugs
    gc_x, gc_y = gc_track(seq, window=60, step=6)
    st.plotly_chart(
        plot_overview_minimap(seq, pam_sites, grnas_raw, gc_x, gc_y),
        use_container_width=True,
        key="overview"
    )

    # Detailed multi-track map in selected window
    st.plotly_chart(
        plot_detail_map(seq, pam_sites, grnas_raw, start_pos=start_pos, end_pos=end_pos),
        use_container_width=True,
        key="detail"
    )

    # Table (filtered to window) + CSV export
    st.subheader("gRNA candidates")
    win = [g for g in grnas_annot if start_pos <= g["pos"] < end_pos]
    df = pd.DataFrame(win or grnas_annot)
    st.dataframe(df, use_container_width=True, hide_index=True)

    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Download CSV",
        data=csv,
        file_name="grnas.csv",
        mime="text/csv",
        use_container_width=True
    )

else:
    # 3D helix (windowed, max detail)
    fig3d = plot_double_helix_windowed(
        seq, pam_sites, grnas_raw,
        start_pos=start_pos, end_pos=end_pos,
        connector_step=1  # max detail; set to 2+ if you want lighter
    )
    st.plotly_chart(fig3d, use_container_width=True, key="helix3d")
