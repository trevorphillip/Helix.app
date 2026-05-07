# utils/dna_utils.py

from __future__ import annotations
from typing import List, Dict


def clean_dna(seq: str) -> str:
    seq = (seq or "").upper()
    return "".join(b for b in seq if b in "ACGT")


def is_valid_dna(seq: str) -> bool:
    if not seq:
        return False
    return all(b in "ACGT" for b in seq.upper())


def gc_content(seq: str) -> float:
    seq = clean_dna(seq)
    if not seq:
        return 0.0
    gc = seq.count("G") + seq.count("C")
    return gc / len(seq) * 100.0


# Genetic code
CODON_TABLE: Dict[str, str] = {
    "TTT":"F","TTC":"F","TTA":"L","TTG":"L","CTT":"L","CTC":"L","CTA":"L","CTG":"L",
    "ATT":"I","ATC":"I","ATA":"I","ATG":"M","GTT":"V","GTC":"V","GTA":"V","GTG":"V",
    "TCT":"S","TCC":"S","TCA":"S","TCG":"S","AGT":"S","AGC":"S","CCT":"P","CCC":"P",
    "CCA":"P","CCG":"P","ACT":"T","ACC":"T","ACA":"T","ACG":"T","GCT":"A","GCC":"A",
    "GCA":"A","GCG":"A","TAT":"Y","TAC":"Y","CAT":"H","CAC":"H","CAA":"Q","CAG":"Q",
    "AAT":"N","AAC":"N","AAA":"K","AAG":"K","GAT":"D","GAC":"D","GAA":"E","GAG":"E",
    "TGT":"C","TGC":"C","TGA":"*","TGG":"W","CGT":"R","CGC":"R","CGA":"R","CGG":"R",
    "AGA":"R","AGG":"R","GGT":"G","GGC":"G","GGA":"G","GGG":"G","TAA":"*","TAG":"*"
}


def translate_dna(seq: str, frame: int = 0, stop_symbol: str = "*") -> str:
    seq = clean_dna(seq)
    frame = frame % 3
    aa = []
    for i in range(frame, len(seq)-2, 3):
        codon = seq[i:i+3]
        aa_char = CODON_TABLE.get(codon, "X")
        aa.append(stop_symbol if aa_char == "*" else aa_char)
    return "".join(aa)


def find_orfs(seq: str, min_aa_len: int = 30) -> List[dict]:
    seq = clean_dna(seq)
    stop_codons = {"TAA", "TAG", "TGA"}
    orfs = []

    for frame in (0, 1, 2):
        i = frame
        while i < len(seq)-2:
            if seq[i:i+3] == "ATG":
                start = i
                j = i
                protein = []
                stop_reached = False

                while j < len(seq)-2:
                    cod = seq[j:j+3]
                    if cod in stop_codons:
                        protein.append("*")
                        stop_reached = True
                        j += 3
                        break
                    protein.append(CODON_TABLE.get(cod, "X"))
                    j += 3

                if stop_reached and len(protein) >= min_aa_len:
                    orfs.append({
                        "start_nt": start,
                        "end_nt": j,
                        "length_nt": j - start,
                        "length_aa": len(protein),
                        "frame": frame,
                        "protein": "".join(protein),
                    })

                i = j
            else:
                i += 3

    return orfs
