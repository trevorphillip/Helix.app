from __future__ import annotations

from typing import Any

from helix_core.crisprutils import (
    GUIDE_LENGTHS,
    PAM_SEQUENCES,
    PAM_SIDE,
    annotate_grnas,
    find_sites_for_enzyme,
    map_rc_start_to_fwd,
    reverse_complement,
    sanitize_sequence,
)


def build_session_snapshot(
    *,
    sequence: str,
    win: tuple[int, int],
    enzyme: str,
    pam: str,
    pam_side: str,
    guide_len: int,
    hyper: bool,
) -> dict[str, Any]:
    return {
        "sequence": sequence,
        "win": list(win),
        "enzyme": enzyme,
        "pam": pam,
        "pam_side": pam_side,
        "guide_len": guide_len,
        "hyper": hyper,
    }


def apply_session_snapshot(current_state: dict[str, Any], snapshot: dict[str, Any]) -> dict[str, Any]:
    next_state = dict(current_state)
    next_state["sequence"] = snapshot.get("sequence", current_state.get("sequence", ""))
    next_state["win"] = tuple(snapshot.get("win", current_state.get("win", (0, 0))))
    next_state["enzyme"] = snapshot.get("enzyme", current_state.get("enzyme"))
    if "hyper" in snapshot:
        next_state["hyper_mode"] = snapshot["hyper"]
    return next_state


def analyze_grnas(sequence: str, enzyme: str = "SpCas9", scan_reverse: bool = False) -> dict[str, Any]:
    seq = sanitize_sequence(sequence)
    if not seq:
        return {
            "sequence_length": 0,
            "enzyme": enzyme,
            "pam": PAM_SEQUENCES[enzyme],
            "pam_side": PAM_SIDE[enzyme],
            "guide_length": GUIDE_LENGTHS[enzyme],
            "grnas": [],
        }

    pam_sites_fwd, grnas_fwd = find_sites_for_enzyme(seq, enzyme=enzyme)
    guides = [
        {
            **row,
            "strand": "+",
        }
        for row in annotate_grnas(seq, grnas_fwd, GUIDE_LENGTHS[enzyme], enzyme=enzyme)
    ]

    if scan_reverse:
        rc = reverse_complement(seq)
        _pam_sites_rc, grnas_rc = find_sites_for_enzyme(rc, enzyme=enzyme)
        mapped = [
            (
                guide,
                map_rc_start_to_fwd(
                    pos,
                    len(seq),
                    PAM_SIDE[enzyme],
                    GUIDE_LENGTHS[enzyme],
                    pam_len=len(PAM_SEQUENCES[enzyme]),
                ),
            )
            for guide, pos in grnas_rc
        ]
        guides.extend(
            {
                **row,
                "strand": "-",
            }
            for row in annotate_grnas(seq, mapped, GUIDE_LENGTHS[enzyme], enzyme=enzyme)
        )

    guides.sort(key=lambda row: (row["pos"], row["strand"]))
    return {
        "sequence_length": len(seq),
        "enzyme": enzyme,
        "pam": PAM_SEQUENCES[enzyme],
        "pam_side": PAM_SIDE[enzyme],
        "guide_length": GUIDE_LENGTHS[enzyme],
        "pam_count": len(pam_sites_fwd),
        "grnas": guides,
    }
