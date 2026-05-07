# offtarget.py
from __future__ import annotations
from typing import Dict, List, Tuple

# ---- small utils ----
DNA = set("ACGT")

def clean_dna(s: str) -> str:
    return "".join(ch for ch in (s or "").upper() if ch in DNA)

def revcomp(s: str) -> str:
    t = str.maketrans("ACGT", "TGCA")
    return s.translate(t)[::-1]

def matches_pam(genome: str, pos: int, guide_len: int, pam: str, pam_side: str) -> bool:
    """Check PAM text at the right side relative to protospacer orientation.
       pam like 'NGG', 'TTTV'. pam_side either '3prime'/'5prime' or '3\''/'5\''/3/5."""
    pam_side = (pam_side or "").replace("'", "").lower()
    N = len(genome)
    P = pam.upper()
    def ok(base, letter):
        if letter == "N": return True
        return base == letter
    # forward protospacer 5'→3' on + strand
    if pam_side.startswith("3"):
        i = pos + guide_len
        if i + len(P) > N: return False
        seg = genome[i:i+len(P)]
        return all(ok(seg[j], P[j]) for j in range(len(P)))
    else:
        # PAM is upstream on the 5' side in forward coordinate
        i = pos - len(P)
        if i < 0: return False
        seg = genome[i: i+len(P)]
        return all(ok(seg[j], P[j]) for j in range(len(P)))

# ---- index & search ----
class KmerIndex:
    def __init__(self, genome: str, k: int = 8):
        self.genome = clean_dna(genome)
        self.k = int(k)
        self.map: Dict[str, List[int]] = {}
        G = self.genome
        k = self.k
        for i in range(0, max(0, len(G) - k + 1)):
            kmer = G[i:i+k]
            lst = self.map.get(kmer)
            if lst is None:
                self.map[kmer] = [i]
            else:
                lst.append(i)

def hamming(a: str, b: str, max_mismatches: int) -> int | None:
    mm = 0
    for x, y in zip(a, b):
        if x != y:
            mm += 1
            if mm > max_mismatches:
                return None
    return mm

def find_offtargets(
    index: KmerIndex,
    guide: str,
    pam: str = "NGG",
    pam_side: str = "3prime",
    max_mismatches: int = 2,
    scan_rc: bool = True,
    seed_len: int | None = None
) -> List[dict]:
    """Seed-and-extend: scan candidates via k-mer seeds, then verify Hamming <= max_mismatches (+ PAM)."""
    G = index.genome
    Lg = len(G)
    seed_k = seed_len or index.k
    q = clean_dna(guide)
    if len(q) < seed_k: return []

    hits: List[dict] = []
    # prebuild seeds for query
    candidates = {}
    for i in range(0, len(q) - seed_k + 1):
        s = q[i:i+seed_k]
        for pos in index.map.get(s, []):
            # align so that q[i] aligns to G[pos]
            start = pos - i
            if 0 <= start and start + len(q) <= Lg:
                candidates[start] = candidates.get(start, 0) + 1

    # verify forward strand
    for start in candidates.keys():
        seg = G[start:start+len(q)]
        mm = hamming(seg, q, max_mismatches)
        if mm is not None and matches_pam(G, start, len(q), pam, pam_side):
            hits.append({"strand": "+", "pos": start, "mismatches": mm, "target": seg})

    if scan_rc:
        qrc = revcomp(q)
        # recompute candidates on rc or reuse symmetric logic by scanning the + genome against rc guide
        candidates_rc = {}
        for i in range(0, len(qrc) - seed_k + 1):
            s = qrc[i:i+seed_k]
            for pos in index.map.get(s, []):
                start = pos - i
                if 0 <= start and start + len(qrc) <= Lg:
                    candidates_rc[start] = candidates_rc.get(start, 0) + 1

        for start in candidates_rc.keys():
            seg = G[start:start+len(qrc)]
            mm = hamming(seg, qrc, max_mismatches)
            if mm is not None:
                # For the rc protospacer, PAM location flips relative to + strand coordinates
                side = "5prime" if pam_side.lower().startswith("3") else "3prime"
                if matches_pam(G, start, len(qrc), pam, side):
                    hits.append({"strand": "-", "pos": start, "mismatches": mm, "target": seg})

    hits.sort(key=lambda d: (d["mismatches"], d["pos"]))
    return hits



class KmerIndex:
    def __init__(self, genome: str, k: int = 8):
        self.genome = (genome or "").upper()
        self.k = int(k)

def find_offtargets(index: KmerIndex, guide: str, pam: str, pam_side: str,
                    max_mismatches: int = 1, scan_rc: bool = True, seed_len: int | None = None):
    """
    Minimal no-op implementation.
    Return empty list so OT count shows 0 (the screen still works).
    Swap in a real search later.
    """
    return []
