# codon.py
from typing import Dict, List
from collections import Counter

# Simplified preferred codons (common choices)
PREFERRED = {
    "E_coli": {
        "A":"GCT","R":"CGT","N":"AAT","D":"GAT","C":"TGC","Q":"CAA","E":"GAA","G":"GGT",
        "H":"CAT","I":"ATT","L":"CTG","K":"AAA","M":"ATG","F":"TTT","P":"CCG","S":"TCT",
        "T":"ACC","W":"TGG","Y":"TAT","V":"GTG","*":"TAA"
    },
    "Yeast": {
        "A":"GCT","R":"AGA","N":"AAT","D":"GAT","C":"TGT","Q":"CAA","E":"GAA","G":"GGA",
        "H":"CAT","I":"ATT","L":"TTA","K":"AAA","M":"ATG","F":"TTT","P":"CCA","S":"TCT",
        "T":"ACC","W":"TGG","Y":"TAT","V":"GTT","*":"TAA"
    },
    "Human": {
        "A":"GCC","R":"CGC","N":"AAC","D":"GAC","C":"TGC","Q":"CAG","E":"GAG","G":"GGC",
        "H":"CAC","I":"ATC","L":"CTG","K":"AAG","M":"ATG","F":"TTC","P":"CCC","S":"AGC",
        "T":"ACC","W":"TGG","Y":"TAC","V":"GTG","*":"TAA"
    }
}

GENETIC_CODE = {
    "TTT":"F","TTC":"F","TTA":"L","TTG":"L","TCT":"S","TCC":"S","TCA":"S","TCG":"S",
    "TAT":"Y","TAC":"Y","TAA":"*","TAG":"*","TGT":"C","TGC":"C","TGA":"*","TGG":"W",
    "CTT":"L","CTC":"L","CTA":"L","CTG":"L","CCT":"P","CCC":"P","CCA":"P","CCG":"P",
    "CAT":"H","CAC":"H","CAA":"Q","CAG":"Q","CGT":"R","CGC":"R","CGA":"R","CGG":"R",
    "ATT":"I","ATC":"I","ATA":"I","ATG":"M","ACT":"T","ACC":"T","ACA":"T","ACG":"T",
    "AAT":"N","AAC":"N","AAA":"K","AAG":"K","AGT":"S","AGC":"S","AGA":"R","AGG":"R",
    "GTT":"V","GTC":"V","GTA":"V","GTG":"V","GCT":"A","GCC":"A","GCA":"A","GCG":"A",
    "GAT":"D","GAC":"D","GAA":"E","GAG":"E","GGT":"G","GGC":"G","GGA":"G","GGG":"G",
}

def translate_dna(seq: str) -> str:
    s = seq.upper()
    return "".join(GENETIC_CODE.get(s[i:i+3], "X") for i in range(0, len(s)-2, 3))

def codon_usage(seq: str) -> Dict[str, int]:
    s = seq.upper()
    codons = [s[i:i+3] for i in range(0, len(s)-2, 3) if len(s[i:i+3]) == 3]
    return dict(Counter(codons))

def optimize_coding_sequence(seq: str, organism: str = "Human") -> str:
    """
    Replace each codon by the preferred codon for its amino acid.
    Non-triplet tails are kept as-is.
    """
    pref = PREFERRED.get(organism, PREFERRED["Human"])
    out = []
    s = seq.upper()
    for i in range(0, len(s)-2, 3):
        cod = s[i:i+3]
        aa = GENETIC_CODE.get(cod, "X")
        out.append(pref.get(aa, cod))
    tail = s[(len(s)//3)*3:]
    return "".join(out) + tail
