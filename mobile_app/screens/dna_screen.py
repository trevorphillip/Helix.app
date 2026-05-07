import re
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.metrics import dp
from kivy.graphics import Color, RoundedRectangle, Rectangle
from mobile_app.utils.crispr_utils import ENZYMES, find_guides, gc_percent


# ─────────────────────────────────────────
# Simple local DNA utils (no external deps)
# ─────────────────────────────────────────

DNA_CHARS = set("ACGTacgt")


def sanitize_sequence(seq: str) -> str:
    if not seq:
        return ""
    return "".join(ch for ch in seq.upper() if ch in DNA_CHARS)


def dna_to_rna(seq: str) -> str:
    # keep T in DNA, make U only in RNA string (as it should)
    return sanitize_sequence(seq).replace("T", "U")


def translate_frame(seq: str, frame: int = 0) -> str:
    """
    Simple translation, forward strand, chosen frame (0/1/2).
    Stops are shown as '*'.
    """
    codon_table = {
        "TTT": "F", "TTC": "F", "TTA": "L", "TTG": "L",
        "CTT": "L", "CTC": "L", "CTA": "L", "CTG": "L",
        "ATT": "I", "ATC": "I", "ATA": "I", "ATG": "M",
        "GTT": "V", "GTC": "V", "GTA": "V", "GTG": "V",
        "TCT": "S", "TCC": "S", "TCA": "S", "TCG": "S",
        "CCT": "P", "CCC": "P", "CCA": "P", "CCG": "P",
        "ACT": "T", "ACC": "T", "ACA": "T", "ACG": "T",
        "GCT": "A", "GCC": "A", "GCA": "A", "GCG": "A",
        "TAT": "Y", "TAC": "Y", "TAA": "*", "TAG": "*",
        "CAT": "H", "CAC": "H", "CAA": "Q", "CAG": "Q",
        "AAT": "N", "AAC": "N", "AAA": "K", "AAG": "K",
        "GAT": "D", "GAC": "D", "GAA": "E", "GAG": "E",
        "TGT": "C", "TGC": "C", "TGA": "*", "TGG": "W",
        "CGT": "R", "CGC": "R", "CGA": "R", "CGG": "R",
        "AGT": "S", "AGC": "S", "AGA": "R", "AGG": "R",
        "GGT": "G", "GGC": "G", "GGA": "G", "GGG": "G",
    }
    seq = sanitize_sequence(seq)
    aa = []
    for i in range(frame, len(seq) - 2, 3):
        codon = seq[i:i + 3]
        aa.append(codon_table.get(codon, "X"))
    return "".join(aa)


def find_orfs_simple(seq: str, min_aa: int = 30):
    """
    Very simple ORF finder on the forward strand:
    - Start codon: ATG
    - Stops: TAA, TAG, TGA
    - Reports ORFs with length >= min_aa
    Returns list of dicts: {start_bp, end_bp, frame, aa_len}
    """
    seq = sanitize_sequence(seq)
    stops = {"TAA", "TAG", "TGA"}
    orfs = []

    for frame in range(3):
        i = frame
        while i < len(seq) - 2:
            codon = seq[i:i + 3]
            if codon == "ATG":
                start = i
                j = i + 3
                while j < len(seq) - 2:
                    cod2 = seq[j:j + 3]
                    if cod2 in stops:
                        aa_len = (j - start) // 3
                        if aa_len >= min_aa:
                            orfs.append({
                                "start_bp": start,
                                "end_bp": j + 3,
                                "frame": frame + 1,  # 1,2,3 style
                                "aa_len": aa_len,
                            })
                        i = j + 3
                        break
                    j += 3
                else:
                    # reached the end without stop
                    i = j
            else:
                i += 3

    return orfs


def gc_content(seq: str) -> float:
    seq = sanitize_sequence(seq)
    if not seq:
        return 0.0
    g = seq.count("G")
    c = seq.count("C")
    return 100.0 * (g + c) / len(seq)

# --- motif + restriction site helpers ----------------------------------------

MOTIF_PATTERNS = {
    "TATA-like (TATA box)": r"TATA[AT]A[AT]",    # simple TATA-ish
    "GC-box (SP1-like)":    r"GGGCGG",
}

RE_SITES = {
    "EcoRI (GAATTC)": "GAATTC",
    "BamHI (GGATCC)": "GGATCC",
}


def find_motifs_regex(seq: str):
    """
    Very simple motif finder using regex patterns in MOTIF_PATTERNS.
    Returns list of dicts with name and start position (0-based).
    """
    seq = sanitize_sequence(seq)
    hits = []
    for name, pat in MOTIF_PATTERNS.items():
        for m in re.finditer(pat, seq):
            hits.append({
                "name": name,
                "start": m.start(),
                "end": m.end(),
            })
    return hits


def find_restriction_sites(seq: str):
    """
    Simple literal search for common restriction enzymes in RE_SITES.
    Returns list of dicts with enzyme name, site, and start position.
    """
    seq = sanitize_sequence(seq)
    hits = []
    for enzyme, site in RE_SITES.items():
        i = seq.find(site)
        while i != -1:
            hits.append({
                "enzyme": enzyme,
                "site": site,
                "start": i,
                "end": i + len(site),
            })
            i = seq.find(site, i + 1)
    return hits


def simulate_digest(seq: str, cut_positions):
    """
    Given a list of cut positions (0-based), return fragment sizes (bp).
    Includes 0 and len(seq) as boundaries.
    """
    seq = sanitize_sequence(seq)
    if not seq:
        return []

    cuts = sorted(set([0] + cut_positions + [len(seq)]))
    frags = []
    for i in range(len(cuts) - 1):
        frags.append(cuts[i + 1] - cuts[i])
    return frags


# ───────────── CRISPR: SpCas9 NGG, very simple ─────────────

def find_spcas9_sites(seq: str, guide_len: int = 20):
    """
    Very simple SpCas9 finder on the forward strand:
    PAM = NGG, on the 3' side of the guide:
        [guide (20 nt)][PAM (NGG)]
    We:
      - scan for positions where seq[p+1:p+3] == "GG"
      - take guide from (p - guide_len) ... p
    Returns list of dicts: {pos, guide, pam, gc}
      pos = guide start (0-based)
    """
    seq = sanitize_sequence(seq)
    sites = []
    for p in range(len(seq) - 2):
        pam = seq[p:p + 3]
        if len(pam) < 3:
            continue
        if pam[1:] == "GG":    # N GG
            guide_start = p - guide_len
            if guide_start < 0:
                continue
            guide = seq[guide_start:guide_start + guide_len]
            if len(guide) != guide_len:
                continue
            gc = gc_content(guide)
            sites.append({
                "pos": guide_start,
                "guide": guide,
                "pam": pam,
                "gc": gc,
            })
    return sites


def score_guide_gc(gc: float) -> float:
    """
    Ideal around 50% GC. Score in [0,1].
    """
    return 1.0 - min(abs(gc - 50.0), 50.0) / 50.0
def find_motifs_and_sites(seq: str):
    """
    Tiny motif/RE scanner (forward strand, literal matches).
    Returns list of dicts: {name, pattern, pos}
    """
    seq = sanitize_sequence(seq)
    motifs = [
        ("TATA box", "TATA"),
        ("CpG dinucleotide", "CG"),
        ("EcoRI", "GAATTC"),
        ("BamHI", "GGATCC"),
        ("HindIII", "AAGCTT"),
    ]
    hits = []
    for name, pattern in motifs:
        start = 0
        while True:
            idx = seq.find(pattern, start)
            if idx == -1:
                break
            hits.append({
                "name": name,
                "pattern": pattern,
                "pos": idx,        # 0-based index
            })
            start = idx + 1
    return hits


# ─────────────────────────────────────────
# DNAScreen
# ─────────────────────────────────────────

class DNAScreen(Screen):
    """
    DNA / CRISPR tools (mobile)
    - Paste DNA
    - Basic stats
    - CRISPR (SpCas9 NGG) summary
    - Transcription + translation frames
    - Simple ORFs
    - In-silico edits (SNP / insertion / deletion)
    """

    def open_guide_detail(self, hit: dict):
        if not self.manager:
            return
        detail = self.manager.get_screen("guide_detail")
        detail.set_guide(self.current_dna, hit)
        self.manager.current = "guide_detail"


    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Root background
        root = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(12))
        with root.canvas.before:
            Color(0.04, 0.07, 0.12, 1)
            self._bg_rect = Rectangle(pos=root.pos, size=root.size)
        root.bind(pos=self._update_bg, size=self._update_bg)
        self.add_widget(root)

        # Top bar: back + title
        top_bar = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(44),
            spacing=dp(8),
        )

        back_btn = Button(
            text="← Home",
            size_hint_x=None,
            width=dp(90),
            background_normal="",
            background_color=(0.20, 0.30, 0.50, 1),
            color=(0.95, 0.98, 1.0, 1),
            font_size="14sp",
        )
        back_btn.bind(on_press=self.on_back)

        title_lbl = Label(
            text="🧬 DNA Tools",
            font_size="20sp",
            bold=True,
            color=(0.93, 0.98, 1.0, 1),
        )

        top_bar.add_widget(back_btn)
        top_bar.add_widget(title_lbl)
        root.add_widget(top_bar)

        # Subtitle
        root.add_widget(Label(
            text="Paste DNA → stats • CRISPR • RNA • ORFs • Edits",
            font_size="13sp",
            color=(0.70, 0.82, 0.98, 1),
            size_hint_y=None,
            height=dp(24),
        ))

        # TEXT INPUT CARD
        input_card = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            height=dp(190),
            padding=dp(8),
            spacing=dp(6),
        )
        with input_card.canvas.before:
            Color(0.10, 0.15, 0.26, 1)
            input_card._rect = RoundedRectangle(
                radius=[dp(16)] * 4,
                pos=input_card.pos,
                size=input_card.size,
            )
        input_card.bind(pos=self._update_card_rect, size=self._update_card_rect)

        input_card.add_widget(Label(
            text="DNA sequence (5' → 3')",
            font_size="15sp",
            color=(0.88, 0.96, 1.0, 1),
            size_hint_y=None,
            height=dp(24),
        ))

        example = "ATGGCCATTGTAATGGGCCGCTGAAAGGGTGCCCGATAG"
        self.dna_input = TextInput(
            text=example,
            multiline=True,
            size_hint_y=1,
            font_size="13sp",
            background_color=(0.03, 0.05, 0.09, 1),
            foreground_color=(0.93, 0.98, 1.0, 1),
            cursor_color=(0.60, 0.85, 0.98, 1),
        )
        input_card.add_widget(self.dna_input)

        root.add_widget(input_card)

        # --- CRISPR settings card ---
        crispr_card = BoxLayout(orientation="vertical", size_hint_y=None,
                                height=dp(120), padding=dp(8), spacing=dp(6))
        with crispr_card.canvas.before:
            Color(0.13, 0.18, 0.30, 1)
            crispr_card._rect = RoundedRectangle(radius=[dp(16)] * 4,
                                                 pos=crispr_card.pos, size=crispr_card.size)
        crispr_card.bind(pos=self._update_card_rect, size=self._update_card_rect)

        crispr_card.add_widget(Label(text="CRISPR settings", font_size="15sp",
                                     size_hint_y=None, height=dp(24)))

        # Simple “dropdown” in pure Kivy = cycle button
        self.enzyme_names = list(ENZYMES.keys())
        self.enzyme_idx = 0
        self.enzyme_btn = Button(
            text=f"Enzyme: {self.enzyme_names[self.enzyme_idx]}",
            size_hint_y=None, height=dp(44),
        )

        def _cycle_enzyme(*_):
            self.enzyme_idx = (self.enzyme_idx + 1) % len(self.enzyme_names)
            self.enzyme_btn.text = f"Enzyme: {self.enzyme_names[self.enzyme_idx]}"

        self.enzyme_btn.bind(on_press=_cycle_enzyme)
        crispr_card.add_widget(self.enzyme_btn)

        self.scan_rc = True
        self.scan_btn = Button(
            text="Scan reverse strand: ON",
            size_hint_y=None, height=dp(40),
        )

        def _toggle_scan(*_):
            self.scan_rc = not self.scan_rc
            self.scan_btn.text = f"Scan reverse strand: {'ON' if self.scan_rc else 'OFF'}"

        self.scan_btn.bind(on_press=_toggle_scan)
        crispr_card.add_widget(self.scan_btn)

        root.add_widget(crispr_card)

        # ACTION BUTTON
        analyze_btn = Button(
            text="🔬 Analyze sequence",
            size_hint_y=None,
            height=dp(50),
            background_normal="",
            background_color=(0.35, 0.80, 0.45, 1),
            color=(0, 0, 0, 1),
            bold=True,
            font_size="15sp",
        )
        analyze_btn.bind(on_press=self.on_analyze)
        root.add_widget(analyze_btn)

        # SCROLLABLE RESULTS
        scroll = ScrollView(size_hint=(1, 1))
        results_container = BoxLayout(
            orientation="vertical",
            padding=dp(4),
            spacing=dp(8),
            size_hint_y=None,
        )
        results_container.bind(minimum_height=results_container.setter("height"))
        scroll.add_widget(results_container)
        root.add_widget(scroll)

        self.results_container = results_container

        # edit inputs will be attached later
        self.snp_pos_input = None
        self.snp_base_input = None
        self.ins_pos_input = None
        self.ins_seq_input = None
        self.del_start_input = None
        self.del_end_input = None

    # ─────────────────────────────────────────
    # Drawing helpers
    # ─────────────────────────────────────────
    def _update_bg(self, instance, value):
        if hasattr(self, "_bg_rect"):
            self._bg_rect.pos = instance.pos
            self._bg_rect.size = instance.size

    def _update_card_rect(self, instance, value):
        if hasattr(instance, "_rect"):
            instance._rect.pos = instance.pos
            instance._rect.size = instance.size

    # ─────────────────────────────────────────
    # Navigation
    # ─────────────────────────────────────────
    def on_back(self, *args):
        if self.manager:
            self.manager.current = "home"

    # ─────────────────────────────────────────
    # Logic
    # ─────────────────────────────────────────
    def on_analyze(self, *args):
        dna_raw = self.dna_input.text or ""
        dna = sanitize_sequence(dna_raw)
        self.results_container.clear_widgets()

        if not dna:
            self.results_container.add_widget(Label(
                text="No valid A/C/G/T bases found.",
                font_size="14sp",
                color=(0.96, 0.88, 0.88, 1),
                size_hint_y=None,
                height=dp(28),
            ))
            return

        length = len(dna)
        gc = gc_content(dna)

        # --- CRISPR scan ---
        enz_name = self.enzyme_names[self.enzyme_idx]
        cfg = ENZYMES[enz_name]
        hits = find_guides(
            dna,
            pam=cfg["pam"],
            pam_side=cfg["pam_side"],
            guide_len=cfg["guide_len"],
            scan_rc=self.scan_rc,
        )

        # show a CRISPR results card
        crispr_res = BoxLayout(orientation="vertical", padding=dp(8), spacing=dp(4),
                               size_hint_y=None, height=dp(40 + 22 * max(1, min(10, len(hits)))))
        with crispr_res.canvas.before:
            Color(0.12, 0.18, 0.30, 1)
            crispr_res._rect = RoundedRectangle(radius=[dp(16)] * 4,
                                                pos=crispr_res.pos, size=crispr_res.size)
        crispr_res.bind(pos=self._update_card_rect, size=self._update_card_rect)

        crispr_res.add_widget(Label(
            text=f"CRISPR: {enz_name} — hits: {len(hits)}",
            font_size="14sp", size_hint_y=None, height=dp(24)
        ))

        # show top 10 guides
        self.current_dna = dna  # store for detail screen

        for h in hits[:10]:
            gcv = gc_percent(h.guide)
            line = f"{h.strand}  pam@{h.pam_start}  guide@{h.guide_start}  GC {gcv:.1f}%"

            btn = Button(
                text=line,
                size_hint_y=None,
                height=dp(44),
                background_normal="",
                background_color=(0.20, 0.26, 0.40, 1),
                color=(1, 1, 1, 1),
                font_size="12sp",
            )

            # pack what GuideDetailScreen needs
            hit_dict = {
                "guide": h.guide,
                "pam": h.pam,
                "strand": h.strand,
                "pos": int(h.guide_start),
                "pam_side": cfg["pam_side"],
                "guide_len": cfg["guide_len"],
                "pam_len": len(cfg["pam"]),
            }

            btn.bind(on_press=lambda _btn, hd=hit_dict: self.open_guide_detail(hd))
            crispr_res.add_widget(btn)

        self.results_container.add_widget(crispr_res)

        # === BASIC STATS CARD ==========================================
        stats_card = BoxLayout(
            orientation="vertical",
            padding=dp(8),
            spacing=dp(4),
            size_hint_y=None,
            height=dp(90),
        )
        with stats_card.canvas.before:
            Color(0.10, 0.17, 0.30, 1)
            stats_card._rect = RoundedRectangle(
                radius=[dp(16)] * 4,
                pos=stats_card.pos,
                size=stats_card.size,
            )
        stats_card.bind(pos=self._update_card_rect, size=self._update_card_rect)

        stats_card.add_widget(Label(
            text=f"Length: {length} bp   •   GC%: {gc:.1f}",
            font_size="14sp",
            color=(0.93, 0.98, 1.0, 1),
            size_hint_y=None,
            height=dp(24),
        ))

        # short preview
        preview = dna[:60] + ("…" if len(dna) > 60 else "")
        stats_card.add_widget(Label(
            text=f"5'→3':  {preview}",
            font_size="13sp",
            color=(0.82, 0.92, 1.0, 1),
            size_hint_y=None,
            height=dp(40),
        ))
        self.results_container.add_widget(stats_card)



        # === RNA + TRANSLATION CARD ====================================
        rna = dna_to_rna(dna)
        aa1 = translate_frame(dna, 0)
        aa2 = translate_frame(dna, 1)
        aa3 = translate_frame(dna, 2)

        trans_card = BoxLayout(
            orientation="vertical",
            padding=dp(8),
            spacing=dp(4),
            size_hint_y=None,
            height=dp(210),
        )
        with trans_card.canvas.before:
            Color(0.13, 0.19, 0.32, 1)
            trans_card._rect = RoundedRectangle(
                radius=[dp(16)] * 4,
                pos=trans_card.pos,
                size=trans_card.size,
            )
        trans_card.bind(pos=self._update_card_rect, size=self._update_card_rect)

        trans_card.add_widget(Label(
            text="Transcription & Translation (forward strand)",
            font_size="15sp",
            color=(0.93, 0.98, 1.0, 1),
            size_hint_y=None,
            height=dp(24),
        ))

        rna_preview = rna[:80] + ("…" if len(rna) > 80 else "")
        trans_card.add_widget(Label(
            text=f"mRNA (5'→3'): {rna_preview}",
            font_size="12sp",
            color=(0.82, 0.92, 1.0, 1),
            size_hint_y=None,
            height=dp(32),
        ))

        # 3 frames
        for idx, aa in enumerate([aa1, aa2, aa3], start=1):
            aa_prev = aa[:60] + ("…" if len(aa) > 60 else "")
            trans_card.add_widget(Label(
                text=f"+{idx} frame: {aa_prev}",
                font_size="12sp",
                color=(0.84, 0.94, 1.0, 1),
                size_hint_y=None,
                height=dp(26),
            ))

        self.results_container.add_widget(trans_card)

        # === ORFs CARD ===================================================
        orfs = find_orfs_simple(dna, min_aa=10)   # small threshold for mobile demo

        orf_card = BoxLayout(
            orientation="vertical",
            padding=dp(8),
            spacing=dp(4),
            size_hint_y=None,
            height=dp(40 + 22 * max(1, len(orfs[:8]))),
        )
        with orf_card.canvas.before:
            Color(0.12, 0.18, 0.30, 1)
            orf_card._rect = RoundedRectangle(
                radius=[dp(16)] * 4,
                pos=orf_card.pos,
                size=orf_card.size,
            )
        orf_card.bind(pos=self._update_card_rect, size=self._update_card_rect)

        if orfs:
            orf_card.add_widget(Label(
                text="ORFs (forward strand, min 10 aa) — showing up to 8",
                font_size="14sp",
                color=(0.93, 0.98, 1.0, 1),
                size_hint_y=None,
                height=dp(24),
            ))
            for o in orfs[:8]:
                line = f"Frame +{o['frame']} • {o['start_bp']}–{o['end_bp']} bp  ({o['aa_len']} aa)"
                orf_card.add_widget(Label(
                    text=line,
                    font_size="12sp",
                    color=(0.86, 0.95, 1.0, 1),
                    size_hint_y=None,
                    height=dp(20),
                ))
        else:
            orf_card.add_widget(Label(
                text="No ORFs ≥ 10 aa found on the forward strand.",
                font_size="13sp",
                color=(0.86, 0.90, 1.0, 1),
                size_hint_y=None,
                height=dp(26),
            ))

        self.results_container.add_widget(orf_card)

        # === MOTIFS + RESTRICTION SITES CARD =============================
        motifs = find_motifs_regex(dna)
        re_hits = find_restriction_sites(dna)

        # collect cut positions for all RE hits
        cut_positions = [h["start"] for h in re_hits]
        frag_sizes = simulate_digest(dna, cut_positions) if cut_positions else []

        motif_card_height = dp(40)  # base
        motif_lines = max(1, len(motifs[:5]) + len(re_hits[:5]))
        motif_card_height += dp(20) * motif_lines
        if frag_sizes:
            motif_card_height += dp(26)

        motif_card = BoxLayout(
            orientation="vertical",
            padding=dp(8),
            spacing=dp(4),
            size_hint_y=None,
            height=motif_card_height,
        )
        with motif_card.canvas.before:
            Color(0.11, 0.17, 0.29, 1)
            motif_card._rect = RoundedRectangle(
                radius=[dp(16)] * 4,
                pos=motif_card.pos,
                size=motif_card.size,
            )
        motif_card.bind(pos=self._update_card_rect, size=self._update_card_rect)

        motif_card.add_widget(Label(
            text="Motifs & Restriction Sites",
            font_size="14sp",
            size_hint_y=None,
            height=dp(22),
        ))

        if motifs:
            motif_card.add_widget(Label(
                text=f"Motifs (showing up to 5):",
                font_size="12sp",
                size_hint_y=None,
                height=dp(18),
            ))
            for m in motifs[:5]:
                line = f"- {m['name']} at {m['start']}–{m['end']} bp"
                motif_card.add_widget(Label(
                    text=line,
                    font_size="11sp",
                    size_hint_y=None,
                    height=dp(18),
                ))
        else:
            motif_card.add_widget(Label(
                text="No TATA / GC-box motifs found (simple patterns).",
                font_size="11sp",
                size_hint_y=None,
                height=dp(18),
            ))

        if re_hits:
            motif_card.add_widget(Label(
                text=f"Restriction sites (showing up to 5):",
                font_size="12sp",
                size_hint_y=None,
                height=dp(18),
            ))
            for h in re_hits[:5]:
                line = f"- {h['enzyme']} at {h['start']}–{h['end']} bp"
                motif_card.add_widget(Label(
                    text=line,
                    font_size="11sp",
                    size_hint_y=None,
                    height=dp(18),
                ))
        else:
            motif_card.add_widget(Label(
                text="No EcoRI / BamHI sites found.",
                font_size="11sp",
                size_hint_y=None,
                height=dp(18),
            ))

        if frag_sizes:
            frag_sizes_sorted = sorted(frag_sizes, reverse=True)
            frag_str = ", ".join(str(x) for x in frag_sizes_sorted[:6])
            if len(frag_sizes_sorted) > 6:
                frag_str += ", …"
            motif_card.add_widget(Label(
                text=f"Simulated digest fragments (bp): {frag_str}",
                font_size="11sp",
                size_hint_y=None,
                height=dp(22),
            ))

        self.results_container.add_widget(motif_card)

        # === EDITING CARD ===============================================
        edit_card = BoxLayout(
            orientation="vertical",
            padding=dp(8),
            spacing=dp(4),
            size_hint_y=None,
            height=dp(210),
        )
        with edit_card.canvas.before:
            Color(0.11, 0.19, 0.34, 1)
            edit_card._rect = RoundedRectangle(
                radius=[dp(16)] * 4,
                pos=edit_card.pos,
                size=edit_card.size,
            )
        edit_card.bind(pos=self._update_card_rect, size=self._update_card_rect)

        edit_card.add_widget(Label(
            text="✂️ In-silico editing (applies to input and re-analyzes)",
            font_size="14sp",
            color=(0.93, 0.98, 1.0, 1),
            size_hint_y=None,
            height=dp(24),
        ))

        # SNP row
        snp_row = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(30),
            spacing=dp(4),
        )
        snp_row.add_widget(Label(
            text="SNP @ pos:",
            font_size="12sp",
            color=(0.86, 0.95, 1.0, 1),
            size_hint_x=None,
            width=dp(70),
        ))
        self.snp_pos_input = TextInput(
            text="0",
            multiline=False,
            size_hint_x=None,
            width=dp(60),
            font_size="12sp",
        )
        self.snp_base_input = TextInput(
            text="A",
            multiline=False,
            size_hint_x=None,
            width=dp(40),
            font_size="12sp",
        )
        snp_apply = Button(
            text="Apply SNP",
            size_hint_x=1,
            font_size="12sp",
            background_normal="",
            background_color=(0.30, 0.70, 0.95, 1),
        )
        snp_apply.bind(on_press=self._apply_snp)

        snp_row.add_widget(self.snp_pos_input)
        snp_row.add_widget(self.snp_base_input)
        snp_row.add_widget(snp_apply)
        edit_card.add_widget(snp_row)

        # Insertion row
        ins_row = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(30),
            spacing=dp(4),
        )
        ins_row.add_widget(Label(
            text="Insert @ pos:",
            font_size="12sp",
            color=(0.86, 0.95, 1.0, 1),
            size_hint_x=None,
            width=dp(80),
        ))
        self.ins_pos_input = TextInput(
            text=str(length),
            multiline=False,
            size_hint_x=None,
            width=dp(60),
            font_size="12sp",
        )
        self.ins_seq_input = TextInput(
            text="TTT",
            multiline=False,
            size_hint_x=1,
            font_size="12sp",
        )
        ins_apply = Button(
            text="Apply ins",
            size_hint_x=None,
            width=dp(80),
            font_size="12sp",
            background_normal="",
            background_color=(0.25, 0.75, 0.55, 1),
        )
        ins_apply.bind(on_press=self._apply_insertion)

        ins_row.add_widget(self.ins_pos_input)
        ins_row.add_widget(self.ins_seq_input)
        ins_row.add_widget(ins_apply)
        edit_card.add_widget(ins_row)

        # Deletion row
        del_row = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(30),
            spacing=dp(4),
        )
        del_row.add_widget(Label(
            text="Delete [start,end):",
            font_size="12sp",
            color=(0.86, 0.95, 1.0, 1),
            size_hint_x=None,
            width=dp(110),
        ))
        self.del_start_input = TextInput(
            text="0",
            multiline=False,
            size_hint_x=None,
            width=dp(60),
            font_size="12sp",
        )
        self.del_end_input = TextInput(
            text=str(min(10, length)),
            multiline=False,
            size_hint_x=None,
            width=dp(60),
            font_size="12sp",
        )
        del_apply = Button(
            text="Apply del",
            size_hint_x=1,
            font_size="12sp",
            background_normal="",
            background_color=(0.85, 0.45, 0.45, 1),
        )
        del_apply.bind(on_press=self._apply_deletion)

        del_row.add_widget(self.del_start_input)
        del_row.add_widget(self.del_end_input)
        del_row.add_widget(del_apply)
        edit_card.add_widget(del_row)

        # small hint
        edit_card.add_widget(Label(
            text="Indices are 0-based. After edit, the input box is updated and re-analyzed.",
            font_size="11sp",
            color=(0.80, 0.88, 1.0, 1),
            size_hint_y=None,
            height=dp(32),
        ))

        self.results_container.add_widget(edit_card)

    # ─────────────────────────────────────────
    # Edit actions
    # ─────────────────────────────────────────
    def _apply_snp(self, *args):
        dna = sanitize_sequence(self.dna_input.text or "")
        if not dna:
            return
        try:
            pos = int(self.snp_pos_input.text)
        except (TypeError, ValueError):
            return
        base = (self.snp_base_input.text or "").upper()
        if base not in "ACGT":
            return
        if not (0 <= pos < len(dna)):
            return
        dna_list = list(dna)
        dna_list[pos] = base
        self.dna_input.text = "".join(dna_list)
        self.on_analyze()

    def _apply_insertion(self, *args):
        dna = sanitize_sequence(self.dna_input.text or "")
        if not dna:
            return
        try:
            pos = int(self.ins_pos_input.text)
        except (TypeError, ValueError):
            return
        ins_seq = sanitize_sequence(self.ins_seq_input.text or "")
        if not ins_seq:
            return
        pos = max(0, min(len(dna), pos))
        new_seq = dna[:pos] + ins_seq + dna[pos:]
        self.dna_input.text = new_seq
        self.on_analyze()

    def _apply_deletion(self, *args):
        dna = sanitize_sequence(self.dna_input.text or "")
        if not dna:
            return
        try:
            s = int(self.del_start_input.text)
            e = int(self.del_end_input.text)
        except (TypeError, ValueError):
            return
        s = max(0, min(len(dna), s))
        e = max(0, min(len(dna), e))
        if e <= s:
            return
        new_seq = dna[:s] + dna[e:]
        self.dna_input.text = new_seq
        self.on_analyze()
