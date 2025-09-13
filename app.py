all_orfs2 = []  # always defined, even if ORF checkbox is off
min2 = 60

from protein_tools import ca_coords_from_pdb, contact_matrix, contact_edges
from structure_viewer import apply_residue_coloring  # new helper you just added

import sonify
# app.py
# ---- our local modules (make sure these files exist) ----
import re
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
from primer import design_primers, primers_to_fasta


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
    st.markdown("### Display / realism")
    hyper = st.checkbox("Hyper-realistic mode", value=False,
                        help="More physically-faithful visuals (B-DNA), glossy protein surfaces, and NN Tm for primers.")

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

# ---------- B-DNA helix (realistic geometry) ----------
import numpy as np
import plotly.graph_objects as go

def plot_bdna_windowed(start_pos: int, end_pos: int,
                       twist_deg: float = 36.0,    # ~10 bp per turn
                       rise_A: float = 3.32,       # Å per base pair
                       radius_A: float = 10.0,     # Å backbone radius
                       rung_thickness: float = 1.2,
                       strand_thickness: float = 2.2):
    """
    Physically-reasonable B-DNA: two sugar-phosphate backbones + basepair 'rungs'.
    Coordinates in Å; Plotly is unitless so this is for realism & proportion.
    """
    n = max(2, int(end_pos - start_pos))
    ang = np.deg2rad(np.arange(n) * twist_deg)
    z   = np.arange(n) * rise_A

    # Two backbones 180° apart
    x1 = radius_A * np.cos(ang); y1 = radius_A * np.sin(ang)
    x2 = radius_A * np.cos(ang + np.pi); y2 = radius_A * np.sin(ang + np.pi)

    fig = go.Figure()

    # backbone 1
    fig.add_trace(go.Scatter3d(
        x=x1, y=y1, z=z, mode="lines",
        line=dict(width=strand_thickness),
        name="Backbone A"
    ))
    # backbone 2
    fig.add_trace(go.Scatter3d(
        x=x2, y=y2, z=z, mode="lines",
        line=dict(width=strand_thickness),
        name="Backbone B"
    ))

    # rungs (base pairs) as short segments between the two backbones
    for i in range(n):
        fig.add_trace(go.Scatter3d(
            x=[x1[i], x2[i]], y=[y1[i], y2[i]], z=[z[i], z[i]],
            mode="lines",
            line=dict(width=rung_thickness),
            showlegend=False,
        ))

    fig.update_scenes(aspectmode="data")
    fig.update_layout(
        height=640, margin=dict(l=0, r=0, t=20, b=0),
        scene=dict(
            xaxis=dict(visible=False), yaxis=dict(visible=False), zaxis=dict(visible=False),
        ),
        showlegend=False
    )
    return fig


import re
from typing import List, Tuple, Union

PROSITE_LITE = [
    ("N-glycosylation",      r"N(?!P)[ST](?!P)"),   # N{P}[ST]{P}
    ("PKC phosphorylation",  r"[ST].[RK]"),
    ("CK2 phosphorylation",  r"[ST]..[DE]"),
    ("Proline-directed",     r"[ST]P"),
    ("N-myristoylation",     r"G..[STAGCN][STAGCN]"),
]

def scan_protein_motifs(seq: str) -> List[dict]:
    seq = "".join(ch for ch in (seq or "").upper() if ch in "ACDEFGHIKLMNPQRSTVWY")
    hits = []
    for name, pat in PROSITE_LITE:
        for m in re.finditer(pat, seq):
            s, e = m.start() + 1, m.end()  # 1-based
            hits.append({"Motif": name, "Start": s, "End": e, "Length": e - s + 1, "Seq": seq[s-1:e]})
    return hits

def motif_highlight_string(hits: List[dict], chain: str = "A") -> str:
    parts = []
    for h in hits:
        s, e = h["Start"], h["End"]
        parts.append(f"{chain}:{s}-{e}" if e > s else f"{chain}:{s}")
    return ", ".join(parts)

# ---------- Primer design helpers (educational; heuristic, not clinical) ----------
import math, re

def _gc_pct_local(s: str) -> float:
    s = s.upper()
    return 100.0 * (s.count("G") + s.count("C")) / max(1, len(s))

def _tm_wallace(s: str) -> float:
    s = s.upper()
    return 2.0 * (s.count("A") + s.count("T")) + 4.0 * (s.count("G") + s.count("C"))

def _bad_runs(s: str, n: int = 4) -> bool:
    return re.search(r"(A{%d,}|C{%d,}|G{%d,}|T{%d,})" % (n, n, n, n), s.upper()) is not None

def _gc_clamp(s: str) -> bool:
    return s and s[-1].upper() in ("G", "C")

def _revcomp(s: str) -> str:
    # use your existing helper if you prefer: reverse_complement(s)
    d = str.maketrans("ACGTacgt", "TGCAtgca")
    return s.translate(d)[::-1]

def _suffix_prefix_comp_len(a: str, b: str) -> int:
    """
    Longest k such that a's 3' suffix of length k equals complement of b's 5' prefix of length k.
    Simple proxy for 3'-anchored heterodimer risk.
    """
    rb = _revcomp(b)
    m = min(len(a), len(rb))
    for k in range(m, 0, -1):
        if a[-k:].upper() == rb[:k].upper():
            return k
    return 0

def _hairpin_len(s: str) -> int:
    """
    Longest k such that 3' suffix of s of length k complements a prefix elsewhere in s (rough hairpin proxy).
    """
    r = _revcomp(s)
    m = min(len(s), len(r))
    best = 0
    # check suffix of s vs anywhere in r (limit search a bit)
    targ = s[-12:].upper()
    rr = r.upper()
    for k in range(min(12, len(targ)), 0, -1):
        if targ[-k:] in [rr[i:i+k] for i in range(0, len(rr)-k+1)]:
            return k
    return best

def _count_occurrences(genome: str, pattern: str) -> int:
    g = genome.upper()
    p = pattern.upper()
    n = 0
    i = g.find(p)
    while i != -1:
        n += 1
        i = g.find(p, i+1)
    return n

def _check_primer(seq: str, min_len=18, max_len=26, tm_range=(55, 65), gc_range=(40, 60)) -> dict | None:
    s = seq.strip().upper()
    if not (min_len <= len(s) <= max_len):
        return None
    tm = _tm_wallace(s)
    gc = _gc_pct_local(s)
    if not (tm_range[0] <= tm <= tm_range[1]): return None
    if not (gc_range[0] <= gc <= gc_range[1]): return None
    if _bad_runs(s): return None
    hp = _hairpin_len(s)
    if hp >= 5: return None  # reject strong hairpins
    clamp = _gc_clamp(s)
    return {"seq": s, "len": len(s), "tm": tm, "gc": gc, "clamp": clamp, "hairpin": hp}

def _find_primers_for_window(genome: str, start_bp: int, end_bp: int,
                             left_span: int = 140, right_span: int = 140,
                             min_len=18, max_len=26, tm_range=(55,65), gc_range=(40,60),
                             max_candidates=60):
    """
    Scan for left primers near window start (forward strand) and right primers near window end (reverse strand).
    Returns (left_list, right_list) with metrics.
    """
    G = genome.upper()
    L = len(G)
    # Left search region: inside window from start_bp to start_bp+left_span
    ls = max(0, start_bp)
    le = min(L, start_bp + left_span)
    lefts = []
    for pos in range(ls, le):
        for ln in range(min_len, max_len+1):
            if pos + ln > L: break
            cand = G[pos:pos+ln]
            meta = _check_primer(cand, min_len, max_len, tm_range, gc_range)
            if meta:
                meta.update({"pos": pos, "strand": "+", "tail12_count": _count_occurrences(G, cand[-12:])})
                lefts.append(meta)
                if len(lefts) >= max_candidates: break
        if len(lefts) >= max_candidates: break

    # Right search region: inside window from end_bp - right_span to end_bp
    rs = max(0, end_bp - right_span)
    re_ = min(L, end_bp)
    rights = []
    for endpos in range(re_, rs, -1):  # walk backwards
        for ln in range(min_len, max_len+1):
            start = endpos - ln
            if start < 0: break
            cand = G[start:endpos]
            cand_rc = _revcomp(cand)
            meta = _check_primer(cand_rc, min_len, max_len, tm_range, gc_range)
            if meta:
                meta.update({"pos": start, "strand": "-", "tail12_count": _count_occurrences(G, cand_rc[-12:])})
                rights.append(meta)
                if len(rights) >= max_candidates: break
        if len(rights) >= max_candidates: break

    return lefts, rights

def _pair_primers(lefts, rights, start_bp, end_bp,
                  max_delta_tm=2.5, prod_min=80, prod_max=1800):
    """
    Pair compatible primers; score by clamp, |ΔTm|, uniqueness of 3'12-mer, and product close to window.
    """
    pairs = []
    for Lp in lefts:
        for Rp in rights:
            delta_tm = abs(Lp["tm"] - Rp["tm"])
            if delta_tm > max_delta_tm: continue
            # product: from Lp.pos to Rp.pos+Rp.len
            prod = (Rp["pos"] + Rp["len"]) - Lp["pos"]
            if not (prod_min <= prod <= prod_max): continue
            # simple dimer risk
            dimer_k = max(_suffix_prefix_comp_len(Lp["seq"], Rp["seq"]),
                          _suffix_prefix_comp_len(Rp["seq"], Lp["seq"]))
            if dimer_k >= 5:  # strong 3' complementarity
                continue
            # score
            clamp_bonus = (1 if Lp["clamp"] else 0) + (1 if Rp["clamp"] else 0)
            uniq_bonus = (1.0 / max(1, Lp["tail12_count"])) + (1.0 / max(1, Rp["tail12_count"]))
            center = (start_bp + end_bp) / 2.0
            prod_center = Lp["pos"] + prod/2.0
            center_pen = abs(prod_center - center) / max(1, (end_bp - start_bp)/2.0)  # 0..~1
            score = (2.0 - min(delta_tm, 2.0)) + clamp_bonus + 0.5*uniq_bonus + (1.0 - min(center_pen, 1.0))
            pairs.append({
                "Left": Lp["seq"], "Right": Rp["seq"],
                "Tm_L": round(Lp["tm"],1), "Tm_R": round(Rp["tm"],1), "ΔTm": round(delta_tm,1),
                "GC%_L": round(Lp["gc"],1), "GC%_R": round(Rp["gc"],1),
                "Clamp_L": "✓" if Lp["clamp"] else "",
                "Clamp_R": "✓" if Rp["clamp"] else "",
                "3p12_hits_L": Lp["tail12_count"], "3p12_hits_R": Rp["tail12_count"],
                "Prod_len_bp": prod,
                "L_start": Lp["pos"], "R_end": Rp["pos"] + Rp["len"],
                "Score": round(score,3)
            })
    pairs.sort(key=lambda d: d["Score"], reverse=True)
    return pairs


# ---------- Protein helpers ----------
from typing import List, Tuple, Union, Optional

def _aa_only(seq: str) -> str:
    return "".join(ch for ch in (seq or "").upper() if ch in "ACDEFGHIKLMNPQRSTVWY")

def parse_highlight_spec(spec: str) -> List[Tuple[str, Union[int, Tuple[int,int]]]]:
    """
    Parse 'A:10, A:40-50, B:12' -> [('A',10), ('A',(40,50)), ('B',12)]
    """
    out = []
    for token in (spec or "").split(","):
        t = token.strip()
        if not t or ":" not in t:
            continue
        chain, rest = t.split(":", 1)
        chain = chain.strip()
        rest = rest.strip()
        if "-" in rest:
            a, b = rest.split("-", 1)
            out.append((chain, (int(a), int(b))))
        else:
            out.append((chain, int(rest)))
    return out

def hydropathy_profile(seq: str, window: int = 9):
    # Kyte–Doolittle scale
    kd = {
        'I':4.5,'V':4.2,'L':3.8,'F':2.8,'C':2.5,'M':1.9,'A':1.8,'G':-0.4,
        'T':-0.7,'S':-0.8,'W':-0.9,'Y':-1.3,'P':-1.6,'H':-3.2,'E':-3.5,
        'Q':-3.5,'D':-3.5,'N':-3.5,'K':-3.9,'R':-4.5
    }
    x = np.array([kd.get(a, 0.0) for a in seq], dtype=float)
    if len(x) < 1:
        return np.array([]), np.array([])
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
    fig.update_layout(
        height=260, margin=dict(l=20,r=20,t=30,b=10),
        xaxis_title="Residue", yaxis_title=f"Hydropathy (window={window})"
    )
    return fig


# Top-3 within window
window_guides = [(g, p) for (g, p) in grnas_simple if start_pos <= p < end_pos]
scored = sorted(window_guides, key=lambda gp: score_guide(gp[1], gp[0], start_pos, end_pos), reverse=True)
top_positions = {p for (_g, p) in scored[:3]}

# Off-targets (Hamming ≤ 2) in window
off_targets = []
for g, p in window_guides:
    off_targets.extend(find_off_targets_window(seq, start_pos, end_pos, guide_seq=g, max_mismatches=2))


tabtutorial, tabDNA, tabProtein, tabSonify,  tabAI = st.tabs([
    "📘 Tutorial",
    "🧬 DNA",
    "🧪 Protein",
    "🎵 Sonify",
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
        "🧪 Primer Designer",
        "🧷 Variants",
        "🧫 Codon Usage",
        "🧯 MSA",
        "✂️ Editing (in-silico)",
        "🧭 Genome Annotation",
    ])
    (tabfiles, tab2d, tab3d, tab3x, tabmotif,
     tabtrans, tabprimer,  tabvars, tabcodon, tabmsa, tabedit, tabannot) = dna_tabs

    # ===== Protein group =====
    with tabProtein:
        protein_tabs = st.tabs([
            "🧱 Protein Structure",
            "Properties"
        ])
        tabstruct, tabpprop = protein_tabs

    # ---------- Sonify ----------
    with tabSonify:
        st.subheader("Sequence → Music (MIDI)")
        st.caption("Turn DNA or protein into a melody. All offline.")

        mode = st.radio("Input type", ["DNA", "Protein"], horizontal=True)
        colL, colR = st.columns([0.6, 0.4])

        with colL:
            if mode == "DNA":
                seq_in = st.text_area("DNA (A/C/G/T)", height=140, placeholder="ATGCGT...")
                map_style = st.radio("Mapping", ["Nucleotide→notes", "Translate→AA→notes"], horizontal=True)
            else:
                seq_in = st.text_area("Protein (one-letter amino acids)", height=140,
                                      placeholder="ACDEFGHIKLMNPQRSTVWY")
                map_style = "AA only"

            seq_in = (seq_in or "").strip()

            bpm = st.slider("Tempo (BPM)", 60, 200, 120)
            note_len = st.slider("Note length (beats)", 0.25, 1.0, 0.5, 0.25)
            base_oct = st.slider("Base octave", 2, 6, 5)
            base_note = 12 * base_oct  # 5→60(C4), 4→48(C3), etc.

            program_name = st.selectbox(
                "Instrument",
                ["Acoustic Grand (0)", "Electric Piano (4)", "Marimba (12)",
                 "Church Organ (19)", "Guitar (24)", "Strings (48)", "Synth Pad (88)"],
                index=0
            )
            program = int(program_name.split("(")[-1].split(")")[0])

            if st.button("🎼 Create MIDI", type="primary", use_container_width=True):
                try:
                    if mode == "DNA":
                        dna = sonify.dna_only(seq_in)
                        if not dna:
                            st.warning("Please paste a DNA sequence (A/C/G/T).")
                        else:
                            if map_style.startswith("Translate"):
                                aa = sonify.aa_only(translate_dna(dna, frame=0))  # you already import translate_dna
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
                        midi_bytes = sonify.make_midi(
                            pitches, bpm=bpm, program=program, note_len_beats=note_len
                        )
                        st.success(f"Generated {len(pitches)} notes.")
                        st.download_button("⬇️ Download MIDI", data=midi_bytes, file_name=label,
                                           mime="audio/midi", use_container_width=True)
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

# --- Base Editor Sandbox (ABE / CBE) ---
with st.expander("🧪 Base Editor Sandbox (ABE / CBE)", expanded=False):
    if not grnas_all:
        st.info("No gRNAs found yet. Pick an enzyme / window that yields candidates.")
    else:
        editor = st.radio("Editor", ["ABE (A→G)", "CBE (C→T)"], horizontal=True)
        # Typical windows (1-based positions in protospacer, 5'→3')
        default_win = (4, 8) if editor.startswith("ABE") else (3, 9)
        wstart = st.number_input("Edit window start (1-based)", 1, guide_len, value=default_win[0])
        wend   = st.number_input("Edit window end (1-based)", 1, guide_len, value=default_win[1])
        if wend < wstart:
            st.warning("End < Start: swap them to continue.")
        else:
            # pick a gRNA within the current window, show strand and pos
            options = [f"{s} | pos {p} | {g}" for (s, g, p) in grnas_all if start_pos <= p < end_pos]
            if not options:
                st.info("No gRNAs inside the current window.")
            else:
                pick = st.selectbox("gRNA", options)
                # parse back
                try:
                    sgn = pick.split("|")[0].strip()        # '+' or '-'
                    sgn = sgn[0]
                    pos = int(pick.split("pos")[1].split("|")[0].strip())
                    g   = pick.split("|")[-1].strip()
                except Exception:
                    sgn, pos, g = "+", start_pos, options[0].split("|")[-1].strip()

                # protospacer sequence (5'→3' of target strand)
                region = seq[pos:pos+guide_len]
                from crisprutils import reverse_complement
                prot = region if sgn == "+" else reverse_complement(region)

                # indices to edit (0-based within prot)
                i0 = max(0, int(wstart)-1); i1 = min(guide_len-1, int(wend)-1)
                idxs = list(range(i0, i1+1))

                # define base conversion on prot strand and mapping back to forward-genome
                def complement(b):
                    return {"A":"T","C":"G","G":"C","T":"A"}.get(b, "N")

                edits = []
                prot_list = list(prot)
                for i in idxs:
                    b = prot_list[i]
                    if editor.startswith("ABE") and b == "A":
                        b_new = "G"
                    elif editor.startswith("CBE") and b == "C":
                        b_new = "T"
                    else:
                        continue

                    # Genomic coordinate for this prot index
                    if sgn == "+":
                        j = pos + i
                        new_base_genome = b_new  # same orientation
                    else:
                        j = pos + (guide_len - 1 - i)
                        new_base_genome = complement(b_new)  # prot change maps to complement on forward genome

                    old_base_genome = seq[j]
                    if old_base_genome == new_base_genome:
                        effect = "no change"
                    else:
                        effect = f"{old_base_genome}→{new_base_genome}"

                    edits.append({
                        "Prot idx (1-based)": i+1,
                        "Genome bp": j,
                        "Edit": effect,
                    })

                if edits:
                    df_ed = pd.DataFrame(edits)
                    st.dataframe(df_ed, use_container_width=True, hide_index=True)
                else:
                    st.info("No targetable bases in the selected window for this editor.")

                # Build a full edited sequence applying ALL eligible conversions in one go
                if st.button("Build edited sequence (apply all in-window conversions)", use_container_width=True):
                    seq_list = list(seq)
                    for row in edits:
                        j = int(row["Genome bp"])
                        to = row["Edit"].split("→")[-1]
                        if len(to) == 1 and to in "ACGT":
                            seq_list[j] = to
                    new_seq = "".join(seq_list)
                    # Preview around the gRNA
                    left = max(0, pos-30); right = min(len(new_seq), pos+guide_len+30)
                    st.code(new_seq[left:right])
                    from io_utils import to_fasta, save_text_download
                    save_text_download("⬇️ Download edited FASTA", to_fasta("BaseEdited", new_seq), "base_edited.fasta", st)


# ---------- 3D Helix ----------
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

# ---------- Primer Designer (PCR) ----------
with tabprimer:
    st.subheader("Primer Designer (PCR)")
    st.caption("Heuristic, offline primer picking around the current window. Educational use only.")

    colL, colR = st.columns([0.55, 0.45])

    with colL:
        primer_len = st.slider("Primer length (nt)", 18, 30, (20, 24), 1)
        tm_min, tm_max = st.slider("Target Tm (°C)", 45, 75, (58, 64), 1)
        gc_min, gc_max = st.slider("GC% range", 30, 70, (40, 60), 1)
        delta_tm = st.slider("Max ΔTm (°C)", 0.5, 5.0, 2.5, 0.5)
        left_span = st.slider("Left search span inside window (bp)", 40, 400, 140, 10)
        right_span = st.slider("Right search span inside window (bp)", 40, 400, 140, 10)
        prod_min, prod_max = st.slider("Product size (bp)", 50, 3000, (120, 1200), 10)
        top_k = st.number_input("How many pairs to report", min_value=1, max_value=50, value=10, step=1)

        if st.button("Design primers", type="primary", use_container_width=True):
            with st.spinner("Scanning primers..."):
                pairs = design_primers(
                    genome=seq,
                    start_bp=start_pos, end_bp=end_pos,
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
                    import pandas as pd
                    dfp = pd.DataFrame(pairs)
                    st.dataframe(dfp, use_container_width=True, hide_index=True)

                    fasta = primers_to_fasta(pairs)
                    st.download_button("⬇️ Download primers (FASTA)",
                        data=fasta.encode("utf-8"),
                        file_name=f"primers_{start_pos}-{end_pos}.fasta",
                        mime="text/plain",
                        use_container_width=True)

    with colR:
        st.markdown("**Design region**")
        st.code(f"Window: {start_pos}–{end_pos} (len {end_pos-start_pos} bp)")
        st.caption("Left primers are picked near the window start; right primers near the window end (reverse strand).")
        st.markdown("**Notes**")
        st.write("- Tm uses the Wallace rule (rough).")
        st.write("- Screens: GC%, GC clamp, homopolymer runs, basic hairpin/dimer proxy, 3' 12-mer uniqueness.")
        st.write("- Validate with dedicated primer tools and wet-lab controls before any real experiment.")








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
        color_by = st.selectbox("Residue coloring", ["None", "Hydropathy", "Charge"], index=0)


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
            viewer_mode = "single"  # or "overlay" / "grid"
            chains = None
            align = "none"

            if source == "Example (1CRN)":
                pdb_text = PDB_1CRN

            elif source == "Upload PDB":
                up_pdb = st.file_uploader("Upload .pdb", type=["pdb"])
                if up_pdb:
                    pdb_text = up_pdb.read().decode("utf-8", errors="ignore")

            elif source == "Build from sequence":
                default_seq_in = st.session_state.get("tut_seq_pep", "ACDEFGHIKLMNPQRSTVWY")
                seq_in = st.text_input("AA sequence (one-letter, standard 20)", value=default_seq_in)
                conf = st.selectbox("Backbone conformation", ["helix", "beta", "coil"], index=0)
                jitter = st.slider("Backbone jitter (°)", 0.0, 10.0, 4.0, 0.5,
                                   help="Small per-residue φ/ψ randomness so models differ visually")
                seed = st.number_input("Random seed (optional)", min_value=0, value=42, step=1)
                if st.button("Build model", type="primary", use_container_width=True):
                    try:
                        pdb_text = build_peptide_pdb(seq_in, conformation=conf, jitter_deg=jitter, seed=int(seed))
                        st.session_state["pdb_current"] = pdb_text
                        st.success(f"Built model: {len(seq_in)} aa, {conf}.")
                    except Exception as e:
                        st.error(str(e))

            elif source == "Build segmented":
                default_seg_seq = st.session_state.get("tut_seq_pep", "AAAAAAAAAAAAGGGPPPGGGVVVVVVVVVV")
                seq_in = st.text_input("AA sequence", value=default_seg_seq)
                spec_default = st.session_state.get("tut_segs", "1-12:helix,13-18:coil,19-30:beta")
                spec = st.text_input("Segments (1-based, comma sep)", value=spec_default,
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
                        st.session_state["pdb_current"] = pdb_text
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

            st.divider()
            st.markdown("### Highlights")
            hl_default = st.session_state.get("tut_hl", "")
            hl = st.text_input("Residues (chain:resi or chain:start-end, comma-separated)",
                               value=hl_default, placeholder="e.g., A:15, A:40-50, B:12")

            if st.session_state.get("pdb_current"):
                st.download_button(
                    "⬇️ Download current PDB",
                    data=st.session_state["pdb_current"],
                    file_name="model.pdb",
                    mime="chemical/x-pdb",
                    use_container_width=True,
                )
        with tabpprop:
            st.subheader("Protein Properties")
            pep = st.text_area("Amino-acid sequence (one-letter; standard 20)", height=120,
                               placeholder="e.g. AKLAEELAKLAEELAKL")
            pep = _aa_only(pep)

            colA, colB = st.columns([0.55, 0.45])
            with colA:
                if pep:
                    ana = ProteinAnalysis(pep)
                    mw = ana.molecular_weight()
                    pi = ana.isoelectric_point()
                    gravy = ana.gravy()
                    aro = ana.aromaticity()
                    ph = st.slider("pH", 0.0, 14.0, 7.0, 0.5)
                    try:
                        charge = ana.charge_at_pH(ph)  # may not exist on older BioPython
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

                    win = st.slider("Hydropathy window", 3, 21, 9, 2)
                    st.plotly_chart(plot_hydropathy(pep, window=win), use_container_width=True)
                else:
                    st.info("Paste a protein sequence to compute properties.")

            with colB:
                st.markdown("**Amino-acid composition**")
                if pep:
                    comp = ProteinAnalysis(pep).get_amino_acids_percent()
                    fig = go.Figure(go.Bar(x=list(comp.keys()), y=[100 * v for v in comp.values()]))
                    fig.update_layout(height=260, margin=dict(l=20, r=20, t=30, b=10),
                                      xaxis_title="AA", yaxis_title="Percent")
                    st.plotly_chart(fig, use_container_width=True)
                    st.download_button("⬇️ Download sequence (FASTA)",
                                       data=f">protein\n{pep}\n".encode("utf-8"),
                                       file_name="protein.fasta", mime="text/plain", use_container_width=True)
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
                    st.session_state["tut_hl"] = hl_str  # optional: auto-fill in 3D tab
                else:
                    st.caption("No motif hits with the current patterns.")
            else:
                st.caption("Paste a protein sequence above to scan motifs.")
        # -------- Viewer (right) --------
        with colV:
            highlight = parse_highlight_spec(hl)
            if source != "Compare multiple":
                if pdb_text:
                    v = show_pdb(
                        pdb_text,
                        style=style,
                        color=color,  # alias supported
                        stick_radius=stick_radius,
                        dark_bg=dark_bg,
                        show_ligands=show_lig,  # your existing variable name
                        chains=chains,
                        highlight=highlight,
                        surface_ms_opacity=(0.28 if hyper else None),  # ✨ adds glossy molecular surface in hyper mode
                    )
                    # after v = show_pdb(...)
                    if color_by != "None":
                        v = apply_residue_coloring(v, pdb_text, scheme=color_by.lower(), stick_radius=stick_radius)
                    st.components.v1.html(to_html(v), height=620, scrolling=False)

                    # Keep a copy for download
                    st.session_state["pdb_current"] = pdb_text
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
                            st.components.v1.html(to_html(v_or_grid), height=670, scrolling=False)
                        else:
                            cols_per_row = 3
                            cols = st.columns(cols_per_row)
                            for i, vv in enumerate(v_or_grid):
                                with cols[i % cols_per_row]:
                                    st.components.v1.html(to_html(vv), height=340, scrolling=False)
                    except Exception as e:
                        st.error(str(e))

                        with st.expander("🧩 Cα Contact Map + Network", expanded=False):
                            if not pdb_text:
                                st.info("Load or build a protein first.")
                            else:
                                cutoff = st.slider("Contact cutoff (Å)", 4.0, 12.0, 8.0, 0.5)
                                show_heat = st.checkbox("Show distance heatmap", value=True)
                                topN = st.slider("Top contacts to list", 10, 200, 50, 10)

                                X, labels = ca_coords_from_pdb(pdb_text, chains=None)
                                if X.size == 0:
                                    st.warning("No Cα atoms detected.")
                                else:
                                    D = contact_matrix(X)
                                    edges = contact_edges(D, cutoff=float(cutoff))
                                    st.caption(f"Contacts ≤ {cutoff:.1f} Å: **{len(edges)}**")

                                    # List top contacts
                                    if edges:
                                        rows = []
                                        for i, (a, b, d) in enumerate(edges[:topN], start=1):
                                            (c1, r1), (c2, r2) = labels[a], labels[b]
                                            rows.append({"#": i, "Residue A": f"{c1}:{r1}", "Residue B": f"{c2}:{r2}",
                                                         "Distance (Å)": round(d, 2)})
                                        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
                                    else:
                                        st.caption("No contacts under cutoff.")

                                    # Heatmap (optional)
                                    if show_heat and D.size:
                                        import plotly.graph_objects as go

                                        fig = go.Figure(data=go.Heatmap(z=D, colorbar=dict(title="Å")))
                                        fig.update_layout(height=400, margin=dict(l=0, r=0, t=10, b=0))
                                        st.plotly_chart(fig, use_container_width=True)

    # ---------- Protein Properties ----------


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
                        mode=viewer_mode,
                        style=style,
                        color=color,
                        stick_radius=stick_radius,
                        dark_bg=dark_bg,
                        show_ligands=show_lig,
                        chains=chains,
                        align=align,
                        highlight_sets=None,
                        surface_ms_opacity=(0.20 if hyper else None),  # ✨
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

# ---------- Editing (in-silico) ----------
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

        # ---- result preview & actions ----
        if new_seq != seq:
            st.success(f"Edited length: {len(new_seq)} bp (was {len(seq)}).")
            left = max(0, start_pos - 60)
            right = min(len(new_seq), end_pos + 60)
            st.code(new_seq[left:right])

            # Download edited sequence
            save_text_download("⬇️ Download edited FASTA", to_fasta("Edited", new_seq), "edited_sequence.fasta", st)

            # Optional: promote to current sequence
            if st.toggle("Replace the current sequence with this edit?", value=False, key="promote_edit"):
                st.session_state.sequence = new_seq
                # keep the window within bounds after length change
                L = len(new_seq)
                st.session_state.win = (0, min(600, L))
                st.experimental_rerun()
        else:
            st.caption("Choose parameters and click Apply to preview the edited sequence.")


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
