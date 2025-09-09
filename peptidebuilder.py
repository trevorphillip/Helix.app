# peptide_builder.py
# Robust, version-tolerant peptide builders for PeptideBuilder variants.
# - build_peptide_pdb(seq, conformation="helix"/"beta"/"coil", jitter_deg=...)
# - build_peptide_pdb_segmented(seq, segments=[(start,end,kind)], ...)
#
# Works with packages that expose:
#   - PeptideBuilder.Geometry.Geometry  (newer fork)
#   - PeptideBuilder.geometry(...)      (your version)
#   - PeptideBuilder.make_structure     (fallback)
#
# Requires: biopython

from __future__ import annotations

import io, random
from typing import List, Optional, Tuple, Literal

from Bio.PDB import PDBIO
import PeptideBuilder as PB

# ---- Detect available APIs ----
_HAS_CLASS_GEOMETRY = False
_HAS_FACTORY_GEOMETRY = False
_HAS_MAKE_STRUCTURE_FROM_GEOS = hasattr(PB, "make_structure_from_geos")
_HAS_MAKE_STRUCTURE = hasattr(PB, "make_structure")

# Try to import class-based Geometry
try:
    import PeptideBuilder.Geometry as _Gmod
    if hasattr(_Gmod, "Geometry"):
        _GeometryClass = _Gmod.Geometry  # not present in your install
        _HAS_CLASS_GEOMETRY = True
    # Your install: module has 'geometry' function & 'Geo' class — use factory path below
except Exception:
    _Gmod = None

# Try to resolve a geometry factory function
# Some builds export it as PB.geometry, others as PeptideBuilder.Geometry.geometry
_geometry_factory = None
if hasattr(PB, "geometry"):
    _geometry_factory = PB.geometry
    _HAS_FACTORY_GEOMETRY = True
elif _Gmod is not None and hasattr(_Gmod, "geometry"):
    _geometry_factory = _Gmod.geometry
    _HAS_FACTORY_GEOMETRY = True

# ---- Educational presets ----
PHI_PSI = {
    "helix": (-57.0, -47.0),
    "beta":  (-139.0, 135.0),
    "coil":  (-75.0, 145.0),
}
RES_RULES = {
    "P": {"phi": -65.0, "psi": 145.0, "extra_jitter": 6.0},
    "G": {"phi": -75.0, "psi": 155.0, "extra_jitter": 8.0},
}
AA20 = set("ACDEFGHIKLMNPQRSTVWY")

def _phi_psi_for_res(aa: str, base_phi: float, base_psi: float, jitter_deg: float) -> Tuple[float, float]:
    r = RES_RULES.get(aa.upper(), {})
    j = jitter_deg + r.get("extra_jitter", 0.0)
    phi = r.get("phi", base_phi) + random.uniform(-j, j)
    psi = r.get("psi", base_psi) + random.uniform(-j, j)
    return phi, psi

def _make_geo(aa: str, phi: float, psi: float, omega: float):
    """
    Create a per-residue 'geometry' object compatible with the installed PeptideBuilder.
    """
    if _HAS_CLASS_GEOMETRY:
        g = _GeometryClass(aa)
    elif _HAS_FACTORY_GEOMETRY and callable(_geometry_factory):
        # Your environment will hit this path
        g = _geometry_factory(aa)
    else:
        g = None  # will trigger fallback
    if g is not None:
        # Set dihedrals if attributes exist
        if hasattr(g, "phi"): g.phi = phi
        if hasattr(g, "psi_im1"): g.psi_im1 = psi
        if hasattr(g, "omega"): g.omega = omega
    return g

def _structure_from_geos(geos: List[object]):
    """
    Build a Structure from a list of geometry objects, using whatever API is available.
    """
    if _HAS_MAKE_STRUCTURE_FROM_GEOS:
        return PB.make_structure_from_geos(geos)
    # manual path
    if not geos:
        raise ValueError("No geometry objects provided.")
    # initialize first residue
    structure = PB.initialize_res(geos[0])
    # add the rest
    add_fn = getattr(PB, "add_residue_from_geo", None) or getattr(PB, "add_residue", None)
    if add_fn is None:
        raise RuntimeError("PeptideBuilder has neither add_residue_from_geo nor add_residue.")
    for g in geos[1:]:
        add_fn(structure, g)
    return structure

def _dump_pdb(structure) -> str:
    buf = io.StringIO()
    io_obj = PDBIO()
    io_obj.set_structure(structure)
    io_obj.save(buf)
    s = buf.getvalue()
    # ensure single END
    return s if s.rstrip().endswith("END") else (s + "END\n")

def build_peptide_pdb(
    seq: str,
    conformation: Literal["helix", "beta", "coil"] = "helix",
    omega: float = 180.0,
    jitter_deg: float = 3.0,
    seed: Optional[int] = None,
    add_header: bool = True,
) -> str:
    """
    Build an idealized peptide with a uniform backbone conformation.
    Tries (1) class/factory + make_structure_from_geos; else (2) fallback make_structure.
    """
    if seed is not None:
        random.seed(seed)

    seq = (seq or "").strip().upper()
    if not seq or any(ch not in AA20 for ch in seq):
        raise ValueError("Sequence must be standard 20 AAs (one-letter).")

    base_phi, base_psi = PHI_PSI[conformation]

    if _HAS_CLASS_GEOMETRY or _HAS_FACTORY_GEOMETRY:
        geos = []
        # first residue
        phi0, psi0 = _phi_psi_for_res(seq[0], base_phi, base_psi, jitter_deg)
        g0 = _make_geo(seq[0], phi0, psi0, omega)
        if g0 is None:
            # fallback straight away
            if _HAS_MAKE_STRUCTURE:
                s = PB.make_structure(seq)
                out = _dump_pdb(s)
                return (f"HEADER    IDEALIZED {conformation.upper():<6} PEPTIDE (EDU)\n" if add_header else "") + out
            raise RuntimeError("Cannot create geometry object with this PeptideBuilder build.")
        geos.append(g0)
        # remaining residues
        for aa in seq[1:]:
            phi, psi = _phi_psi_for_res(aa, base_phi, base_psi, jitter_deg)
            geos.append(_make_geo(aa, phi, psi, omega))
        structure = _structure_from_geos(geos)
        out = _dump_pdb(structure)
        header = f"HEADER    IDEALIZED {conformation.upper():<6} PEPTIDE (EDU)\n" if add_header else ""
        return header + out

    # Last resort: simple builder (angles may be library defaults)
    if _HAS_MAKE_STRUCTURE:
        structure = PB.make_structure(seq)
        out = _dump_pdb(structure)
        header = f"HEADER    IDEALIZED {conformation.upper():<6} PEPTIDE (EDU) [FALLBACK]\n" if add_header else ""
        return header + out

    raise RuntimeError("No compatible PeptideBuilder API found.")

def build_peptide_pdb_segmented(
    seq: str,
    segments: List[Tuple[int, int, Literal["helix", "beta", "coil"]]],
    omega: float = 180.0,
    jitter_deg: float = 3.0,
    seed: Optional[int] = None,
    add_header: bool = True,
) -> str:
    """
    Build an idealized peptide with per-segment conformations.
    Falls back to build_peptide_pdb if segment APIs are missing.
    """
    if seed is not None:
        random.seed(seed)

    seq = (seq or "").strip().upper()
    if not seq or any(ch not in AA20 for ch in seq):
        raise ValueError("Sequence must be standard 20 AAs (one-letter).")

    n = len(seq)
    kinds = ["coil"] * n
    for s, e, k in segments:
        if k not in PHI_PSI:
            raise ValueError(f"Unknown conformation '{k}'.")
        s = max(1, int(s)); e = min(n, int(e))
        for i in range(s - 1, e):
            kinds[i] = k

    # If we can’t create per-residue geometry, fall back to uniform
    if not (_HAS_CLASS_GEOMETRY or _HAS_FACTORY_GEOMETRY):
        # choose the first segment kind or default
        first_kind = kinds[0] if kinds else "coil"
        return build_peptide_pdb(seq, conformation=first_kind, omega=omega, jitter_deg=jitter_deg, seed=seed, add_header=add_header)

    geos = []
    # first residue
    base_phi, base_psi = PHI_PSI[kinds[0]]
    phi0, psi0 = _phi_psi_for_res(seq[0], base_phi, base_psi, jitter_deg)
    geos.append(_make_geo(seq[0], phi0, psi0, omega))
    # the rest
    for i in range(1, n):
        base_phi, base_psi = PHI_PSI[kinds[i]]
        phi, psi = _phi_psi_for_res(seq[i], base_phi, base_psi, jitter_deg)
        geos.append(_make_geo(seq[i], phi, psi, omega))

    structure = _structure_from_geos(geos)
    out = _dump_pdb(structure)
    header = "HEADER    IDEALIZED SEGMENTED PEPTIDE (EDU)\n" if add_header else ""
    return header + out
