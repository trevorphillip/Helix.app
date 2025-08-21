import numpy as np
import plotly.graph_objects as go

PALETTE = {
    "dna": "black",
    "pam": "rgba(0, 123, 255, 1)",     # blue
    "grna": "rgba(40, 167, 69, 1)",    # green
    "off": "rgba(220, 53, 69, 1)",     # red
    "gc": "rgba(90, 90, 90, 1)",
}

# ---------- Overview (minimap) with GC% + PAM/gRNA rugs ----------
def plot_overview_minimap(sequence, pam_sites, grnas, gc_x, gc_y):
    fig = go.Figure()

    # GC% line
    fig.add_trace(go.Scatter(
        x=gc_x, y=gc_y, mode="lines",
        line=dict(width=2, color=PALETTE["gc"]),
        name="GC% (windowed)",
        hovertemplate="Pos %{x:.0f}<br>GC %{y:.1f}%<extra></extra>"
    ))

    # PAM rug
    if pam_sites:
        fig.add_trace(go.Scatter(
            x=pam_sites, y=[-2] * len(pam_sites), mode="markers",
            marker=dict(symbol="line-ns-open", size=8, color=PALETTE["pam"]),
            name="PAMs", hovertemplate="PAM at %{x:.0f}<extra></extra>"
        ))

    # gRNA start rug
    if grnas:
        starts = [pos for (_g, pos) in grnas]
        fig.add_trace(go.Scatter(
            x=starts, y=[-4] * len(starts), mode="markers",
            marker=dict(symbol="line-ns-open", size=8, color=PALETTE["grna"]),
            name="gRNA starts", hovertemplate="gRNA start %{x:.0f}<extra></extra>"
        ))

    fig.update_layout(
        title="Overview",
        height=200,
        margin=dict(l=40, r=20, t=40, b=20),
        showlegend=True,
        xaxis=dict(title="Position (bp)", zeroline=False),
        yaxis=dict(title="GC%", range=[-5, 100], zeroline=False),
    )
    return fig

# ---------- Detailed multi-track map (2D) ----------
def plot_detail_map(sequence, pam_sites, grnas, start_pos=0, end_pos=None, off_targets=None):
    if end_pos is None:
        end_pos = len(sequence)
    off_targets = off_targets or []

    # Filter to window
    pam_sites = [p for p in pam_sites if start_pos <= p < end_pos]
    grnas = [(g, pos) for g, pos in grnas if start_pos <= pos < end_pos]
    off_targets = [ot for ot in off_targets if start_pos <= ot.get("start", -1) < end_pos]

    fig = go.Figure()

    # Y lanes
    y_dna = 0.0
    y_pam = 1.0
    y_grna = -1.0
    y_off = 2.0

    # DNA baseline
    fig.add_trace(go.Scatter(
        x=[start_pos, end_pos], y=[y_dna, y_dna],
        mode="lines", line=dict(color=PALETTE["dna"], width=3),
        name="DNA", hoverinfo="skip"
    ))

    # PAM short ticks
    for p in pam_sites:
        fig.add_trace(go.Scatter(
            x=[p, p], y=[y_pam - 0.2, y_pam + 0.2],
            mode="lines", line=dict(color=PALETTE["pam"], width=3),
            name="PAM", showlegend=False,
            hovertemplate=f"PAM at {p}<br>Seq: {sequence[p:p+3]}<extra></extra>"
        ))

    # gRNA 20-bp bars + direction caret
    for idx, (guide, pos) in enumerate(grnas, start=1):
        x0, x1 = pos, pos + 20
        gc = round((guide.count('G') + guide.count('C')) / 20 * 100, 1)
        fig.add_trace(go.Scatter(
            x=[x0, x1], y=[y_grna, y_grna],
            mode="lines", line=dict(color=PALETTE["grna"], width=8),
            name="gRNA", showlegend=False,
            hovertemplate=f"gRNA #{idx}<br>Pos: {x0}-{x1}<br>GC: {gc}%<br>Seq: {guide}<extra></extra>"
        ))
        fig.add_trace(go.Scatter(  # 5' caret
            x=[x0], y=[y_grna],
            mode="markers",
            marker=dict(symbol="triangle-right", size=9, color=PALETTE["grna"]),
            hoverinfo="skip", showlegend=False
        ))

    # Optional off-target dashed segments
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
        height=420,
        margin=dict(l=40, r=20, t=40, b=30),
        xaxis=dict(range=[start_pos, end_pos], title="Position (bp)"),
        yaxis=dict(visible=False),
        legend=dict(orientation="h", y=1.08),
        shapes=[
            dict(type="line", x0=start_pos, x1=end_pos, y0=y_pam, y1=y_pam, line=dict(color="rgba(0,0,0,0.05)")),
            dict(type="line", x0=start_pos, x1=end_pos, y0=y_grna, y1=y_grna, line=dict(color="rgba(0,0,0,0.05)")),
            dict(type="line", x0=start_pos, x1=end_pos, y0=y_off, y1=y_off, line=dict(color="rgba(0,0,0,0.05)")),
        ]
    )
    return fig

# ---------- Windowed 3D double helix (max detail) ----------
def plot_double_helix_windowed(sequence, pam_sites, grnas, start_pos=0, end_pos=None, connector_step=1):
    """
    3D double helix across the selected window:
      - PAM = 3 bp red segments
      - gRNA = 20 bp green segments
      - Base-pair connectors batched; connector_step=1 draws every connector
    """
    seq_len = len(sequence)
    if end_pos is None or end_pos > seq_len:
        end_pos = seq_len
    if start_pos < 0:
        start_pos = 0
    if start_pos >= end_pos:
        start_pos = max(0, end_pos - 1)

    # Window
    n = max(1, end_pos - start_pos)
    sub_seq = sequence[start_pos:end_pos]

    # Helix geometry (~10 bp/turn)
    turns = n / 10.0
    theta = np.linspace(0, turns * 2 * np.pi, n)
    r = 1.0
    x1, y1 = r * np.cos(theta), r * np.sin(theta)
    x2, y2 = r * np.cos(theta + np.pi), r * np.sin(theta + np.pi)
    z = np.linspace(0, turns, n)

    fig = go.Figure()

    # Strands
    fig.add_trace(go.Scatter3d(x=x1, y=y1, z=z, mode="lines",
                               line=dict(color="blue", width=4), name="Strand A"))
    fig.add_trace(go.Scatter3d(x=x2, y=y2, z=z, mode="lines",
                               line=dict(color="orange", width=4), name="Strand B"))

    # Connectors (batched)
    cx, cy, cz = [], [], []
    step = max(1, int(connector_step))
    for i in range(0, n, step):
        cx += [x1[i], x2[i], None]
        cy += [y1[i], y2[i], None]
        cz += [z[i],  z[i],  None]
    fig.add_trace(go.Scatter3d(
        x=cx, y=cy, z=cz, mode="lines",
        line=dict(color="gray", width=2),
        showlegend=False
    ))

    # Helper to add a colored segment on strand A between indices i0..i1
    def add_segment(i0, i1, color, name, hover):
        i0 = max(0, min(n - 1, i0))
        i1 = max(0, min(n - 1, i1))
        if i1 < i0:
            i0, i1 = i1, i0
        fig.add_trace(go.Scatter3d(
            x=x1[i0:i1 + 1], y=y1[i0:i1 + 1], z=z[i0:i1 + 1],
            mode="lines", line=dict(color=color, width=8),
            name=name, hovertext=hover, hoverinfo="text",
            showlegend=False
        ))

    # PAM segments (3 bp)
    for pam_abs in pam_sites:
        rel = pam_abs - start_pos
        if 0 <= rel < n:
            i0 = rel
            i1 = min(n - 1, rel + 2)
            pam_seq = sub_seq[i0:i1 + 1] if i1 + 1 <= len(sub_seq) else ""
            add_segment(i0, i1, "red", "PAM", f"PAM {pam_seq} at {pam_abs}")

    # gRNA segments (20 bp)
    for guide, gpos_abs in grnas:
        rel = gpos_abs - start_pos
        if 0 <= rel < n:
            i0 = rel
            i1 = min(n - 1, rel + 19)
            hover = f"gRNA (20nt) at {gpos_abs}<br>Seq: {guide}"
            add_segment(i0, i1, "green", "gRNA", hover)

    fig.update_layout(
        title=f"3D Double Helix (bp {start_pos}–{end_pos})",
        scene=dict(
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            zaxis=dict(title="Helix axis")
        ),
        showlegend=True,
        height=750,
        margin=dict(l=0, r=0, t=60, b=0)
    )
    return fig

