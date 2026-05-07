from __future__ import annotations

from typing import List

from fastapi import APIRouter
from pydantic import BaseModel

from helix_core.crisprutils import find_sites_for_enzyme, reverse_complement, gc_track
from helix_core.scoring_model import score_guide_ml

router = APIRouter()


class GRNARequest(BaseModel):
    sequence: str
    enzyme: str = "SpCas9"
    scan_reverse: bool = False


class GRNARow(BaseModel):
    pos: int
    guide: str
    strand: str
    gc: float
    score: float
    risk: str


class GCTrack(BaseModel):
    x: List[int]
    y: List[float]


class GRNAResponse(BaseModel):
    grnas: List[GRNARow]
    pam_count: int
    gc_track: GCTrack


def _gc(guide: str) -> float:
    g = guide.upper()
    return 100.0 * (g.count("G") + g.count("C")) / max(1, len(g))


def _risk(score: float) -> str:
    if score >= 0.8:
        return "low"
    if score >= 0.6:
        return "med"
    return "high"


def _score(guide: str) -> float:
    gc_frac = _gc(guide) / 100.0
    return score_guide_ml(guide) if score_guide_ml(guide) is not None else gc_frac


@router.post("/grnas", response_model=GRNAResponse)
def get_grnas(req: GRNARequest) -> GRNAResponse:
    seq = req.sequence.upper()

    pam_sites_fwd, grnas_fwd = find_sites_for_enzyme(seq, enzyme=req.enzyme)
    all_pam_sites = list(pam_sites_fwd)
    entries: list[tuple[str, int, str]] = [(g, p, "+") for g, p in grnas_fwd]

    if req.scan_reverse:
        rc = reverse_complement(seq)
        pam_sites_rev, grnas_rev = find_sites_for_enzyme(rc, enzyme=req.enzyme)
        all_pam_sites.extend(pam_sites_rev)
        entries.extend((g, p, "-") for g, p in grnas_rev)

    rows: list[GRNARow] = []
    for guide, pos, strand in entries:
        sc = score_guide_ml(guide)
        if sc is None:
            sc = _gc(guide) / 100.0
        rows.append(GRNARow(
            pos=pos,
            guide=guide,
            strand=strand,
            gc=round(_gc(guide), 2),
            score=round(sc, 4),
            risk=_risk(sc),
        ))

    rows.sort(key=lambda r: r.score, reverse=True)

    gc_x, gc_y = gc_track(seq, window=60, step=6)

    return GRNAResponse(
        grnas=rows,
        pam_count=len(all_pam_sites),
        gc_track=GCTrack(x=[int(v) for v in gc_x], y=[round(float(v), 4) for v in gc_y]),
    )
