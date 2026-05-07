from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from helix_core.crisprutils import sanitize_sequence, reverse_complement

router = APIRouter()


class PrimerRequest(BaseModel):
    sequence: str
    cut_position: int
    edit_type: str = "snp"
    edit_sequence: str = ""
    edit_position: int = 0
    edit_length: int = 1


class PrimerInfo(BaseModel):
    sequence: str
    tm: float
    gc: float
    length: int
    position: int


class PrimerResponse(BaseModel):
    forward_primer: PrimerInfo
    reverse_primer: PrimerInfo
    amplicon_size: int
    hdr_donor: str
    left_arm: str
    right_arm: str
    edit_preview: str


def _tm(seq: str) -> float:
    gc = seq.count('G') + seq.count('C')
    return 64.9 + 41 * (gc - 16.4) / len(seq)


def _has_gc_clamp(seq: str) -> bool:
    return seq[-1] in ('G', 'C')


def _has_hairpin(seq: str, min_stem: int = 4) -> bool:
    n = len(seq)
    for i in range(n - min_stem * 2 - 3):
        for stem_len in range(min_stem, (n - i) // 2 + 1):
            stem    = seq[i:i + stem_len]
            rc_stem = reverse_complement(stem)
            for j in range(i + stem_len + 3, n - stem_len + 1):
                if seq[j:j + stem_len] == rc_stem:
                    return True
    return False


def _design_primer(seq: str, start: int) -> PrimerInfo | None:
    best: tuple | None = None
    best_penalty = float('inf')

    for length in range(18, 25):
        candidate = seq[start:start + length]
        if len(candidate) < length:
            break
        gc_count = candidate.count('G') + candidate.count('C')
        gc       = gc_count / length
        tm       = _tm(candidate)
        penalty  = abs(tm - 60) + abs(gc - 0.5) * 5

        if best is None or penalty < best_penalty:
            best = (candidate, tm, gc, length)
            best_penalty = penalty

        if (0.4 <= gc <= 0.6 and 58 <= tm <= 62
                and _has_gc_clamp(candidate)
                and not _has_hairpin(candidate)):
            return PrimerInfo(sequence=candidate, tm=round(tm, 1),
                              gc=round(gc * 100, 1), length=length, position=start)

    if best:
        c, tm, gc, length = best
        return PrimerInfo(sequence=c, tm=round(tm, 1),
                          gc=round(gc * 100, 1), length=length, position=start)
    return None


@router.post("/primers/design")
def design_primers(req: PrimerRequest) -> PrimerResponse:
    seq = sanitize_sequence(req.sequence.upper())
    n   = len(seq)
    cut = min(max(req.cut_position, 0), n)

    # Forward primer: scan [cut-220, cut-130]
    fwd_region_start = max(0, cut - 220)
    fwd_region_end   = max(0, cut - 130)
    fwd_primer: PrimerInfo | None = None
    for s in range(fwd_region_start, fwd_region_end):
        p = _design_primer(seq, s)
        if p:
            fwd_primer = p
            break
    if fwd_primer is None:
        cand = seq[fwd_region_start:fwd_region_start + 20]
        if not cand:
            cand = seq[:20]
        fwd_primer = PrimerInfo(
            sequence=cand, tm=round(_tm(cand), 1),
            gc=round((cand.count('G') + cand.count('C')) / max(len(cand), 1) * 100, 1),
            length=len(cand), position=fwd_region_start,
        )

    # Reverse primer: scan [cut+130, cut+220] on reverse complement
    rev_region_start = min(cut + 130, n)
    rev_region_end   = min(cut + 220, n)
    rev_region_rc    = reverse_complement(seq[rev_region_start:rev_region_end])
    rev_primer: PrimerInfo | None = None
    for s in range(len(rev_region_rc) - 17):
        p = _design_primer(rev_region_rc, s)
        if p:
            rev_primer = PrimerInfo(
                sequence=p.sequence, tm=p.tm, gc=p.gc, length=p.length,
                position=rev_region_end - s - p.length,
            )
            break
    if rev_primer is None:
        cand = rev_region_rc[:20] if len(rev_region_rc) >= 20 else rev_region_rc
        if not cand:
            cand = seq[-20:]
        rev_primer = PrimerInfo(
            sequence=cand, tm=round(_tm(cand), 1),
            gc=round((cand.count('G') + cand.count('C')) / max(len(cand), 1) * 100, 1),
            length=len(cand), position=rev_region_end - len(cand),
        )

    amplicon_size = rev_primer.position + rev_primer.length - fwd_primer.position

    # HDR donor
    ep       = min(max(req.edit_position, 0), n)
    del_len  = max(0, req.edit_length) if req.edit_type == "deletion" else 0
    left_arm = seq[max(0, ep - 80):ep]
    if req.edit_type == "snp":
        edit_seq = sanitize_sequence(req.edit_sequence.upper())[:1]
    elif req.edit_type == "insertion":
        edit_seq = sanitize_sequence(req.edit_sequence.upper())
    else:
        edit_seq = ""
    right_arm = seq[ep + del_len:ep + del_len + 80]
    donor     = left_arm + edit_seq + right_arm

    ctx          = 10
    pre          = seq[max(0, ep - ctx):ep]
    post         = seq[ep + del_len:ep + del_len + ctx]
    edit_preview = f"{pre}[{edit_seq or '-'}]{post}"

    return PrimerResponse(
        forward_primer=fwd_primer,
        reverse_primer=rev_primer,
        amplicon_size=amplicon_size,
        hdr_donor=donor,
        left_arm=left_arm,
        right_arm=right_arm,
        edit_preview=edit_preview,
    )
