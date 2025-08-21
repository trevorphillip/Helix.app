from Bio.Seq import Seq  # reserved for future (revcomp, etc.)

# PAMs for common enzymes (you can add more later)
PAM_SEQUENCES = {
    "SpCas9": "NGG",
    "SaCas9": "NNGRRT",
    "Cpf1":   "TTTV"
}

# Wildcards for PAM matching
WILDCARD_BASES = {
    "N": ["A","T","C","G"],
    "R": ["A","G"],
    "Y": ["C","T"],
    "V": ["A","C","G"],
    "S": ["G","C"],
    "W": ["A","T"],
}

def load_example_sequences():
    return {
        "Green Fluorescent Protein": (
            "ATGGTGAGCAAGGGCGAGGAGCTGTTCACCGGGGTGGTGCCCATCCTGGTCGAGCTGGACGGCGACGTAAACGGCCACAAGTTCAGCGTGTCCGGCGAGGGCGAGGGCGATGCCACCTACGGC"
            "AAGCTGACCCTGAAGTTCATCTGCACCACCGGCAAGCTGCCCGTGCCCTGGCCCACCCTCGTGACCACCCTGACCTACGGCGTGCAGTGCTTCAGCCGCTACCCCGACCACATGAAGCAGCAC"
            "GACTTCTTCAAGTCCGCCATGCCCGAAGGCTACGTCCAGGAGCGCACCATCTTCTTCAAGGACGACGGCAACTACAAGACCCGCGCCGAGGTGAAGTTCGAGGGCGACACCCTGGTGAACCGC"
            "ATCGAGCTGAAGGGCATCGACTTCAAGGAGGACGGCAACATCCTGGGGCACAAGCTGGAGTACAACTACAACAGCCACAACGTCTATATCATGGCCGACAAGCAGAAGAACGGCATCAAGGTG"
            "AACTTCAAGATCCGCCACAACATCGAGGACGGCAGCGTGCAGCTCGCCGACCACTACCAGCAGAACACCCCCATCGGCGACGGCCCCGTGCTGCTGCCCGACAACCACTACCTGAGCACCCAG"
            "TCCGCCCTGAGCAAAGACCCCAACGAGAAGCGCGATCACATGGTCCTGCTGGAGTTCGTGACCGCCGCCGGGATCACTCTCGGCATGGACGAGCTGTACAAGTAA"
        ),
        "Human Insulin": (
            "ATGCCCTGTGGATGCGCCTCCTGCACCCGCCCAGCAGGCCATCAAGCAGATCCAGTTTTGTGCCCGTGACCCAGGCCACCTTTGTGGGGAACCTGACCCAGCCGCAGCCTTTGTGAACCAACA"
            "CCTGTGCGGCTCACACCTGGTGGAGGCTGCAGTAGTTCTGCCATGG"
        ),
        "Hemoglobin Subunit Beta": (
            "ATGGTGCATCTGACTCCTGAGGAGAAGTCTGCCGTTACTGCCCTGTGGGGCAAGGTGAACGTGGATGAAGTTGGTGGTGAGGCCCTGGGCAGGTTGGTATCAAGGTTACAAGACAGGTTTAAG"
            "GAGACCAATAGAAACTGGGCATGTGGAGACAGAGAAGACTCTTGGGGGGAAGGTGAACGTGGATGAAGTTGGTGGTGAGGCCCTGGGCAG"
        ),
        "Luciferase": (
            "ATGGAAGACGCCAAAAACATAAAGAAAGGCCCGGCGCCATTCTGGTAGTCACACTGAAACAGAGGCGGCGGAAGCCTACGAGGACGGCACCGAGGTGTTCCGGAAGTCCAAGTTCATCTGCACC"
            "ACCGGCAAGCTGCCCGTGCCCTGGCCCACCCTCGTGACCACCCTGACCTACGGCGTGCAGTGCTTCAGCCGCTACCCCGACCACATGAAGCAGCACGACTTCTTCAAG"
        ),
        "Beta-Galactosidase": (
            "ATGACCATGATTACGGATTCACTGGCCGTCGTTTTACAACGTCGTGACTGGGAAAACCCTGGCGTTACCCAACTTAATCGCCTTGCAGCACATCCCCCTTTCGCCAGCTGGCGTAATAGCGAAG"
            "AGGCCCGCACCGATCGCCCTTCCCAACAGTTGCGCAGCCTGAATGGCGAATGGCGCCTGATGCGGTATTTTCTCCTTACGCATCTGTGCGGTATTTCACACCGCATACGTCAAAGCAACGCCG"
            "CGTCGATGGTGCGCTGGGCGATCTGCA"
        )
    }

def matches_pam(pam_seq: str, pam_pattern: str) -> bool:
    pam_seq = pam_seq.upper()
    pam_pattern = pam_pattern.upper()
    if len(pam_seq) != len(pam_pattern):
        return False
    for base_seq, base_pat in zip(pam_seq, pam_pattern):
        if base_pat in WILDCARD_BASES:
            if base_seq not in WILDCARD_BASES[base_pat]:
                return False
        elif base_seq != base_pat:
            return False
    return True

def find_pam_sites(sequence: str, enzyme: str = "SpCas9") -> list[int]:
    """Return start indices of PAM (first base of the PAM triplet) for the chosen enzyme."""
    pam = PAM_SEQUENCES.get(enzyme)
    if not pam:
        raise ValueError(f"Unknown enzyme: {enzyme}")
    sequence = sequence.upper()
    target_len, pam_len = 20, len(pam)
    sites = []
    for i in range(len(sequence) - (target_len + pam_len) + 1):
        pam_seq = sequence[i + target_len: i + target_len + pam_len]
        if matches_pam(pam_seq, pam):
            sites.append(i + target_len)
    return sites

def find_grnas(sequence: str, pam: str = "NGG") -> list[tuple[str, int]]:
    """Return list of (20nt guide, start_pos) for the given PAM."""
    sequence = sequence.upper()
    out = []
    for i in range(len(sequence) - 23):  # 20 nt + 3 nt PAM
        guide = sequence[i: i + 20]
        pam_seq = sequence[i + 20: i + 23]
        if matches_pam(pam_seq, pam):
            out.append((guide, i))
    return out

# ---- GC utilities & annotations ----
def gc_percent(s: str) -> float:
    s = s.upper()
    g = s.count("G"); c = s.count("C")
    return 100.0 * (g + c) / max(1, len(s))

def gc_track(sequence: str, window: int = 60, step: int = 6):
    """Return (positions, gc_values) for a sliding-window GC% overview track."""
    seq = sequence.upper()
    xs, ys = [], []
    for start in range(0, max(1, len(seq) - window + 1), step):
        win = seq[start: start + window]
        xs.append(start + window / 2)
        ys.append(gc_percent(win))
    return xs, ys

def annotate_grnas(sequence: str, grnas: list[tuple[str, int]]):
    seq = sequence.upper()
    out = []
    for guide, pos in grnas:
        out.append({
            "pos": pos,
            "guide": guide,
            "GC%": round(gc_percent(guide), 2),
            "PAM": seq[pos + 20: pos + 23]
        })
    return out

