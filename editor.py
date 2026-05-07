# editor.py
from typing import Tuple

def apply_snp(seq: str, pos: int, base: str) -> str:
    s = list(seq.upper())
    if 0 <= pos < len(s):
        s[pos] = base.upper()
    return "".join(s)

def apply_insertion(seq: str, pos: int, insert_seq: str) -> str:
    pos = max(0, min(len(seq), pos))
    return seq[:pos] + insert_seq.upper() + seq[pos:]

def apply_deletion(seq: str, start: int, end: int) -> str:
    start, end = sorted((max(0, start), min(len(seq), end)))
    return seq[:start] + seq[end:]

def apply_cut_and_ko(seq: str, cut_pos: int, del_len: int = 5) -> Tuple[str, int, int]:
    """
    Simulate a CRISPR cut at cut_pos and a small KO deletion around it.
    Returns (new_seq, del_start, del_end).
    """
    s = max(0, cut_pos - del_len//2)
    e = min(len(seq), cut_pos + (del_len - del_len//2))
    return apply_deletion(seq, s, e), s, e
