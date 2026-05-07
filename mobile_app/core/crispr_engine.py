# mobile_app/core/crispr_engine.py
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Tuple

DNA = set("ACGT")

def sanitize(seq: str) -> str:
    if not seq:
        return ""
    seq = seq.upper()
    return "".join(ch for ch in seq if ch in DNA)

def reverse_complement(seq: str) -> str:
    comp = {"A":"T","T":"A","C":"G","G":"C"}
    s = sanitize(seq)
    return "".join(comp[b] for b in reversed(s))

def gc_pct(seq: str) -> float:
    s = sanitize(seq)
    if not s:
        return 0.0
    return 100.0 * (s.count("G") + s.count("C")) / len(s)

# --- Minimal enzyme presets (expand later) ---
# pam_side = "3prime" means PAM is immediately AFTER the protospacer on the + strand
# pam_side = "5prime" means PAM is immediately BEFORE the protospacer on the + strand
ENZYMES: Dict[str, Dict] = {
    "SpCas9 (NGG)": {"pam": "NGG", "pam_side": "3prime", "guide_len": 20},
    "AsCas12a (TTTV)": {"pam": "TTTV", "pam_side": "5prime", "guide_len": 20},
}

def _match_iupac(pat: str, tri: str) -> bool:
    # pat contains A/C/G/T and IUPAC: N, V
    # N = any, V = A/C/G (not T)
    m = {"A":{"A"}, "C":{"C"}, "G":{"G"}, "T":{"T"},
         "N":{"A","C","G","T"}, "V":{"A","C","G"}}
    pat = pat.upper()
    tri = tri.upper()
    if len(pat) != len(tri):
        return False
    for p, b in zip(pat, tri):
        if b not in m.get(p, {p}):
            return False
    return True

def find_pams(seq: str, pam: str) -> List[int]:
    s = sanitize(seq)
    L = len(pam)
    out = []
    for i in range(0, len(s) - L + 1):
        if _match_iupac(pam, s[i:i+L]):
            out.append(i)
    return out

@dataclass
class GuideHit:
    strand: str          # "+" or "-"
    pam_start: int       # PAM start on forward coordinate system
    guide_start: int     # protospacer start on forward coordinates
    guide: str           # protospacer DNA (T, not U)
    pam: str             # concrete PAM bases found
    gc: float

def _pam_concrete(seq: str, start: int, pam_len: int) -> str:
    return sanitize(seq)[start:start+pam_len]

def scan_guides(seq: str, enzyme_key: str, scan_rc: bool = True) -> Tuple[List[int], List[GuideHit]]:
    """
    Returns (pam_positions_on_forward, guide_hits)
    For "-" hits, guide_start is mapped onto forward coordinates.
    """
    s = sanitize(seq)
    if not s:
        return [], []

    cfg = ENZYMES[enzyme_key]
    pam = cfg["pam"]
    side = cfg["pam_side"]
    glen = int(cfg["guide_len"])
    pam_len = len(pam)

    pam_pos_fwd = find_pams(s, pam)
    hits: List[GuideHit] = []

    def add_hits_from_strand(tseq: str, strand: str, mapper):
        # mapper converts positions in tseq to forward coords
        pam_pos = find_pams(tseq, pam)
        for p in pam_pos:
            if side == "3prime":
                guide_start = p - glen
                pam_start = p
                if guide_start < 0:
                    continue
                guide = tseq[guide_start:guide_start+glen]
                pam_conc = tseq[p:p+pam_len]
            else:  # 5prime
                guide_start = p + pam_len
                pam_start = p
                if guide_start + glen > len(tseq):
                    continue
                guide = tseq[guide_start:guide_start+glen]
                pam_conc = tseq[p:p+pam_len]

            # map to forward
            pam_f = mapper(pam_start)
            guide_f = mapper(guide_start)

            hits.append(GuideHit(
                strand=strand,
                pam_start=pam_f,
                guide_start=guide_f,
                guide=guide,
                pam=pam_conc,
                gc=gc_pct(guide)
            ))

    # + strand
    add_hits_from_strand(s, "+", lambda x: x)

    # - strand (scan reverse complement)
    if scan_rc:
        rc = reverse_complement(s)

        def map_rc(pos_in_rc: int) -> int:
            # maps index in rc to index in forward (start of that substring)
            # forward_index = len-1 - pos_in_rc, but for substring start we use:
            return len(s) - (pos_in_rc) - 1

        # careful: mapping substring starts: if substring starts at rc index i,
        # the corresponding forward start is len - i - length(substring)
        def map_rc_start(i: int, sub_len: int) -> int:
            return len(s) - i - sub_len

        pam_pos_rc = find_pams(rc, pam)
        for p in pam_pos_rc:
            if side == "3prime":
                guide_start = p - glen
                pam_start = p
                if guide_start < 0:
                    continue
                guide = rc[guide_start:guide_start+glen]
                pam_conc = rc[p:p+pam_len]
                pam_f = map_rc_start(pam_start, pam_len)
                guide_f = map_rc_start(guide_start, glen)
            else:  # 5prime
                guide_start = p + pam_len
                pam_start = p
                if guide_start + glen > len(rc):
                    continue
                guide = rc[guide_start:guide_start+glen]
                pam_conc = rc[p:p+pam_len]
                pam_f = map_rc_start(pam_start, pam_len)
                guide_f = map_rc_start(guide_start, glen)

            hits.append(GuideHit(
                strand="-",
                pam_start=pam_f,
                guide_start=guide_f,
                guide=guide,   # still DNA letters, OK
                pam=pam_conc,
                gc=gc_pct(guide)
            ))

    # PAM positions for quick rendering
    pam_all = sorted({h.pam_start for h in hits})
    # Sort guides: fewer edge issues + nicer UX
    hits.sort(key=lambda h: (h.pam_start, h.strand))
    return pam_all, hits

def apply_ko_deletion(seq: str, cut_pos: int, del_len: int = 30) -> Tuple[str, int, int]:
    """
    Deletes del_len bases centered around cut_pos.
    Returns (new_seq, del_start, del_end_exclusive)
    """
    s = sanitize(seq)
    if not s:
        return "", 0, 0
    cut_pos = max(0, min(cut_pos, len(s)))
    half = del_len // 2
    a = max(0, cut_pos - half)
    b = min(len(s), a + del_len)
    # ensure length is del_len when possible
    a = max(0, b - del_len)
    new = s[:a] + s[b:]
    return new, a, b
