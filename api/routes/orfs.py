from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from helix_core.crisprutils import sanitize_sequence, reverse_complement, translate_dna

router = APIRouter()

_STOP = {"TAA", "TAG", "TGA"}


class OrfRequest(BaseModel):
    sequence: str
    min_length: int = 100


class OrfRow(BaseModel):
    id: int
    frame: str
    start: int
    end: int
    length: int
    protein: str
    full_protein: str


class OrfResponse(BaseModel):
    orfs: list[OrfRow]
    total: int
    sequence_length: int


def _scan(seq: str, offset: int, strand: str, original_len: int, min_length: int) -> list[dict]:
    s = seq.upper()
    n = len(s)
    label = f"{'+' if strand == '+' else '-'}{offset + 1}"
    orfs: list[dict] = []
    i = offset
    while i <= n - 3:
        if s[i:i+3] == "ATG":
            j = i + 3
            while j <= n - 3:
                if s[j:j+3] in _STOP:
                    orf_len = j + 3 - i
                    if orf_len >= min_length:
                        if strand == "+":
                            start, end = i, j + 3
                        else:
                            start = original_len - (j + 3)
                            end = original_len - i
                        orfs.append({
                            "frame": label,
                            "start": start,
                            "end": end,
                            "length": orf_len,
                            "full_protein": translate_dna(s[i:j], frame=0, stop_at_stop=False),
                        })
                    i = j + 3
                    break
                j += 3
            else:
                i += 3
        else:
            i += 3
    return orfs


@router.post("/orfs", response_model=OrfResponse)
def get_orfs(req: OrfRequest) -> OrfResponse:
    seq = sanitize_sequence(req.sequence)
    seq_len = len(seq)

    raw: list[dict] = []
    for offset in range(3):
        raw.extend(_scan(seq, offset, "+", seq_len, req.min_length))
    rc = reverse_complement(seq)
    for offset in range(3):
        raw.extend(_scan(rc, offset, "-", seq_len, req.min_length))

    raw.sort(key=lambda o: o["length"], reverse=True)

    orfs = []
    for idx, o in enumerate(raw):
        pep = o["full_protein"]
        protein = (pep[:30] + "...") if len(pep) > 30 else pep
        orfs.append(OrfRow(
            id=idx + 1,
            frame=o["frame"],
            start=o["start"],
            end=o["end"],
            length=o["length"],
            protein=protein,
            full_protein=pep,
        ))

    return OrfResponse(orfs=orfs, total=len(orfs), sequence_length=seq_len)