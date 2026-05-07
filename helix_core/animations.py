# animations.py
from __future__ import annotations
import numpy as np
import plotly.graph_objects as go

# ---------- 1) Animated B-DNA build (frames add bp one-by-one) ----------
def animate_bdna_build(n_bp: int, twist_deg: float = 36.0, rise_A: float = 3.32,
                       radius_A: float = 10.0, strand_thickness=2.2, rung_thickness=1.2):
    n_bp = max(2, int(n_bp))
    ang_all = np.deg2rad(np.arange(n_bp) * twist_deg)
    z_all   = np.arange(n_bp) * rise_A
    x1_all, y1_all = radius_A * np.cos(ang_all), radius_A * np.sin(ang_all)
    x2_all, y2_all = radius_A * np.cos(ang_all + np.pi), radius_A * np.sin(ang_all + np.pi)

    # base figure
    fig = go.Figure()
    # add empty three traces we will update: backbone A, backbone B, and a dummy rung (not used)
    fig.add_trace(go.Scatter3d(x=[], y=[], z=[], mode="lines", line=dict(width=strand_thickness), name="A"))
    fig.add_trace(go.Scatter3d(x=[], y=[], z=[], mode="lines", line=dict(width=strand_thickness), name="B"))

    frames = []
    for k in range(2, n_bp+1):
        x1, y1, z = x1_all[:k], y1_all[:k], z_all[:k]
        x2, y2    = x2_all[:k], y2_all[:k]
        # rungs rendered as one multi-segment via separate trace list (one per rung) to avoid hundreds of traces:
        rungs_x = []; rungs_y = []; rungs_z = []
        for i in range(k):
            rungs_x += [x1[i], x2[i], None]
            rungs_y += [y1[i], y2[i], None]
            rungs_z += [z[i],  z[i],  None]
        frames.append(go.Frame(
            data=[
                go.Scatter3d(x=x1, y=y1, z=z),
                go.Scatter3d(x=x2, y=y2, z=z),
                go.Scatter3d(x=rungs_x, y=rungs_y, z=rungs_z, mode="lines",
                             line=dict(width=rung_thickness), showlegend=False)
            ],
            name=str(k)
        ))

    fig.frames = frames
    fig.update_scenes(aspectmode="data")
    fig.update_layout(
        height=640, margin=dict(l=0,r=0,t=10,b=0),
        scene=dict(xaxis=dict(visible=False), yaxis=dict(visible=False), zaxis=dict(visible=False)),
        updatemenus=[{
            "type":"buttons", "showactive":True,
            "buttons":[
                {"label":"▶ Build", "method":"animate",
                 "args":[None, {"frame":{"duration":60,"redraw":True}, "fromcurrent":True, "transition":{"duration":0}}]},
                {"label":"⏹ Stop", "method":"animate", "args":[[None], {"mode":"immediate"}]}
            ]
        }]
    )
    # set initial data (first frame)
    if frames:
        fig.update(data=frames[0].data)
    return fig


# ---------- 2) Animated PAM scanner (moving spotlight) ----------
def animate_pam_scan(seq_len: int, pam_positions: list[int], start: int, end: int, steps: int = 40):
    start, end = int(start), int(end)
    x = np.arange(start, end)
    y = np.zeros_like(x)

    fig = go.Figure()
    # PAM dots
    inwin = [p for p in pam_positions if start <= p < end]
    fig.add_trace(go.Scatter(x=inwin, y=[0.5]*len(inwin), mode="markers", name="PAMs",
                             marker=dict(size=8)))
    # spotlight as semi-transparent rectangle updated in frames
    width = max(10, (end-start)//8)
    frames = []
    for i in range(steps):
        cx = int(np.linspace(start, end, steps)[i])
        x0, x1 = cx - width//2, cx + width//2
        frames.append(go.Frame(layout=go.Layout(shapes=[dict(
            type="rect", xref="x", yref="paper",
            x0=x0, x1=x1, y0=0, y1=1,
            line=dict(width=0), fillcolor="rgba(255,200,0,0.15)"
        )])))
    fig.frames = frames
    fig.update_layout(
        xaxis=dict(range=[start, end], title="bp"), yaxis=dict(visible=False, range=[0,1]),
        height=160, margin=dict(l=10,r=10,t=10,b=20),
        updatemenus=[{
            "type":"buttons","showactive":True,
            "buttons":[{"label":"▶ Scan","method":"animate",
                        "args":[None, {"frame":{"duration":80}, "fromcurrent":True, "transition":{"duration":0}}]}]
        }]
    )
    # initial shape
    if frames:
        fig.update_layout(shapes=frames[0].layout.shapes)
    return fig


# ---------- 3) Animated base-editor window across a protospacer ----------
def animate_base_editor_window(guide_len: int, win_a: int, win_b: int):
    x = np.arange(1, guide_len+1)
    fig = go.Figure(go.Scatter(x=x, y=[1]*len(x), mode="markers+lines", name="protospacer",
                               marker=dict(size=6)))
    frames = []
    for pos in range(1, guide_len+1):
        a = max(1, pos - (win_b - win_a))
        b = min(guide_len, a + (win_b - win_a))
        frames.append(go.Frame(layout=go.Layout(shapes=[dict(
            type="rect", xref="x", yref="y",
            x0=a, x1=b, y0=0.8, y1=1.2,
            line=dict(color="rgba(220,20,60,0.7)", width=2),
            fillcolor="rgba(220,20,60,0.15)"
        )])))
    fig.frames = frames
    fig.update_layout(
        xaxis=dict(range=[0, guide_len+1], title="Protospacer index (1-based)"),
        yaxis=dict(visible=False, range=[0.6,1.4]),
        height=180, margin=dict(l=10,r=10,t=10,b=35),
        updatemenus=[{
            "type":"buttons","showactive":True,
            "buttons":[{"label":"▶ Sweep","method":"animate",
                        "args":[None, {"frame":{"duration":90},"fromcurrent":True,"transition":{"duration":0}}]}]
        }]
    )
    if frames:
        fig.update_layout(shapes=frames[0].layout.shapes)
    return fig


# ---------- 4) Animated gel run (bands migrate down) ----------
def animate_gel_run(frag_sizes: list[int], duration_ms: int = 2000, frames_n: int = 30, lane_width=150, height=500):
    fs = np.array(sorted([max(1, int(x)) for x in frag_sizes], reverse=True), dtype=float)
    # y target positions based on log-size rule
    y_target = 30 + (height - 60) * (np.log(fs.max()) - np.log(fs)) / (np.log(fs.max()) - np.log(50) + 1e-9)

    fig = go.Figure()
    # lane
    fig.add_shape(type="rect", x0=0, x1=lane_width, y0=0, y1=height, line=dict(width=0), fillcolor="rgba(230,230,230,0.6)")
    # bands as scatter lines (each band uses a rectangle via line width; simpler to animate centroids)
    xs = [ [5, lane_width-5, None] for _ in fs ]
    ys0 = np.linspace(40, 60, len(fs))  # initial near the wells
    data = []
    for y in ys0:
        data.append(go.Scatter(x=[5, lane_width-5, None], y=[y, y, None], mode="lines",
                               line=dict(width=4, color="black"), showlegend=False))
    fig.data = tuple(data)

    frames = []
    for t in range(frames_n):
        alpha = (t+1)/frames_n
        ys = ys0 + alpha*(y_target - ys0)
        frames.append(go.Frame(data=[
            go.Scatter(x=[5, lane_width-5, None], y=[float(y), float(y), None]) for y in ys
        ]))
    fig.frames = frames

    fig.update_xaxes(visible=False, range=[0, lane_width])
    fig.update_yaxes(visible=False, range=[height, 0])
    fig.update_layout(
        height=height, width=lane_width+20, margin=dict(l=0,r=0,t=10,b=0),
        paper_bgcolor="white", plot_bgcolor="white",
        updatemenus=[{"type":"buttons","showactive":False,
                      "buttons":[{"label":"▶ Run gel","method":"animate",
                                  "args":[None, {"frame":{"duration":duration_ms/frames_n},"fromcurrent":True}]}]}]
    )
    return fig
