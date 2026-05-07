# screen_design.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import re
import math
import pandas as pd
import numpy as np

# Your local helpers
from crisprutils import (
    PAM_SEQUENCES, PAM_SIDE, GUIDE_LENGTHS,
    sanitize_sequence, translate_dna, reverse_complement,
    find_sites_for_enzyme
)
from offtarget import KmerIndex, find_offtargets


# ---------- Small utilities ----------

DNA = set("ACGT")

def _dna_only(s: str) -> str:
    return "".join(ch for ch in (s or "").upper() if ch in DNA)

def _gc_pct(s: str) -> float:
    s = s.upper()
    return 100.0 * (s.count("G") + s.count("C")) / max(1, len(s))

def _bad_runs(s: str, n: int = 4) -> bool:
    return re.search(r"(A{%d,}|C{%d,}|G{%d,}|T{%d,})" % (n, n, n, n), s.upper()) is not None

def _tri_nt_repeat(s: str) -> bool:
    # reject long simple repeats like (AT)n (very rough)
    return re.search(r"(?:AT|TA|AC|CA|TG|GT){4,}", s.upper()) is not None

def _score_position_for_KO(pos: int, L: int) -> float:
    # earlier in CDS is better (0..1)
    if L <= 1: return 0.5
    return 1.0 - min(1.0, pos / max(1.0, L - 1.0))

def _score_position_for_i_a(dist_to_tss: int) -> float:
    # CRISPRi/a sweet spot ~ +50..+150 bp downstream of TSS (for i) / upstream (for a)
    # Use a soft Gaussian-like bump around 100 bp
    mu, sigma = 100.0, 80.0
    return math.exp(-0.5 * ((abs(dist_to_tss) - mu) / sigma) ** 2)

def _diversity_pick(rows: List[dict], keep: int, min_sep: int = 15) -> List[dict]:
    # Greedy: take best score, then keep adding far-enough spacers
    chosen, taken_pos = [], []
    for r in rows:
        p = int(r["pos"])
        if all(abs(p - q) >= min_sep for q in taken_pos):
            chosen.append(r)
            taken_pos.append(p)
            if len(chosen) >= keep:
                break
    return chosen


# ---------- Core: enumerate + filter + score ----------

@dataclass
class DesignParams:
    enzyme: str = "SpCas9"
    mode: str = "KO"  # "KO" | "CRISPRi" | "CRISPRa"
    guides_per_gene: int = 4
    scan_reverse: bool = True
    gc_range: Tuple[float, float] = (35.0, 80.0)
    max_homopolymer: int = 4
    prefilter_offtargets: bool = True
    max_mismatches: int = 2
    seed_len: int = 8
    tss_window: Tuple[int, int] = (-300, +300)  # for CRISPRi/a (relative to TSS)
    diversity_min_sep: int = 15  # nt between chosen spacers


def enumerate_candidates_for_sequence(
    seq: str,
    enzyme: str,
    scan_reverse: bool = True
) -> List[Tuple[str, int, str, str]]:
    """
    Returns a list of (strand, pos, guide, pam) within 'seq' coordinates.
    pos is 0-based start of protospacer on the *forward* orientation of 'seq'.
    """
    seq = _dna_only(seq)
    pam = PAM_SEQUENCES[enzyme]
    side = PAM_SIDE[enzyme]
    gL = GUIDE_LENGTHS[enzyme]

    # forward
    pam_fwd, grna_fwd = find_sites_for_enzyme(seq, enzyme=enzyme)
    out = [("+", p, g, seq[p + gL : p + gL + len(pam)]) for (g, p) in grna_fwd]

    # reverse (map into forward coordinates of this subsequence)
    if scan_reverse:
        rc = reverse_complement(seq)
        pam_rc, grna_rc = find_sites_for_enzyme(rc, enzyme=enzyme)
        # position in forward sequence: reverse index
        for (g, p_rc) in grna_rc:
            # p_rc is on rc; convert to forward
            # protospacer covers [p_rc, p_rc+gL) on rc → on fwd it maps to:
            start_on_fwd = len(seq) - (p_rc + gL)
            pam_seq = seq[max(0, start_on_fwd - len(pam)) : start_on_fwd]  # PAM on 5' side for rc case
            out.append(("-", start_on_fwd, g, pam_seq))

    return out


def _passes_filters(guide: str, gc_range: Tuple[float, float], max_homo: int) -> bool:
    gc = _gc_pct(guide)
    if gc < gc_range[0] or gc > gc_range[1]:
        return False
    if _bad_runs(guide, n=max_homo):
        return False
    if _tri_nt_repeat(guide):
        return False
    return True


def _score_guide(
    strand: str,
    pos: int,
    guide: str,
    pam: str,
    L: int,
    mode: str,
    tss_pos: Optional[int] = None
) -> float:
    # GC center ~ 45–55%
    gc = _gc_pct(guide)
    gc_score = 1.0 - min(abs(gc - 50.0), 50.0)/50.0  # 0..1

    # simple PAM preference (canonical NGG best)
    pam_bonus = 1.0 if pam.upper() in ("GG", "AGG", "TGG", "CGG") or pam.upper().endswith("GG") else 0.6

    if mode == "KO":
        pos_sc = _score_position_for_KO(pos, L)
    else:
        # need distance to TSS in sequence coordinates if provided
        if tss_pos is None:
            pos_sc = 0.6
        else:
            center = pos + len(guide)//2
            dist = center - tss_pos
            pos_sc = _score_position_for_i_a(dist)

    # final weighted score (0..~3)
    return 0.5*gc_score + 1.0*pam_bonus + 1.0*pos_sc


def design_library_from_sequences(
    targets_by_gene: Dict[str, str],
    params: DesignParams,
    genome_for_offtargets: Optional[str] = None,
    tss_by_gene: Optional[Dict[str, int]] = None,
) -> pd.DataFrame:
    """
    targets_by_gene: {gene: DNA subsequence} — e.g., CDS or ±region around TSS.
    tss_by_gene: optional {gene: tss_index_in_sequence} for CRISPRi/a scoring.
    genome_for_offtargets: optional large DNA string to index (if None, off-target step is skipped).
    """
    rows = []
    idx = None
    if params.prefilter_offtargets and genome_for_offtargets:
        idx = KmerIndex(genome_for_offtargets, k=params.seed_len)

    for gene, raw in targets_by_gene.items():
        seq = _dna_only(raw)
        if not seq:
            continue
        cands = enumerate_candidates_for_sequence(seq, params.enzyme, params.scan_reverse)

        # filter + score
        L = len(seq)
        tss_here = None
        if params.mode.lower().startswith("crispri") or params.mode.lower().startswith("crispra"):
            tss_here = (tss_by_gene or {}).get(gene, None)

        kept = []
        for strand, pos, guide, pam in cands:
            if not _passes_filters(guide, params.gc_range, params.max_homopolymer):
                continue

            # optional off-target lite filter
            ot_hits = None
            if idx is not None:
                try:
                    ot = find_offtargets(
                        idx, guide, pam=PAM_SEQUENCES[params.enzyme],
                        pam_side=PAM_SIDE[params.enzyme],
                        max_mismatches=params.max_mismatches, scan_rc=True,
                        seed_len=params.seed_len
                    )
                    ot_hits = len(ot)
                except Exception:
                    ot_hits = None

                # drop guides with multiple close hits (rough)
                if ot_hits is not None and ot_hits > 3:
                    continue

            score = _score_guide(strand, pos, guide, pam, L, params.mode, tss_pos=tss_here)
            kept.append({
                "gene": gene,
                "strand": strand,
                "pos": pos,
                "guide": guide,
                "pam": pam,
                "GC%": round(_gc_pct(guide), 1),
                "score": round(score, 3),
                "offtarget_hits": ot_hits
            })

        kept.sort(key=lambda d: d["score"], reverse=True)
        chosen = _diversity_pick(kept, params.guides_per_gene, params.diversity_min_sep)
        rows.extend(chosen)

    df = pd.DataFrame(rows)
    return df.sort_values(["gene", "score"], ascending=[True, False]).reset_index(drop=True)


# ---------- Oligo builder ----------

_OVERHANGS = {
    # Minimal examples; customize to your cloning backbone
    "u6_bsmBI": {
        "prefix": "ACCG",   # 5' overhang
        "suffix": "GTTTT",  # 3' overhang + terminator stub
    },
    "t7_bsaI": {
        "prefix": "GCGT",
        "suffix": "AAAC",
    }
}

def make_oligos(
    df_guides: pd.DataFrame,
    scheme: str = "u6_bsmBI",
    add_barcode: bool = False,
    barcode_len: int = 6
) -> pd.DataFrame:
    oh = _OVERHANGS.get(scheme, _OVERHANGS["u6_bsmBI"])
    pref, suff = oh["prefix"], oh["suffix"]

    out = df_guides.copy()
    # Optional tiny barcode (A/C/G/T cycling) — not collision-safe, just a placeholder
    if add_barcode:
        ABCD = ["ACGT", "TGCA", "GACT", "CTGA"]
        barcodes = []
        for i in range(len(out)):
            b = (ABCD[i % len(ABCD)] * ((barcode_len // 4) + 1))[:barcode_len]
            barcodes.append(b)
        out["barcode"] = barcodes
    else:
        out["barcode"] = ""

    out["oligo"] = out.apply(lambda r: f'{pref}{r["guide"]}{suff}{r["barcode"]}', axis=1)
    cols = ["gene", "guide", "pam", "strand", "pos", "GC%", "score", "offtarget_hits", "oligo"]
    return out[cols]
