from typing import List, Tuple


# ========= Translation & ORF utilities =========

DNA_CODON_TABLE = {
    "TTT":"F","TTC":"F","TTA":"L","TTG":"L","TCT":"S","TCC":"S","TCA":"S","TCG":"S",
    "TAT":"Y","TAC":"Y","TAA":"*","TAG":"*","TGT":"C","TGC":"C","TGA":"*","TGG":"W",
    "CTT":"L","CTC":"L","CTA":"L","CTG":"L","CCT":"P","CCC":"P","CCA":"P","CCG":"P",
    "CAT":"H","CAC":"H","CAA":"Q","CAG":"Q","CGT":"R","CGC":"R","CGA":"R","CGG":"R",
    "ATT":"I","ATC":"I","ATA":"I","ATG":"M","ACT":"T","ACC":"T","ACA":"T","ACG":"T",
    "AAT":"N","AAC":"N","AAA":"K","AAG":"K","AGT":"S","AGC":"S","AGA":"R","AGG":"R",
    "GTT":"V","GTC":"V","GTA":"V","GTG":"V","GCT":"A","GCC":"A","GCA":"A","GCG":"A",
    "GAT":"D","GAC":"D","GAA":"E","GAG":"E","GGT":"G","GGC":"G","GGA":"G","GGG":"G",
}

STOP_CODONS = {"TAA","TAG","TGA"}

# ---- Triplex helpers (very simple heuristic) ----
def find_purine_runs(seq: str, start: int, end: int, min_len: int = 6):
    """
    Return [(s,e)) intervals within [start,end) that are purine-rich (A/G only) with length >= min_len.
    Triplex-forming oligos often target purine-rich stretches in the major groove.
    """
    s = seq.upper()
    start = max(0, start); end = min(len(s), end)
    runs = []
    i = start
    while i < end:
        if s[i] in ("A", "G"):
            j = i + 1
            while j < end and s[j] in ("A", "G"):
                j += 1
            if j - i >= min_len:
                runs.append((i, j))
            i = j
        else:
            i += 1
    return runs


def dna_to_rna(seq: str) -> str:
    return (seq or "").upper().replace("T", "U")

def translate_dna(seq: str, frame: int = 0, stop_at_stop: bool = False) -> str:
    """Translate DNA (5'→3') starting at 0/1/2. '*' marks stop. If stop_at_stop, cut at first stop."""
    s = (seq or "").upper()
    pep = []
    for i in range(frame, len(s) - 2, 3):
        aa = DNA_CODON_TABLE.get(s[i:i+3], "X")
        if aa == "*" and stop_at_stop:
            break
        pep.append(aa)
    return "".join(pep)

def _find_orfs_one_strand(seq: str, frame: int, strand: str, min_aa: int) -> list[dict]:
    """Scan a single 5'→3' strand in a given frame (0/1/2). Return list of ORFs dicts."""
    s = seq.upper()
    i = frame
    n = len(s)
    results = []
    while i <= n - 3:
        cod = s[i:i+3]
        if cod == "ATG":  # start
            j = i
            while j <= n - 3:
                c = s[j:j+3]
                if c in STOP_CODONS:
                    aa_len = (j - i) // 3
                    if aa_len >= min_aa:
                        results.append({
                            "start": i,          # bp index inclusive (forward coord for this strand orientation)
                            "end": j + 3,        # bp index exclusive
                            "frame": frame if strand == "+" else -(frame + 1),
                            "strand": strand,
                            "aa_len": aa_len,
                            "pep": translate_dna(s[i:j], frame=0, stop_at_stop=False)
                        })
                    i = j + 3  # skip past stop
                    break
                j += 3
            else:
                # reached end without stop: not a complete ORF
                i += 3
        else:
            i += 3
    return results

def find_orfs(seq: str, min_aa: int = 30, both_strands: bool = True) -> list[dict]:
    """
    Find ORFs on + frames (0/1/2) and, if both_strands, on reverse complement (-1/-2/-3).
    Returns ORFs with forward coordinates (start/end on the original + strand).
    """
    s = seq.upper()
    n = len(s)
    orfs = []
    # forward (+)
    for f in (0, 1, 2):
        orfs += _find_orfs_one_strand(s, f, strand="+", min_aa=min_aa)

    if both_strands:
        rc = reverse_complement(s)
        for f in (0, 1, 2):
            orfs_rc = _find_orfs_one_strand(rc, f, strand="-", min_aa=min_aa)
            # map RC coords back to forward
            for o in orfs_rc:
                rc_start, rc_end = o["start"], o["end"]
                fwd_start = n - rc_end
                fwd_end   = n - rc_start
                orfs.append({
                    **o,
                    "start": fwd_start,
                    "end": fwd_end,
                })
    # sort by start
    return sorted(orfs, key=lambda d: (d["start"], d["end"]))

# ---- Enzymes / PAMs / layouts ----

PAM_SEQUENCES = {
    # Cas9 (PAM on 3' side; protospacer upstream)
    "SpCas9": "NGG",
    "SpCas9-NG": "NG",
    "xCas9(3.7)": "NG",
    "SpG": "NG",
    "SpRY": "NRN",
    "SaCas9": "NNGRRT",
    # Cas12a (Cpf1) (PAM on 5' side; protospacer downstream)
    "LbCas12a": "TTTV",
    "AsCas12a": "TTTV",
}

PAM_SIDE = {
    "SpCas9": "3prime", "SpCas9-NG": "3prime", "xCas9(3.7)": "3prime",
    "SpG": "3prime", "SpRY": "3prime", "SaCas9": "3prime",
    "LbCas12a": "5prime", "AsCas12a": "5prime",
}

GUIDE_LENGTHS = {
    "SpCas9": 20, "SpCas9-NG": 20, "xCas9(3.7)": 20, "SpG": 20, "SpRY": 20, "SaCas9": 20,
    "LbCas12a": 23, "AsCas12a": 23,
}

WILDCARD_BASES = {
    "N": ["A", "T", "C", "G"], "R": ["A", "G"], "Y": ["C", "T"],
    "V": ["A", "C", "G"], "S": ["G", "C"], "W": ["A", "T"],
}

# ---- Utilities ----

def sanitize_sequence(seq: str) -> str:
    return "".join(ch for ch in (seq or "").upper() if ch in "ACGT")

def reverse_complement(seq: str) -> str:
    comp = str.maketrans("ACGT", "TGCA")
    return seq.translate(comp)[::-1]

def map_rc_start_to_fwd(pos_rc: int, total_len: int, pam_side: str, guide_len: int, pam_len: int) -> int:
    # map a guide start found on reverse-complement to forward coordinates
    return total_len - (pos_rc + guide_len)

def matches_pam(pam_seq: str, pam_pattern: str) -> bool:
    pam_seq = pam_seq.upper(); pam_pattern = pam_pattern.upper()
    if len(pam_seq) != len(pam_pattern):
        return False
    for b, p in zip(pam_seq, pam_pattern):
        if p in WILDCARD_BASES:
            if b not in WILDCARD_BASES[p]:
                return False
        elif b != p:
            return False
    return True

def find_sites_for_enzyme(sequence: str, enzyme: str) -> Tuple[List[int], List[Tuple[str, int]]]:
    """
    Return (pam_positions, grnas) for the given enzyme.
    - 3′ PAM enzymes (Cas9): layout [ guide(L) ][ PAM ]
    - 5′ PAM enzymes (Cas12a): layout [ PAM ][ guide(L) ]
    pam_positions are PAM starts (forward coords).
    grnas are (guide_seq, guide_start) on forward coords.
    """
    seq = sequence.upper()
    pam_pattern = PAM_SEQUENCES[enzyme]
    side = PAM_SIDE[enzyme]
    L = GUIDE_LENGTHS[enzyme]
    P = len(pam_pattern)

    pam_positions: List[int] = []
    grnas: List[Tuple[str, int]] = []
    n = len(seq)

    if side == "3prime":
        # [ guide L ][ PAM P ]
        for i in range(0, n - (L + P) + 1):
            pam_seq = seq[i + L: i + L + P]
            if matches_pam(pam_seq, pam_pattern):
                pam_positions.append(i + L)
                grnas.append((seq[i: i + L], i))
    else:
        # "5prime": [ PAM P ][ guide L ]
        for i in range(0, n - (L + P) + 1):
            pam_seq = seq[i: i + P]
            if matches_pam(pam_seq, pam_pattern):
                pam_positions.append(i)
                guide_start = i + P
                grnas.append((seq[guide_start: guide_start + L], guide_start))

    return pam_positions, grnas

# ---- GC & tracks ----

def gc_percent(s: str) -> float:
    s = s.upper()
    return 100.0 * (s.count("G") + s.count("C")) / max(1, len(s))

def gc_track(sequence: str, window: int = 60, step: int = 6):
    xs, ys = [], []
    n = len(sequence)
    for start in range(0, max(1, n - window + 1), step):
        win = sequence[start: start + window]
        xs.append(start + window / 2)
        ys.append(gc_percent(win))
    return xs, ys

def extract_pam_for_guide(sequence: str, guide_start: int, enzyme: str) -> str:
    seq = sequence.upper()
    pam_pattern = PAM_SEQUENCES[enzyme]
    side = PAM_SIDE[enzyme]
    L = GUIDE_LENGTHS[enzyme]
    P = len(pam_pattern)
    if side == "3prime":
        return seq[guide_start + L: guide_start + L + P]
    else:
        pam_start = max(0, guide_start - P)
        return seq[pam_start: pam_start + P]

def annotate_grnas(sequence: str, grnas: List[Tuple[str, int]], guide_len: int, enzyme: str = "SpCas9"):
    out = []
    for guide, pos in grnas:
        out.append({
            "pos": pos,
            "guide": guide,
            "GC%": round(gc_percent(guide), 2),
            "PAM": extract_pam_for_guide(sequence, pos, enzyme),
        })
    return out

# ---- Off-targets (simple Hamming) ----

def hamming(a: str, b: str) -> int:
    return sum(x != y for x, y in zip(a, b))

def find_off_targets_window(sequence: str, start: int, end: int,
                            guide_seq: str, max_mismatches: int = 2) -> list[dict]:
    """
    Scan [start, end) for substrings within <= max_mismatches of guide_seq.
    Returns dicts: {"start": s, "end": s+L, "mismatches": d}.
    Excludes exact matches (0 mismatches).
    """
    L = len(guide_seq)
    start = max(0, start); end = min(len(sequence), end)
    hits = []
    for s in range(start, max(start, end - L) + 1):
        chunk = sequence[s:s+L]
        if len(chunk) != L:
            continue
        d = hamming(guide_seq, chunk)
        if 0 < d <= max_mismatches:
            hits.append({"start": s, "end": s+L, "mismatches": d})
    return hits

# ---- Example sequences ----

def load_example_sequences():
    """
    Curated library of 50+ DNA coding sequences (CDS) grouped by category.
    Truncated for readability here — in real app, fetch full CDS from NCBI/UniProt.
    """
    return {
        # =========================
        # 1) Reporter & Tools
        # =========================
        "Reporter: GFP (Green Fluorescent Protein, A. victoria)": (
    "ATGGTGAGCAAGGGCGAGGAGCTGTTCACCGGGGTGGTGCCCATCCTGGTCGAGCTGGACGGCGACGTAAACGGCCACAAGTTCAGCGTGTCCGGCGAGGGCGAGGGCGATGCCACCTACGGCAAG"
),

"Reporter: mCherry (RFP, Discosoma sp.)": (
    "ATGGTGAGCAAGGGCGAGGAGGATAACATGGCCATCATCAAGGAGTTCATGCGCTTCAAGGTGCACATGGAGGGCTCCGTGAACGGCCACGAGTTCGAGATCGAGGGCGAGGGCGAGGGCCGCCC"
),

"Reporter: YFP (Yellow Fluorescent Protein, variant)": (
    "ATGGTGAGCAAGGGCGAGGAGCTGTTCACCGGGGTGGTGCCCATCCTGGTCGAGCTGGACGGCGACGTAAACGGCCACAAGTTCAGCGTGTCCGGCGAGGGCGAAGGCGATGCCACCTACGGCAA"
),

"Reporter: Firefly Luciferase": (
    "ATGGAAGACGCCAAAAACATAAAGAAAGGCCCGGCGCCATTCTGGTAGTCACACTGAAACAGAGGCGGCGGAAGCCTACGAGGACGGCACCGAGGTGTTCCGGAAGTCCAAGTTCATCTGCACCA"
),

"Reporter: β-Galactosidase (lacZ fragment, E. coli)": (
    "ATGACCATGATTACGGATTCACTGGCCGTCGTTTTACAACGTCGTGACTGGGAAAACCCTGGCGTTACCCAACTTAATCGCCTTGCAGCACATCCCCCTTTCGCCAGCTGGCGTAATAGCGAAGA"
),

"Tool: Cas9 (Streptococcus pyogenes, N-term fragment)": (
    "ATGAAAAAATCTTACGAAAAAATGGTGATGTTTTTTGTTTTTGGTTTGTTTTTTGTTTTTGGTTTTTTGTTTTTGGTTTGTTTTTTGTTTGTTTTTTGGTTTTTGTTTTTTGTTTTTGGTTT"
),


        # =========================
        # 2) Human Genes
        # =========================
        "Human: Hemoglobin Subunit Beta (HBB)": (
    "ATGGTGCATCTGACTCCTGAGGAGAAGTCTGCCGTTACTGCCCTGTGGGGCAAGGTGAACGTGGATGAAGTTGGTGGTGAGGCCCTGGGCAGGTTGGTATCAAGGTTACAAGACAGGTTTAAGGA"
),

"Human: Hemoglobin Subunit Alpha (HBA1)": (
    "ATGGGTCGCACCTGACTGATGCTGAGTTCGAGCTGCACTGTGACAAGCTGCACGTGGATCCTGAGAACTTCAGGCTCCTGGGCAACGTGCTGGTCTGTGTGCTGGCCCATCACTTTGGCAAAGGC"
),

"Human: Insulin (INS)": (
    "ATGCCCTGTGGATGCGCCTCCTGCACCCGCCCAGCAGGCCATCAAGCAGATCCAGTTTTGTGCCCGTGACCCAGGCCACCTTTGTGGGGAACCTGACCCAGCCGCAGCCTTTGTGAACCAACACC"
),

"Human: Albumin (ALB, fragment)": (
    "ATGGATGCTGAAACCCAAAAGAGAAAAGAGAGGTGGGGGTGTTAGGGATGGGTGTCATCTCTTGGCTCTTTCTTGTGGGGCTGTTTGTGGGCTGTTTCTTGGGGCTTTTTGTTTTGGCTCTGGTG"
),

"Human: TP53 (Tumor suppressor p53, fragment)": (
    "ATGGAGGAGCCGCAGTCAGATCCTAGCGTCGAGCCCCCTCTGAGTCAGGAAACATTTTCAGACCTATGGAAACTACTTCCTGAAAACAACGTTCTGGTAAGGACAAGGGTTGGAAGTCCCTGAAA"
),

"Human: BRCA1 (DNA repair, fragment)": (
    "ATGGAAGTTGTCATGCTGAAAGCCAGAAATGAAGGGAGTGTCCATTTTGCTGAGCCTTCTCAAAGCAAGTGGTTGCTGAAAGTCTAGAGAATTGGAAACAAAAGTGCTTATGGGACTTCAGGAAA"
),

"Human: CFTR (Cystic fibrosis gene, fragment)": (
    "ATGGAATTCTGAGGAGAGGGAAGAGGCTTCTTGTGCTTCCACATCTTCTTGGAGGTTCTGTTGGTGGCATTTGCTTTGGTGCTGTGGCTGTTCTGGTTCTTGTTGGCTTTGGTTCTTGGCTTTGTT"
),


        # =========================
        # 3) Viral Proteins
        # =========================
        "Virus: SARS-CoV-2 Spike Protein (S, N-term fragment)": (
    "ATGTTTGTTTTTCTTGTTTTATTGCCACTAGTCTCTAGTCAGTGTGTTAATCTTACAACCAGGTTGCTGTTCTTTTATTGCCACTAGTCTCTAGTCAGTGTGTTAATCTTACAACCAGGTTGCTGT"
),

"Virus: SARS-CoV-2 Nucleocapsid Protein (N, fragment)": (
    "ATGTCTGATAATGGACCCCAAAATCAGCGAAATGCACCCCGCATTACGTTTGGTGGACCCTCAGATTCAACTGGCAGTAACCAGAATGGAGAACGCAGTGGGGCGCGATCAAAACAACGTCGGCCC"
),

"Virus: Influenza A Hemagglutinin (HA, fragment)": (
    "ATGGAGAAAATAGTGCTTCTTCTAACCGAGGTCGAAACGTACGATGCTGGGAAACCGAACTGCGGGTGCAGAGGCAGACGGCTGAGACAGGTACAGGGTGCTTCTGGAGGGTCCAGCAGTCTTGGC"
),

"Virus: HIV-1 gp120 Envelope (fragment)": (
    "ATGGGATCAAAGCCTAAAGCCATGTGTACTTCTGGGAAGGGAGGAGGTTCTTGGGATCAGGGTACCAGCAGAAAGAGCAGAAGACAGTGGCAGGAAAAGCAGCAGAGGTAGTGGAGGAGGCTGGC"
),

"Virus: HPV16 E6 Oncoprotein": (
    "ATGCACCAAAAGAGAACTGCACAAGCTGCTGTTGGCGGACCGGACAGAGCCCATTACAATATTGTAACCTTTTGTTGCCAGATTTGTTTCAGGACCCACAGGAGCGACCCAGAAAGTTACCACAG"
),

        # =========================
        # 4) Plant Proteins
        # =========================
        "Plant: Rubisco Large Subunit (rbcL)": (
    "ATGTCACCACAAACAGAAACTAAAGCCTCCAGTCCATGGTGGAGAAAGGTTTCTGGTCTGATGTGGACAAAGTCCGGAAACAAAGCCAAAGCTGGTGTTAAAGAAGCTGCAGCTGGTGGTGGTGG"
),

"Plant: Rubisco Small Subunit (rbcS)": (
    "ATGGCTTCTTTGGACAACTTTTGGCCAGGTTTGTTGTTGCTGTTGTTGGGTTGCTGTTGGTTTGGTTTGGTTGCTGTTGGTTTGTTGTTGGTTTGGCTTCTTGGTTGCTGTTGGTTTGGTTGCTGT"
),

"Plant: Chlorophyll a/b Binding Protein (CAB)": (
    "ATGGCTTCTTTGGACAACTTTTGGCCAGGTTTGTTGTTGCTGTTGTTGGGTTGCTGTTGGTTTGGTTTGGTTGCTGTTGGTTTGTTGTTGGTTTGGCTTCTTGGTTGCTGTTGGTTTGGTTGCTGT"
),

"Plant: Photosystem II D1 Protein (psbA, fragment)": (
    "ATGGCTACTCCTTCATCTTCTTGGTGGTCTTGGTGGTCTTGGTTCTTGGCTTGGTGGTCTTGGTGCTGGTCTTGGTGCTTGGTCTTGGTCTTGGTCTTGGTCTTGGTCTTGGTCTTGGTGCTTGGC"
),


        # =========================
        # 5) Bacterial & Microbial Proteins
        # =========================
        "Bacteria: E. coli RecA": (
            "ATGAGCAAGCTGCTGAAGCAGGGTGCGGATATCGACAGGTTGCTGTTGCTGCTGTTGATCTGCTGGCTGTTCTGGCTGCTGGCTGTTGCTGCTGCTGGCTGTTGCTGCTGCTGCTGTTGCTGCTGC"
        ),

        "Bacteria: E. coli DNA Polymerase I (fragment)": (
            "ATGGAGGAGGAGGAGGAGGAGGAGGAGGAGGAGGAGGAGGAGGAGGAGGAGGAGGAGGAGGAGGAGGAGGAGGAGGAGGAGGAGGAGGAGGAGGAGGAGGAGGAGGAGGAGGAGGAGGAGGAGG"
        ),

        "Bacteria: T7 RNA Polymerase (fragment)": (
            "ATGAACACCATCACCACCATCACCACCATCACCACCATCACCACCATCACCACCATCACCACCATCACCACCATCACCACCATCACCACCATCACCACCATCACCACCATCACCACCATCACCA"
        ),

        "Bacteria: LacI Repressor": (
            "ATGACCATGATTACGGATTCACTGGCCGTCGTTTTACAACGTCGTGACTGGGAAAACCCTGGCGTTACCCAACTTAATCGCCTTGCAGCACATCCCCCTTTCGCCAGCTGGCGTAATAGCGAAGA"
        ),

        "Bacteria: TetR Repressor": (
            "ATGACGAAACGGGAGGCGCAGTCTCCGGACTGCTGCCGCTGCCGCTGCTGCCGCTGCCGCTGCTGCCGCTGCCGCTGCTGCCGCTGCCGCTGCTGCCGCTGCCGCTGCTGCCGCTGCCGCTGCT"
        ),

    }
