
# Global Plotly layout (clean, dark, consistent)
PLOTLY_TEMPLATE = dict(
    layout=dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Segoe UI, system-ui, sans-serif", size=14, color="#E5E7EB"),
        legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor="rgba(0,0,0,0)", orientation="h", y=1.08),
        xaxis=dict(gridcolor="rgba(255,255,255,0.06)", zeroline=False),
        yaxis=dict(gridcolor="rgba(255,255,255,0.06)", zeroline=False),
        margin=dict(l=40, r=20, t=48, b=36),
        hoverlabel=dict(
            bgcolor="rgba(18,24,38,0.95)",
            bordercolor="rgba(255,255,255,0.1)",
            font=dict(color="#E5E7EB")
        ),
    )
)
