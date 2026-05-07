## structure_viewer.py
# Lightweight protein viewer utilities for py3Dmol
# - Single model: show_pdb(...)
# - Multi model:  show_pdbs(..., mode="overlay" | "grid")
# Enhancements: cartoon+sticks style, optional CA superposition, chain filter, residue highlighting
from __future__ import annotations

from typing import Iterable, List, Sequence, Tuple, Union, Optional
import io
import py3Dmol

# Optional: Bio.PDB for superposition (safe fallback if missing)
try:
    from Bio.PDB import PDBParser, PDBIO, Superimposer
    from Bio.PDB.Polypeptide import is_aa
    _HAS_BIOPDB = True
except Exception:
    _HAS_BIOPDB = False

# Tiny example structure (1CRN – crambin, 46 aa)
PDB_1CRN = """\
HEADER    PLANT SEED PROTEIN                      01-AUG-84   1CRN
ATOM      1  N   THR A   1      6.204  13.207   2.136  1.00  0.00           N
ATOM      2  CA  THR A   1      5.621  11.890   1.776  1.00  0.00           C
ATOM      3  C   THR A   1      4.118  12.021   1.478  1.00  0.00           C
ATOM      4  O   THR A   1      3.684  13.111   1.047  1.00  0.00           O
ATOM      5  CB  THR A   1      6.334  11.273   0.539  1.00  0.00           C
TER
END
"""

# ---------------- Public API ---------------- #

def show_pdb(
    pdb_text: str,                             # <-- non-default FIRST (fixes the SyntaxError)
    style: str = "stick",                      # "cartoon", "stick", "line", "surface", "cartoon+sticks"
    color_scheme: str = "chain",               # "chain","spectrum","ssPyMol","resi","element","#rrggbb"
    color: Optional[str] = None,               # backward-compatible alias for color_scheme
    dark_bg: bool = True,
    show_ligands: bool = True,
    stick_radius: float = 0.25,
    width: int = 800,
    height: int = 600,
    chains: Optional[Sequence[str]] = None,    # e.g., ["A","B"]
    highlight: Optional[Sequence[Tuple[str, Union[int, Tuple[int,int]]]]] = None,
    surface_ms_opacity: float | None = None,   # optional glossy molecular surface overlay
):
    """
    Render a single structure and return a py3Dmol view.
    """
    if color is not None:
        color_scheme = color

    v = py3Dmol.view(width=width, height=height)
    v.addModel(pdb_text, "pdb")
    v.setBackgroundColor("0x0d1117" if dark_bg else "0xffffff")

    _apply_style(v, selector=_sel_chains(chains), style=style,
                 color_scheme=color_scheme, stick_radius=stick_radius)

    if show_ligands:
        _highlight_ligands(v)

    if highlight:
        _apply_highlights(v, highlight)

    # Soft molecular surface overlay for realism
    if surface_ms_opacity is not None and surface_ms_opacity > 0:
        try:
            v.addSurface(py3Dmol.MS, {"opacity": float(surface_ms_opacity)}, {})
        except Exception:
            pass

    v.zoomTo()
    return v



# --- Residue painters (hydropathy / charge) ---

_THREE_TO_ONE = {
    "ALA":"A","ARG":"R","ASN":"N","ASP":"D","CYS":"C",
    "GLN":"Q","GLU":"E","GLY":"G","HIS":"H","ILE":"I",
    "LEU":"L","LYS":"K","MET":"M","PHE":"F","PRO":"P",
    "SER":"S","THR":"T","TRP":"W","TYR":"Y","VAL":"V",
}

# Kyte–Doolittle hydropathy
_KD = {"I":4.5,"V":4.2,"L":3.8,"F":2.8,"C":2.5,"M":1.9,"A":1.8,
       "G":-0.4,"T":-0.7,"S":-0.8,"W":-0.9,"Y":-1.3,"P":-1.6,
       "H":-3.2,"E":-3.5,"Q":-3.5,"D":-3.5,"N":-3.5,"K":-3.9,"R":-4.5}

def _parse_residue_table(pdb_text: str):
    """
    Return list of residues: [(chain, resi, aa1)], taking CA records.
    """
    out = []
    seen = set()
    for line in pdb_text.splitlines():
        if not line.startswith("ATOM"):
            continue
        name = line[12:16].strip()
        if name != "CA":
            continue
        res3 = line[17:20].strip().upper()
        aa = _THREE_TO_ONE.get(res3, "X")
        chain = line[21].strip() or "A"
        try:
            resi = int(line[22:26])
        except Exception:
            continue
        key = (chain, resi)
        if key in seen:
            continue
        seen.add(key)
        out.append((chain, resi, aa))
    return out

def apply_residue_coloring(view, pdb_text: str, scheme: str = "hydropathy", stick_radius: float = 0.25):
    """
    Re-color the existing model by residue categories.
    scheme: 'hydropathy' or 'charge'
    """
    residues = _parse_residue_table(pdb_text)
    if not residues:
        return view

    if scheme.lower().startswith("hydro"):
        # 5-bin palette (blue → red)
        bins = [(-10, -2.0), (-2.0, -0.5), (-0.5, 0.5), (0.5, 2.0), (2.0, 10)]
        colors = ["#2a6fdb", "#63a3ff", "#d9d9d9", "#ffb366", "#e6452e"]
        # group resi by chain per bin
        groups = [dict() for _ in bins]
        for ch, ri, aa in residues:
            v = _KD.get(aa, 0.0)
            for k, (lo, hi) in enumerate(bins):
                if lo <= v <= hi:
                    groups[k].setdefault(ch, []).append(ri)
                    break
        for k, g in enumerate(groups):
            if not g:
                continue
            col = colors[k]
            for ch, res_list in g.items():
                sel = {"chain": ch, "resi": sorted(res_list)}
                view.addStyle(sel, {"cartoon": {"color": col}})
                view.addStyle(sel, {"stick": {"color": col, "radius": float(stick_radius)}})

    else:  # charge
        pos = set("KRH")   # treat H as basic-ish
        neg = set("DE")
        c_groups = {"pos": ("#5bc0eb", {}), "neg": ("#ff5d73", {}), "neu": ("#c7c7c7", {})}
        for ch, ri, aa in residues:
            if aa in pos:
                key = "pos"
            elif aa in neg:
                key = "neg"
            else:
                key = "neu"
            c_groups[key][1].setdefault(ch, []).append(ri)
        for key, (col, per_chain) in c_groups.items():
            for ch, res_list in per_chain.items():
                sel = {"chain": ch, "resi": sorted(res_list)}
                view.addStyle(sel, {"cartoon": {"color": col}})
                view.addStyle(sel, {"stick": {"color": col, "radius": float(stick_radius)}})
    return view

def show_pdbs(
    pdb_texts: list[str],                      # <-- non-default FIRST
    mode: str = "overlay",                     # "overlay" | "grid"
    style: str = "stick",
    color_scheme: str = "chain",
    color: str | None = None,                  # alias for color_scheme
    dark_bg: bool = True,
    show_ligands: bool = True,
    stick_radius: float = 0.25,
    chains: Optional[Sequence[str]] = None,    # limit display to these chains
    align: str = "none",                       # "none" | "ca_to_first" (if Bio.PDB installed)
    highlight_sets: Optional[List[Sequence[Tuple[str, Union[int, Tuple[int,int]]]]]] = None,
    width_overlay: int = 950,
    height_overlay: int = 650,
    cell_width: int = 320,
    cell_height: int = 300,
    surface_ms_opacity: float | None = None,   # optional glossy molecular surface overlay
):
    """
    Overlay: returns (single_view, False)
    Grid:    returns ([view, view, ...], True)
    """
    if not pdb_texts:
        raise ValueError("pdb_texts must be a non-empty list of PDB strings.")
    if color is not None:
        color_scheme = color

    # Optional superposition for overlay only
    if mode.lower().startswith("overlay") and align == "ca_to_first":
        pdb_texts = _superpose_pdb_texts(pdb_texts, chains=chains)

    if mode.lower().startswith("overlay"):
        v = py3Dmol.view(width=width_overlay, height=height_overlay)
        for i, pdb_txt in enumerate(pdb_texts, start=1):
            v.addModel(pdb_txt, "pdb")
            _apply_style(v, selector=_merge_sel({"model": i}, _sel_chains(chains)),
                         style=style, color_scheme=color_scheme, stick_radius=stick_radius)
            if highlight_sets and len(highlight_sets) >= i and highlight_sets[i-1]:
                _apply_highlights(v, highlight_sets[i-1], model_index=i)
            if surface_ms_opacity is not None and surface_ms_opacity > 0:
                try:
                    v.addSurface(py3Dmol.MS, {"opacity": float(surface_ms_opacity)}, {"model": i})
                except Exception:
                    pass
        if show_ligands:
            _highlight_ligands(v)
        v.setBackgroundColor("0x0d1117" if dark_bg else "0xffffff")
        v.zoomTo()
        return v, False

    # -------- Grid mode without createViewerGrid --------
    views: List[py3Dmol.view] = []
    for idx, pdb_txt in enumerate(pdb_texts):
        viewer = py3Dmol.view(width=cell_width, height=cell_height)
        viewer.addModel(pdb_txt, "pdb")
        _apply_style(viewer, selector=_sel_chains(chains), style=style,
                     color_scheme=color_scheme, stick_radius=stick_radius)
        if show_ligands:
            _highlight_ligands(viewer)
        if highlight_sets and len(highlight_sets) > idx and highlight_sets[idx]:
            _apply_highlights(viewer, highlight_sets[idx])
        if surface_ms_opacity is not None and surface_ms_opacity > 0:
            try:
                viewer.addSurface(py3Dmol.MS, {"opacity": float(surface_ms_opacity)}, {})
            except Exception:
                pass
        viewer.setBackgroundColor("0x0d1117" if dark_bg else "0xffffff")
        viewer.zoomTo()
        views.append(viewer)
    return views, True


def to_html(view_or_grid, height: int | None = None, scrolling: bool = False) -> str:
    """
    Return embeddable HTML for a single py3Dmol view.
    If you need to handle multiple views (grid), iterate and call to_html(v) per view.
    """
    if hasattr(view_or_grid, "_make_html"):
        return view_or_grid._make_html()
    raise TypeError(
        "to_html() expects a single py3Dmol view. "
        "For multiple views, iterate and call to_html(v) per view."
    )

# ---------------- Internals ---------------- #

def _sel_chains(chains: Optional[Sequence[str]]):
    """Return a 3Dmol selector filtering to given chains, or {} for all."""
    if not chains:
        return {}
    chains = [c.strip() for c in chains if str(c).strip()]
    if not chains:
        return {}
    return {"or": [{"chain": ch} for ch in chains]}

def _merge_sel(a: dict, b: dict) -> dict:
    """Combine two selectors with 'and' if both non-empty."""
    if not a and not b:
        return {}
    if not a:
        return b
    if not b:
        return a
    return {"and": [a, b]}

def _apply_style(view, selector, style: str, color_scheme: str, stick_radius: float):
    """
    Map our style + color settings to 3Dmol.js style payloads robustly.
    - If color_scheme is hex ('#rrggbb' or '0x...') => use 'color'
    - Else treat it as a scheme keyword ('chain','spectrum','ssPyMol','resi','element')
    """
    def _is_hex(s: str) -> bool:
        return isinstance(s, str) and (s.startswith("#") or s.startswith("0x"))

    stick_line_color = {"color": color_scheme} if _is_hex(color_scheme) else {"colorscheme": color_scheme}
    cartoon_color = {"color": color_scheme}

    sty = (style or "").lower().strip()
    if sty == "cartoon":
        view.setStyle(selector, {"cartoon": dict(cartoon_color)})
    elif sty == "stick":
        payload = {"stick": {"radius": float(stick_radius)}}
        payload["stick"].update(stick_line_color)
        view.setStyle(selector, payload)
    elif sty in ("line", "lines"):
        view.setStyle(selector, {"line": dict(stick_line_color)})
    elif sty == "surface":
        view.setStyle(selector, {"cartoon": {"opacity": 0.25}})
        view.addSurface(py3Dmol.VDW, {"opacity": 0.85}, selector)
    elif sty == "cartoon+sticks":
        view.setStyle(selector, {"cartoon": dict(cartoon_color)})
        backbone = {"or": [{"atom": "N"}, {"atom": "CA"}, {"atom": "C"}, {"atom": "O"}]}
        sidechain_sel = {"and": [selector, {"not": backbone}]}
        payload = {"stick": {"radius": float(stick_radius)}}
        payload["stick"].update(stick_line_color)
        view.setStyle(sidechain_sel, payload)
    else:
        view.setStyle(selector, {"line": dict(stick_line_color)})

def _highlight_ligands(view):
    """
    Show non-protein HET groups as sticks and hide waters.
    """
    view.addStyle({"hetflag": True, "resn": ["HOH", "WAT"]}, {"hidden": True})
    view.setStyle(
        {"hetflag": True, "invert": True, "resn": ["HOH", "WAT"]},
        {"stick": {"radius": 0.25}}
    )
    view.addSurface(
        py3Dmol.VDW, {"opacity": 0.3},
        {"hetflag": True, "invert": True, "resn": ["HOH", "WAT"]}
    )

def _apply_highlights(view, items: Sequence[Tuple[str, Union[int, Tuple[int,int]]]], model_index: Optional[int] = None):
    """
    Highlight residues by (chain, resi) or (chain, (start,end)) inclusive.
    """
    for chain, res in items:
        if isinstance(res, tuple):
            start, end = int(res[0]), int(res[1])
            sel = {"chain": chain, "resi": list(range(start, end + 1))}
        else:
            sel = {"chain": chain, "resi": int(res)}
        if model_index is not None:
            sel = _merge_sel(sel, {"model": int(model_index)})
        view.addStyle(sel, {"stick": {"radius": 0.35, "color": "#ffcc00"}})
        view.addStyle(sel, {"cartoon": {"color": "#ffcc00"}})

# ---------- Optional superposition utilities (Bio.PDB) ----------

def _superpose_pdb_texts(pdb_texts: List[str], chains: Optional[Sequence[str]] = None) -> List[str]:
    """
    Superpose all models to the first one using Cα atoms.
    Returns new list of PDB texts (if Bio.PDB available); otherwise original list.
    """
    if not _HAS_BIOPDB or len(pdb_texts) < 2:
        return pdb_texts

    parser = PDBParser(QUIET=True)
    io_obj = PDBIO()

    # Parse reference
    ref_struct = parser.get_structure("ref", io.StringIO(pdb_texts[0]))
    ref_cas = _get_ca_atoms(ref_struct, chains)

    out_texts = [pdb_texts[0]]

    for i in range(1, len(pdb_texts)):
        mob_struct = parser.get_structure(f"mob{i}", io.StringIO(pdb_texts[i]))
        mob_cas = _get_ca_atoms(mob_struct, chains)
        n = min(len(ref_cas), len(mob_cas))
        if n < 8:
            out_texts.append(pdb_texts[i])
            continue
        sup = Superimposer()
        sup.set_atoms(ref_cas[:n], mob_cas[:n])
        sup.apply(mob_struct.get_atoms())
        buf = io.StringIO()
        io_obj.set_structure(mob_struct)
        io_obj.save(buf)
        out_texts.append(buf.getvalue())
    return out_texts

def _get_ca_atoms(struct, chains: Optional[Sequence[str]] = None):
    """Collect Cα atoms, optionally filtering by chain list."""
    model = next(struct.get_models())
    cas = []
    chain_set = set(chains) if chains else None
    for ch in model.get_chains():
        if chain_set and ch.id not in chain_set:
            continue
        for res in ch.get_residues():
            if is_aa(res, standard=True) and "CA" in res:
                cas.append(res["CA"])
    return cas

