
from __future__ import annotations

import re
from typing import Iterable, Tuple

def format_context(
    *,
    sequence: str,
    enzyme: str,
    pam: str,
    pam_side: str,
    guide_len: int,
    start: int,
    end: int,
    grnas: Iterable[Tuple[str, int]],  # (guide_seq, start_pos)
) -> str:
    """
    Build a compact, human-readable context block for the AI helper.
    Kept deliberately simple — used only for offline reasoning text.
    """
    grna_lines = []
    for g, p in grnas:
        gc = 100.0 * (g.upper().count("G") + g.upper().count("C")) / max(1, len(g))
        grna_lines.append(f"- pos {p:>6} | GC {gc:>5.1f}% | {g}")

    lines = [
        f"ENZYME: {enzyme}",
        f"PAM: {pam} (side={pam_side})",
        f"GUIDE_LEN: {guide_len}",
        f"WINDOW: {start}-{end} (len {max(0, end-start)} bp)",
        "GRNAS:",
        *(grna_lines or ["(none)"]),
    ]
    return "\n".join(lines)

def ask_ai(question: str, context_block: str) -> str:
    """
    Offline heuristic “AI” answerer.
    It does NOT make network calls; it just gives sensible guidance based on the context text.
    """
    # Parse a little context to mention back to the user
    enzyme = _extract(r"ENZYME:\s*(.+)", context_block) or "unknown enzyme"
    pam     = _extract(r"PAM:\s*([A-ZN]+)", context_block) or "unknown PAM"
    win     = _extract(r"WINDOW:\s*(\d+-\d+)", context_block) or "N/A"
    guide_L = _extract(r"GUIDE_LEN:\s*(\d+)", context_block)

    # Pull the gRNA lines
    grnas = []
    for line in context_block.splitlines():
        if line.strip().startswith("- pos"):
            m = re.search(r"pos\s+(\d+)\s*\|\s*GC\s+([\d.]+)%\s*\|\s*([ACGT]+)", line, re.I)
            if m:
                pos = int(m.group(1))
                gc  = float(m.group(2))
                seq = m.group(3).upper()
                grnas.append((pos, gc, seq))

    # Rank a few guides by a tiny heuristic that echoes your app: GC ~50% and center-of-window
    pick_lines = []
    if grnas and "-" in win:
        try:
            w0, w1 = map(int, win.split("-"))
            center = (w0 + w1) / 2.0
            def score(item):
                pos, gc, seq = item
                gc_score = 1.0 - min(abs(gc - 50.0), 50.0)/50.0
                center_score = 1.0 - min(abs((pos + len(seq)/2.0) - center) / max(1.0, (w1 - w0)/2.0), 1.0)
                return 0.6*gc_score + 0.4*center_score
            ranked = sorted(grnas, key=score, reverse=True)[:3]
            for i,(pos,gc,seq) in enumerate(ranked, start=1):
                pick_lines.append(f"{i}) pos {pos} • GC {gc:.1f}% • {seq}")
        except Exception:
            pass

    tips = [
        f"- For {enzyme} with PAM '{pam}', start by favoring canonical PAMs (e.g., NGG for SpCas9) when available.",
        "- Aim for guide GC around ~40–60%; extreme GC or AT can reduce performance.",
        "- Avoid long homopolymers and repetitive trinucleotide runs.",
        "- Prefer guides spaced apart to diversify cut sites.",
        "- If you’ll validate, check off-targets with ≤1–2 mismatches near seed.",
    ]

    answer = []
    answer.append(f"Here’s a quick offline read on your window {win} for {enzyme}:")
    if pick_lines:
        answer.append("\nTop candidates by simple GC+centering heuristic:")
        answer.append("\n".join(pick_lines))
    else:
        answer.append("\nNo candidate gRNAs were parsed from the context, so I’ll share general guidance.")

    answer.append("\nPractical tips:")
    answer.append("\n".join(tips))

    if guide_L:
        answer.append(f"\n(Note: your guide length is {guide_L} nt.)")

    if question.strip():
        answer.append("\nYour question:")
        answer.append(f"“{question.strip()}”")
        answer.append("\nShort answer (heuristic):\n- Use the highest-ranked guide(s) above as a starting point; then confirm with off-target search and any functional constraints near coding/critical motifs.")

    return "\n".join(answer)

def _extract(pat: str, text: str) -> str | None:
    m = re.search(pat, text)
    return m.group(1).strip() if m else None
