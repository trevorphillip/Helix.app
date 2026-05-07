# helix_api/main.py

from __future__ import annotations

from typing import List, Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

# 🔬 import your existing logic
from helix_core.crisprutils import (
    PAM_SEQUENCES,
    PAM_SIDE,
    GUIDE_LENGTHS,
    sanitize_sequence,
    find_sites_for_enzyme,
    gc_track,
)

app = FastAPI(
    title="Helix Genetics API",
    description="Backend API for Helix — CRISPR, ORFs, motifs, etc.",
    version="0.1.0",
)


# ─────────────────────────────────────────────────────────────────────────────
# Pydantic models (request / response)
# ─────────────────────────────────────────────────────────────────────────────

class GrnaRequest(BaseModel):
    sequence: str = Field(..., description="DNA sequence (5'→3')")
    enzyme: str = Field("SpCas9", description="Key from PAM_SEQUENCES, e.g. 'SpCas9'")
    scan_reverse: bool = Field(
        False,
        description="Whether to also scan reverse complement (− strand)"
    )


class GrnaHit(BaseModel):
    strand: Literal["+", "-"]
    position: int = Field(..., description="0-based start position of protospacer")
    guide: str = Field(..., description="gRNA / protospacer sequence")
    pam: str = Field(..., description="PAM sequence")
    gc_percent: float = Field(..., description="GC% of the guide")


class GrnaResponse(BaseModel):
    enzyme: str
    pam_pattern: str
    pam_side: str
    guide_length: int
    length_bp: int
    pam_count: int
    grna_count: int
    gc_track_x: List[int]
    gc_track_y: List[float]
    hits: List[GrnaHit]


# ─────────────────────────────────────────────────────────────────────────────
# Health check
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok"}


# ─────────────────────────────────────────────────────────────────────────────
# Core CRISPR endpoint
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/api/grnas", response_model=GrnaResponse)
def scan_grnas(payload: GrnaRequest) -> GrnaResponse:
    # 1) Clean sequence
    seq = sanitize_sequence(payload.sequence)
    if not seq:
        raise HTTPException(status_code=400, detail="No valid A/C/G/T bases in sequence.")

    # 2) Validate enzyme
    enzyme = payload.enzyme
    if enzyme not in PAM_SEQUENCES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown enzyme '{enzyme}'. Known: {sorted(PAM_SEQUENCES.keys())}"
        )

    pam_pattern = PAM_SEQUENCES[enzyme]
    pam_side = PAM_SIDE[enzyme]
    guide_len = GUIDE_LENGTHS[enzyme]

    # 3) Scan forward strand
    pam_sites_fwd, grnas_fwd = find_sites_for_enzyme(seq, enzyme=enzyme)

    # 4) Optionally also scan reverse
    from helix_core.crisprutils import reverse_complement, map_rc_start_to_fwd

    pam_sites_rev, grnas_rev = [], []
    if payload.scan_reverse:
        rc = reverse_complement(seq)
        pam_sites_rc, grnas_rc = find_sites_for_enzyme(rc, enzyme=enzyme)
        pam_sites_rev = [
            map_rc_start_to_fwd(p, len(seq), pam_side, guide_len, pam_len=len(pam_pattern))
            for p in pam_sites_rc
        ]
        grnas_rev = [
            (g, map_rc_start_to_fwd(pos, len(seq), pam_side, guide_len, pam_len=len(pam_pattern)))
            for (g, pos) in grnas_rc
        ]

    # 5) Combine
    pam_sites_all = [(p, "+") for p in pam_sites_fwd] + [(p, "-") for p in pam_sites_rev]
    grnas_all = [("+", g, p) for (g, p) in grnas_fwd] + [("-", g, p) for (g, p) in grnas_rev]

    # 6) GC track (same as Streamlit app)
    x_gc, y_gc = gc_track(seq, window=60, step=6)

    def _gc_pct(s: str) -> float:
        s = s.upper()
        return 100.0 * (s.count("G") + s.count("C")) / max(1, len(s))

    hits: list[GrnaHit] = []
    for strand, g, pos in grnas_all:
        # determine PAM sequence at this position
        if pam_side.startswith("3"):
            pam_here = seq[pos + guide_len: pos + guide_len + len(pam_pattern)]
        else:  # "5prime"
            pam_here = seq[max(0, pos - len(pam_pattern)): pos]

        hits.append(
            GrnaHit(
                strand=strand,
                position=pos,
                guide=g,
                pam=pam_here,
                gc_percent=round(_gc_pct(g), 1),
            )
        )

    return GrnaResponse(
        enzyme=enzyme,
        pam_pattern=pam_pattern,
        pam_side=pam_side,
        guide_length=guide_len,
        length_bp=len(seq),
        pam_count=len(pam_sites_all),
        grna_count=len(hits),
        gc_track_x=list(x_gc),
        gc_track_y=list(y_gc),
        hits=hits,
    )
