from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from helix_core.crisprutils import sanitize_sequence, find_sites_for_enzyme

router = APIRouter()

_ENZYME   = "SpCas9"
_SEED_LEN = 12


class VariantRequest(BaseModel):
    sequence: str   # query
    reference: str


class VariantRow(BaseModel):
    pos: int
    type: str
    ref: str
    alt: str
    impact: str


class VariantResponse(BaseModel):
    variants: list[VariantRow]
    total: int
    snp_count: int
    ins_count: int
    del_count: int


def _pam_positions(ref: str) -> frozenset[int]:
    pos: set[int] = set()
    for i in range(len(ref) - 2):
        if ref[i+1] == "G" and ref[i+2] == "G":   # NGG at [i, i+1, i+2]
            pos.add(i)
            pos.add(i + 1)
    return frozenset(pos)


def _seed_positions(ref: str) -> frozenset[int]:
    if len(ref) < 23:
        return frozenset()
    try:
        _, grnas = find_sites_for_enzyme(ref, _ENZYME)
    except Exception:
        return frozenset()
    pos: set[int] = set()
    for _, grna_start in grnas:
        for offset in range(_SEED_LEN):
            pos.add(grna_start + offset)
    return frozenset(pos)


def _impact(pos: int, pam: frozenset[int], seed: frozenset[int]) -> str:
    if pos in pam:
        return "disrupts_pam"
    if pos in seed:
        return "disrupts_seed"
    return "safe"


@router.post("/variants", response_model=VariantResponse)
def get_variants(req: VariantRequest) -> VariantResponse:
    ref = sanitize_sequence(req.reference)
    qry = sanitize_sequence(req.sequence)

    pam  = _pam_positions(ref)
    seed = _seed_positions(ref)

    max_len  = max(len(ref), len(qry), 1)
    variants: list[VariantRow] = []
    snp = ins = del_ = 0

    for i in range(max_len):
        has_ref = i < len(ref)
        has_qry = i < len(qry)

        if has_ref and has_qry:
            if ref[i] == qry[i]:
                continue
            variants.append(VariantRow(pos=i, type="SNP", ref=ref[i], alt=qry[i],
                                       impact=_impact(i, pam, seed)))
            snp += 1
        elif has_ref:
            variants.append(VariantRow(pos=i, type="DEL", ref=ref[i], alt="-",
                                       impact=_impact(i, pam, seed)))
            del_ += 1
        else:
            variants.append(VariantRow(pos=i, type="INS", ref="-", alt=qry[i],
                                       impact="safe"))
            ins += 1

    return VariantResponse(
        variants=variants,
        total=len(variants),
        snp_count=snp,
        ins_count=ins,
        del_count=del_,
    )
