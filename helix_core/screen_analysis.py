# screen_analysis.py
from __future__ import annotations
from typing import Dict, List, Tuple
import numpy as np
import pandas as pd
import math
import plotly.graph_objects as go


def _mad(x: np.ndarray) -> float:
    med = np.nanmedian(x)
    return 1.4826 * np.nanmedian(np.abs(x - med))


def normalize_counts(counts: pd.DataFrame, pseudocount: float = 1.0) -> pd.DataFrame:
    """Library-size normalize to CPM-like scale; return log2(CPM+pseudo)."""
    csum = counts.sum(axis=0).replace(0, np.nan)
    norm = counts.div(csum, axis=1) * 1e6
    return np.log2(norm + pseudocount)


def log2fc(lnorm: pd.DataFrame, treat_cols: List[str], ctrl_cols: List[str]) -> pd.Series:
    t = lnorm[treat_cols].mean(axis=1)
    c = lnorm[ctrl_cols].mean(axis=1)
    return t - c


def guide_level_table(
    counts: pd.DataFrame,
    treat_cols: List[str],
    ctrl_cols: List[str],
    mapping: pd.DataFrame | None = None
) -> pd.DataFrame:
    """
    counts: rows=sgRNA (index), columns=samples
    mapping (optional): columns ['sgRNA','gene'] to attach gene info
    """
    lnorm = normalize_counts(counts)
    lfc = log2fc(lnorm, treat_cols, ctrl_cols)
    out = pd.DataFrame({
        "sgRNA": counts.index,
        "log2FC": lfc.values
    }).set_index("sgRNA")

    if mapping is not None:
        m = mapping.set_index("sgRNA")
        out = out.join(m, how="left")

    return out.reset_index()


def gene_level_table_guidemedian(guide_table: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregates by median log2FC per gene; computes robust z-score and normal p/FDR (approx).
    Expects columns: ['sgRNA','gene','log2FC']
    """
    df = guide_table.dropna(subset=["gene"]).copy()
    G = df.groupby("gene")["log2FC"].median().rename("gene_median_LFC")
    med_all = df["log2FC"].median()
    mad_all = _mad(df["log2FC"].values)
    if mad_all <= 1e-9:
        mad_all = 0.3  # fallback small spread

    z = (G - med_all) / mad_all
    # normal p two-sided
    p = 2.0 * 0.5 * (1.0 - erf_abs(z) )  # ≈2*(1-Φ(|z|))
    res = pd.DataFrame({"gene": G.index, "median_log2FC": G.values, "z": z.values, "p": p})
    # BH-FDR
    res["FDR"] = bh_fdr(res["p"].values)
    return res.sort_values(["FDR", "median_log2FC"]).reset_index(drop=True)


def erf_abs(z: np.ndarray | pd.Series) -> np.ndarray:
    # approximate Φ using erf: Φ(z)=0.5[1+erf(z/√2)]
    zz = np.abs(np.asarray(z, dtype=float)) / math.sqrt(2.0)
    # use a quick polynomial approximation to erf for speed
    # Abramowitz-Stegun 7.1.26
    t = 1.0/(1.0 + 0.5*zz)
    # erf approx on |z|
    tau = t * np.exp(-zz*zz - 1.26551223 + t*(1.00002368 + t*(0.37409196 +
           t*(0.09678418 + t*(-0.18628806 + t*(0.27886807 +
           t*(-1.13520398 + t*(1.48851587 + t*(-0.82215223 + t*0.17087277)))))))))
    erf_abs_val = 1.0 - tau
    return erf_abs_val


def bh_fdr(pvals: np.ndarray) -> np.ndarray:
    p = np.asarray(pvals, dtype=float)
    n = len(p)
    order = np.argsort(p)
    ranked = p[order]
    q = ranked * n / (np.arange(n) + 1)
    # enforce monotonicity
    for i in range(n-2, -1, -1):
        q[i] = min(q[i], q[i+1])
    out = np.empty_like(q)
    out[order] = np.minimum(q, 1.0)
    return out


# ---------- Tiny plot helpers ----------

def plot_volcano(guide_or_gene_df: pd.DataFrame, lfc_col: str, p_col: str, title: str = "Volcano"):
    x = guide_or_gene_df[lfc_col].values
    p = np.clip(guide_or_gene_df[p_col].values, 1e-300, 1.0)
    y = -np.log10(p)
    fig = go.Figure(go.Scattergl(x=x, y=y, mode="markers"))
    fig.update_layout(
        title=title,
        xaxis_title="log2 fold-change",
        yaxis_title="-log10 p",
        height=420, margin=dict(l=10, r=10, t=40, b=10)
    )
    return fig

def plot_top_genes(res: pd.DataFrame, k: int = 20, up: bool = True):
    df = res.sort_values("median_log2FC", ascending=not up).head(k)
    fig = go.Figure(go.Bar(x=df["median_log2FC"][::-1], y=df["gene"][::-1], orientation="h"))
    fig.update_layout(
        title=("Top enriched" if up else "Top depleted"),
        height=480, margin=dict(l=10, r=10, t=40, b=10),
        xaxis_title="median log2FC"
    )
    return fig
