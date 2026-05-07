# mobile_app/utils/crispr_utils.py
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple, Optional

DNA = set("ACGT")

def sanitize_dna(seq: str) -> str:
    if not seq:
        return ""
    seq = seq.upper()
    return "".join(ch for ch in seq if ch in DNA)

def reverse_complement(seq: str) -> str:
    comp = {"A":"T","C":"G","G":"C","T":"A"}
    s = sanitize_dna(seq)
    return "".join(comp[b] for b in reversed(s))

@dataclass
class GuideHit:
    strand: str              # "+" or "-"
    pam_start: int           # 0-based
    guide_start: int         # 0-based (start of protospacer on forward reference coords)
    guide: str               # DNA letters (A/C/G/T)
    pam: str                 # DNA letters (A/C/G/T)

def _match_iupac(base: str, pat: str) -> bool:
    # IUPAC codes needed for common PAMs
    table = {
        "A": {"A"}, "C": {"C"}, "G": {"G"}, "T": {"T"},
        "N": {"A","C","G","T"},
        "R": {"A","G"},
        "Y": {"C","T"},
        "W": {"A","T"},
        "S": {"C","G"},
        "K": {"G","T"},
        "M": {"A","C"},
        # extend later if you want (B, D, H, V)
    }
    base = base.upper()
    pat = pat.upper()
    return base in table.get(pat, {pat})

def _pam_matches(seq: str, i: int, pam_pat: str) -> bool:
    if i < 0 or i + len(pam_pat) > len(seq):
        return False
    for j, p in enumerate(pam_pat):
        if not _match_iupac(seq[i+j], p):
            return False
    return True

def find_guides(
    genome: str,
    *,
    pam: str = "NGG",
    pam_side: str = "3prime",          # "3prime" or "5prime"
    guide_len: int = 20,
    scan_rc: bool = True,
) -> List[GuideHit]:
    """
    Returns guides in forward reference coordinates.
    For reverse strand hits, guide/pam are reported as DNA in 5'->3' guide orientation,
    while positions map onto the forward reference index.
    """
    s = sanitize_dna(genome)
    hits: List[GuideHit] = []

    # ---- forward strand scan
    # ---- reverse strand scan
    rc = reverse_complement(s)
    L = len(s)

    for i in range(0, len(rc) - len(pam) + 1):
        if not _pam_matches(rc, i, pam):
            continue

        if pam_side == "3prime":
            guide_start_rc = i - guide_len
            if guide_start_rc < 0:
                continue

            guide_rc = rc[guide_start_rc:guide_start_rc + guide_len]
            pam_rc = rc[i:i + len(pam)]

            # Map rc index to forward reference
            # rc[i:i+pam_len] corresponds to forward [L - i - pam_len : L - i]
            pam_start_fwd = L - i - len(pam)

            # For 3' PAM systems (Cas9): on forward coords for "-" hits, protospacer is downstream of PAM
            guide_start_fwd = pam_start_fwd + len(pam)

            # ✅ bounds check (prevents negative/overflow slicing later)
            if guide_start_fwd < 0 or guide_start_fwd + guide_len > L:
                continue

            hits.append(GuideHit("-", pam_start_fwd, guide_start_fwd, guide_rc, pam_rc))

        else:
            # 5prime PAM systems (Cas12a): on forward coords for "-" hits, protospacer is upstream of PAM
            guide_start_rc = i + len(pam)
            if guide_start_rc + guide_len > len(rc):
                continue

            guide_rc = rc[guide_start_rc:guide_start_rc + guide_len]
            pam_rc = rc[i:i + len(pam)]

            pam_start_fwd = L - i - len(pam)
            guide_start_fwd = pam_start_fwd - guide_len

            # ✅ bounds check
            if guide_start_fwd < 0 or guide_start_fwd + guide_len > L:
                continue

            hits.append(GuideHit("-", pam_start_fwd, guide_start_fwd, guide_rc, pam_rc))

    return hits

def gc_percent(seq: str) -> float:
    s = sanitize_dna(seq)
    if not s:
        return 0.0
    return 100.0 * (s.count("G") + s.count("C")) / len(s)


ENZYMES = {
    "SpCas9 (NGG)":   {"pam":"NGG",  "pam_side":"3prime", "guide_len":20},
    "SaCas9 (NNGRRT)":{"pam":"NNGRRT","pam_side":"3prime","guide_len":21},
    "Cas12a (TTTV)":  {"pam":"TTTV", "pam_side":"5prime", "guide_len":20},  # simplified
}
