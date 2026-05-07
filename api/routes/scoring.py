from __future__ import annotations

from typing import List

from fastapi import APIRouter
from pydantic import BaseModel

from helix_core.scoring_model import score_guide_ml

router = APIRouter()


class ScoreRequest(BaseModel):
    guides: List[str]


class ScoreRow(BaseModel):
    guide: str
    score: float
    risk: str


class ScoreResponse(BaseModel):
    scores: List[ScoreRow]


def _risk(score: float) -> str:
    if score >= 0.8:
        return "low"
    if score >= 0.6:
        return "med"
    return "high"


@router.post("/score", response_model=ScoreResponse)
def score_guides(req: ScoreRequest) -> ScoreResponse:
    rows: list[ScoreRow] = []
    for guide in req.guides:
        g = guide.upper()
        sc = score_guide_ml(g)
        if sc is None:
            gc = (g.count("G") + g.count("C")) / max(1, len(g))
            sc = gc
        sc = round(float(sc), 4)
        rows.append(ScoreRow(guide=guide, score=sc, risk=_risk(sc)))
    return ScoreResponse(scores=rows)
