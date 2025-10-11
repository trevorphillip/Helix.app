from __future__ import annotations

# --- standard libs ---
import json
import time
import re
from typing import List, Tuple

# --- third-party ---
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# ───────────────────────────────────────────────────────────────────────────────
# Streamlit page setup must be early
# ───────────────────────────────────────────────────────────────────────────────
st.set_page_config(layout="wide", page_title="Helix — Genetics Suite", page_icon="🧬")

# ───────────────────────────────────────────────────────────────────────────────
# Theming (no side-effects on widget keys)
# ───────────────────────────────────────────────────────────────────────────────
from helix_desktop.ui_plus import inject_visual_theme, set_plotly_template
inject_visual_theme(neon=True)
set_plotly_template("neon")

# ───────────────────────────────────────────────────────────────────────────────
# Auth + DB (safe if simple; no conflicting keys)
# ───────────────────────────────────────────────────────────────────────────────
from helix_core.auth import login
from helix_core.db import init_db

init_db()
authed, username = login()
if not authed:
    st.stop()

# ───────────────────────────────────────────────────────────────────────────────
# Core imports — always through helix_core.<module>
# ───────────────────────────────────────────────────────────────────────────────
from helix_core.crisprutils import (
    PAM_SEQUENCES, PAM_SIDE, GUIDE_LENGTHS,
    load_example_sequences, sanitize_sequence,
    find_sites_for_enzyme, gc_track, annotate_grnas,
    reverse_complement, map_rc_start_to_fwd,
    find_off_targets_window, dna_to_rna, translate_dna,
    find_orfs, find_purine_runs,
)
import helix_core.visuals as V
def render_crispr_sandbox(*, set_config: bool = True) -> None:
    # call this only when running app.py directly
    if set_config:
        # keep your existing page_config here if you had one
        # st.set_page_config(page_title="Helix – CRISPR Sandbox", layout="wide")
        pass
# Fallbacks for visuals if functions are missing
def _fallback_fig(title="Figure"):
    fig = go.Figure()
    fig.add_annotation(text=f"{title} (placeholder)", x=0.5, y=0.5, showarrow=False)
    fig.update_layout(height=300, margin=dict(l=10, r=10, t=30, b=10))
    return fig

def _basic_minimap(sequence, pam_positions, grnas, gc_x, gc_y):
    fig = go.Figure()
    if gc_x and gc_y:
        fig.add_trace(go.Scatter(x=gc_x, y=gc_y, mode="lines", name="GC%"))
    for p in pam_positions or []:
        fig.add_vline(x=p, line_width=1, opacity=0.2)
    for g, p in grnas or []:
        fig.add_vline(x=p, line_width=2, opacity=0.3)
    fig.update_layout(height=260, margin=dict(l=10, r=10, t=20, b=20),
                      xaxis_title="bp", yaxis_title="GC%")
    return fig

plot_overview_minimap      = getattr(V, "plot_overview_minimap",      _basic_minimap)
plot_detail_map            = getattr(V, "plot_detail_map",            lambda *a, **k: _fallback_fig("detail_map"))
plot_double_helix_windowed = getattr(V, "plot_double_helix_windowed", lambda *a, **k: _fallback_fig("double_helix"))
plot_triple_helix_windowed = getattr(V, "plot_triple_helix_windowed", lambda *a, **k: _fallback_fig("triple_helix"))
plot_orf_map               = getattr(V, "plot_orf_map",               lambda *a, **k: _fallback_fig("orf_map"))
plot_variant_positions     = getattr(V, "plot_variant_positions",     lambda *a, **k: _fallback_fig("variant_positions"))
plot_codon_usage           = getattr(V, "plot_codon_usage",           lambda *a, **k: _fallback_fig("codon_usage"))
plot_identity_heatmap      = getattr(V, "plot_identity_heatmap",      lambda *a, **k: _fallback_fig("identity_heatmap"))
plot_motif_track           = getattr(V, "plot_motif_track",           lambda *a, **k: _fallback_fig("motif_track"))

from helix_core.io_utils import load_sequence_file, to_fasta, save_text_download, load_multifasta_file
from helix_core.variants import global_align, call_variants, predict_snp_effect
from helix_core.codon import codon_usage as codon_usage_count, optimize_coding_sequence, translate_dna as translate_dna_codon
from helix_core.msa_utils import parse_fasta_multi, progressive_align, consensus_from_alignment
from helix_core.primer import design_primers, primers_to_fasta
from helix_core.structure_viewer import PDB_1CRN, show_pdb, show_pdbs, to_html, apply_residue_coloring
from helix_desktop.ui import inject_base_css, hero_header, sticky_toolbar, stat_row, inject_neon_theme, command_palette, handle_command
from helix_core.peptidebuilder import build_peptide_pdb, build_peptide_pdb_segmented
from helix_core.editor import apply_snp, apply_insertion, apply_deletion, apply_cut_and_ko
from helix_core.ai_stub import ask_ai, format_context
from helix_core.offtarget import KmerIndex, find_offtargets
from helix_core import sonify
from helix_core.motifs import scan_promoters, scan_restriction_sites, within_window
from Bio.SeqUtils.ProtParam import ProteinAnalysis

# ───────────────────────────────────────────────────────────────────────────────
# CSS / theme tweaks
# ───────────────────────────────────────────────────────────────────────────────
inject_base_css()
inject_neon_theme()

st.markdown("""
<style>
[data-baseweb="tab-list"] { display:flex; overflow-x:auto; overflow-y:hidden; white-space:nowrap; }
[data-baseweb="tab"] { flex:0 0 auto !important; }
.block-container { padding-top: 1.0rem; }
.stMetric { background:#121826; border-radius:14px; padding:10px 14px; }
[data-testid="stMetricDelta"] { font-weight:600; }
[data-testid="stTable"] table, .stDataFrame { border-radius:12px; overflow:hidden; }
label, .stRadio > label, .stSelectbox label { font-weight:600; letter-spacing:.2px; }
.stDownloadButton button, .stButton button { border-radius:12px; padding:.6rem 1rem; font-weight:600; }
h1, h2, h3 { letter-spacing:.3px; }
</style>
""", unsafe_allow_html=True)

# ───────────────────────────────────────────────────────────────────────────────
# Caches
# ───────────────────────────────────────────────────────────────────────────────
@st.cache_resource
def _build_index_cached(genome: str, k: int = 8) -> KmerIndex:
    return KmerIndex(genome, k=k)

# ───────────────────────────────────────────────────────────────────────────────
# Header
# ───────────────────────────────────────────────────────────────────────────────
hero_header(
    "Helix — Genetics Suite",
    "CRISPR • ORFs • Variants • Motifs • MSA • 3D Helix • Structures — now with a cleaner, faster UI"
)

# ───────────────────────────────────────────────────────────────────────────────
# Input sequence (library / paste)
# ───────────────────────────────────────────────────────────────────────────────
examples = load_example_sequences()
if "sequence" not in st.session_state:
    first_name = next(iter(examples.keys()))
    st.session_state.sequence = sanitize_sequence(examples[first_name])
if "win" not in st.session_state:
    L = len(st.session_state.sequence)
    st.session_state.win = (0, min(600, L))

with st.expander("Sequence input (quick)"):
    mode = st.radio("Load sequence from", ["Library", "Paste"], horizontal=True, key="src_mode")
    if mode == "Library":
        name = st.selectbox("Choose example", list(examples.keys()), key="example_pick")
        seq_in = examples[name]
    else:
        seq_in = st.text_area("Paste DNA (5'→3')", height=140, value=st.session_state.sequence[:800], key="paste_dna")

    if st.button("Use this sequence", type="primary", key="use_seq_btn"):
        seq_clean = sanitize_sequence(seq_in)
        if seq_clean:
            st.session_state.sequence = seq_clean
            st.session_state.win = (0, min(600, len(seq_clean)))
            st.success(f"Loaded {len(seq_clean)} bp.")
            st.rerun()
        else:
            st.warning("No valid A/C/G/T bases found.")

seq = st.session_state.sequence

# ───────────────────────────────────────────────────────────────────────────────
# Sidebar
# ───────────────────────────────────────────────────────────────────────────────
with st.sidebar:
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

    w_min, w_max = 0, len(seq)
    def_win = st.session_state.win
    win = st.slider("Window (bp)", min_value=w_min, max_value=w_max, value=(def_win[0], def_win[1]), key="win")
    start_pos, end_pos = win

    cmd = command_palette()
    if cmd:
        handle_command(cmd, seq, start_pos, end_pos)
        st.rerun()

    st.caption(f"PAM: **{pam_pattern}** • PAM side: **{pam_side}** • Guide: **{guide_len} nt**")

# ───────────────────────────────────────────────────────────────────────────────
# Scan PAMs/gRNAs
# ───────────────────────────────────────────────────────────────────────────────
with st.spinner("Scanning for PAMs and gRNAs..."):
    pam_sites_fwd, grnas_fwd = find_sites_for_enzyme(seq, enzyme=enzyme)

pam_sites_rev, grnas_rev = [], []
if scan_reverse:
    rc = reverse_complement(seq)
    pam_sites_rc, grnas_rc = find_sites_for_enzyme(rc, enzyme=enzyme)
    pam_sites_rev = [map_rc_start_to_fwd(p, len(seq), pam_side, guide_len, pam_len=len(pam_pattern)) for p in pam_sites_rc]
    grnas_rev = [(g, map_rc_start_to_fwd(pos, len(seq), pam_side, guide_len, pam_len=len(pam_pattern))) for (g, pos) in grnas_rc]

pam_sites_all = [(p, "+") for p in pam_sites_fwd] + [(p, "-") for p in pam_sites_rev]
grnas_all = [("+" , g, p) for (g, p) in grnas_fwd] + [("-", g, p) for (g, p) in grnas_rev]

stat_row([
    {"label": f"PAMs ({pam_pattern})", "value": str(len(pam_sites_all))},
    {"label": "gRNAs", "value": str(len(grnas_all))},
    {"label": "Length (bp)", "value": f"{len(seq):,}"},
])

m1, m2, m3 = st.columns(3)
m1.metric(f"PAMs ({pam_pattern})", len(pam_sites_all))
m2.metric("gRNAs", len(grnas_all))
m3.metric("Length (bp)", len(seq))

gc_x, gc_y = gc_track(seq, window=60, step=6)
pam_positions = [p for (p, _s) in pam_sites_all]
grnas_simple = [(g, p) for (_s, g, p) in grnas_all]

def _gc_pct(s: str) -> float:
    s = s.upper()
    return 100.0 * (s.count("G") + s.count("C")) / max(1, len(s))

def score_guide(pos: int, guide: str, win_start: int, win_end: int, w_gc: float = 0.6, w_center: float = 0.4) -> float:
    gc = _gc_pct(guide)
    gc_score = 1.0 - min(abs(gc - 50.0), 50.0)/50.0
    center = (win_start + win_end) / 2.0
    dist = abs((pos + len(guide)/2.0) - center)
    max_dist = max(1.0, (win_end - win_start) / 2.0)
    center_score = 1.0 - min(dist / max_dist, 1.0)
    return w_gc*gc_score + w_center*center_score

window_guides = [(g, p) for (g, p) in grnas_simple if start_pos <= p < end_pos]
scored = sorted(window_guides, key=lambda gp: score_guide(gp[1], gp[0], start_pos, end_pos), reverse=True)
top_positions = {p for (_g, p) in scored[:3]}

off_targets = []
for g, p in window_guides:
    off_targets.extend(find_off_targets_window(seq, start_pos, end_pos, guide_seq=g, max_mismatches=2))

# ───────────────────────────────────────────────────────────────────────────────
# Save / restore session
# ───────────────────────────────────────────────────────────────────────────────
def _snapshot_state():
    return {
        "sequence": st.session_state.sequence,
        "win": st.session_state.win,
        "enzyme": enzyme,
        "pam": pam_pattern,
        "pam_side": pam_side,
        "guide_len": guide_len,
        "hyper": st.session_state.get("hyper_mode", False),
    }

st.download_button(
    "💾 Save session",
    data=json.dumps(_snapshot_state(), indent=2).encode("utf-8"),
    file_name=f"helix_session_{int(time.time())}.json",
    mime="application/json",
    use_container_width=True,
    key="save_session_btn"
)

up_sess = st.file_uploader("Restore session (.json)", type=["json"], key="sessup")
if up_sess:
    try:
        S = json.loads(up_sess.read().decode("utf-8"))
        st.session_state.sequence = S.get("sequence", st.session_state.sequence)
        st.session_state.win = tuple(S.get("win", st.session_state.win))
        st.session_state["enzyme"] = S.get("enzyme", st.session_state.get("enzyme"))
        st.rerun()
    except Exception as e:
        st.error(f"Could not load session: {e}")

# ───────────────────────────────────────────────────────────────────────────────
# Top-level tabs
# ───────────────────────────────────────────────────────────────────────────────
tabtutorial, tabDNA, tabProtein, tabSonify, tabAI = st.tabs([
    "📘 Tutorial", "🧬 DNA", "🧪 Protein", "🎵 Sonify", "🤖 AI Assistant"
])

# ==============================================================================
# TUTORIAL
# ==============================================================================
with tabtutorial:
    st.title("Welcome to Helix — quick tutorial")
    st.caption("A fast tour of the key features. Nothing gets uploaded — all offline.")

    st.markdown("### 1) Load a DNA sequence")
    st.write("Go to **📤 Files** → upload FASTA/GenBank or paste DNA in **Sequence input (quick)** and click **Use this sequence**.")

    st.markdown("### 2) See PAM sites & gRNAs")
    st.write("Open **📊 2D Tracks**. Choose your **Enzyme** in the sidebar. You’ll see PAMs, gRNAs, GC% track, and a detailed window view.")
    st.info("Tip: move the **Window (bp)** slider in the sidebar to zoom to a region.")

    st.markdown("### 3) Find ORFs & translate")
    st.write("Open **🧬 Translation & ORFs**. Adjust **Minimum ORF length (aa)** and view table + map of ORFs within your window.")

    st.markdown("### 4) 3D DNA visuals")
    st.write("Try **🧪 3D Helix** and **🧪 Triple Helix (Concept)**.")

    st.markdown("### 5) Protein structures")
    st.write("Open **🧱 Protein** to view PDBs, build peptides, color by hydropathy/charge, and compare models.")

    st.markdown("### 6) In-silico edits")
    st.write("Open **✂️ Editing** to simulate SNPs, insertions, deletions, or KO cut windows.")

    st.markdown("### 7) Variants & MSA")
    st.write("Use **🧷 Variants** & **🧯 MSA** for alignments, calls, and identity heatmaps.")

    st.divider()
    st.markdown("## One-click presets")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("**Peptide (bulky aromatics)**")
        if st.button("Use `WWWWWWWWWW`", key="tut_w10"):
            st.session_state.setdefault("tut_seq_pep", "WWWWWWWWWW")
            st.success("Preset saved. Go to **🧱 Protein → Build from sequence**.")
    with c2:
        st.markdown("**Peptide (Pro kink)**")
        if st.button("Use `AAAAAPAAAAA`", key="tut_prok"):
            st.session_state.setdefault("tut_seq_pep", "AAAAAPAAAAA")
            st.success("Preset saved. Go to **🧱 Protein → Build from sequence**.")
    with c3:
        st.markdown("**Segmented example**")
        if st.button("Use segmented demo", key="tut_segs_btn"):
            # IMPORTANT: do NOT use any widget key here
            st.session_state["tut_seq_pep"] = "AAAAAAAAAAAAGGGPPPGGGVVVVVVVVVV"
            st.session_state["preset_segments"] = "1-12:helix,13-18:coil,19-30:beta"
            st.success("Presets saved. Go to **🧱 Protein → Build segmented**.")

    st.caption("Try `GGGPPPGGG`, `STNQSTNQSTNQ`, `VVVVVVVVVVVV`.")

# ==============================================================================
# DNA
# ==============================================================================
with tabDNA:
    dna_tabs = st.tabs([
        "📤 Files",
        "📊 2D Tracks",
        "🧪 3D Helix",
        "🧪 Triple Helix (Concept)",
        "🔎 Motifs & Restriction Sites",
        "🧬 Translation & ORFs",
        "🧪 Primer Designer",
        "🛰️ Off-Targets (fast)",
        "🧬 CRISPR Screen",
        "🧷 Variants",
        "🧫 Codon Usage",
        "🧯 MSA",
        "✂️ Editing (in-silico)",
        "🧭 Genome Annotation",
    ])
    (tabfiles, tab2d, tab3d, tab3x, tabmotif,
     tabtrans, tabprimer, tabofftarget, tabscreen,
     tabvars, tabcodon, tabmsa, tabedit, tabannot) = dna_tabs

    # ---------- Files ----------
    with tabfiles:
        st.subheader("Load & Export Sequences")
        up = st.file_uploader("Upload FASTA (.fa/.fasta) or GenBank (.gb/.gbk)", type=["fa","fasta","gb","gbk"])
        if up is not None:
            seq_loaded, meta = load_sequence_file(up, up.name)
            if seq_loaded:
                seq_new = sanitize_sequence(seq_loaded)
                st.session_state.sequence = seq_new
                st.session_state.win = (0, min(600, len(seq_new)))
                st.success(f"Loaded {len(seq_new)} bp from {meta.get('name', up.name)}")
                if "description" in meta:
                    st.caption(meta["description"])
                st.rerun()
            else:
                st.error("Could not parse the file. Make sure it is FASTA/GenBank.")

        st.markdown("**Export current sequence:**")
        save_text_download("⬇️ Download FASTA", to_fasta("Sequence", seq), "sequence.fasta", st)
        save_text_download(
            "⬇️ Download FASTA (window)",
            to_fasta(f"Sequence_{start_pos}_{end_pos}", seq[start_pos:end_pos]),
            f"sequence_{start_pos}-{end_pos}.fasta",
            st
        )

        # Bookmarks + Find
        st.session_state.setdefault("bookmarks", [])
        col1, col2, col3 = st.columns([0.44, 0.32, 0.24])
        with col1:
            q = st.text_input("Find (DNA, supports regex)", key="findq", placeholder="e.g. TATA|TTGACA")
        with col2:
            bk_name = st.text_input("Bookmark name", key="bname", placeholder="Exon 2")
        with col3:
            if st.button("➕ Add bookmark @ center", key="add_bm"):
                mid = (start_pos + end_pos)//2
                st.session_state.bookmarks.append({"name": bk_name or f"pos {mid}", "pos": mid, "color": "#ffcc00"})
        if st.session_state.bookmarks:
            st.dataframe(pd.DataFrame(st.session_state.bookmarks), use_container_width=True, hide_index=True)

        # search hits
        hits = []
        pat = (q or "").strip()
        if pat:
            try:
                for m in re.finditer(pat, seq, flags=re.IGNORECASE):
                    hits.append(m.start())
            except re.error:
                st.caption("Invalid regex; searching literally.")
                i = seq.find(pat)
                while i != -1:
                    hits.append(i); i = seq.find(pat, i+1)

    # ---------- 2D Tracks ----------
    with tab2d:
        st.plotly_chart(
            plot_overview_minimap(seq, pam_positions, grnas_simple, gc_x, gc_y),
            use_container_width=True,
            key="overview1"
        )

        st.plotly_chart(
            plot_detail_map(
                sequence=seq, pam_sites=pam_positions, grnas=grnas_simple,
                start_pos=start_pos, end_pos=end_pos,
                strand_by_pos={p: s for (p, s) in pam_sites_all},
                grna_strand_by_pos={p: s for (s, _g, p) in grnas_all},
                guide_len=guide_len, off_targets=off_targets,
                highlight_positions=top_positions,
            ),
            use_container_width=True, key="detail"
        )

        st.subheader("gRNA candidates")
        annotated = annotate_grnas(seq, [(g, p) for (_s, g, p) in grnas_all], guide_len=guide_len, enzyme=enzyme)
        for row in annotated:
            row["strand"] = next((s for (s, gg, pp) in grnas_all if gg == row["guide"] and pp == row["pos"]), "+")
            row["Score"] = round(score_guide(row["pos"], row["guide"], start_pos, end_pos), 3)
            row["Top3"] = "★" if row["pos"] in top_positions else ""
        windowed = [r for r in annotated if start_pos <= r["pos"] < end_pos]
        df = pd.DataFrame(windowed or annotated)
        cols = [c for c in ["Top3", "pos", "strand", "guide", "PAM", "GC%", "Score"] if c in df.columns]
        df = df[cols].rename(columns={"pos": "Position (bp)", "guide": "gRNA (nt)"})
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.download_button(
            "⬇️ Download gRNAs (CSV)",
            data=df.to_csv(index=False).encode("utf-8"),
            file_name=f"grnas_{enzyme}_{start_pos}-{end_pos}.csv",
            mime="text/csv",
            use_container_width=True,
            key="dl_grnas"
        )

        # IGV-style nav
        nav_click = sticky_toolbar([
            {"label":"⟲ Start","key":"start"},
            {"label":"Zoom ×2 in","key":"zin"},
            {"label":"Zoom ×2 out","key":"zout"},
            {"label":"Center","key":"center"},
            {"label":"↦ End","key":"end"},
            {"label":"1 kb","key":"1kb"},
        ])
        if nav_click:
            mid = (start_pos + end_pos) // 2
            curw = max(50, end_pos - start_pos)
            if nav_click == "start":
                st.session_state.win = (0, min(curw, len(seq)))
            elif nav_click == "zin":
                neww = max(50, curw // 2); a = max(0, mid - neww//2); b = min(len(seq), a + neww); st.session_state.win = (a, b)
            elif nav_click == "zout":
                neww = min(len(seq), curw * 2); a = max(0, mid - neww//2); b = min(len(seq), a + neww); st.session_state.win = (a, b)
            elif nav_click == "center":
                a = max(0, mid - curw//2); b = min(len(seq), a + curw); st.session_state.win = (a, b)
            elif nav_click == "end":
                a = max(0, len(seq) - curw); st.session_state.win = (a, len(seq))
            elif nav_click == "1kb":
                w = 1000; a = max(0, mid - w//2); b = min(len(seq), a + w); st.session_state.win = (a, b)
            st.rerun()

    # ---------- 3D Helix ----------
    def plot_bdna_windowed(start_pos: int, end_pos: int,
                           twist_deg: float = 36.0,
                           rise_A: float = 3.32,
                           radius_A: float = 10.0,
                           rung_thickness: float = 1.2,
                           strand_thickness: float = 2.2):
        n = max(2, int(end_pos - start_pos))
        ang = np.deg2rad(np.arange(n) * twist_deg)
        z = np.arange(n) * rise_A
        x1 = radius_A * np.cos(ang); y1 = radius_A * np.sin(ang)
        x2 = radius_A * np.cos(ang + np.pi); y2 = radius_A * np.sin(ang + np.pi)
        fig = go.Figure()
        fig.add_trace(go.Scatter3d(x=x1, y=y1, z=z, mode="lines", line=dict(width=strand_thickness), name="Backbone A"))
        fig.add_trace(go.Scatter3d(x=x2, y=y2, z=z, mode="lines", line=dict(width=strand_thickness), name="Backbone B"))
        for i in range(n):
            fig.add_trace(go.Scatter3d(x=[x1[i], x2[i]], y=[y1[i], y2[i]], z=[z[i], z[i]],
                                       mode="lines", line=dict(width=rung_thickness), showlegend=False))
        fig.update_scenes(aspectmode="data")
        fig.update_layout(height=640, margin=dict(l=0, r=0, t=20, b=0),
                          scene=dict(xaxis=dict(visible=False), yaxis=dict(visible=False), zaxis=dict(visible=False)),
                          showlegend=False)
        return fig

    with tab3d:
        if hyper:
            st.caption("B-DNA (realistic geometry: twist≈36°, rise≈3.3 Å).")
            fig3d = plot_bdna_windowed(start_pos, end_pos)
        else:
            fig3d = plot_double_helix_windowed(
                sequence=seq, pam_sites=pam_positions, grnas=grnas_simple,
                start_pos=start_pos, end_pos=end_pos, pam_len=len(pam_pattern),
                guide_len=guide_len, connector_step=1
            )
        st.plotly_chart(fig3d, use_container_width=True, key="helix3d")

        # optional animation if available
        try:
            from helix_core.animations import animate_bdna_build
            n_bp = max(2, end_pos - start_pos)
            st.markdown("**Animation**")
            st.plotly_chart(animate_bdna_build(n_bp), use_container_width=True, key="anim_bdna_build")
        except Exception:
            pass

    # ---------- Triple Helix ----------
    with tab3x:
        st.subheader("Triple-Helix DNA (concept visual)")
        colL, colR = st.columns([0.65, 0.35])
        with colR:
            st.caption("Display parameters")
            bp_turn = st.slider("bp per turn", 8.0, 14.0, 10.5, 0.1, key="tri_turn")
            r_main = st.slider("radius (main strands)", 0.6, 1.6, 1.0, 0.05, key="tri_rmain")
            r_third = st.slider("radius (third strand)", 0.8, 2.0, 1.15, 0.05, key="tri_rthird")
            conn_every = st.slider("connector step (every N bp)", 1, 8, 2, 1, key="tri_conn")
            min_run = st.slider("min purine-run length for triplex highlight", 4, 20, 8, 1, key="tri_minrun")
            st.caption("Conceptual visualization of triplex DNA.")
        with colL:
            purine_intervals = find_purine_runs(seq, start_pos, end_pos, min_len=min_run)
            fig3x = plot_triple_helix_windowed(
                sequence=seq, start_pos=start_pos, end_pos=end_pos,
                radius_main=r_main, radius_third=r_third,
                bp_per_turn=bp_turn, highlight_intervals=purine_intervals,
                connector_every=conn_every
            )
            st.plotly_chart(fig3x, use_container_width=True, key="triple3d")
        if purine_intervals:
            df_runs = pd.DataFrame([{"Start (bp)": s, "End (bp)": e, "Length": e - s} for (s, e) in purine_intervals])
            st.dataframe(df_runs, use_container_width=True, hide_index=True)
        else:
            st.caption("No purine-rich runs ≥ threshold in this window.")

    # ---------- Motifs & Restriction Sites ----------
    def simulate_digest(seq_str, sites):
        cuts = sorted([0] + [c for c in sites if 0 < c < len(seq_str)] + [len(seq_str)])
        return [cuts[i+1]-cuts[i] for i in range(len(cuts)-1)]

    def fake_gel(frag_sizes, lane_width=150, height=500):
        if not frag_sizes:
            frag_sizes = [len(seq)]
        fs = np.array(sorted([max(1, int(x)) for x in frag_sizes], reverse=True), dtype=float)
        y_norm = (np.log(fs.max()) - np.log(fs)) / (np.log(fs.max()) - np.log(50) + 1e-9)
        y = 30 + (height - 60) * y_norm
        fig = go.Figure()
        fig.add_shape(type="rect", x0=0, x1=lane_width, y0=0, y1=height, line=dict(width=0), fillcolor="rgba(230,230,230,0.6)")
        for yy in y:
            fig.add_shape(type="rect", x0=5, x1=lane_width-5, y0=float(yy-2), y1=float(yy+2), line=dict(width=0), fillcolor="rgba(0,0,0,0.88)")
        fig.update_xaxes(visible=False, range=[0, lane_width])
        fig.update_yaxes(visible=False, range=[height, 0])
        fig.update_layout(height=height, width=lane_width+20, margin=dict(l=0, r=0, t=10, b=0),
                          paper_bgcolor="white", plot_bgcolor="white", showlegend=False)
        return fig

    with tabmotif:
        st.subheader("Motifs & Restriction Sites")
        p_hits = scan_promoters(seq)
        r_hits = scan_restriction_sites(seq)
        hits = p_hits + r_hits
        st.plotly_chart(plot_motif_track(seq, hits, start_pos=start_pos, end_pos=end_pos), use_container_width=True, key="motif_main")

        with st.expander("🧪 Restriction digest & gel", expanded=False):
            enzyme_seq = st.text_input("Cut site (literal)", value="GAATTC", key="re_lit")
            cuts, i = [], seq.find(enzyme_seq)
            while i != -1:
                cuts.append(i); i = seq.find(enzyme_seq, i+1)
            frags = simulate_digest(seq, cuts)
            st.write(f"Fragments: {len(frags)} | sizes (bp):", ", ".join(map(str, sorted(frags, reverse=True)[:20])) + ("..." if len(frags)>20 else ""))
            st.plotly_chart(fake_gel(frags), use_container_width=False, key="gel_sim")

        win_hits = within_window(hits, start_pos, end_pos)
        if win_hits:
            dfh = pd.DataFrame([{"Name": h["name"], "Type": h["type"], "Pattern": h["pattern"], "Start (bp)": h["start"], "End (bp)": h["end"]} for h in win_hits])
            st.dataframe(dfh.sort_values("Start (bp)"), use_container_width=True, hide_index=True)
        else:
            st.caption("No motif/RE hits in this window.")

    # ---------- Translation & ORFs ----------
    with tabtrans:
        st.subheader("DNA → RNA → Protein & ORF Finder")
        colA, colB = st.columns([0.6, 0.4])
        with colA:
            st.markdown("**Windowed translation (forward strand)**")
            rna_win = dna_to_rna(seq[start_pos:end_pos])
            st.code(f"RNA (5'→3'):\n{rna_win[:300]}{'...' if len(rna_win)>300 else ''}")
            f1 = translate_dna(seq[start_pos:end_pos], frame=0)
            f2 = translate_dna(seq[start_pos:end_pos], frame=1)
            f3 = translate_dna(seq[start_pos:end_pos], frame=2)
            st.code(f"+1 frame:\n{f1[:300]}{'...' if len(f1)>300 else ''}")
            st.code(f"+2 frame:\n{f2[:300]}{'...' if len(f2)>300 else ''}")
            st.code(f"+3 frame:\n{f3[:300]}{'...' if len(f3)>300 else ''}")
        with colB:
            st.markdown("**ORF Finder (both strands)**")
            min_aa = st.slider("Minimum ORF length (aa)", 10, 300, 60, 10, key="orf_minlen")
            all_orfs = find_orfs(seq, min_aa=min_aa, both_strands=True)
            st.plotly_chart(plot_orf_map(seq, all_orfs, start_pos=start_pos, end_pos=end_pos, min_aa=min_aa), use_container_width=True, key="orfmap_trans")
            win_orfs = [o for o in all_orfs if not (o["end"] <= start_pos or o["start"] >= end_pos)]
            if win_orfs:
                dfo = pd.DataFrame([{
                    "Strand": o["strand"], "Frame": o["frame"], "Start (bp)": o["start"],
                    "End (bp)": o["end"], "Length (aa)": o["aa_len"],
                    "Peptide (N-term →)": (o["pep"][:40] + "…") if len(o["pep"]) > 40 else o["pep"]
                } for o in win_orfs])
                st.dataframe(dfo.sort_values(["Strand", "Start (bp)"]), use_container_width=True, hide_index=True)
                st.download_button("⬇️ Download ORFs (CSV)", data=dfo.to_csv(index=False).encode("utf-8"),
                                   file_name=f"orfs_{start_pos}-{end_pos}_min{min_aa}.csv",
                                   mime="text/csv", use_container_width=True, key="dl_orfs")
            else:
                st.info("No ORFs ≥ selected length in this window.")

    # ---------- Primer Designer ----------
    with tabprimer:
        st.subheader("Primer Designer (PCR)")
        st.caption("Heuristic, offline primer picking around the current window. Educational use only.")
        colL, colR = st.columns([0.55, 0.45])
        with colL:
            primer_len = st.slider("Primer length (nt)", 18, 30, (20, 24), 1, key="pr_len")
            tm_min, tm_max = st.slider("Target Tm (°C)", 45, 75, (58, 64), 1, key="pr_tm")
            gc_min, gc_max = st.slider("GC% range", 30, 70, (40, 60), 1, key="pr_gc")
            delta_tm = st.slider("Max ΔTm (°C)", 0.5, 5.0, 2.5, 0.5, key="pr_dtm")
            left_span = st.slider("Left search span inside window (bp)", 40, 400, 140, 10, key="pr_lspan")
            right_span = st.slider("Right search span inside window (bp)", 40, 400, 140, 10, key="pr_rspan")
            prod_min, prod_max = st.slider("Product size (bp)", 50, 3000, (120, 1200), 10, key="pr_prod")
            top_k = st.number_input("How many pairs to report", min_value=1, max_value=50, value=10, step=1, key="pr_topk")

            if st.button("Design primers", type="primary", use_container_width=True, key="pr_go"):
                with st.spinner("Scanning primers..."):
                    pairs = design_primers(
                        genome=seq, start_bp=start_pos, end_bp=end_pos,
                        primer_len_range=(int(primer_len[0]), int(primer_len[1])),
                        tm_range=(float(tm_min), float(tm_max)),
                        gc_range=(float(gc_min), float(gc_max)),
                        left_span=int(left_span), right_span=int(right_span),
                        max_delta_tm=float(delta_tm),
                        prod_min=int(prod_min), prod_max=int(prod_max),
                        top_k=int(top_k),
                    )
                if not pairs:
                    st.warning("No primer pairs met the constraints. Loosen ranges or widen spans.")
                else:
                    dfp = pd.DataFrame(pairs)
                    st.dataframe(dfp, use_container_width=True, hide_index=True)
                    fasta = primers_to_fasta(pairs)
                    st.download_button("⬇️ Download primers (FASTA)", data=fasta.encode("utf-8"),
                                       file_name=f"primers_{start_pos}-{end_pos}.fasta",
                                       mime="text/plain", use_container_width=True, key="dl_primers")

        with colR:
            st.markdown("**Design region**")
            st.code(f"Window: {start_pos}–{end_pos} (len {end_pos-start_pos} bp)")
            st.caption("Left primers near window start; right primers near window end (reverse strand).")
            st.markdown("**Notes**")
            st.write("- Tm uses the Wallace rule (rough).")
            st.write("- Screens: GC%, GC clamp, homopolymer runs, basic hairpin/dimer proxy, 3' 12-mer uniqueness.")
            st.write("- Validate with dedicated primer tools and wet-lab controls before real experiments.")

    # ---------- Off-targets ----------
    with tabofftarget:
        st.subheader("Genome-wide Off-Target Search (≤2 mismatches)")
        k = st.slider("Seed length (k-mer)", 6, 10, 8, 1, help="Index k-mer used to seed candidates.", key="off_k")
        st.caption("Index current genome/sequence for fast lookups.")
        if st.button("Build/Refresh Index", type="primary", key="off_idx_btn"):
            _ = _build_index_cached(seq, k)  # warm cache
            st.success(f"Indexed {len(seq):,} bp with k={k}.")
        idx = _build_index_cached(seq, k)

        colA, colB, colC = st.columns([0.42, 0.28, 0.30])
        with colA:
            guide_q = st.text_input("Guide / protospacer (5'→3')", value=(grnas_simple[0][0] if grnas_simple else ""), key="off_g")
            mm = st.slider("Max mismatches", 0, 4, 2, 1, key="off_mm")
        with colB:
            enzyme_q = st.selectbox("Enzyme", list(PAM_SEQUENCES.keys()), index=0, key="off_enzyme")
            pam_q = PAM_SEQUENCES[enzyme_q]
            side_q = PAM_SIDE[enzyme_q]
            st.text(f"PAM: {pam_q}  |  PAM side: {side_q}")
        with colC:
            scan_rc2 = st.checkbox("Scan reverse complement", value=True, key="off_scanrc")
            go = st.button("Search", type="primary", use_container_width=True, key="off_go")

        if go:
            if not guide_q or len(guide_q) < 12:
                st.warning("Paste a guide (≥12 nt).")
            else:
                with st.spinner("Searching…"):
                    hits = find_offtargets(idx, guide_q, pam=pam_q, pam_side=side_q,
                                           max_mismatches=mm, scan_rc=scan_rc2, seed_len=k)
                if not hits:
                    st.info("No hits found under current settings.")
                else:
                    st.success(f"Found {len(hits)} candidate sites.")
                    dfh = pd.DataFrame([{
                        "Strand": h["strand"],
                        "Start (bp)": h["pos"],
                        "Target": h["target"],
                        "Mismatches": h["mismatches"],
                        "PAM": (seq[h["pos"]+len(guide_q): h["pos"]+len(guide_q)+len(pam_q)] if side_q.startswith("3")
                                else seq[max(0, h["pos"]-len(pam_q)): h["pos"]]),
                    } for h in hits])
                    st.dataframe(dfh, use_container_width=True, hide_index=True)
                    st.download_button("⬇️ Download hits (CSV)", data=dfh.to_csv(index=False).encode("utf-8"),
                                       file_name="offtargets.csv", mime="text/csv",
                                       use_container_width=True, key="dl_offtargets")

    # ---------- CRISPR Screen (beta) ----------
    with tabscreen:
        st.subheader("CRISPR Pooled Screen Designer (beta)")
        left, right = st.columns([0.58, 0.42])

        with left:
            target_src = st.radio(
                "Targets input",
                ["Use current sequence (1 gene)", "Paste Multi-FASTA"],
                horizontal=True,
                key="scr_src",
            )
            if target_src.startswith("Use"):
                targets = [("Gene1", seq)]
                st.caption(f"Using the active sequence as 'Gene1' ({len(seq)} bp).")
            else:
                block = st.text_area(
                    "Targets (Multi-FASTA)",
                    height=180,
                    key="scr_fasta",
                    placeholder=">TP53\nATGG...\n>EGFR\nATGAA..."
                )
                targets = parse_fasta_multi(block) if block else []
                if not targets:
                    st.info("Paste at least one sequence in FASTA format.")

            enz_scr = st.selectbox(
                "Enzyme",
                list(PAM_SEQUENCES.keys()),
                index=list(PAM_SEQUENCES.keys()).index(enzyme) if enzyme in PAM_SEQUENCES else 0,
                key="scr_enzyme",
            )
            per_gene = st.slider("Guides per gene", 2, 10, 4, key="scr_per_gene")
            min_space = st.slider("Min spacing between guides (bp)", 0, 50, 10, key="scr_spacing")
            include_rc = st.checkbox("Also scan reverse complement", True, key="scr_scan_rc")

        with right:
            bg_mode = st.radio(
                "Off-target background",
                ["Concatenate targets", "Paste background seq"],
                horizontal=False,
                key="scr_bgmode",
            )
            if bg_mode == "Paste background seq":
                bg_seq = sanitize_sequence(
                    st.text_area("Background DNA (used to check seeds/12-mers)", height=120, key="scr_bg_txt")
                )
            else:
                bg_seq = "".join([sanitize_sequence(s) for (_n, s) in targets]) if targets else seq

            seed_k = st.slider("Seed length k", 6, 10, 8, key="scr_k")
            mm_max = st.slider("Count off-targets up to mismatches", 0, 2, 1, key="scr_mm")
            run = st.button("Design guides", type="primary", use_container_width=True, key="scr_run")

        def _gc_pct_str(s: str) -> float:
            s = s.upper()
            return 100.0 * (s.count("G") + s.count("C")) / max(1, len(s))

        def _tail12_uniq_count(background: str, guide: str) -> int:
            b = (background or "").upper()
            tail = guide[-12:].upper()
            if not b or len(b) < 12:
                return 0
            n = 0
            i = b.find(tail)
            while i != -1:
                n += 1
                i = b.find(tail, i + 1)
            return n

        def _pick_non_overlapping(rows, min_bp: int):
            rows_sorted = sorted(rows, key=lambda r: (-r["Score"], r["Gene"], r["Start (bp)"]))
            picked, last_pos = [], {}
            for r in rows_sorted:
                g = r["Gene"]; p = r["Start (bp)"]
                ok = all(abs(p - q) >= min_bp for q in last_pos.get(g, []))
                if ok:
                    picked.append(r)
                    last_pos.setdefault(g, []).append(p)
            return picked

        def _pam_at(tseq: str, pos: int, strand: str, pam: str, side: str, glen: int) -> str:
            from helix_core.crisprutils import reverse_complement
            if side == "3prime":
                if strand == "+":
                    return tseq[pos + glen: pos + glen + len(pam)]
                else:
                    return reverse_complement(tseq[max(0, pos - len(pam)): pos])
            else:  # "5prime"
                if strand == "+":
                    return tseq[max(0, pos - len(pam)): pos]
                else:
                    return reverse_complement(tseq[pos + glen: pos + glen + len(pam)])

        if run and targets:
            idx = _build_index_cached(bg_seq, k=seed_k)
            out_rows = []
            for gene, tseq in targets:
                tseq = sanitize_sequence(tseq)
                if not tseq:
                    continue

                pam = PAM_SEQUENCES[enz_scr]
                side = PAM_SIDE[enz_scr]
                glen = GUIDE_LENGTHS[enz_scr]

                _pams_fwd, guides_fwd = find_sites_for_enzyme(tseq, enzyme=enz_scr)
                candidates = [("+", g, p) for (g, p) in guides_fwd]

                if include_rc:
                    rc = reverse_complement(tseq)
                    _pams_rc, guides_rc = find_sites_for_enzyme(rc, enzyme=enz_scr)
                    candidates += [
                        ("-", g, map_rc_start_to_fwd(p, len(tseq), side, glen, pam_len=len(pam)))
                        for (g, p) in guides_rc
                    ]

                for strand, gseq, pos in candidates:
                    if pos < 0 or pos >= len(tseq):
                        continue
                    gc = _gc_pct_str(gseq)
                    center_score = 1.0 - abs((pos + len(gseq)/2.0) - (len(tseq)/2.0)) / max(1, len(tseq)/2.0)
                    gc_score = 1.0 - min(abs(gc - 50.0), 50.0) / 50.0
                    try:
                        hits = find_offtargets(idx, gseq, pam=pam, pam_side=side,
                                               max_mismatches=mm_max, scan_rc=True, seed_len=seed_k)
                        ot_hits = max(0, len(hits) - 1)
                    except Exception:
                        ot_hits = max(0, _tail12_uniq_count(bg_seq, gseq) - 1)

                    ot_pen = min(1.0, ot_hits / 5.0)
                    score = 0.55 * gc_score + 0.35 * center_score + 0.10 * (1.0 - ot_pen)
                    pam_here = _pam_at(tseq, pos, strand, pam, side, glen)

                    out_rows.append({
                        "Gene": gene,
                        "Strand": strand,
                        "Start (bp)": pos,
                        "gRNA": gseq,
                        "PAM": pam_here,
                        "GC%": round(gc, 1),
                        f"OT_hits(≤{mm_max}mm)": ot_hits,
                        "Score": round(score, 3),
                    })

            if not out_rows:
                st.warning("No candidate guides found. Try a different enzyme or sequences.")
            else:
                final_rows = []
                for gene_name in sorted({r["Gene"] for r in out_rows}):
                    rs = [r for r in out_rows if r["Gene"] == gene_name]
                    rs_diverse = _pick_non_overlapping(rs, min_space)
                    final_rows += rs_diverse[:per_gene]

                df_scr = pd.DataFrame(final_rows).sort_values(["Gene", "Score"], ascending=[True, False])
                st.success(f"Designed {len(df_scr)} guides across {len(set(df_scr['Gene']))} genes.")
                st.dataframe(df_scr, use_container_width=True, hide_index=True)

                fasta = "\n".join(
                    f">{r['Gene']}|{r['Strand']}|{r['Start (bp)']}|{r['PAM']}\n{r['gRNA']}"
                    for _, r in df_scr.iterrows()
                )
                st.download_button("⬇️ Download guides (FASTA)", data=fasta.encode("utf-8"),
                                   file_name="screen_guides.fasta", mime="text/plain", use_container_width=True)
                st.download_button("⬇️ Download guides (CSV)", data=df_scr.to_csv(index=False).encode("utf-8"),
                                   file_name="screen_guides.csv", mime="text/csv", use_container_width=True)
        elif run and not targets:
            st.warning("No targets: use current sequence or paste a Multi-FASTA.")

    # ---------- Variants ----------
    with tabvars:
        st.subheader("Variant / SNP Analysis")
        st.caption("Compare a reference and an alternate sequence (paste or upload).")
        col1, col2 = st.columns(2)
        with col1:
            ref_src = st.radio("Reference source", ["Use current sequence", "Paste"], horizontal=True, key="refsrc")
            if ref_src == "Paste":
                ref_seq = st.text_area("Reference DNA (5'→3')", height=140, key="refpaste")
            else:
                ref_seq = seq
            ref_seq = sanitize_sequence(ref_seq)
        with col2:
            alt_src = st.radio("Alternate source", ["Paste", "Upload"], horizontal=True, key="altsrc")
            if alt_src == "Paste":
                alt_seq = st.text_area("Alternate DNA (5'→3')", height=140, key="altpaste")
            else:
                up2 = st.file_uploader("Upload ALT FASTA/GenBank", type=["fa","fasta","gb","gbk"], key="altfile")
                alt_seq = ""
                if up2:
                    alt_seq, _meta2 = load_sequence_file(up2, up2.name)
            alt_seq = sanitize_sequence(alt_seq)

        if st.button("Align & Call Variants", type="primary", key="var_go"):
            if not ref_seq or not alt_seq:
                st.warning("Provide both sequences.")
            else:
                aln_a, aln_b = global_align(ref_seq, alt_seq)
                diffs = call_variants(aln_a, aln_b)
                st.plotly_chart(plot_variant_positions(diffs, length=len(ref_seq)), use_container_width=True)
                if diffs:
                    dfv = pd.DataFrame(diffs)
                    st.dataframe(dfv, use_container_width=True, hide_index=True)
                    st.download_button("⬇️ Download variants (CSV)", data=dfv.to_csv(index=False).encode("utf-8"),
                                       file_name="variants.csv", mime="text/csv", use_container_width=True, key="dl_vars")
                else:
                    st.info("No differences found.")
                effects = predict_snp_effect(ref_seq, alt_seq, start_pos=0)
                if effects:
                    dfe = pd.DataFrame(effects)
                    st.subheader("Coding impact (AA changes, simple model)")
                    st.dataframe(dfe, use_container_width=True, hide_index=True)
                else:
                    st.caption("No codon-level AA changes detected (simple model).")

    # ---------- Codon Usage ----------
    with tabcodon:
        st.subheader("Codon Usage & Optimization")
        st.caption("Analyze codon usage and generate an organism-optimized coding sequence.")
        coding_region = st.text_area("Paste a coding DNA sequence (CDS)", height=140,
                                     placeholder="Must be a coding region with length multiple of 3.", key="cds_in")
        coding_region = sanitize_sequence(coding_region)
        if coding_region:
            usage = codon_usage_count(coding_region)
            st.plotly_chart(plot_codon_usage(usage), use_container_width=True, key="codon_plot")
            org = st.selectbox("Target organism for optimization", ["Human", "E_coli", "Yeast"], key="opt_org")
            if st.button("Optimize CDS", type="primary", key="opt_cds_go"):
                opt = optimize_coding_sequence(coding_region, organism=org)
                st.code(opt[:600] + ("..." if len(opt) > 600 else ""), language="text")
                aa_ref = translate_dna_codon(coding_region)
                aa_opt = translate_dna_codon(opt)
                ok = "✅" if aa_ref == aa_opt else "⚠️"
                st.caption(f"{ok} Amino acid sequence preserved: {aa_ref == aa_opt}")
                save_text_download("⬇️ Download optimized FASTA", to_fasta(f"CDS_optimized_{org}", opt),
                                   f"cds_optimized_{org}.fasta", st)
        else:
            st.caption("Tip: copy an ORF from the Translation & ORFs tab.")

    # ---------- MSA ----------
    with tabmsa:
        st.subheader("Multiple Sequence Alignment (DNA)")
        mode_msa = st.radio("Input", ["Paste Multi-FASTA", "Upload Multi-FASTA"], horizontal=True, key="msa_mode")
        if mode_msa == "Paste Multi-FASTA":
            block = st.text_area("Paste Multi-FASTA sequences", height=220, placeholder=">seq1\nATGC...\n>seq2\nATGCC...\n", key="msa_block")
        else:
            upmsa = st.file_uploader("Upload Multi-FASTA", type=["fa","fasta"], key="msa_up")
            block = load_multifasta_file(upmsa) if upmsa else ""
        seqs_msa = parse_fasta_multi(block) if block else []
        if seqs_msa and st.button("Align", type="primary", key="msa_go"):
            aligned = progressive_align(seqs_msa)
            names = [n for (n, _) in aligned]
            strings = [s for (_, s) in aligned]
            cons = consensus_from_alignment(aligned)
            st.text_area("Consensus", value=cons, height=80, key="msa_cons")
            for nm, s_aln in aligned:
                st.text(f"{nm:>15}  {s_aln}")
            st.plotly_chart(plot_identity_heatmap(names, strings), use_container_width=True, key="msa_heat")
        elif not seqs_msa:
            st.caption("Provide 2+ sequences to align.")

    # ---------- Editing ----------
    with tabedit:
        st.subheader("In-silico Editing (no wet-lab)")
        if not seq:
            st.info("Load a DNA sequence first in 📤 Files or the quick input.")
        else:
            op = st.selectbox("Edit type", ["SNP", "Insertion", "Deletion", "Cut + KO deletion"], key="edit_op")
            new_seq = seq

            if op == "SNP":
                c1, c2 = st.columns(2)
                with c1:
                    pos = st.number_input("Position (0-based index)", min_value=0, max_value=max(0, len(seq)-1),
                                          value=min(start_pos, len(seq)-1), key="edit_snp_pos")
                with c2:
                    base = st.text_input("New base (A/C/G/T)", value="A", max_chars=1, key="edit_snp_base").upper()
                if st.button("Apply SNP", key="apply_snp_btn"):
                    new_seq = apply_snp(seq, int(pos), base)

            elif op == "Insertion":
                c1, c2 = st.columns(2)
                with c1:
                    pos = st.number_input("Insert at position", min_value=0, max_value=len(seq),
                                          value=min(end_pos, len(seq)), key="edit_ins_pos")
                with c2:
                    ins = st.text_input("Insert sequence (ACGT)", value="TTT", key="edit_ins_seq").upper()
                if st.button("Apply Insertion", key="apply_ins_btn"):
                    new_seq = apply_insertion(seq, int(pos), ins)

            elif op == "Deletion":
                c1, c2 = st.columns(2)
                with c1:
                    sdel = st.number_input("Delete start", min_value=0, max_value=max(0, len(seq)-1),
                                           value=start_pos, key="edit_del_start")
                with c2:
                    edel = st.number_input("Delete end (exclusive)", min_value=0, max_value=len(seq),
                                           value=end_pos, key="edit_del_end")
                if st.button("Apply Deletion", key="apply_del_btn"):
                    new_seq = apply_deletion(seq, int(sdel), int(edel))

            else:  # Cut + KO deletion
                c1, c2 = st.columns(2)
                with c1:
                    cut = st.number_input("Cut position", min_value=0, max_value=max(0, len(seq)-1),
                                          value=(start_pos + end_pos) // 2, key="edit_cut_pos")
                with c2:
                    dl = st.slider("KO deletion length", 1, 200, 30, key="edit_cut_len")
                if st.button("Apply Cut+KO", key="apply_cut_btn"):
                    new_seq, ds, de = apply_cut_and_ko(seq, int(cut), int(dl))
                    st.caption(f"Deleted bp {ds}–{de}")

            if new_seq != seq:
                st.success(f"Edited length: {len(new_seq)} bp (was {len(seq)}).")
                left = max(0, start_pos - 60)
                right = min(len(new_seq), end_pos + 60)
                st.code(new_seq[left:right])
                save_text_download("⬇️ Download edited FASTA", to_fasta("Edited", new_seq), "edited_sequence.fasta", st)
                if st.toggle("Replace the current sequence with this edit?", value=False, key="promote_edit"):
                    st.session_state.sequence = new_seq
                    st.session_state.win = (0, min(600, len(new_seq)))
                    st.rerun()
            else:
                st.caption("Choose parameters and click Apply to preview the edited sequence.")

    # ---------- Genome Annotation ----------
    with tabannot:
        st.subheader("Genome Annotation Mode")
        show_pams = st.checkbox("Show PAMs/gRNAs", True, key="ann_pams")
        show_mot  = st.checkbox("Show motifs/RE", True, key="ann_mot")
        show_orf  = st.checkbox("Show ORFs", True, key="ann_orf")

        st.plotly_chart(
            plot_overview_minimap(seq, pam_positions, grnas_simple, gc_x, gc_y),
            use_container_width=True,
            key="overview_annot2"
        )

        if show_pams:
            st.plotly_chart(
                plot_detail_map(
                    sequence=seq, pam_sites=pam_positions, grnas=grnas_simple,
                    start_pos=start_pos, end_pos=end_pos,
                    strand_by_pos={p: s for (p, s) in pam_sites_all},
                    grna_strand_by_pos={p: s for (s, _g, p) in grnas_all},
                    guide_len=guide_len, off_targets=off_targets,
                    highlight_positions=top_positions
                ),
                use_container_width=True,
                key="detail_annot"
            )

        if show_mot:
            hits2 = scan_promoters(seq) + scan_restriction_sites(seq)
            st.plotly_chart(
                plot_motif_track(seq, hits2, start_pos=start_pos, end_pos=end_pos),
                use_container_width=True,
                key="motif_annot"
            )

        if show_orf:
            min2 = st.slider("Min ORF length (aa)", 10, 300, 60, 10, key="annot_orf_min")
            all_orfs2 = find_orfs(seq, min_aa=min2, both_strands=True)
            if all_orfs2:
                st.plotly_chart(
                    plot_orf_map(seq, all_orfs2, start_pos=start_pos, end_pos=end_pos, min_aa=min2),
                    use_container_width=True,
                    key="orfmap_annot"
                )
            else:
                st.info("No ORFs found with current threshold.")

# ==============================================================================
# PROTEIN
# ==============================================================================
def _aa_only(seq: str) -> str:
    return "".join(ch for ch in (seq or "").upper() if ch in "ACDEFGHIKLMNPQRSTVWY")

def hydropathy_profile(seq: str, window: int = 9):
    kd = {'I':4.5,'V':4.2,'L':3.8,'F':2.8,'C':2.5,'M':1.9,'A':1.8,'G':-0.4,'T':-0.7,'S':-0.8,'W':-0.9,'Y':-1.3,
          'P':-1.6,'H':-3.2,'E':-3.5,'Q':-3.5,'D':-3.5,'N':-3.5,'K':-3.9,'R':-4.5}
    x = np.array([kd.get(a, 0.0) for a in seq], dtype=float)
    if len(x) < 1: return np.array([]), np.array([])
    w = max(1, int(window))
    kernel = np.ones(w)/w
    y = np.convolve(x, kernel, mode="same")
    return np.arange(1, len(seq)+1), y

def plot_hydropathy(seq: str, window: int = 9):
    pos, y = hydropathy_profile(seq, window)
    fig = go.Figure()
    if y.size:
        fig.add_trace(go.Scatter(x=pos, y=y, mode="lines", name="Hydropathy (KD)"))
        fig.add_hline(y=0, line_dash="dot")
    fig.update_layout(height=260, margin=dict(l=20,r=20,t=30,b=10),
                      xaxis_title="Residue", yaxis_title=f"Hydropathy (window={window})")
    return fig

PROSITE_LITE = [
    ("N-glycosylation",      r"N(?!P)[ST](?!P)"),
    ("PKC phosphorylation",  r"[ST].[RK]"),
    ("CK2 phosphorylation",  r"[ST]..[DE]"),
    ("Proline-directed",     r"[ST]P"),
    ("N-myristoylation",     r"G..[STAGCN][STAGCN]"),
]

def scan_protein_motifs(seq: str) -> List[dict]:
    seq = _aa_only(seq)
    hits = []
    for name, pat in PROSITE_LITE:
        for m in re.finditer(pat, seq):
            s, e = m.start() + 1, m.end()
            hits.append({"Motif": name, "Start": s, "End": e, "Length": e - s + 1, "Seq": seq[s-1:e]})
    return hits

def motif_highlight_string(hits: List[dict], chain: str = "A") -> str:
    parts = []
    for h in hits:
        s, e = h["Start"], h["End"]
        parts.append(f"{chain}:{s}-{e}" if e > s else f"{chain}:{s}")
    return ", ".join(parts)

with tabProtein:
    protein_tabs = st.tabs(["🧱 Protein Structure", "Properties"])
    tabstruct, tabpprop = protein_tabs

    with tabstruct:
        st.subheader("Protein Structure (PDB / Built Models)")
        colS, colV = st.columns([0.42, 0.58], gap="large")

        with colS:
            st.markdown("### Display")
            style = st.selectbox("Style", ["cartoon+sticks", "stick", "cartoon", "line", "surface"], index=0, key="struct_style")
            color = st.selectbox("Color", ["chain", "spectrum", "ssPyMol", "resi", "element", "#ffffff"], index=0, key="struct_color")
            stick_radius = st.slider("Stick radius", 0.1, 0.6, 0.25, 0.05, key="struct_stick_radius")
            dark_bg = st.checkbox("Dark background", value=True, key="struct_darkbg")
            show_lig = st.checkbox("Highlight ligands (HET, no water)", value=True, key="struct_showlig")

            color_by = st.selectbox("Residue coloring", ["None", "Hydropathy", "Charge"], index=0, key="struct_color_by")
            pH_val = st.slider("Electrostatics pH", 2.0, 12.0, 7.4, 0.1, key="struct_color_ph") if color_by == "Charge" else None

            st.divider()
            st.markdown("### Source")
            source = st.radio("Choose source", ["Example (1CRN)", "Upload PDB", "Build from sequence", "Build segmented", "Compare multiple"], horizontal=False, key="struct_source")

            pdb_text = ""
            viewer_mode = "single"
            chains = None
            align = "none"

            if source == "Example (1CRN)":
                pdb_text = PDB_1CRN
            elif source == "Upload PDB":
                up_pdb = st.file_uploader("Upload .pdb", type=["pdb"], key="struct_up")
                if up_pdb:
                    pdb_text = up_pdb.read().decode("utf-8", errors="ignore")
            elif source == "Build from sequence":
                default_seq_in = st.session_state.get("tut_seq_pep", "ACDEFGHIKLMNPQRSTVWY")
                seq_in = st.text_input("AA sequence (one-letter, standard 20)", value=default_seq_in, key="struct_seq_in")
                conf = st.selectbox("Backbone conformation", ["helix", "beta", "coil"], index=0, key="struct_conf")
                jitter = st.slider("Backbone jitter (°)", 0.0, 10.0, 4.0, 0.5, key="struct_jitter",
                                   help="Small per-residue φ/ψ randomness so models differ visually")
                seed = st.number_input("Random seed (optional)", min_value=0, value=42, step=1, key="struct_seed")
                if st.button("Build model", type="primary", use_container_width=True, key="struct_build"):
                    try:
                        pdb_text = build_peptide_pdb(seq_in, conformation=conf, jitter_deg=jitter, seed=int(seed))
                        st.session_state["pdb_current"] = pdb_text
                        st.success(f"Built model: {len(seq_in)} aa, {conf}.")
                    except Exception as e:
                        st.error(str(e))
            elif source == "Build segmented":
                default_seg_seq = st.session_state.get("tut_seq_pep", "AAAAAAAAAAAAGGGPPPGGGVVVVVVVVVV")
                seq_in = st.text_input("AA sequence", value=default_seg_seq, key="seg_seq")
                spec_default = st.session_state.get("preset_segments", "1-12:helix,13-18:coil,19-30:beta")
                spec = st.text_input("Segments (1-based, comma sep)", value=spec_default, key="seg_spec",
                                     help="Format: start-end:type, e.g., 1-12:helix,13-18:coil,19-30:beta")
                jitter = st.slider("Backbone jitter (°)", 0.0, 10.0, 4.0, 0.5, key="seg_jitter")
                seed = st.number_input("Random seed", min_value=0, value=42, step=1, key="seg_seed")
                if st.button("Build segmented model", type="primary", use_container_width=True, key="seg_build"):
                    try:
                        segs = []
                        for part in spec.split(","):
                            rng, kind = part.strip().split(":")
                            s, e = rng.split("-")
                            segs.append((int(s), int(e), kind.strip()))
                        pdb_text = build_peptide_pdb_segmented(seq_in, segments=segs, jitter_deg=jitter, seed=int(seed))
                        st.session_state["pdb_current"] = pdb_text
                        st.success(f"Built segmented model: {len(seq_in)} aa.")
                    except Exception as e:
                        st.error(f"Segment spec error: {e}")
            else:
                st.caption("Build several **helix** peptides and compare. Use overlay + Cα superposition or grid.")
                seqs_raw = st.text_area("Sequences (one per line)", height=140, value="AAAAAPAAAAA\nWWWWWWWWWW\nGGGPPPGGG", key="cmp_lines")
                view_mode = st.radio("View mode", ["Overlay (aligned)", "Grid"], horizontal=True, index=0, key="cmp_view")
                chains_in = st.text_input("Limit to chains (optional, e.g., A,B)", value="", key="cmp_chains")
                chains = [c.strip() for c in chains_in.split(",") if c.strip()] or None
                align = "ca_to_first" if view_mode.startswith("Overlay") else "none"
                viewer_mode = "overlay" if view_mode.startswith("Overlay") else "grid"

            st.divider()
            st.markdown("### Highlights")
            hl_default = st.session_state.get("tut_hl", "")
            hl = st.text_input("Residues (chain:resi or chain:start-end, comma-separated)", value=hl_default,
                               placeholder="e.g., A:15, A:40-50, B:12", key="struct_hl")

            if st.session_state.get("pdb_current"):
                st.download_button("⬇️ Download current PDB", data=st.session_state["pdb_current"],
                                   file_name="model.pdb", mime="chemical/x-pdb", use_container_width=True, key="dl_pdb")

        with colV:
            highlight: List[Tuple[str, int | Tuple[int, int]]] = []
            if hl:
                for token in hl.split(","):
                    t = token.strip()
                    if not t or ":" not in t: continue
                    chain, rest = t.split(":", 1)
                    rest = rest.strip()
                    if "-" in rest:
                        a, b = rest.split("-", 1)
                        highlight.append((chain.strip(), (int(a), int(b))))
                    else:
                        highlight.append((chain.strip(), int(rest)))

            if source != "Compare multiple":
                if pdb_text:
                    v = show_pdb(
                        pdb_text,
                        style=style,
                        color=color,
                        stick_radius=stick_radius,
                        dark_bg=dark_bg,
                        show_ligands=show_lig,
                        chains=chains,
                        highlight=highlight,
                        surface_ms_opacity=(0.28 if st.session_state.get("hyper_mode") else None),
                    )
                    if color_by != "None":
                        v = apply_residue_coloring(
                            v, pdb_text,
                            scheme=("charge" if color_by == "Charge" else "hydropathy"),
                            ph=pH_val,
                            stick_radius=stick_radius
                        )
                    try:
                        from helix_core.structure_viewer import enable_spin, apply_glow_surface
                        if st.checkbox("Cinematic spin", value=False, key="spin_on"):
                            v = enable_spin(v, on=True, speed=1.2)
                        if st.checkbox("Glow surface", value=st.session_state.get("hyper_mode"), key="glow_on"):
                            v = apply_glow_surface(v, opacity=0.28)
                    except Exception:
                        pass

                    st.components.v1.html(to_html(v), height=620, scrolling=False)
                    st.session_state["pdb_current"] = pdb_text
                else:
                    st.info("Choose a source or build a peptide to visualize.")
            else:
                seqs = [s.strip() for s in seqs_raw.splitlines() if s.strip()]
                if not seqs:
                    st.info("Add at least one sequence (one per line).")
                else:
                    try:
                        pdbs = [build_peptide_pdb(s, conformation="helix", jitter_deg=4.0, seed=42) for s in seqs]
                        v_or_grid, is_grid = show_pdbs(
                            pdbs,
                            mode=viewer_mode,
                            style=style,
                            color=color,
                            stick_radius=stick_radius,
                            dark_bg=dark_bg,
                            show_ligands=show_lig,
                            chains=chains,
                            align=align,
                            highlight_sets=None,
                            surface_ms_opacity=(0.20 if st.session_state.get("hyper_mode") else None),
                        )
                        if not is_grid:
                            if color_by != "None":
                                v_or_grid = apply_residue_coloring(
                                    v_or_grid, pdbs[0],
                                    scheme=("charge" if color_by == "Charge" else "hydropathy"),
                                    ph=pH_val,
                                    stick_radius=stick_radius
                                )
                            st.components.v1.html(to_html(v_or_grid), height=670, scrolling=False)
                        else:
                            cols_per_row = 3
                            cols = st.columns(cols_per_row)
                            for i, (vv, pdb_txt_i) in enumerate(zip(v_or_grid, pdbs)):
                                if color_by != "None":
                                    vv = apply_residue_coloring(
                                        vv, pdb_txt_i,
                                        scheme=("charge" if color_by == "Charge" else "hydropathy"),
                                        ph=pH_val,
                                        stick_radius=stick_radius
                                    )
                                with cols[i % cols_per_row]:
                                    st.components.v1.html(to_html(vv), height=340, scrolling=False)
                    except Exception as e:
                        st.error(str(e))

    with tabpprop:
        st.subheader("Protein Properties")
        pep = st.text_area("Amino-acid sequence (one-letter; standard 20)", height=120,
                           placeholder="e.g. AKLAEELAKLAEELAKL", key="prop_pep")
        pep = _aa_only(pep)
        colA, colB = st.columns([0.55, 0.45])
        with colA:
            if pep:
                ana = ProteinAnalysis(pep)
                mw = ana.molecular_weight()
                pi = ana.isoelectric_point()
                gravy = ana.gravy()
                aro = ana.aromaticity()
                ph = st.slider("pH", 0.0, 14.0, 7.0, 0.5, key="prop_ph")
                try:
                    charge = ana.charge_at_pH(ph)
                except Exception:
                    charge = float("nan")
                m1, m2, m3, m4, m5 = st.columns(5)
                m1.metric("Length (aa)", len(pep))
                m2.metric("MW (Da)", f"{mw:.1f}")
                m3.metric("pI", f"{pi:.2f}")
                m4.metric("GRAVY", f"{gravy:+.2f}")
                m5.metric("Aromaticity", f"{aro:.3f}")
                st.caption(f"Estimated net charge @ pH {ph:.1f}: {charge:.2f}" if charge == charge else
                           "Charge @ pH not available in this BioPython version.")
                win = st.slider("Hydropathy window", 3, 21, 9, 2, key="prop_win")
                st.plotly_chart(plot_hydropathy(pep, window=win), use_container_width=True, key="prop_hydro")
            else:
                st.info("Paste a protein sequence to compute properties.")
        with colB:
            st.markdown("**Amino-acid composition**")
            if pep:
                comp = ProteinAnalysis(pep).get_amino_acids_percent()
                fig = go.Figure(go.Bar(x=list(comp.keys()), y=[100 * v for v in comp.values()]))
                fig.update_layout(height=260, margin=dict(l=20, r=20, t=30, b=10),
                                  xaxis_title="AA", yaxis_title="Percent")
                st.plotly_chart(fig, use_container_width=True, key="prop_comp")
                st.download_button("⬇️ Download sequence (FASTA)",
                                   data=f">protein\n{pep}\n".encode("utf-8"),
                                   file_name="protein.fasta", mime="text/plain", use_container_width=True, key="dl_pep")
            else:
                st.caption("AA composition and FASTA export appear after you paste a sequence.")

        st.divider()
        st.markdown("### Motifs (PROSITE-lite)")
        if pep:
            hits = scan_protein_motifs(pep)
            if hits:
                dft = pd.DataFrame(hits).sort_values(["Start", "End"])
                st.dataframe(dft, use_container_width=True, hide_index=True)
                hl_str = motif_highlight_string(hits, chain="A")
                st.text_input("Copy into Protein Structure → Highlights", value=hl_str, key="motif_hl_str")
                st.session_state["tut_hl"] = hl_str
            else:
                st.caption("No motif hits with the current patterns.")
        else:
            st.caption("Paste a protein sequence above to scan motifs.")

# ==============================================================================
# SONIFY
# ==============================================================================
with tabSonify:
    st.subheader("Sequence → Music (MIDI)")
    st.caption("Turn DNA or protein into a melody. All offline.")
    mode = st.radio("Input type", ["DNA", "Protein"], horizontal=True, key="son_mode")
    colL, colR = st.columns([0.6, 0.4])
    with colL:
        if mode == "DNA":
            seq_in = st.text_area("DNA (A/C/G/T)", height=140, placeholder="ATGCGT...", key="son_dna")
            map_style = st.radio("Mapping", ["Nucleotide→notes", "Translate→AA→notes"], horizontal=True, key="son_map")
        else:
            seq_in = st.text_area("Protein (one-letter amino acids)", height=140, placeholder="ACDEFGHIKLMNPQRSTVWY", key="son_aa")
            map_style = "AA only"
        seq_in = (seq_in or "").strip()
        bpm = st.slider("Tempo (BPM)", 60, 200, 120, key="son_bpm")
        note_len = st.slider("Note length (beats)", 0.25, 1.0, 0.5, 0.25, key="son_note_len")
        base_oct = st.slider("Base octave", 2, 6, 5, key="son_oct")
        base_note = 12 * base_oct
        program_name = st.selectbox("Instrument", ["Acoustic Grand (0)", "Electric Piano (4)", "Marimba (12)", "Church Organ (19)", "Guitar (24)", "Strings (48)", "Synth Pad (88)"], index=0, key="son_prog")
        program = int(program_name.split("(")[-1].split(")")[0])
        if st.button("🎼 Create MIDI", type="primary", use_container_width=True, key="son_go"):
            try:
                if mode == "DNA":
                    dna = sonify.dna_only(seq_in)
                    if not dna:
                        st.warning("Please paste a DNA sequence (A/C/G/T).")
                    else:
                        if str(map_style).startswith("Translate"):
                            aa = sonify.aa_only(translate_dna(dna, frame=0))
                            pitches = sonify.aa_to_pitches(aa, base_note=base_note)
                            label = f"dna_translated_{len(aa)}aa.mid"
                        else:
                            pitches = sonify.dna_to_pitches(dna, base_note=base_note)
                            label = f"dna_{len(dna)}nt.mid"
                else:
                    aa = sonify.aa_only(seq_in)
                    if not aa:
                        st.warning("Please paste a protein sequence.")
                        pitches, label = [], "protein.mid"
                    else:
                        pitches = sonify.aa_to_pitches(aa, base_note=base_note)
                        label = f"protein_{len(aa)}aa.mid"

                if pitches:
                    midi_bytes = sonify.make_midi(pitches, bpm=bpm, program=program, note_len_beats=note_len)
                    st.success(f"Generated {len(pitches)} notes.")
                    st.download_button("⬇️ Download MIDI", data=midi_bytes, file_name=label, mime="audio/midi", use_container_width=True, key="dl_midi")
            except Exception as e:
                st.error(str(e))
    with colR:
        st.markdown("**How mapping works**")
        if mode == "DNA":
            st.write("- **Nucleotide→notes**: A, C, G, T map to nearby scale tones around middle C.")
            st.write("- **Translate→AA→notes**: translate DNA (frame +1) to protein, then map AA to notes.")
        else:
            st.write("- **AA→notes**: 20 amino acids spread across an octave for a compact melody.")
        st.caption("Tip: Try slower tempo (80 BPM) and longer notes (1 beat) for calmer tracks.")

# ==============================================================================
# AI Assistant
# ==============================================================================
with tabAI:
    st.subheader("Ask questions about your current sequence/window")
    st.caption("Try: *Which gRNA looks best here and why?* • *Explain TTTV vs NGG* • *What does GC% imply?*")
    q = st.text_area("Your question", height=120, placeholder="Ask anything about this sequence, PAMs, or gRNAs…", key="ai_q")
    context_block = format_context(sequence=seq, enzyme=enzyme, pam=pam_pattern, pam_side=pam_side, guide_len=guide_len,
                                   start=start_pos, end=end_pos, grnas=grnas_simple)
    pick_options = [f"pos {p} | {g}" for (g, p) in [(g, p) for (g, p) in grnas_simple if start_pos <= p < end_pos]]
    pick = st.selectbox("Critique a specific gRNA (optional)", options=pick_options, key="ai_pick") if pick_options else None
    if st.button("🧠 Analyze (offline)", type="primary", use_container_width=True, key="ai_go"):
        ask = (q or "").strip()
        if pick:
            try:
                pos = int(pick.split("|")[0].replace("pos", "").strip())
                g = next(g for (g, p) in grnas_simple if p == pos)
                pam_here = seq[pos + guide_len: pos + guide_len + len(pam_pattern)]
                gc_here = round((g.count("G") + g.count("C")) / len(g) * 100, 1)
                ask += f"\n\nFocus on gRNA at pos {pos} (seq={g}, GC={gc_here}%, PAM={pam_here})."
            except Exception:
                pass
        with st.spinner("Reasoning..."):
            answer = ask_ai(ask or "Explain this window at a high level.", context_block)
        st.markdown("### Answer")
        st.write(answer)
if __name__ == "__main__":
    render_crispr_sandbox(set_config=True)