# motifs.py
import re
from typing import Dict, List, Tuple

# IUPAC mapping
IUPAC = {
    "A": "A", "C": "C", "G": "G", "T": "T",
    "R": "[AG]", "Y": "[CT]", "S": "[GC]", "W": "[AT]", "K": "[GT]", "M": "[AC]",
    "B": "[CGT]", "D": "[AGT]", "H": "[ACT]", "V": "[ACG]", "N": "[ACGT]",
}

def iupac_to_regex(pattern: str) -> str:
    return "".join(IUPAC.get(ch, ch) for ch in pattern.upper())

def scan_iupac(sequence: str, name: str, pattern: str) -> List[Dict]:
    seq = sequence.upper()
    rgx = re.compile(iupac_to_regex(pattern))
    hits = []
    for m in rgx.finditer(seq):
        s, e = m.start(), m.end()
        hits.append({"name": name, "start": s, "end": e, "pattern": pattern, "type": "motif"})
    return hits

# Promoters / regulatory motifs (DNA form; Kozak consensus adapted to DNA)
PROMOTER_MOTIFS: Dict[str, str] = {
    "TATA box": "TATAAA",
    "CAAT box": "CCAAT",
    "GC box (Sp1)": "GGGCGG",
    "Kozak (consensus)": "GCCRCCATGG",  # R=A/G
    "Poly-A signal": "AATAAA",
}

# Common restriction sites (+ conceptual cut offsets)
RE_SITES: Dict[str, Tuple[str, int]] = {
    "EcoRI": ("GAATTC", 1),
    "BamHI": ("GGATCC", 1),
    "HindIII": ("AAGCTT", 1),
    "NotI": ("GCGGCCGC", 2),
    "XhoI": ("CTCGAG", 1),
}

def scan_promoters(sequence: str) -> List[Dict]:
    out: List[Dict] = []
    for name, pat in PROMOTER_MOTIFS.items():
        out += scan_iupac(sequence, name, pat)
    return out

def scan_restriction_sites(sequence: str) -> List[Dict]:
    out: List[Dict] = []
    s = sequence.upper()
    for name, (site, cut) in RE_SITES.items():
        rgx = re.compile(iupac_to_regex(site))
        for m in rgx.finditer(s):
            start = m.start(); end = m.end()
            out.append({"name": name, "start": start, "end": end, "pattern": site, "cut_offset": cut, "type": "restriction"})
    return out

def within_window(items: List[Dict], start: int, end: int) -> List[Dict]:
    return [d for d in items if not (d["end"] <= start or d["start"] >= end)]
