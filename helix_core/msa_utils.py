from __future__ import annotations
from typing import List, Tuple, Dict
from Bio import pairwise2

def parse_fasta_multi(text: str) -> List[Tuple[str, str]]:
    names = []
    seq = []
    out = []
    cur_name = None
    for line in (text or "").splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith(">"):
            if cur_name is not None:
                out.append((cur_name, "".join(seq).upper()))
            cur_name = line[1:].strip() or f"seq{len(out)+1}"
            seq = []
        else:
            seq.append(line)
    if cur_name is not None:
        out.append((cur_name, "".join(seq).upper()))
    return out

def _align_two(a: str, b: str) -> Tuple[str, str]:
    aln = pairwise2.align.globalms(a, b, 2, -1, -5, -1, one_alignment_only=True)
    if not aln:
        return a, b
    A, B, *_ = aln[0]
    return A, B

def progressive_align(seqs: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
    """
    Very simple progressive alignment: align sequences sequentially to a growing profile string.
    OK for short/medium sequences; not meant to replace Clustal/MUSCLE.
    """
    if not seqs:
        return []
    names, strings = zip(*seqs)
    profile = strings[0]
    aligned = [(names[0], profile)]
    for i in range(1, len(strings)):
        A, B = _align_two(profile, strings[i])
        # re-align all previous aligned sequences to new gaps of A
        new_aligned = []
        idx_old = 0
        for (nm, aln_old) in aligned:
            new = []
            j_old = 0
            for j in range(len(A)):
                if A[j] == "-":
                    new.append("-")
                else:
                    new.append(aln_old[j_old] if j_old < len(aln_old) else "-")
                    j_old += 1
            new_aligned.append((nm, "".join(new)))
        aligned = new_aligned + [(names[i], B)]
        profile = A
    return aligned

def consensus_from_alignment(aligned: List[Tuple[str, str]]) -> str:
    if not aligned:
        return ""
    cols = zip(*[s for (_n, s) in aligned])
    cons = []
    for col in cols:
        counts: Dict[str, int] = {}
        for c in col:
            if c == "-":
                continue
            counts[c] = counts.get(c, 0) + 1
        cons.append(max(counts, key=counts.get) if counts else "-")
    return "".join(cons)
"""Compatibility proxy for legacy module."""



from ._proxy import export

export("msa_utils", globals())