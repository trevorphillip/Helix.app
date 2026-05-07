from __future__ import annotations

from typing import Any, List

from fastapi import FastAPI
from pydantic import BaseModel

# Reuse your existing Helix core
from helix_apps.crispr_sandbox.services import analyze_grnas
from helix_core.crisprutils import sanitize_sequence, translate_dna, reverse_complement

app = FastAPI(title="Helix Mobile API", version="0.1.0")


class RNAToolsRequest(BaseModel):
    dna: str           # full DNA sequence (A/C/G/T)
    start: int         # window start (0-based)
    end: int           # window end (0-based, exclusive)
    max_codons: int    # how many codons to include from that window


class RNACodonRow(BaseModel):
    codon_index: int
    genomic_start: int
    dna_codon: str
    mrna_codon: str
    trna_anticodon: str
    aa_one: str


class RNAToolsResponse(BaseModel):
    rows: List[RNACodonRow]
    used_start: int
    used_end: int
    total_codons: int


class GRNARequest(BaseModel):
    sequence: str
    enzyme: str = "SpCas9"
    scan_reverse: bool = False


class GRNARow(BaseModel):
    pos: int
    guide: str
    strand: str
    pam: str
    gc_percent: float


class GRNAResponse(BaseModel):
    sequence_length: int
    enzyme: str
    pam: str
    pam_side: str
    guide_length: int
    pam_count: int
    grnas: List[GRNARow]


def dna_to_mrna(dna: str) -> str:
    return (dna or "").upper().replace("T", "U")


def mrna_to_trna_anticodon(mrna_codon: str) -> str:
    """
    mRNA codon (5'→3', with U) → tRNA anticodon (3'→5', with U).
    Convert U→T, reverse_complement as DNA, then T→U.
    """
    dna_like = (mrna_codon or "").upper().replace("U", "T")
    anti_dna = reverse_complement(dna_like)
    return anti_dna.replace("T", "U")


def _to_grna_response(data: dict[str, Any]) -> GRNAResponse:
    rows = [
        GRNARow(
            pos=row["pos"],
            guide=row["guide"],
            strand=row["strand"],
            pam=row["PAM"],
            gc_percent=row["GC%"],
        )
        for row in data["grnas"]
    ]
    return GRNAResponse(
        sequence_length=data["sequence_length"],
        enzyme=data["enzyme"],
        pam=data["pam"],
        pam_side=data["pam_side"],
        guide_length=data["guide_length"],
        pam_count=data["pam_count"],
        grnas=rows,
    )


@app.post("/rna_tools", response_model=RNAToolsResponse)
def rna_tools(req: RNAToolsRequest) -> RNAToolsResponse:
    # 1) Clean DNA
    seq = sanitize_sequence(req.dna or "")
    n = len(seq)
    if n == 0:
        return RNAToolsResponse(rows=[], used_start=0, used_end=0, total_codons=0)

    # Clamp window to sequence length
    start = max(0, min(req.start, n))
    end = max(start, min(req.end, n))

    region = seq[start:end]
    if len(region) < 3:
        return RNAToolsResponse(rows=[], used_start=start, used_end=end, total_codons=0)

    # Only full codons
    usable_len = (len(region) // 3) * 3
    region = region[:usable_len]
    total_codons = usable_len // 3

    max_codons = max(1, min(req.max_codons, total_codons))

    rows: list[RNACodonRow] = []
    for i in range(0, max_codons * 3, 3):
        dna_codon = region[i:i+3]
        mrna_codon = dna_to_mrna(dna_codon)
        trna = mrna_to_trna_anticodon(mrna_codon)

        aa = translate_dna(dna_codon, frame=0)
        aa_one = aa[0] if aa else "?"

        rows.append(
            RNACodonRow(
                codon_index=(i // 3) + 1,
                genomic_start=start + i,
                dna_codon=dna_codon,
                mrna_codon=mrna_codon,
                trna_anticodon=trna,
                aa_one=aa_one,
            )
        )

    return RNAToolsResponse(
        rows=rows,
        used_start=start,
        used_end=start + usable_len,
        total_codons=total_codons,
    )


@app.post("/grnas", response_model=GRNAResponse)
def grna_tools(req: GRNARequest) -> GRNAResponse:
    data = analyze_grnas(req.sequence, enzyme=req.enzyme, scan_reverse=req.scan_reverse)
    return _to_grna_response(data)
