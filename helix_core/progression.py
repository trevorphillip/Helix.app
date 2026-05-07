# helix_core/progression.py
from __future__ import annotations
import os, json, math, re
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
import streamlit as st

# uses your existing helpers
from helix_core.crisprutils import reverse_complement, find_off_targets_window

# -------- storage (simple JSON beside repo root) --------
PROG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "progress.json"))

def _load():
    if os.path.exists(PROG_PATH):
        try: return json.load(open(PROG_PATH, "r", encoding="utf-8"))
        except Exception: pass
    return {"xp": 0, "level": 1, "badges": [], "history": []}

def _save(p): json.dump(p, open(PROG_PATH, "w", encoding="utf-8"), indent=2)

def level_from_xp(xp: int) -> int:
    # triangular-ish curve: L(L+1)/2 * 150 ≈ xp → L ~ O(sqrt(xp))
    # smooth growth that doesn't need streaks
    return max(1, int((math.sqrt(1 + 8*xp/150) - 1) // 2) + 1)

def add_xp(amount: int, note: str = "") -> Dict:
    p = _load()
    p["xp"] = int(p.get("xp", 0)) + int(amount)
    new_level = level_from_xp(p["xp"])
    if new_level > p.get("level", 1):
        p["level"] = new_level
        if "Level Up!" not in p["badges"]:
            p["badges"].append("Level Up!")
    if note:
        p["history"].append({"xp": amount, "note": note})
    _save(p)
    return p

def profile() -> Dict:
    p = _load()
    p["level"] = level_from_xp(p["xp"])
    return p

# -------- gRNA grading rubric --------
IUPAC = str.maketrans({
    "R":"[AG]","Y":"[CT]","S":"[GC]","W":"[AT]",
    "K":"[GT]","M":"[AC]","B":"[CGT]","D":"[AGT]",
    "H":"[ACT]","V":"[ACG]","N":"[ACGT]"
})
def iupac_to_regex(pat: str) -> str:
    return "^" + re.sub(r"[RYSWKMBDHVN]", lambda m: m.group(0).translate(IUPAC), pat) + "$"

def _pam_at(seq: str, pos: int, strand: str, pam: str, pam_side: str, glen: int) -> bool:
    """Return True if PAM at genome is compatible with (pos, strand) guide."""
    s = seq.upper()
    pat = iupac_to_regex(pam.upper())
    if strand == "+":
        if pam_side.startswith("3"):  # PAM is downstream of protospacer
            span = s[pos+glen : pos+glen+len(pam)]
        else:  # PAM upstream
            span = s[max(0, pos-len(pam)) : pos]
    else:
        # reverse strand: compute on RC orientation
        if pam_side.startswith("3"):
            j = pos - len(pam)  # because RC protospacer is left of PAM on + strand
            span = s[max(0, j): max(0, j)+len(pam)]
        else:
            j = pos + glen
            span = s[j:j+len(pam)]
        # when checking minus strand, compare to RC of span
        span = reverse_complement(span)
    return bool(re.match(iupac_to_regex(pam), span))

def gc_pct(s: str) -> float:
    s = s.upper(); L = max(1, len(s))
    return 100.0 * (s.count("G")+s.count("C")) / L

def has_homopolymer(s: str, n: int = 5) -> bool:
    return re.search(rf"(A{{{n},}}|C{{{n},}}|G{{{n},}}|T{{{n},}})", s.upper()) is not None

@dataclass
class GRNAGrade:
    total: int
    breakdown: Dict[str, int]
    notes: List[str]

def grade_grna(
    genome: str,
    guide: str,
    pos: int,
    strand: str,
    pam: str,
    pam_side: str,
    glen: int,
    window: Tuple[int,int],
    max_mm_for_penalty: int = 2,
    editor: Optional[str] = None,          # "ABE" or "CBE" or None
    edit_window: Tuple[int,int] = (4, 8)   # 1-based within protospacer
) -> GRNAGrade:
    """
    Deterministic 0–100 grading for a guide at (pos,strand) in genome.
    Heavier penalty for off-targets; no streak mechanics required.
    """
    scores = {}
    notes = []

    # 1) PAM validity (gate)
    if _pam_at(genome, pos, strand, pam, pam_side, glen):
        scores["pam"] = 20
    else:
        scores["pam"] = 0
        notes.append("PAM mismatch for this enzyme/side (0/20).")

    # 2) GC band (40–60 → full; mild falloff)
    gc = gc_pct(guide)
    if 40 <= gc <= 60:
        scores["gc"] = 20
    elif 35 <= gc < 40 or 60 < gc <= 65:
        scores["gc"] = 12
        notes.append(f"GC {gc:.1f}% slightly off (12/20).")
    else:
        scores["gc"] = 6
        notes.append(f"GC {gc:.1f}% off-range (6/20).")

    # 3) Centering in window (closer to center → higher)
    a, b = window
    center = (a + b) / 2.0
    gcenter = pos + len(guide)/2.0
    dist = abs(gcenter - center)
    maxd = max(1.0, (b - a) / 2.0)
    cent = 1.0 - min(dist/maxd, 1.0)
    scores["centering"] = int(round(cent * 20))

    # 4) Homopolymer check
    scores["poly"] = 10 if not has_homopolymer(guide, n=5) else 2
    if scores["poly"] == 2: notes.append("Homopolymer ≥5 detected (2/10).")

    # 5) Off-targets (≤2 mismatches) inside window as quick proxy
    hits = find_off_targets_window(genome, a, b, guide_seq=guide, max_mismatches=max_mm_for_penalty)
    # score: 20 with none; 12 with 1; 4 otherwise
    if not hits:
        scores["offtargets"] = 20
    elif len(hits) == 1:
        scores["offtargets"] = 12; notes.append("1 off-target (12/20).")
    else:
        scores["offtargets"] = 4; notes.append(f"{len(hits)} off-targets (4/20).")

    # 6) Base-editor coverage bonus (optional)
    be_bonus = 0
    if editor:
        prot = genome[pos:pos+glen] if strand == "+" else reverse_complement(genome[pos:pos+glen])
        i0, i1 = max(1, edit_window[0]), min(glen, edit_window[1])  # 1-based inclusive
        window_seq = prot[i0-1:i1]
        if editor.upper().startswith("ABE"):
            count = window_seq.count("A")
        elif editor.upper().startswith("CBE"):
            count = window_seq.count("C")
        else:
            count = 0
        be_bonus = min(10, 2*count)  # up to +10
        if be_bonus > 0: notes.append(f"{editor} window captures {count} targetable base(s) (+{be_bonus}).")
    scores["be_bonus"] = be_bonus

    total = sum(v for k,v in scores.items() if k != "be_bonus") + be_bonus
    total = max(0, min(100, total))
    return GRNAGrade(total=total, breakdown=scores, notes=notes)
