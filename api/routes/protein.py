from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from helix_core.crisprutils import sanitize_sequence, translate_dna

router = APIRouter()

AA_MW: dict[str, int] = {
    'A': 89,  'R': 174, 'N': 132, 'D': 133, 'C': 121,
    'Q': 146, 'E': 147, 'G': 75,  'H': 155, 'I': 131,
    'L': 131, 'K': 146, 'M': 149, 'F': 165, 'P': 115,
    'S': 105, 'T': 119, 'W': 204, 'Y': 181, 'V': 117,
}

ALL_AA = list('ACDEFGHIKLMNPQRSTVWY')


class TranslateRequest(BaseModel):
    sequence: str
    frame: int = 0


class TranslateResponse(BaseModel):
    protein: str
    length: int
    frame: int
    dna_used: str
    codon_count: int
    stop_position: int | None


class AnalyzeRequest(BaseModel):
    protein: str


class AnalyzeResponse(BaseModel):
    mw: float
    pi: float
    hydrophobic_percent: float
    aa_composition: dict[str, int]
    most_common: list[dict]


def _estimate_pi(protein: str) -> float:
    p = protein.replace('*', '').upper()
    acidic = p.count('D') + p.count('E')
    basic  = p.count('K') + p.count('R') + p.count('H')
    if acidic + basic == 0:
        return 7.0
    net   = basic - acidic
    total = acidic + basic
    return round(7.0 + (net / total) * 4.5, 1)


@router.post("/protein/translate", response_model=TranslateResponse)
def translate_sequence(req: TranslateRequest) -> TranslateResponse:
    frame  = max(0, min(2, req.frame))
    seq    = sanitize_sequence(req.sequence)
    sliced = seq[frame:]
    protein = translate_dna(sliced, frame=0, stop_at_stop=False)
    stop_idx = protein.find('*')
    return TranslateResponse(
        protein=protein,
        length=len(protein),
        frame=frame,
        dna_used=sliced,
        codon_count=len(sliced) // 3,
        stop_position=stop_idx if stop_idx != -1 else None,
    )


@router.post("/protein/analyze", response_model=AnalyzeResponse)
def analyze_protein(req: AnalyzeRequest) -> AnalyzeResponse:
    p = req.protein.replace('*', '').upper()
    n = max(len(p), 1)

    mw              = float(sum(AA_MW.get(aa, 0) for aa in p))
    pi              = _estimate_pi(p)
    hydrophobic_cnt = sum(1 for aa in p if aa in 'AILMFWV')
    hydrophobic_pct = round(hydrophobic_cnt / n * 100, 1)

    aa_comp     = {aa: p.count(aa) for aa in ALL_AA}
    most_common = sorted(
        [{'aa': aa, 'count': cnt} for aa, cnt in aa_comp.items()],
        key=lambda x: x['count'],
        reverse=True,
    )[:5]

    return AnalyzeResponse(
        mw=mw,
        pi=pi,
        hydrophobic_percent=hydrophobic_pct,
        aa_composition=aa_comp,
        most_common=most_common,
    )
