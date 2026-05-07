import numpy as np
import plotly.graph_objects as go
from stylekit import PLOTLY_TEMPLATE


# ---------- ORF Track Map ----------
def plot_orf_map(sequence, orfs, start_pos=0, end_pos=None, min_aa=30):
    if end_pos is None:
        end_pos = len(sequence)
    # lanes for frames: +1/+2/+3 and -1/-2/-3
    lanes = {+1: 1.2, +2: 0.6, +3: 0.0, -1: -0.4, -2: -1.0, -3: -1.6}
    fig = go.Figure()

    # baseline
    fig.add_trace(go.Scatter(
        x=[start_pos, end_pos], y=[0, 0], mode="lines",
        line=dict(color=PALETTE["dna"], width=2), name="DNA", hoverinfo="skip"
    ))

    # lane guide lines (faint)
    for y in lanes.values():
        fig.add_shape(type="line", x0=start_pos, x1=end_pos, y0=y, y1=y,
                      line=dict(color="rgba(255,255,255,0.06)", width=1))

    # ORFs overlapping the window
    def overlaps(a0, a1, b0, b1):  # [a0,a1) vs [b0,b1)
        return not (a1 <= b0 or b1 <= a0)

    shown = 0
    for o in orfs:
        if not overlaps(o["start"], o["end"], start_pos, end_pos):
            continue
        strand = o["strand"]
        frame = o["frame"]
        lane_y = lanes[int(frame/abs(frame)) * abs(frame)] if frame != 0 else 0.0
        x0, x1 = max(start_pos, o["start"]), min(end_pos, o["end"])
        aa = o["aa_len"]
        color = "#34D399" if strand == "+" else "#60A5FA"
        fig.add_trace(go.Scatter(
            x=[x0, x1], y=[lane_y, lane_y],
            mode="lines",
            line=dict(color=color, width=10, shape="hv"),
            name=f"ORF {strand}",
            showlegend=False,
            hovertemplate=f"ORF ({strand})<br>Frame: {frame}<br>bp: {o['start']}-{o['end']}<br>aa: {aa}<extra></extra>"
        ))
        shown += 1

    fig.update_layout(
        title=f"ORF Map (min {min_aa} aa)",
        height=360,
        xaxis=dict(range=[start_pos, end_pos], title="Position (bp)"),
        yaxis=dict(visible=False),
    )
    fig.update_layout(**PLOTLY_TEMPLATE["layout"])
    return fig

PALETTE = {
    "dna": "#E5E7EB",
    "pam": "#60A5FA",   # soft blue
    "grna": "#34D399",  # emerald
    "off": "#F87171",   # light red
    "gc": "#9CA3AF",    # gray
}

# ---------- Overview (GC% + rugs) ----------
def plot_overview_minimap(sequence, pam_sites, grnas, gc_x, gc_y):
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=gc_x, y=gc_y, mode="lines",
        line=dict(width=2, color=PALETTE["gc"]),
        name="GC% (windowed)",
        hovertemplate="Pos %{x:.0f}<br>GC %{y:.1f}%<extra></extra>"
    ))

    if pam_sites:
        fig.add_trace(go.Scatter(
            x=pam_sites, y=[-2] * len(pam_sites), mode="markers",
            marker=dict(symbol="line-ns-open", size=8, color=PALETTE["pam"]),
            name="PAMs", hovertemplate="PAM at %{x:.0f}<extra></extra>"
        ))

    if grnas:
        starts = [pos for (_g, pos) in grnas]
        fig.add_trace(go.Scatter(
            x=starts, y=[-4] * len(starts), mode="markers",
            marker=dict(symbol="line-ns-open", size=8, color=PALETTE["grna"]),
            name="gRNA starts", hovertemplate="gRNA start %{x:.0f}<extra></extra>"
        ))

    fig.update_layout(title="Overview", height=200)
    fig.update_layout(**PLOTLY_TEMPLATE["layout"])
    return fig

# ---------- Detailed multi-track (2D) ----------
def plot_detail_map(
    sequence, pam_sites, grnas, start_pos=0, end_pos=None,
    strand_by_pos=None, grna_strand_by_pos=None, guide_len=20,
    off_targets=None, highlight_positions=None
):
    if end_pos is None:
        end_pos = len(sequence)
    off_targets = off_targets or []
    strand_by_pos = strand_by_pos or {}
    grna_strand_by_pos = grna_strand_by_pos or {}
    highlight_positions = set(highlight_positions or [])

    # Filter
    pam_sites = [p for p in pam_sites if start_pos <= p < end_pos]
    grnas = [(g, pos) for g, pos in grnas if start_pos <= pos < end_pos]
    off_targets = [ot for ot in off_targets if start_pos <= ot.get("start", -1) < end_pos]

    fig = go.Figure()

    # Lanes
    y_dna, y_pam, y_grna, y_off = 0.0, 1.0, -1.0, 2.0

    # DNA baseline
    fig.add_trace(go.Scatter(
        x=[start_pos, end_pos], y=[y_dna, y_dna],
        mode="lines", line=dict(color=PALETTE["dna"], width=3),
        name="DNA", hoverinfo="skip"
    ))

    # PAM ticks
    for p in pam_sites:
        fig.add_trace(go.Scatter(
            x=[p, p], y=[y_pam - 0.2, y_pam + 0.2],
            mode="lines", line=dict(color=PALETTE["pam"], width=3),
            name="PAM", showlegend=False,
            hovertemplate=f"PAM at {p}<br>Seq: {sequence[p:p+3]}<extra></extra>"
        ))

    # gRNA bars + caret; highlight top-selected fat bars
    for idx, (guide, pos) in enumerate(grnas, start=1):
        x0, x1 = pos, pos + guide_len
        gc = round((guide.count('G') + guide.count('C')) / len(guide) * 100, 1)
        width = 12 if pos in highlight_positions else 8
        fig.add_trace(go.Scatter(
            x=[x0, x1], y=[y_grna, y_grna],
            mode="lines", line=dict(color=PALETTE["grna"], width=width),
            name="gRNA", showlegend=False,
            hovertemplate=f"gRNA #{idx}<br>Pos: {x0}-{x1}<br>GC: {gc}%<br>Seq: {guide}<extra></extra>"
        ))
        fig.add_trace(go.Scatter(
            x=[x0], y=[y_grna],
            mode="markers",
            marker=dict(symbol="triangle-right", size=9, color=PALETTE["grna"]),
            hoverinfo="skip", showlegend=False
        ))

    # Off-target dashed segments
    for ot in off_targets:
        s, e = ot.get("start"), ot.get("end")
        mis = ot.get("mismatches", "?")
        if s is None or e is None:
            continue
        fig.add_trace(go.Scatter(
            x=[s, e], y=[y_off, y_off],
            mode="lines", line=dict(color=PALETTE["off"], width=6, dash="dot"),
            name="Off-target", showlegend=False,
            hovertemplate=f"Off-target<br>Pos: {s}-{e}<br>Mismatches: {mis}<extra></extra>"
        ))

    fig.update_layout(
        title="Detailed Map",
        height=440,
        xaxis=dict(range=[start_pos, end_pos], title="Position (bp)"),
        yaxis=dict(visible=False),
        shapes=[
            dict(type="line", x0=start_pos, x1=end_pos, y0=y_pam, y1=y_pam, line=dict(color="rgba(255,255,255,0.06)")),
            dict(type="line", x0=start_pos, x1=end_pos, y0=y_grna, y1=y_grna, line=dict(color="rgba(255,255,255,0.06)")),
            dict(type="line", x0=start_pos, x1=end_pos, y0=y_off, y1=y_off, line=dict(color="rgba(255,255,255,0.06)")),
        ]
    )
    fig.update_layout(**PLOTLY_TEMPLATE["layout"])
    return fig

# ---------- Windowed 3D double helix ----------
def plot_double_helix_windowed(
    sequence, pam_sites, grnas, start_pos=0, end_pos=None,
    pam_len=3, guide_len=20, connector_step=1
):
    seq_len = len(sequence)
    if end_pos is None or end_pos > seq_len:
        end_pos = seq_len
    if start_pos < 0:
        start_pos = 0
    if start_pos >= end_pos:
        start_pos = max(0, end_pos - 1)

    n = max(1, end_pos - start_pos)
    sub_seq = sequence[start_pos:end_pos]

    turns = n / 10.0
    theta = np.linspace(0, turns * 2 * np.pi, n)
    r = 1.0
    x1, y1 = r * np.cos(theta), r * np.sin(theta)
    x2, y2 = r * np.cos(theta + np.pi), r * np.sin(theta + np.pi)
    z = np.linspace(0, turns, n)

    fig = go.Figure()
    fig.add_trace(go.Scatter3d(x=x1, y=y1, z=z, mode="lines", line=dict(color="#60A5FA", width=4), name="Strand A"))
    fig.add_trace(go.Scatter3d(x=x2, y=y2, z=z, mode="lines", line=dict(color="#FBBF24", width=4), name="Strand B"))

    # Connectors
    cx, cy, cz = [], [], []
    step = max(1, int(connector_step))
    for i in range(0, n, step):
        cx += [x1[i], x2[i], None]
        cy += [y1[i], y2[i], None]
        cz += [z[i],  z[i],  None]
    fig.add_trace(go.Scatter3d(x=cx, y=cy, z=cz, mode="lines", line=dict(color="gray", width=2), showlegend=False))

    def add_segment(i0, i1, color, name, hover):
        i0 = max(0, min(n - 1, i0))
        i1 = max(0, min(n - 1, i1))
        if i1 < i0:
            i0, i1 = i1, i0
        fig.add_trace(go.Scatter3d(
            x=x1[i0:i1 + 1], y=y1[i0:i1 + 1], z=z[i0:i1 + 1],
            mode="lines", line=dict(color=color, width=8),
            name=name, hovertext=hover, hoverinfo="text", showlegend=False
        ))

    # PAM segments
    for pam_abs in pam_sites:
        rel = pam_abs - start_pos
        if 0 <= rel < n:
            i0 = rel
            i1 = min(n - 1, rel + (pam_len - 1))
            pam_seq = sub_seq[i0:i1 + 1] if i1 + 1 <= len(sub_seq) else ""
            add_segment(i0, i1, "#F87171", "PAM", f"PAM {pam_seq} at {pam_abs}")

    # gRNA segments
    for guide, gpos_abs in grnas:
        rel = gpos_abs - start_pos
        if 0 <= rel < n:
            i0 = rel
            i1 = min(n - 1, rel + (guide_len - 1))
            hover = f"gRNA ({guide_len}nt) at {gpos_abs}<br>Seq: {guide}"
            add_segment(i0, i1, "#34D399", "gRNA", hover)

    fig.update_layout(
        title=f"3D Double Helix (bp {start_pos}–{end_pos})",
        scene=dict(xaxis=dict(visible=False), yaxis=dict(visible=False), zaxis=dict(title="Helix axis")),
        height=750, margin=dict(l=0, r=0, t=60, b=0)
    )
    fig.update_layout(**PLOTLY_TEMPLATE["layout"])
    return fig

import numpy as np
import plotly.graph_objects as go
from stylekit import PLOTLY_TEMPLATE

# ---------- Conceptual Triple-Helix (3-strand) ----------
def plot_triple_helix_windowed(
    sequence: str,
    start_pos: int = 0, end_pos: int | None = None,
    radius_main: float = 1.0,
    radius_third: float = 1.15,
    bp_per_turn: float = 10.5,
    highlight_intervals: list[tuple[int,int]] | None = None,
    connector_every: int = 2,
):
    """
    Conceptual visualization of a DNA triple helix: two canonical strands + a third strand
    in the major groove. 'highlight_intervals' (list of (s,e) bp coords) are shown where
    triplex-forming is more plausible (e.g., purine-rich runs).
    """
    seq_len = len(sequence)
    if end_pos is None or end_pos > seq_len:
        end_pos = seq_len
    start_pos = max(0, start_pos)
    if start_pos >= end_pos:
        start_pos = max(0, end_pos - 1)

    n = max(1, end_pos - start_pos)
    turns = n / bp_per_turn
    t = np.linspace(0, turns * 2 * np.pi, n)

    # two backbone strands (A,B)
    xA, yA = radius_main*np.cos(t), radius_main*np.sin(t)
    xB, yB = radius_main*np.cos(t + np.pi), radius_main*np.sin(t + np.pi)
    z = np.linspace(0, turns, n)

    # third strand sits in major groove; phase offset ~ 60°
    phi = np.deg2rad(60.0)
    xC = radius_third*np.cos(t + phi)
    yC = radius_third*np.sin(t + phi)

    fig = go.Figure()
    # main backbones
    fig.add_trace(go.Scatter3d(x=xA, y=yA, z=z, mode="lines",
                               line=dict(color="#60A5FA", width=5), name="Strand A"))
    fig.add_trace(go.Scatter3d(x=xB, y=yB, z=z, mode="lines",
                               line=dict(color="#FBBF24", width=5), name="Strand B"))
    # third strand
    fig.add_trace(go.Scatter3d(x=xC, y=yC, z=z, mode="lines",
                               line=dict(color="#EC4899", width=4), name="Third strand"))

    # base-pair connectors between A and B
    cx, cy, cz = [], [], []
    step = max(1, int(connector_every))
    for i in range(0, n, step):
        cx += [xA[i], xB[i], None]
        cy += [yA[i], yB[i], None]
        cz += [z[i],  z[i],  None]
    fig.add_trace(go.Scatter3d(x=cx, y=cy, z=cz, mode="lines",
                               line=dict(color="rgba(229,231,235,0.7)", width=2),
                               showlegend=False))

    # “Hoogsteen” connectors from A to the third strand (only in highlighted intervals)
    if highlight_intervals:
        for (s_abs, e_abs) in highlight_intervals:
            s = max(start_pos, s_abs) - start_pos
            e = min(end_pos, e_abs) - start_pos
            for i in range(max(0, s), min(n, e), step):
                fig.add_trace(go.Scatter3d(
                    x=[xA[i], xC[i]], y=[yA[i], yC[i]], z=[z[i], z[i]],
                    mode="lines",
                    line=dict(color="#EC4899", width=3, dash="dot"),
                    showlegend=False,
                    hovertext=f"Triplex-favored bp ~{start_pos+i}",
                    hoverinfo="text"
                ))

    fig.update_layout(
        title=f"Triple Helix (concept) — bp {start_pos}–{end_pos}",
        scene=dict(
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            zaxis=dict(title="Helix axis"),
        ),
        height=800, margin=dict(l=0, r=0, t=60, b=0)
    )
    fig.update_layout(**PLOTLY_TEMPLATE["layout"])
    return fig


# ---------- Variants: mismatch scatter ----------
def plot_variant_positions(diffs, length: int):
    xs = []
    for d in diffs:
        # place by reference coordinate when available
        pos = d.get("ref_pos") or d.get("aln_index")
        xs.append(pos)
    fig = go.Figure()
    if xs:
        fig.add_trace(go.Scatter(x=xs, y=[0]*len(xs), mode="markers",
                                 marker=dict(size=9, color="#F87171"),
                                 name="Variant",
                                 hovertemplate="Variant at %{x}<extra></extra>"))
    fig.update_layout(title="Variant Positions", height=140,
                      xaxis=dict(range=[0, max(1, length)], title="Position (bp)"),
                      yaxis=dict(visible=False))
    fig.update_layout(**PLOTLY_TEMPLATE["layout"])
    return fig

# ---------- Codon usage bar ----------
def plot_codon_usage(usage_dict):
    items = sorted(usage_dict.items(), key=lambda kv: kv[0])
    xs = [k for k,_ in items]; ys = [v for _,v in items]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=xs, y=ys, name="Count"))
    fig.update_layout(title="Codon Usage", xaxis=dict(tickangle=45), height=360)
    fig.update_layout(**PLOTLY_TEMPLATE["layout"])
    return fig

# ---------- Motif / RE track ----------
# ---------- Motif / RE track ----------
import plotly.graph_objects as go

def plot_motif_track(sequence, motifs, start_pos=0, end_pos=None):
    if end_pos is None:
        end_pos = len(sequence)
    # keep only items overlapping the window
    items = [m for m in motifs if not (m["end"] <= start_pos or m["start"] >= end_pos)]

    fig = go.Figure()
    # baseline
    fig.add_trace(go.Scatter(
        x=[start_pos, end_pos], y=[0, 0], mode="lines",
        line=dict(width=3), name="DNA", hoverinfo="skip"
    ))

    # draw motif/restriction ticks
    for m in items:
        color = "#60A5FA" if m.get("type") == "motif" else "#F59E0B"
        fig.add_trace(go.Scatter(
            x=[m["start"], m["start"]], y=[-0.4, 0.8], mode="lines",
            line=dict(color=color, width=3),
            hovertemplate=f"{m['name']}<br>Pattern: {m.get('pattern','')}<br>Start: {m['start']}<extra></extra>",
            showlegend=False
        ))

    fig.update_layout(
        title="Motifs & Restriction Sites",
        height=220,
        xaxis=dict(range=[start_pos, end_pos], title="Position (bp)"),
        yaxis=dict(visible=False),
        margin=dict(l=10, r=10, t=40, b=10),
    )
    return fig


# ---------- Simple identity heatmap for MSA ----------
def plot_identity_heatmap(names, aligned_strings):
    import numpy as np
    n = len(aligned_strings)
    M = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            a, b = aligned_strings[i], aligned_strings[j]
            same = sum(1 for x, y in zip(a, b) if x == y and x != "-")
            total = sum(1 for x, y in zip(a, b) if x != "-" and y != "-")
            M[i, j] = (same / total) * 100 if total else 0
    fig = go.Figure(data=go.Heatmap(z=M, x=names, y=names, colorscale="Viridis"))
    fig.update_layout(title="Pairwise Identity (%)", height=400)
    fig.update_layout(**PLOTLY_TEMPLATE["layout"])
    return fig

