from __future__ import annotations
import math
import random
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class OutcomeRequest(BaseModel):
    sequence: str
    cut_position: int
    n_simulations: int = 10000
    cell_type: str = "dividing"
    has_donor: bool = False


def find_microhomology(left: str, right: str) -> list[dict]:
    mh_list = []
    for length in range(1, 8):
        for pos in range(len(right) - length + 1):
            mh_seq = right[pos: pos + length]
            if left.endswith(mh_seq):
                gc = (mh_seq.count("G") + mh_seq.count("C")) / length
                mh_list.append({
                    "length": length,
                    "sequence": mh_seq,
                    "position": pos,
                    "gc_content": round(gc, 3),
                })
    return mh_list


def apply_indel(sequence: str, cut_pos: int, indel_type: str, indel_size: int) -> str:
    ctx_start = max(0, cut_pos - 10)
    ctx_end   = min(len(sequence), cut_pos + 10)
    local     = sequence[ctx_start:ctx_end]
    local_cut = cut_pos - ctx_start

    if indel_type == "deletion":
        del_start = max(0, local_cut - indel_size // 2)
        del_end   = min(len(local), del_start + indel_size)
        result    = local[:del_start] + local[del_end:]
    elif indel_type == "insertion":
        ins_base = sequence[cut_pos - 1] if cut_pos > 0 else "A"
        result   = local[:local_cut] + ins_base * indel_size + local[local_cut:]
    else:
        result = local

    result = result[:20]
    return result.ljust(20, ".")


@router.post("/outcome/simulate")
def simulate_outcome(req: OutcomeRequest) -> dict:
    seq      = req.sequence.upper().replace(" ", "")
    cut_pos  = max(10, min(req.cut_position, len(seq) - 10))
    n        = max(100, min(req.n_simulations, 50000))
    has_donor = req.has_donor
    cell_type = req.cell_type

    left_seq      = seq[cut_pos - 10: cut_pos]
    right_seq     = seq[cut_pos: cut_pos + 10]
    microhomology = find_microhomology(left_seq, right_seq)

    p_hdr  = (0.08 if cell_type == "dividing" else 0.02) if has_donor else 0.0
    p_nhej = (0.90 if cell_type == "dividing" else 0.97) - p_hdr

    # deletion probs (sizes 1-30)
    del_probs: dict[int, float] = {}
    for d in range(1, 31):
        base = 0.6 * math.exp(-d / 8)
        mh_boost = 0.0
        for mh in microhomology:
            if mh["length"] >= 2 and d == mh["position"] + mh["length"]:
                mh_boost += 0.3 * mh["length"] * (1 + mh["gc_content"])
        local = seq[max(0, cut_pos - d // 2): min(len(seq), cut_pos + d // 2)]
        gc    = (local.count("G") + local.count("C")) / max(len(local), 1)
        del_probs[d] = base * (1 + 0.2 * (gc - 0.5)) + mh_boost

    # insertion probs (sizes 1-5)
    ins_probs: dict[int, float] = {}
    for i in range(1, 6):
        base = 0.25 * math.exp(-i / 2)
        if i == 1:
            ins_base = seq[cut_pos - 1] if cut_pos > 0 else "A"
            if ins_base in ("A", "T"):
                base *= 1.4
        ins_probs[i] = base

    total = sum(del_probs.values()) + sum(ins_probs.values())
    del_probs = {k: v / total * p_nhej for k, v in del_probs.items()}
    ins_probs = {k: v / total * p_nhej for k, v in ins_probs.items()}

    # ordered cumulative table for simulation
    cum_table: list[tuple[str, int, float]] = []
    running = p_hdr
    for size, prob in sorted(del_probs.items()):
        running += prob
        cum_table.append(("deletion", size, running))
    for size, prob in sorted(ins_probs.items()):
        running += prob
        cum_table.append(("insertion", size, running))

    # monte carlo
    counts: dict[tuple[str, int], int] = {}
    hdr_count = 0
    for _ in range(n):
        r = random.random()
        if r < p_hdr:
            hdr_count += 1
            continue
        for otype, osize, cdf in cum_table:
            if r < cdf:
                key = (otype, osize)
                counts[key] = counts.get(key, 0) + 1
                break
        else:
            key = ("insertion", 1)
            counts[key] = counts.get(key, 0) + 1

    # build distribution list
    distribution: list[dict] = []
    fs_count = 0
    for otype, osize, prob in [("deletion", k, del_probs[k]) for k in del_probs] + \
                               [("insertion", k, ins_probs[k]) for k in ins_probs]:
        count  = counts.get((otype, osize), 0)
        is_fs  = (osize % 3) != 0
        if is_fs:
            fs_count += count
        signed = -osize if otype == "deletion" else osize
        distribution.append({
            "size":             signed,
            "type":             otype,
            "count":            count,
            "probability":      round(prob, 6),
            "frameshift":       is_fs,
            "sequence_preview": apply_indel(seq, cut_pos, otype, osize),
        })

    if p_hdr > 0:
        distribution.append({
            "size":             0,
            "type":             "hdr",
            "count":            hdr_count,
            "probability":      round(p_hdr, 6),
            "frameshift":       False,
            "sequence_preview": seq[max(0, cut_pos - 10): cut_pos + 10].ljust(20, "."),
        })

    distribution.sort(key=lambda x: x["probability"], reverse=True)

    nhej_sim = n - hdr_count
    total_sim = nhej_sim + hdr_count
    most = distribution[0] if distribution else None

    summary = {
        "nhej_percent":        round(nhej_sim / n * 100, 1),
        "hdr_percent":         round(hdr_count / n * 100, 1),
        "frameshift_percent":  round(fs_count / max(total_sim, 1) * 100, 1),
        "inframe_percent":     round((nhej_sim - fs_count) / max(total_sim, 1) * 100, 1),
        "most_common_outcome": most["type"] if most else "none",
        "most_common_size":    most["size"] if most else 0,
        "most_common_prob":    round(most["probability"] * 100, 1) if most else 0.0,
    }

    return {
        "cut_position":  cut_pos,
        "n_simulations": n,
        "cell_type":     cell_type,
        "summary":       summary,
        "distribution":  distribution,
        "top_outcomes":  distribution[:10],
        "microhomology": microhomology,
        "model_info": {
            "name":      "Helix inDelphi-simplified",
            "version":   "1.0",
            "reference": "Shen et al. 2018 Nature Biotechnology",
        },
    }
