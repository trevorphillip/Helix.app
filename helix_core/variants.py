# variants.py
from typing import List, Dict, Tuple
from Bio import pairwise2

def global_align(a: str, b: str) -> Tuple[str, str]:
    """
    Needleman–Wunsch (global) with simple scoring.
    """
    alignments = pairwise2.align.globalms(a, b, 2, -1, -5, -1, one_alignment_only=True)
    if not alignments:
        return a, b
    aln_a, aln_b, *_ = alignments[0]
    return aln_a, aln_b

def call_variants(aln_a: str, aln_b: str) -> List[Dict]:
    """
    From two aligned strings, emit per-position differences (SNP/ins/del).
    Coordinates are on the alignment; caller can map back to sequence if needed.
    """
    diffs = []
    ia = ib = 0
    for i, (ca, cb) in enumerate(zip(aln_a, aln_b)):
        if ca != "-": ia += 1
        if cb != "-": ib += 1
        if ca == cb:
            continue
        typ = "SNP"
        if ca == "-": typ = "INS"  # insertion in B relative to A
        elif cb == "-": typ = "DEL"
        diffs.append({
            "aln_index": i,
            "type": typ,
            "ref": ca,
            "alt": cb,
            "ref_pos": ia if ca != "-" else ia,   # closest ref coord
            "alt_pos": ib if cb != "-" else ib
        })
    return diffs

_genetic_code = {
    "TTT":"F","TTC":"F","TTA":"L","TTG":"L","TCT":"S","TCC":"S","TCA":"S","TCG":"S",
    "TAT":"Y","TAC":"Y","TAA":"*","TAG":"*","TGT":"C","TGC":"C","TGA":"*","TGG":"W",
    "CTT":"L","CTC":"L","CTA":"L","CTG":"L","CCT":"P","CCC":"P","CCA":"P","CCG":"P",
    "CAT":"H","CAC":"H","CAA":"Q","CAG":"Q","CGT":"R","CGC":"R","CGA":"R","CGG":"R",
    "ATT":"I","ATC":"I","ATA":"I","ATG":"M","ACT":"T","ACC":"T","ACA":"T","ACG":"T",
    "AAT":"N","AAC":"N","AAA":"K","AAG":"K","AGT":"S","AGC":"S","AGA":"R","AGG":"R",
    "GTT":"V","GTC":"V","GTA":"V","GTG":"V","GCT":"A","GCC":"A","GCA":"A","GCG":"A",
    "GAT":"D","GAC":"D","GAA":"E","GAG":"E","GGT":"G","GGC":"G","GGA":"G","GGG":"G",
}

def codon_to_aa(codon: str) -> str:
    c = codon.upper()
    return _genetic_code.get(c, "X") if len(c) == 3 else "X"

def predict_snp_effect(ref_seq: str, alt_seq: str, start_pos: int = 0) -> List[Dict]:
    """
    Very simple per-codon impact: compare amino acids after substituting diff(s).
    Assumes same frame at 'start_pos' on + strand.
    """
    L = min(len(ref_seq), len(alt_seq))
    effects = []
    for i in range(start_pos, L - 2, 3):
        rc = ref_seq[i:i+3]; ac = alt_seq[i:i+3]
        raa, aaa = codon_to_aa(rc), codon_to_aa(ac)
        if raa != aaa:
            effects.append({"pos": i, "ref_codon": rc, "alt_codon": ac, "ref_aa": raa, "alt_aa": aaa})
    return effects
