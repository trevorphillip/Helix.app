from __future__ import annotations

from typing import List

from fastapi import APIRouter
from pydantic import BaseModel

from helix_core.crisprutils import reverse_complement

router = APIRouter()

SCAFFOLD = (
    "GTTTTAGAGCTAGAAATAGCAAGTTAAAATAAGGCTAGTCCGT"
    "TATCAACTTGAAAAAGTGGCACCGAGTCGGTGC"
)

EDITORS: dict[str, dict] = {
    "BE3": {
        "type": "CBE", "edit": "C_to_T", "window": (4, 8), "pam": "NGG",
        "description": "Cytosine base editor 3 — C to T",
    },
    "BE4max": {
        "type": "CBE", "edit": "C_to_T", "window": (4, 8), "pam": "NGG",
        "description": "Optimized CBE — higher efficiency",
    },
    "ABE7": {
        "type": "ABE", "edit": "A_to_G", "window": (4, 7), "pam": "NGG",
        "description": "Adenine base editor 7 — A to G",
    },
    "ABE8e": {
        "type": "ABE", "edit": "A_to_G", "window": (4, 8), "pam": "NGG",
        "description": "Enhanced ABE — broader window",
    },
    "NG-CBE": {
        "type": "CBE", "edit": "C_to_T", "window": (4, 8), "pam": "NG",
        "description": "CBE with relaxed NG PAM",
    },
}

EDIT_MAP: dict[str, tuple[str, str]] = {
    "C_to_T": ("C", "T"),
    "A_to_G": ("A", "G"),
}


# ─── Models ───────────────────────────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    sequence: str
    target_position: int = 0  # unused, kept for backwards compatibility
    edit_type: str = "any"
    editor_type: str = "all"


class BystanderEdit(BaseModel):
    position: int
    base: str
    result: str


class GuideResult(BaseModel):
    editor: str
    editor_type: str
    editor_description: str
    guide_sequence: str
    pam: str
    position: int
    strand: str
    editing_window: List[int]
    target_base_position: int
    target_base: str
    result_base: str
    bystander_bases: List[BystanderEdit]
    efficiency_estimate: float
    specificity_score: float
    window_sequence: str


class AnalyzeResponse(BaseModel):
    guides: List[GuideResult]
    total_found: int
    total_scanned: int
    valid_found: int
    message: str


class PrimeRequest(BaseModel):
    sequence: str
    edit_position: int
    edit_type: str = "substitution"
    edit_sequence: str = ""
    edit_length: int = 1


class EditPreview(BaseModel):
    before: str
    after: str
    edit_highlighted: str


class OrderingInfo(BaseModel):
    pegrna_length: int
    order_as: str
    recommended_vendor: str


class PrimeResponse(BaseModel):
    spacer: str
    pam: str
    spacer_position: int
    nick_position: int
    rt_template: str
    rt_template_length: int
    pbs: str
    pbs_length: int
    full_pegrna: str
    scaffold: str
    pe3_nicking_guide: str
    pe3_position: int
    edit_preview: EditPreview
    ordering_info: OrderingInfo


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _scan_pam(seq: str, pam: str) -> list[int]:
    hits = []
    if pam == "NGG":
        for i in range(len(seq) - 2):
            if seq[i + 1] == "G" and seq[i + 2] == "G":
                hits.append(i)
    elif pam == "NG":
        for i in range(len(seq) - 1):
            if seq[i + 1] == "G":
                hits.append(i)
    return hits


def _guides_for_editor(
    seq: str,
    editor_name: str,
    editor: dict,
) -> tuple[list[GuideResult], int]:
    """Return (valid guides, total PAM sites scanned)."""
    n = len(seq)
    pam = editor["pam"]
    w_start, w_end = editor["window"]
    src_base, dst_base = EDIT_MAP[editor["edit"]]
    results: list[GuideResult] = []
    total_scanned = 0

    def _process(search_seq: str, strand: str) -> None:
        nonlocal total_scanned
        for pam_i in _scan_pam(search_seq, pam):
            guide_start = pam_i - 20
            if guide_start < 0:
                continue
            total_scanned += 1
            guide_seq = search_seq[guide_start:pam_i]

            # Collect all editable positions in window
            editable = [k for k in range(w_start, w_end + 1) if guide_seq[k - 1] == src_base]
            if not editable:
                continue

            # First editable position is the "target"; rest are bystanders
            tpos = editable[0]
            bystanders = [BystanderEdit(position=k, base=src_base, result=dst_base) for k in editable[1:]]

            window_seq = guide_seq[w_start - 1: w_end]
            center = (w_start + w_end) / 2.0
            base_eff = 0.85 if abs(tpos - center) <= 1 else 0.6
            efficiency = round(max(0.0, base_eff - 0.1 * len(bystanders)), 3)
            specificity = round(max(0.0, 1.0 - 0.15 * len(bystanders)), 3)

            pam_len = 3 if pam == "NGG" else 2
            pam_seq_str = search_seq[pam_i: pam_i + pam_len]
            report_pos = guide_start + 1 if strand == "+" else n - pam_i + 1

            results.append(GuideResult(
                editor=editor_name,
                editor_type=editor["type"],
                editor_description=editor["description"],
                guide_sequence=guide_seq,
                pam=pam_seq_str,
                position=report_pos,
                strand=strand,
                editing_window=[w_start, w_end],
                target_base_position=tpos,
                target_base=src_base,
                result_base=dst_base,
                bystander_bases=bystanders,
                efficiency_estimate=efficiency,
                specificity_score=specificity,
                window_sequence=window_seq,
            ))

    _process(seq, "+")
    _process(reverse_complement(seq), "-")

    return results, total_scanned


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/analyze", response_model=AnalyzeResponse)
def analyze_base_edit(req: AnalyzeRequest) -> AnalyzeResponse:
    seq = req.sequence.upper().replace(" ", "").replace("\n", "")

    active: dict[str, dict] = {}
    for name, ed in EDITORS.items():
        if req.editor_type not in ("all", ed["type"]):
            continue
        if req.edit_type not in ("any", ed["edit"]):
            continue
        active[name] = ed

    all_guides: list[GuideResult] = []
    total_scanned = 0
    for name, ed in active.items():
        guides, scanned = _guides_for_editor(seq, name, ed)
        all_guides.extend(guides)
        total_scanned += scanned

    all_guides.sort(key=lambda g: g.position)

    n = len(all_guides)
    if n == 0:
        msg = f"No editing opportunities found across {total_scanned} PAM sites scanned."
    else:
        msg = f"Found {n} editing {'opportunity' if n == 1 else 'opportunities'} across {total_scanned} PAM sites scanned."

    return AnalyzeResponse(
        guides=all_guides,
        total_found=n,
        total_scanned=total_scanned,
        valid_found=n,
        message=msg,
    )


@router.post("/prime_editor", response_model=PrimeResponse)
def design_prime_editor(req: PrimeRequest) -> PrimeResponse:
    seq = req.sequence.upper().replace(" ", "").replace("\n", "")
    n = len(seq)
    edit_pos_0 = req.edit_position - 1
    rc = reverse_complement(seq)

    _empty = PrimeResponse(
        spacer="", pam="", spacer_position=0, nick_position=0,
        rt_template="", rt_template_length=0, pbs="", pbs_length=0,
        full_pegrna="", scaffold=SCAFFOLD,
        pe3_nicking_guide="", pe3_position=0,
        edit_preview=EditPreview(before="", after="", edit_highlighted=""),
        ordering_info=OrderingInfo(
            pegrna_length=0,
            order_as="IVT template or direct synthesis",
            recommended_vendor="Addgene plasmid or IDT synthesis",
        ),
    )

    # Find best spacer: nick site ~3bp from PAM, within 40bp of edit
    best: dict | None = None
    best_dist = float("inf")

    for strand, s_seq in [("+", seq), ("-", rc)]:
        for pam_i in range(n - 2):
            if s_seq[pam_i + 1] != "G" or s_seq[pam_i + 2] != "G":
                continue
            if pam_i - 20 < 0:
                continue
            nick_i = pam_i - 3
            nick_fwd = nick_i if strand == "+" else (n - 1 - nick_i)
            dist = abs(nick_fwd - edit_pos_0)
            if dist <= 40 and dist < best_dist:
                best_dist = dist
                best = {
                    "strand": strand,
                    "pam_i": pam_i,
                    "nick_i": nick_i,
                    "nick_fwd": nick_fwd,
                    "guide_seq": s_seq[pam_i - 20: pam_i],
                    "pam_seq": s_seq[pam_i: pam_i + 3],
                    "s_seq": s_seq,
                }

    if best is None:
        return _empty

    s_seq = best["s_seq"]
    nick_i = best["nick_i"]
    edit_pos_s = edit_pos_0 if best["strand"] == "+" else (n - 1 - edit_pos_0)

    # Apply edit in strand space
    if req.edit_type == "substitution":
        ins = req.edit_sequence.upper() if best["strand"] == "+" else reverse_complement(req.edit_sequence.upper())
        edited_s = s_seq[:edit_pos_s] + ins + s_seq[edit_pos_s + len(ins):]
        edit_end_s = edit_pos_s + len(ins)
    elif req.edit_type == "insertion":
        ins = req.edit_sequence.upper() if best["strand"] == "+" else reverse_complement(req.edit_sequence.upper())
        edited_s = s_seq[:edit_pos_s] + ins + s_seq[edit_pos_s:]
        edit_end_s = edit_pos_s + len(ins)
    else:  # deletion
        edited_s = s_seq[:edit_pos_s] + s_seq[edit_pos_s + req.edit_length:]
        edit_end_s = edit_pos_s

    # RT template: RC of edited_s from nick to 15nt past edit end
    rt_end = min(edit_end_s + 15, len(edited_s))
    rt_template = reverse_complement(edited_s[nick_i:rt_end])

    # PBS: RC of 13nt upstream of nick
    pbs = reverse_complement(s_seq[max(0, nick_i - 13): nick_i])

    spacer = best["guide_seq"]
    full_pegrna = spacer + SCAFFOLD + rt_template + pbs

    # PE3: nicking guide on opposite strand, 40–90bp from main nick
    pe3_guide = ""
    pe3_pos = 0
    opp_seq = rc if best["strand"] == "+" else seq
    for pam_i in range(n - 2):
        if opp_seq[pam_i + 1] != "G" or opp_seq[pam_i + 2] != "G":
            continue
        if pam_i - 20 < 0:
            continue
        opp_nick_i = pam_i - 3
        opp_nick_fwd = (n - 1 - opp_nick_i) if best["strand"] == "+" else opp_nick_i
        dist = abs(opp_nick_fwd - best["nick_fwd"])
        if 40 <= dist <= 90:
            pe3_guide = opp_seq[pam_i - 20: pam_i]
            pe3_pos = opp_nick_fwd + 1
            break

    # Edit preview in forward strand coordinates
    ctx = 12
    before = seq[max(0, edit_pos_0 - ctx): min(n, edit_pos_0 + ctx)]
    if req.edit_type == "substitution":
        hl = req.edit_sequence.upper()
        after_seq = seq[:edit_pos_0] + hl + seq[edit_pos_0 + len(hl):]
    elif req.edit_type == "insertion":
        hl = req.edit_sequence.upper()
        after_seq = seq[:edit_pos_0] + hl + seq[edit_pos_0:]
    else:
        hl = ""
        after_seq = seq[:edit_pos_0] + seq[edit_pos_0 + req.edit_length:]
    after = after_seq[max(0, edit_pos_0 - ctx): min(len(after_seq), edit_pos_0 + len(hl) + ctx)]

    return PrimeResponse(
        spacer=spacer,
        pam=best["pam_seq"],
        spacer_position=max(1, best["pam_i"] - 19),
        nick_position=best["nick_fwd"] + 1,
        rt_template=rt_template,
        rt_template_length=len(rt_template),
        pbs=pbs,
        pbs_length=len(pbs),
        full_pegrna=full_pegrna,
        scaffold=SCAFFOLD,
        pe3_nicking_guide=pe3_guide,
        pe3_position=pe3_pos,
        edit_preview=EditPreview(before=before, after=after, edit_highlighted=hl),
        ordering_info=OrderingInfo(
            pegrna_length=len(full_pegrna),
            order_as="IVT template or direct synthesis",
            recommended_vendor="Addgene plasmid or IDT synthesis",
        ),
    )
