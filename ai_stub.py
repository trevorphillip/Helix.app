# ai_stub.py — offline, rule-based explainer
from typing import List, Tuple

def _gc_pct(s: str) -> float:
    s = s.upper()
    return 100.0 * (s.count("G") + s.count("C")) / max(1, len(s))

def format_context(sequence: str,
                   enzyme: str, pam: str, pam_side: str, guide_len: int,
                   start: int, end: int,
                   grnas: List[Tuple[str, int]]) -> str:
    # we’ll reuse this shape to keep app.py unchanged if you switch back later
    windowed = [(g, p) for (g, p) in grnas if start <= p < end]
    rows = []
    for (g, p) in windowed[:50]:
        gc = round(_gc_pct(g), 1)
        pam_seq = sequence[p + guide_len: p + guide_len + len(pam)]
        rows.append(f"- pos {p}-{p+len(g)} | GC {gc}% | PAM {pam_seq} | {g}")
    return "\n".join(rows) if rows else "(no gRNAs in this range)"

def ask_ai(question: str, context_block: str) -> str:
    # very simple, deterministic guidance (you can expand it anytime)
    q = (question or "").lower()
    tips = [
        "• Ideal GC% for many Cas9 gRNAs is roughly 40–60% (too high may form secondary structures; too low may reduce binding).",
        "• PAM determines where cuts are possible (e.g., NGG for SpCas9, TTTV for Cas12a).",
        "• Off-target risk increases with similar sequences nearby; mismatches in the seed region are most critical (we’re using a simple Hamming check here).",
        "• Position choice can be pragmatic: avoid overlaps if you plan multiple edits; choose central guides in your region for even coverage."
    ]
    answer = ["Here’s a quick, rule-based assessment (offline):", ""]
    if "best" in q or "which" in q or "recommend" in q:
        answer.append("• Pick gRNAs with GC% near ~50% and clear PAM (exact motif).")
        answer.append("• Prefer guides not overlapping many off-targets.")
    if "tttv" in q or "ngg" in q or "pam" in q:
        answer.append("• IUPAC codes: N=any, R=A/G, Y=C/T, V=A/C/G. So TTTV allows TTT[A/C/G]; NGG requires any base then GG.")
    answer += ["", "General tips:"] + tips
    answer.append("")
    answer.append("Context:")
    answer.append(context_block if context_block.strip() else "(no window data)")
    return "\n".join(answer)
