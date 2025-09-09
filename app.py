all_orfs2 = []  # always defined, even if ORF checkbox is off
min2 = 60


# app.py
# ---- our local modules (make sure these files exist) ----

import streamlit as st
import pandas as pd

from crisprutils import (
    PAM_SEQUENCES, PAM_SIDE, GUIDE_LENGTHS,
    load_example_sequences, sanitize_sequence,
    find_sites_for_enzyme, gc_track, annotate_grnas,
    reverse_complement, map_rc_start_to_fwd,
    find_off_targets_window, dna_to_rna, translate_dna,
    find_orfs, find_purine_runs,
)
from visuals import (
    plot_overview_minimap, plot_detail_map, plot_double_helix_windowed,
    plot_triple_helix_windowed, plot_orf_map,
    plot_variant_positions, plot_codon_usage, plot_identity_heatmap,
    plot_motif_track
)
from io_utils import load_sequence_file, to_fasta, save_text_download, load_multifasta_file
from variants import global_align, call_variants, predict_snp_effect
from codon import codon_usage as codon_usage_count, optimize_coding_sequence, translate_dna as translate_dna_codon
from msa_utils import parse_fasta_multi, progressive_align, consensus_from_alignment

# ⬇️ upgraded viewer (supports cartoon+sticks, overlay/grid, alignment, highlights)
from structure_viewer import PDB_1CRN, show_pdb, show_pdbs, to_html


# ⬇️ peptide builder (uniform + segmented; educational geometry)
from peptidebuilder import build_peptide_pdb, build_peptide_pdb_segmented

from editor import apply_snp, apply_insertion, apply_deletion, apply_cut_and_ko
from ai_stub import ask_ai, format_context  # offline helper

from Bio.SeqUtils.ProtParam import ProteinAnalysis
import numpy as np
import plotly.graph_objects as go


st.markdown("""
<style>
/* force tabs to scroll horizontally if too many */
[data-baseweb="tab-list"] {
    display: flex;
    overflow-x: auto;
    overflow-y: hidden;
    white-space: nowrap;
}

/* make each tab not shrink */
[data-baseweb="tab"] {
    flex: 0 0 auto !important;
}
</style>
""", unsafe_allow_html=True)


# ---------- Page setup ----------
st.set_page_config(layout="wide", page_title="Helix — Genetics Suite", page_icon="🧬")
st.markdown("""
<style>
.block-container { padding-top: 1.0rem; }
.stMetric { background: #121826; border-radius: 14px; padding: 10px 14px; }
[data-testid="stMetricDelta"] { font-weight: 600; }
[data-testid="stTable"] table, .stDataFrame { border-radius: 12px; overflow: hidden; }
label, .stRadio > label, .stSelectbox label { font-weight: 600; letter-spacing: .2px; }
.stDownloadButton button, .stButton button { border-radius: 12px; padding: .6rem 1rem; font-weight: 600; }
h1, h2, h3 { letter-spacing: .3px; }
</style>
""", unsafe_allow_html=True)

# ---------- Header ----------
c1, c2 = st.columns([0.70, 0.30])
with c1:
    st.title("🧬 Helix — Genetics Suite")
    st.caption("CRISPR design • ORFs • Variants • Codon usage • Motifs • MSA • 3D Helix • Triple Helix • Structures • Editing • Genome annotation (offline)")
with c2:
    st.write("")

# ---------- Sequence source (library / paste) ----------
examples = load_example_sequences()

# Session state: active sequence + window
if "sequence" not in st.session_state:
    # default: first example
    first_name = next(iter(examples.keys()))
    st.session_state.sequence = sanitize_sequence(examples[first_name])
if "win" not in st.session_state:
    L = len(st.session_state.sequence)
    st.session_state.win = (0, min(600, L))

with st.expander("Sequence input (quick)"):
    mode = st.radio("Load sequence from", ["Library", "Paste"], horizontal=True)
    if mode == "Library":
        name = st.selectbox("Choose example", list(examples.keys()))
        seq_in = examples[name]
    else:
        seq_in = st.text_area("Paste DNA (5'→3')", height=140, value=st.session_state.sequence[:800])

    if st.button("Use this sequence", type="primary"):
        seq_clean = sanitize_sequence(seq_in)
        if seq_clean:
            st.session_state.sequence = seq_clean
            st.session_state.win = (0, min(600, len(seq_clean)))
            st.success(f"Loaded {len(seq_clean)} bp.")
            st.rerun()

        else:
            st.warning("No valid A/C/G/T bases found.")

# Work on the active sequence
seq = st.session_state.sequence

# ---------- Sidebar controls ----------
with st.sidebar:
    st.header("Controls")
    enzyme = st.selectbox("Enzyme", list(PAM_SEQUENCES.keys()), index=0)
    pam_pattern = PAM_SEQUENCES[enzyme]
    pam_side = PAM_SIDE[enzyme]
    guide_len = GUIDE_LENGTHS[enzyme]
    scan_reverse = st.checkbox("Scan reverse complement (− strand)", value=False)

    w_min, w_max = 0, len(seq)
    def_win = st.session_state.win
    win = st.slider("Window (bp)", min_value=w_min, max_value=w_max,
                    value=(def_win[0], def_win[1]), key="win")
    start_pos, end_pos = win

    st.caption(f"PAM: **{pam_pattern}** • PAM side: **{pam_side}** • Guide: **{guide_len} nt**")

# ---------- Analysis: PAMs & gRNAs ----------
with st.spinner("Scanning for PAMs and gRNAs..."):
    pam_sites_fwd, grnas_fwd = find_sites_for_enzyme(seq, enzyme=enzyme)

pam_sites_rev, grnas_rev = [], []
if scan_reverse:
    rc = reverse_complement(seq)
    pam_sites_rc, grnas_rc = find_sites_for_enzyme(rc, enzyme=enzyme)
    pam_sites_rev = [map_rc_start_to_fwd(p, len(seq), pam_side, guide_len, pam_len=len(pam_pattern))
                     for p in pam_sites_rc]
    grnas_rev = [(g, map_rc_start_to_fwd(pos, len(seq), pam_side, guide_len, pam_len=len(pam_pattern)))
                 for (g, pos) in grnas_rc]

pam_sites_all = [(p, "+") for p in pam_sites_fwd] + [(p, "-") for p in pam_sites_rev]
grnas_all = [("+" , g, p) for (g, p) in grnas_fwd] + [("-", g, p) for (g, p) in grnas_rev]

# Metrics
m1, m2, m3 = st.columns(3)
m1.metric(f"PAMs ({pam_pattern})", len(pam_sites_all))
m2.metric("gRNAs", len(grnas_all))
m3.metric("Length (bp)", len(seq))

# Shared precomputes
gc_x, gc_y = gc_track(seq, window=60, step=6)
pam_positions = [p for (p, _s) in pam_sites_all]
grnas_simple = [(g, p) for (_s, g, p) in grnas_all]

# ---- helper scoring for highlight ----
def _gc_pct(s: str) -> float:
    s = s.upper()
    return 100.0 * (s.count("G") + s.count("C")) / max(1, len(s))

def score_guide(pos: int, guide: str, win_start: int, win_end: int,
                w_gc: float = 0.6, w_center: float = 0.4) -> float:
    gc = _gc_pct(guide)
    gc_score = 1.0 - min(abs(gc - 50.0), 50.0)/50.0
    center = (win_start + win_end) / 2.0
    dist = abs((pos + len(guide)/2.0) - center)
    max_dist = max(1.0, (win_end - win_start) / 2.0)
    center_score = 1.0 - min(dist / max_dist, 1.0)
    return w_gc*gc_score + w_center*center_score

# Top-3 within window
window_guides = [(g, p) for (g, p) in grnas_simple if start_pos <= p < end_pos]
scored = sorted(window_guides, key=lambda gp: score_guide(gp[1], gp[0], start_pos, end_pos), reverse=True)
top_positions = {p for (_g, p) in scored[:3]}

# Off-targets (Hamming ≤ 2) in window
off_targets = []
for g, p in window_guides:
    off_targets.extend(find_off_targets_window(seq, start_pos, end_pos, guide_seq=g, max_mismatches=2))


tabtutorial, tabDNA, tabProtein, tabAI = st.tabs([
    "📘 Tutorial",
    "🧬 DNA",
    "🧪 Protein",
    "🤖 AI Assistant",
])
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
    st.write("Try **🧪 3D Helix** (DNA helix with PAM/gRNA connectors) and **🧪 Triple Helix (Concept)** to highlight purine-runs.")

    st.markdown("### 5) Protein structures")
    st.write("Open **🧱 Protein Structure** to:")
    st.markdown("""
    - **Example (1CRN)** or **Upload PDB** to view a structure.
    - **Build from sequence**: type an AA string and build an idealized **helix/beta/coil** backbone.
    - **Build segmented**: specify blocks like `1-12:helix,13-18:coil,19-30:beta`.
    - **Compare multiple**: paste one AA sequence per line → overlay (aligned) or grid.
    """)
    st.warning("Use **Style = cartoon+sticks** or **stick** so sidechains are visible; cartoon alone hides sidechains.")

    st.markdown("### 6) In-silico edits")
    st.write("Open **✂️ Editing (in-silico)** to simulate SNPs, insertions, deletions, or a simple KO cut window.")

    st.markdown("### 7) Variants & MSA")
    st.write("Use **🧷 Variants** to diff two DNAs and call simple SNP/indel variants. Use **🧯 MSA** to align multiple FASTA entries and see an identity heatmap.")

    st.divider()
    st.markdown("## One-click presets (for a fun first run)")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("**Peptide (bulky aromatics)**")
        if st.button("Use `WWWWWWWWWW`", key="tut_w10"):
            st.session_state.setdefault("tut_seq_pep", "WWWWWWWWWW")
            st.success("Preset saved. Go to **🧱 Protein Structure → Build from sequence** and paste it.")
    with c2:
        st.markdown("**Peptide (Pro kink)**")
        if st.button("Use `AAAAAPAAAAA`", key="tut_prok"):
            st.session_state.setdefault("tut_seq_pep", "AAAAAPAAAAA")
            st.success("Preset saved. Go to **🧱 Protein Structure → Build from sequence** and paste it.")
    with c3:
        st.markdown("**Segmented example**")
        if st.button("Use segmented demo", key="tut_segs"):
            st.session_state["tut_seq_pep"] = "AAAAAAAAAAAAGGGPPPGGGVVVVVVVVVV"
            st.session_state["tut_segs"] = "1-12:helix,13-18:coil,19-30:beta"
            st.success("Presets saved. Go to **🧱 Protein Structure → Build segmented** and paste them.")

    st.caption("Preset tip: also try `GGGPPPGGG`, `STNQSTNQSTNQ`, `VVVVVVVVVVVV`.")
    st.divider()

    with st.expander("Troubleshooting"):
        st.markdown("""
- **I see `'view' object is not iterable`** → You’re looping over an overlay viewer. Only iterate in Grid mode. Use `if not is_grid: ... else: for v in v_or_grid: ...`.
- **Grid not showing** → The Python wrapper for 3Dmol.js doesn’t have `createViewerGrid`. We now build multiple views and layout with `st.columns`.
- **PeptideBuilder errors** → Our builder auto-detects the API. If needed, reinstall: `pip install --upgrade --force-reinstall PeptideBuilder`.
- **Overlay alignment** → Requires `biopython`. Install: `pip install biopython`.
- **Sidechains not visible** → Use **Style = cartoon+sticks** or **stick** and set **stick radius** ~0.25–0.35.
        """)

with tabDNA:
    dna_tabs = st.tabs([
        "📤 Files",
        "📊 2D Tracks",
        "🧪 3D Helix",
        "🧪 Triple Helix (Concept)",
        "🔎 Motifs & Restriction Sites",
        "🧬 Translation & ORFs",
        "🧷 Variants",
        "🧫 Codon Usage",
        "🧯 MSA",
        "✂️ Editing (in-silico)",
        "🧭 Genome Annotation",
    ])
    (tabfiles, tab2d, tab3d, tab3x, tabmotif,
     tabtrans, tabvars, tabcodon, tabmsa, tabedit, tabannot) = dna_tabs

    # ===== Protein group =====
    with tabProtein:
        protein_tabs = st.tabs([
            "🧱 Protein Structure",
            # (Optionally add more later: "📐 Properties", "🧪 Mutations")
        ])
        (tabstruct,) = protein_tabs

    # ===== AI group =====
    with tabAI:
        # Keep your AI assistant UI here
        pass


# ---------- Files tab ----------
with tabfiles:
    st.subheader("Load & Exp  ort Sequences")
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
    save_text_download("⬇️ Download FASTA (window)", to_fasta(f"Sequence_{start_pos}_{end_pos}", seq[start_pos:end_pos]),
                       f"sequence_{start_pos}-{end_pos}.fasta", st)

# ---------- 2D Tracks ----------
with tab2d:
    st.plotly_chart(plot_overview_minimap(seq, pam_positions, grnas_simple, gc_x, gc_y),
                    use_container_width=True,
                    key="overview_annot1")

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
    st.download_button("⬇️ Download gRNAs (CSV)", data=df.to_csv(index=False).encode("utf-8"),
                       file_name=f"grnas_{enzyme}_{start_pos}-{end_pos}.csv", mime="text/csv",
                       use_container_width=True)

# ---------- 3D Helix ----------
with tab3d:
    fig3d = plot_double_helix_windowed(
        sequence=seq, pam_sites=pam_positions, grnas=grnas_simple,
        start_pos=start_pos, end_pos=end_pos, pam_len=len(pam_pattern),
        guide_len=guide_len, connector_step=1
    )
    st.plotly_chart(fig3d, use_container_width=True, key="helix3d")

# ---------- Triple Helix (Concept) ----------
with tab3x:
    st.subheader("Triple-Helix DNA (concept visual)")
    colL, colR = st.columns([0.65, 0.35])
    with colR:
        st.caption("Display parameters")
        bp_turn = st.slider("bp per turn", 8.0, 14.0, 10.5, 0.1)
        r_main = st.slider("radius (main strands)", 0.6, 1.6, 1.0, 0.05)
        r_third = st.slider("radius (third strand)", 0.8, 2.0, 1.15, 0.05)
        conn_every = st.slider("connector step (every N bp)", 1, 8, 2, 1)
        min_run = st.slider("min purine-run length for triplex highlight", 4, 20, 8, 1)
        st.caption("Note: This is a **conceptual** visualization of triplex DNA (third strand in the major groove).")
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
from motifs import scan_promoters, scan_restriction_sites, within_window
with tabmotif:
    st.subheader("Motifs & Restriction Sites")
    p_hits = scan_promoters(seq)
    r_hits = scan_restriction_sites(seq)
    hits = p_hits + r_hits
    st.plotly_chart(
        plot_motif_track(seq, hits, start_pos=start_pos, end_pos=end_pos),
        use_container_width=True,
        key="motif_main"
    )

    win_hits = within_window(hits, start_pos, end_pos)
    if win_hits:
        dfh = pd.DataFrame([{
            "Name": h["name"], "Type": h["type"], "Pattern": h["pattern"],
            "Start (bp)": h["start"], "End (bp)": h["end"]
        } for h in win_hits])
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
        min_aa = st.slider("Minimum ORF length (aa)", min_value=10, max_value=300, value=60, step=10)
        all_orfs = find_orfs(seq, min_aa=min_aa, both_strands=True)
        st.plotly_chart(
            plot_orf_map(seq, all_orfs, start_pos=start_pos, end_pos=end_pos, min_aa=min_aa),
            use_container_width=True,
            key="orfmap_trans"
        )

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
                               mime="text/csv", use_container_width=True)
        else:
            st.info("No ORFs ≥ selected length in this window.")

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
            if up2:
                alt_seq, _meta2 = load_sequence_file(up2, up2.name)
            else:
                alt_seq = ""
        alt_seq = sanitize_sequence(alt_seq)

    if st.button("Align & Call Variants", type="primary"):
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
                                   file_name="variants.csv", mime="text/csv", use_container_width=True)
            else:
                st.info("No differences found.")
            effects = predict_snp_effect(ref_seq, alt_seq, start_pos=0)
            if effects:
                dfe = pd.DataFrame(effects)
                st.subheader("Coding impact (AA changes, simple model)")
                st.dataframe(dfe, use_container_width=True, hide_index=True)
            else:
                st.caption("No codon-level AA changes detected (simple model).")

# ---------- Codon Usage & Optimization ----------
with tabcodon:
    st.subheader("Codon Usage & Optimization")
    st.caption("Analyze codon usage and generate an organism-optimized coding sequence.")
    coding_region = st.text_area("Paste a coding DNA sequence (CDS)", height=140,
                                 placeholder="Must be a coding region with length multiple of 3.")
    coding_region = sanitize_sequence(coding_region)
    if coding_region:
        usage = codon_usage_count(coding_region)
        st.plotly_chart(plot_codon_usage(usage), use_container_width=True)
        org = st.selectbox("Target organism for optimization", ["Human", "E_coli", "Yeast"])
        if st.button("Optimize CDS", type="primary"):
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
    mode_msa = st.radio("Input", ["Paste Multi-FASTA", "Upload Multi-FASTA"], horizontal=True)
    if mode_msa == "Paste Multi-FASTA":
        block = st.text_area("Paste Multi-FASTA sequences", height=220, placeholder=">seq1\nATGC...\n>seq2\nATGCC...\n")
    else:
        upmsa = st.file_uploader("Upload Multi-FASTA", type=["fa","fasta"])
        block = load_multifasta_file(upmsa) if upmsa else ""
    seqs_msa = parse_fasta_multi(block) if block else []
    if seqs_msa and st.button("Align", type="primary"):
        aligned = progressive_align(seqs_msa)
        names = [n for (n, _) in aligned]
        strings = [s for (_, s) in aligned]
        cons = consensus_from_alignment(aligned)
        st.text_area("Consensus", value=cons, height=80)
        for nm, s_aln in aligned:
            st.text(f"{nm:>15}  {s_aln}")
        st.plotly_chart(plot_identity_heatmap(names, strings), use_container_width=True)
    elif not seqs_msa:
        st.caption("Provide 2+ sequences to align.")


# ---------- Protein Structure ----------
with tabstruct:
    st.subheader("Protein Structure (PDB / Built Models)")

    colS, colV = st.columns([0.42, 0.58], gap="large")

    # -------- Controls (left) --------
    with colS:
        st.markdown("### Display")
        style = st.selectbox("Style", ["cartoon+sticks", "stick", "cartoon", "line", "surface"], index=0)
        color = st.selectbox("Color", ["chain", "spectrum", "ssPyMol", "resi", "element", "#ffffff"], index=0)
        stick_radius = st.slider("Stick radius", 0.1, 0.6, 0.25, 0.05)
        dark_bg = st.checkbox("Dark background", value=True)
        show_lig = st.checkbox("Highlight ligands (HET, no water)", value=True)

        st.divider()
        st.markdown("### Source")
        source = st.radio(
            "Choose source",
            ["Example (1CRN)", "Upload PDB", "Build from sequence", "Build segmented", "Compare multiple"],
            horizontal=False,
        )

        pdb_text = ""
        viewer_mode = "single"   # or "overlay" / "grid"
        highlight = None
        chains = None
        align = "none"

        if source == "Example (1CRN)":
            pdb_text = PDB_1CRN

        elif source == "Upload PDB":
            up_pdb = st.file_uploader("Upload .pdb", type=["pdb"])
            if up_pdb:
                pdb_text = up_pdb.read().decode("utf-8", errors="ignore")

        elif source == "Build from sequence":
            seq_in = st.text_input("AA sequence (one-letter, standard 20)", value="ACDEFGHIKLMNPQRSTVWY")
            conf = st.selectbox("Backbone conformation", ["helix", "beta", "coil"], index=0)
            jitter = st.slider("Backbone jitter (°)", 0.0, 10.0, 4.0, 0.5,
                               help="Small per-residue φ/ψ randomness so models differ visually")
            seed = st.number_input("Random seed (optional)", min_value=0, value=42, step=1)
            if st.button("Build model", type="primary", use_container_width=True):
                try:
                    pdb_text = build_peptide_pdb(seq_in, conformation=conf, jitter_deg=jitter, seed=int(seed))
                    st.success(f"Built model: {len(seq_in)} aa, {conf}.")
                except Exception as e:
                    st.error(str(e))

        elif source == "Build segmented":
            seq_in = st.text_input("AA sequence", value="AAAAAAAAAAAAGGGPPPGGGVVVVVVVVVV")
            spec = st.text_input("Segments (1-based, comma sep)", value="1-12:helix,13-18:coil,19-30:beta",
                                 help="Format: start-end:type, e.g., 1-12:helix,13-18:coil,19-30:beta")
            jitter = st.slider("Backbone jitter (°)", 0.0, 10.0, 4.0, 0.5)
            seed = st.number_input("Random seed", min_value=0, value=42, step=1)
            if st.button("Build segmented model", type="primary", use_container_width=True):
                try:
                    segs = []
                    for part in spec.split(","):
                        rng, kind = part.strip().split(":")
                        s, e = rng.split("-")
                        segs.append((int(s), int(e), kind.strip()))
                    pdb_text = build_peptide_pdb_segmented(seq_in, segments=segs,
                                                           jitter_deg=jitter, seed=int(seed))
                    st.success(f"Built segmented model: {len(seq_in)} aa.")
                except Exception as e:
                    st.error(f"Segment spec error: {e}")

        else:  # Compare multiple
            st.caption("Build several **helix** peptides and compare. Use overlay + Cα superposition or grid.")
            seqs_raw = st.text_area("Sequences (one per line)", height=140,
                                    value="AAAAAPAAAAA\nWWWWWWWWWW\nGGGPPPGGG")
            view_mode = st.radio("View mode", ["Overlay (aligned)", "Grid"], horizontal=True, index=0)
            chains_in = st.text_input("Limit to chains (optional, e.g., A,B)", value="")
            chains = [c.strip() for c in chains_in.split(",") if c.strip()] or None
            align = "ca_to_first" if view_mode.startswith("Overlay") else "none"
            viewer_mode = "overlay" if view_mode.startswith("Overlay") else "grid"

    # -------- Viewer (right) --------
    with colV:
        if source != "Compare multiple":
            if pdb_text:
                v = show_pdb(
                    pdb_text,
                    style=style,
                    color=color,               # alias supported
                    stick_radius=stick_radius,
                    dark_bg=dark_bg,
                    show_ligands=show_lig,
                    chains=chains,
                    highlight=highlight,
                )
                st.components.v1.html(to_html(v), height=620, scrolling=False)
            else:
                st.info("Choose a source or build a peptide to visualize.")
        else:
            # Build many small peptides (helix) from the provided sequences
            seqs = [s.strip() for s in seqs_raw.splitlines() if s.strip()]
            if not seqs:
                st.info("Add at least one sequence (one per line).")
            else:
                try:
                    pdbs = [build_peptide_pdb(s, conformation="helix", jitter_deg=4.0, seed=42) for s in seqs]

                    v_or_grid, is_grid = show_pdbs(
                        pdbs,
                        mode=viewer_mode,  # "overlay" or "grid"
                        style=style,
                        color=color,
                        stick_radius=stick_radius,
                        dark_bg=dark_bg,
                        show_ligands=show_lig,
                        chains=chains,
                        align=align,  # "ca_to_first" for overlay alignment
                        highlight_sets=None,
                    )

                    if not is_grid:
                        # v_or_grid is a SINGLE py3Dmol.view
                        st.components.v1.html(to_html(v_or_grid), height=670, scrolling=False)
                    else:
                        # v_or_grid is a LIST of py3Dmol.view
                        cols_per_row = 3
                        cols = st.columns(cols_per_row)
                        for i, v in enumerate(v_or_grid):
                            with cols[i % cols_per_row]:
                                st.components.v1.html(to_html(v), height=340, scrolling=False)

                except Exception as e:
                    st.error(str(e))

# ---------- Genome Annotation (composed) ----------
with tabannot:
    st.subheader("Genome Annotation Mode")
    show_pams = st.checkbox("Show PAMs/gRNAs", True)
    show_mot  = st.checkbox("Show motifs/RE", True)
    show_orf  = st.checkbox("Show ORFs", True)

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

    # 👇 ORFs only run when the box is checked
    if show_orf:
        min2 = st.slider("Min ORF length (aa)", 10, 300, 60, 10, key="annot_orf_min")
        all_orfs2 = find_orfs(seq, min_aa=min2, both_strands=True)
        if all_orfs2:  # only plot if we found ORFs
            st.plotly_chart(
                plot_orf_map(seq, all_orfs2, start_pos=start_pos, end_pos=end_pos, min_aa=min2),
                use_container_width=True,
                key="orfmap_annot"
            )
        else:
            st.info("No ORFs found with current threshold.")

# ---------- AI Assistant (offline) ----------
with tabAI:
    st.subheader("Ask questions about your current sequence/window")
    st.caption("Try: *Which gRNA looks best here and why?* • *Explain TTTV vs NGG* • *What does GC% imply?*")
    q = st.text_area("Your question", height=120, placeholder="Ask anything about this sequence, PAMs, or gRNAs…")
    context_block = format_context(
        sequence=seq, enzyme=enzyme, pam=pam_pattern, pam_side=pam_side, guide_len=guide_len,
        start=start_pos, end=end_pos, grnas=grnas_simple
    )
    pick_options = [f"pos {p} | {g}" for (g, p) in window_guides]
    pick = st.selectbox("Critique a specific gRNA (optional)", options=pick_options) if pick_options else None
    if st.button("🧠 Analyze (offline)", type="primary", use_container_width=True):
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
