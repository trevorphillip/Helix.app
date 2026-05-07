from typing import List, Tuple

def _gc_pct(s: str) -> float:
    s = s.upper()
    return 100.0 * (s.count("G") + s.count("C")) / max(1, len(s))

def format_context(sequence: str,
                   enzyme: str, pam: str, pam_side: str, guide_len: int,
                   start: int, end: int,
                   grnas: List[Tuple[str, int]]) -> str:
    windowed = [(g, p) for (g, p) in grnas if start <= p < end]
    rows = []
    for (g, p) in windowed[:50]:
        gc = round(_gc_pct(g), 1)
        pam_seq = sequence[p + guide_len: p + guide_len + len(pam)]
        rows.append(f"- pos {p}-{p+len(g)} | GC {gc}% | PAM {pam_seq} | {g}")
    return "\n".join(rows) if rows else "(no gRNAs in this range)"

def ask_ai(question: str, context_block: str) -> str:
    q = (question or "").lower()
    tips = [
        "• Aim for gRNA GC% ~40–60% (too high → hairpins; too low → weak binding).",
        "• PAM defines editable loci (e.g., NGG for SpCas9; TTTV for Cas12a).",
        "• Off-target risk rises with similar sequences nearby (seed mismatches matter most).",
        "• If planning multiple edits, avoid overlapping guides; pick central guides for even coverage.",
    ]
    answer = ["Here’s a quick, rule-based assessment (offline):", ""]
    if any(k in q for k in ["best", "which", "recommend"]):
        answer.append("• Prefer guides near ~50% GC with a clean PAM match.")
        answer.append("• Fewer off-targets in the window is better.")
    if any(k in q for k in ["pam", "ngg", "tttv", "nrn", "ryn"]):
        answer.append("• IUPAC: N:any, R:A/G, Y:C/T, V:A/C/G. TTTV = TTT + (A/C/G); NGG = any base + GG.")
    answer += ["", "General tips:"] + tips + ["", "Context:", context_block or "(no window data)"]
    return "\n".join(answer)
