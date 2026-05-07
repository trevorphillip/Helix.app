# primer_designer.py
# Heuristic PCR primer picker (educational; not clinical).
# All functions are pure + offline.

from __future__ import annotations
from typing import List, Dict, Tuple
import re
import math

# ---- small utils ----

def _dna_only(s: str) -> str:
    return "".join(ch for ch in (s or "").upper() if ch in "ACGT")

def revcomp(s: str) -> str:
    t = str.maketrans("ACGTacgt", "TGCAtgca")
    return (s or "").translate(t)[::-1]

def gc_pct(s: str) -> float:
    s = _dna_only(s)
    return 100.0 * (s.count("G") + s.count("C")) / max(1, len(s))

def tm_wallace(s: str) -> float:
    s = _dna_only(s)
    return 2.0 * (s.count("A") + s.count("T")) + 4.0 * (s.count("G") + s.count("C"))

def has_bad_runs(s: str, n: int = 4) -> bool:
    return re.search(r"(A{%d,}|C{%d,}|G{%d,}|T{%d,})" % (n, n, n, n), _dna_only(s)) is not None

def gc_clamp(s: str) -> bool:
    s = _dna_only(s)
    return bool(s) and s[-1] in ("G", "C")

def longest_3p_heterodimer(a: str, b: str) -> int:
    """
    Longest k where 3' suffix of a matches complement of 5' prefix of b (and vice-versa).
    Proxy for dangerous 3'-anchored heterodimers.
    """
    rb = revcomp(b)
    m = min(len(a), len(rb))
    for k in range(m, 0, -1):
        if a[-k:].upper() == rb[:k].upper():
            return k
    return 0

def hairpin_proxy_3prime(s: str, lookback: int = 12) -> int:
    """
    Very simple hairpin proxy: longest complement match within last `lookback` nt of 3' end.
    """
    s = _dna_only(s)
    r = revcomp(s)
    tail = s[-lookback:].upper()
    rr = r.upper()
    best = 0
    for k in range(min(lookback, len(tail)), 0, -1):
        if tail[-k:] in [rr[i:i+k] for i in range(0, max(0, len(rr) - k + 1))]:
            return k
    return best

def count_occurrences(genome: str, pattern: str) -> int:
    """
    Count non-overlapping occurrences of a short pattern (uppercased).
    """
    g = _dna_only(genome)
    p = _dna_only(pattern)
    if not g or not p:
        return 0
    n, i = 0, g.find(p)
    while i != -1:
        n += 1
        i = g.find(p, i + 1)
    return n

# ---- checks & search ----

def check_primer(
    seq: str,
    min_len: int = 18,
    max_len: int = 26,
    tm_range: Tuple[float, float] = (55.0, 65.0),
    gc_range: Tuple[float, float] = (40.0, 60.0),
    max_hairpin: int = 4,
) -> Dict | None:
    s = _dna_only(seq)
    if not (min_len <= len(s) <= max_len):
        return None
    tm = tm_wallace(s)
    gc = gc_pct(s)
    if not (tm_range[0] <= tm <= tm_range[1]): return None
    if not (gc_range[0] <= gc <= gc_range[1]): return None
    if has_bad_runs(s): return None
    hp = hairpin_proxy_3prime(s)
    if hp > max_hairpin: return None
    return {
        "seq": s,
        "len": len(s),
        "tm": tm,
        "gc": gc,
        "clamp": gc_clamp(s),
        "hairpin": hp,
    }

def find_primers_for_window(
    genome: str,
    start_bp: int,
    end_bp: int,
    left_span: int = 140,
    right_span: int = 140,
    min_len: int = 18,
    max_len: int = 26,
    tm_range: Tuple[float, float] = (55.0, 65.0),
    gc_range: Tuple[float, float] = (40.0, 60.0),
    max_candidates: int = 60,
) -> Tuple[List[Dict], List[Dict]]:
    """
    Return (left_candidates, right_candidates). Right primers reported in 5'->3' sense (already RC'ed).
    """
    G = _dna_only(genome)
    L = len(G)
    # left side region: from start_bp forward
    ls = max(0, start_bp)
    le = min(L, start_bp + left_span)
    lefts: List[Dict] = []
    for pos in range(ls, le):
        for ln in range(min_len, max_len + 1):
            if pos + ln > L: break
            cand = G[pos : pos + ln]
            meta = check_primer(cand, min_len, max_len, tm_range, gc_range)
            if meta:
                meta.update({
                    "pos": pos,
                    "strand": "+",
                    "tail12_count": count_occurrences(G, cand[-12:])
                })
                lefts.append(meta)
                if len(lefts) >= max_candidates: break
        if len(lefts) >= max_candidates: break

    # right side region: from end_bp backward
    rs = max(0, end_bp - right_span)
    re_ = min(L, end_bp)
    rights: List[Dict] = []
    for endpos in range(re_, rs, -1):
        for ln in range(min_len, max_len + 1):
            start = endpos - ln
            if start < 0: break
            cand = G[start:endpos]
            cand_rc = revcomp(cand)  # report as 5'->3'
            meta = check_primer(cand_rc, min_len, max_len, tm_range, gc_range)
            if meta:
                meta.update({
                    "pos": start,
                    "len": len(cand_rc),
                    "strand": "-",
                    "seq": cand_rc,
                    "tail12_count": count_occurrences(G, cand_rc[-12:])
                })
                rights.append(meta)
                if len(rights) >= max_candidates: break
        if len(rights) >= max_candidates: break

    return lefts, rights

def pair_primers(
    lefts: List[Dict],
    rights: List[Dict],
    start_bp: int,
    end_bp: int,
    max_delta_tm: float = 2.5,
    prod_min: int = 80,
    prod_max: int = 1800,
) -> List[Dict]:
    pairs: List[Dict] = []
    for Lp in lefts:
        for Rp in rights:
            d_tm = abs(Lp["tm"] - Rp["tm"])
            if d_tm > max_delta_tm:
                continue
            prod = (Rp["pos"] + Rp["len"]) - Lp["pos"]
            if not (prod_min <= prod <= prod_max):
                continue
            dimer_k = max(
                longest_3p_heterodimer(Lp["seq"], Rp["seq"]),
                longest_3p_heterodimer(Rp["seq"], Lp["seq"]),
            )
            if dimer_k >= 5:
                continue
            clamp_bonus = (1 if Lp["clamp"] else 0) + (1 if Rp["clamp"] else 0)
            uniq_bonus = (1.0 / max(1, Lp["tail12_count"])) + (1.0 / max(1, Rp["tail12_count"]))
            center = (start_bp + end_bp) / 2.0
            prod_center = Lp["pos"] + prod / 2.0
            center_pen = abs(prod_center - center) / max(1, (end_bp - start_bp) / 2.0)
            score = (2.0 - min(d_tm, 2.0)) + clamp_bonus + 0.5 * uniq_bonus + (1.0 - min(center_pen, 1.0))
            pairs.append({
                "Left": Lp["seq"], "Right": Rp["seq"],
                "Tm_L": round(Lp["tm"], 1), "Tm_R": round(Rp["tm"], 1), "ΔTm": round(d_tm, 1),
                "GC%_L": round(Lp["gc"], 1), "GC%_R": round(Rp["gc"], 1),
                "Clamp_L": "✓" if Lp["clamp"] else "", "Clamp_R": "✓" if Rp["clamp"] else "",
                "3p12_hits_L": Lp["tail12_count"], "3p12_hits_R": Rp["tail12_count"],
                "Prod_len_bp": prod,
                "L_start": Lp["pos"], "R_end": Rp["pos"] + Rp["len"],
                "Score": round(score, 3)
            })
    pairs.sort(key=lambda d: d["Score"], reverse=True)
    return pairs

def design_primers(
    genome: str,
    start_bp: int, end_bp: int,
    primer_len_range: Tuple[int, int] = (20, 24),
    tm_range: Tuple[float, float] = (58.0, 64.0),
    gc_range: Tuple[float, float] = (40.0, 60.0),
    left_span: int = 140, right_span: int = 140,
    max_delta_tm: float = 2.5,
    prod_min: int = 120, prod_max: int = 1200,
    max_candidates: int = 80,
    top_k: int = 10,
) -> List[Dict]:
    Ls, Rs = find_primers_for_window(
        genome, start_bp, end_bp,
        left_span=left_span, right_span=right_span,
        min_len=primer_len_range[0], max_len=primer_len_range[1],
        tm_range=tm_range, gc_range=gc_range,
        max_candidates=max_candidates,
    )
    pairs = pair_primers(
        Ls, Rs, start_bp, end_bp,
        max_delta_tm=max_delta_tm,
        prod_min=prod_min, prod_max=prod_max
    )
    return pairs[:top_k]

def primers_to_fasta(pairs: List[Dict]) -> str:
    lines = []
    for i, row in enumerate(pairs, 1):
        lines.append(f">Primer_{i}_LEFT_Tm{row['Tm_L']}_GC{row['GC%_L']}_pos{row['L_start']}")
        lines.append(row["Left"])
        lines.append(f">Primer_{i}_RIGHT_Tm{row['Tm_R']}_GC{row['GC%_R']}_pos{row['R_end']}")
        lines.append(row["Right"])
    return "\n".join(lines) + ("\n" if lines else "")
