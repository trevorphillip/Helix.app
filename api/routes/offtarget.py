from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from helix_core.crisprutils import sanitize_sequence, reverse_complement

router = APIRouter()


class OffTargetRequest(BaseModel):
    guide: str
    sequence: str
    max_mismatches: int = 4


class OffTargetSite(BaseModel):
    position: int
    sequence: str
    pam: str
    strand: str
    total_mismatches: int
    seed_mismatches: int
    distal_mismatches: int
    risk_score: float
    risk_level: str
    mismatch_map: list[bool]


class OffTargetResponse(BaseModel):
    guide: str
    total_sites: int
    high_risk: int
    medium_risk: int
    low_risk: int
    sites: list[OffTargetSite]


def _scan_strand(guide: str, strand_seq: str, strand: str, max_mm: int) -> list[OffTargetSite]:
    sites: list[OffTargetSite] = []
    n = len(strand_seq)

    for i in range(n - 23 + 1):
        window = strand_seq[i:i + 20]
        pam    = strand_seq[i + 20:i + 23]

        if pam[1] != 'G' or pam[2] != 'G':
            continue

        seed_mm   = sum(1 for j in range(12)     if window[j] != guide[j])
        distal_mm = sum(1 for j in range(12, 20) if window[j] != guide[j])
        total_mm  = seed_mm + distal_mm

        if total_mm == 0 or total_mm > max_mm:
            continue

        mismatch_map = [window[j] != guide[j] for j in range(20)]
        risk_score   = max(0.0, min(1.0, 1.0 - (seed_mm * 0.3 + distal_mm * 0.1)))

        if risk_score >= 0.7:
            risk_level = "high"
        elif risk_score >= 0.4:
            risk_level = "medium"
        else:
            risk_level = "low"

        sites.append(OffTargetSite(
            position=i,
            sequence=window,
            pam=pam,
            strand=strand,
            total_mismatches=total_mm,
            seed_mismatches=seed_mm,
            distal_mismatches=distal_mm,
            risk_score=round(risk_score, 4),
            risk_level=risk_level,
            mismatch_map=mismatch_map,
        ))

    return sites


@router.post("/offtarget")
def find_off_targets(req: OffTargetRequest) -> OffTargetResponse:
    guide = sanitize_sequence(req.guide.upper())[:20]
    seq   = sanitize_sequence(req.sequence.upper())

    fwd_sites = _scan_strand(guide, seq, "+", req.max_mismatches)
    rev_sites = _scan_strand(guide, reverse_complement(seq), "-", req.max_mismatches)

    all_sites = sorted(fwd_sites + rev_sites, key=lambda s: s.risk_score, reverse=True)

    return OffTargetResponse(
        guide=guide,
        total_sites=len(all_sites),
        high_risk=sum(1 for s in all_sites if s.risk_level == "high"),
        medium_risk=sum(1 for s in all_sites if s.risk_level == "medium"),
        low_risk=sum(1 for s in all_sites if s.risk_level == "low"),
        sites=all_sites,
    )
