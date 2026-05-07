from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.metrics import dp
from kivy.graphics import Color, RoundedRectangle, Rectangle

# ─────────────────────────────────────────
# Simple protein utils (no external deps)
# ─────────────────────────────────────────

AA_SET = set("ACDEFGHIKLMNPQRSTVWY")


def aa_only(seq: str) -> str:
    if not seq:
        return ""
    return "".join(ch for ch in seq.upper() if ch in AA_SET)


# Approximate residue masses (Da), side chain only, but good enough
AA_MASS = {
    "A": 89.09, "C": 121.16, "D": 133.10, "E": 147.13, "F": 165.19,
    "G": 75.07, "H": 155.16, "I": 131.18, "K": 146.19, "L": 131.18,
    "M": 149.21, "N": 132.12, "P": 115.13, "Q": 146.15, "R": 174.20,
    "S": 105.09, "T": 119.12, "V": 117.15, "W": 204.23, "Y": 181.19,
}

# Kyte–Doolittle hydropathy (same as web app logic)
KD = {
    "I": 4.5, "V": 4.2, "L": 3.8, "F": 2.8, "C": 2.5, "M": 1.9,
    "A": 1.8, "G": -0.4, "T": -0.7, "S": -0.8, "W": -0.9,
    "Y": -1.3, "P": -1.6, "H": -3.2, "E": -3.5, "Q": -3.5,
    "D": -3.5, "N": -3.5, "K": -3.9, "R": -4.5,
}


def estimate_mw(seq: str) -> float:
    """
    Rough MW for peptide:
      sum(residue masses) - (n - 1)*18 (water loss for peptide bonds)
    """
    seq = aa_only(seq)
    if not seq:
        return 0.0
    total = sum(AA_MASS.get(a, 110.0) for a in seq)
    # subtract water for each peptide bond
    total -= (len(seq) - 1) * 18.015
    return max(0.0, total)


def gravy_score(seq: str) -> float:
    """
    Simple GRAVY = mean(KD hydropathy).
    """
    seq = aa_only(seq)
    if not seq:
        return 0.0
    vals = [KD.get(a, 0.0) for a in seq]
    return sum(vals) / len(vals)


def aa_composition(seq: str):
    """
    Returns dict {aa: percent} (0–100).
    """
    seq = aa_only(seq)
    n = len(seq)
    if n == 0:
        return {aa: 0.0 for aa in sorted(AA_SET)}
    comp = {aa: 0 for aa in sorted(AA_SET)}
    for a in seq:
        comp[a] += 1
    return {aa: (count / n) * 100.0 for aa, count in comp.items()}


def charge_counts(seq: str):
    """
    Very rough "charged residues" count at neutral pH:
      Positive: K, R, (H mild)
      Negative: D, E
    """
    seq = aa_only(seq)
    pos = seq.count("K") + seq.count("R")
    # treat H as partially positive
    pos_partial = seq.count("H")
    neg = seq.count("D") + seq.count("E")
    return pos, pos_partial, neg


# ─────────────────────────────────────────
# ProteinScreen
# ─────────────────────────────────────────

class ProteinScreen(Screen):
    """
    Protein Tools (mobile)
    - Paste AA sequence
    - Length, MW, GRAVY-like hydropathy
    - Charged residues
    - Composition summary
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Root + background
        root = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(12))
        with root.canvas.before:
            Color(0.05, 0.08, 0.14, 1)
            self._bg_rect = Rectangle(pos=root.pos, size=root.size)
        root.bind(pos=self._update_bg, size=self._update_bg)
        self.add_widget(root)

        # Top bar (back + title)
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
            text="🧪 Protein Tools",
            font_size="20sp",
            bold=True,
            color=(0.93, 0.98, 1.0, 1),
        )

        top_bar.add_widget(back_btn)
        top_bar.add_widget(title_lbl)
        root.add_widget(top_bar)

        # Subtitle
        subtitle = Label(
            text="Paste AA sequence → basic biophysics summary",
            font_size="13sp",
            color=(0.70, 0.82, 0.98, 1),
            size_hint_y=None,
            height=dp(24),
        )
        root.add_widget(subtitle)

        # Input card
        input_card = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            height=dp(170),
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
            text="Protein sequence (one-letter AA)",
            font_size="15sp",
            color=(0.88, 0.96, 1.0, 1),
            size_hint_y=None,
            height=dp(24),
        ))

        # simple demo peptide, helix-y, similar to web app presets
        example = "AKLAEELAKLAEELAKL"
        self.aa_input = TextInput(
            text=example,
            multiline=True,
            size_hint_y=1,
            font_size="13sp",
            background_color=(0.03, 0.05, 0.09, 1),
            foreground_color=(0.93, 0.98, 1.0, 1),
            cursor_color=(0.60, 0.85, 0.98, 1),
        )
        input_card.add_widget(self.aa_input)

        root.add_widget(input_card)

        # Analyze button
        analyze_btn = Button(
            text="🧪 Analyze protein",
            size_hint_y=None,
            height=dp(50),
            background_normal="",
            background_color=(0.25, 0.60, 0.95, 1),
            color=(0.02, 0.04, 0.06, 1),
            bold=True,
            font_size="15sp",
        )
        analyze_btn.bind(on_press=self.on_analyze)
        root.add_widget(analyze_btn)

        # Scrollable results
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
        raw = self.aa_input.text or ""
        seq = aa_only(raw)
        self.results_container.clear_widgets()

        if not seq:
            self.results_container.add_widget(Label(
                text="No valid amino-acid letters found (A C D E F G H I K L M N P Q R S T V W Y).",
                font_size="13sp",
                color=(0.96, 0.88, 0.88, 1),
                size_hint_y=None,
                height=dp(40),
            ))
            return

        n = len(seq)
        mw = estimate_mw(seq)
        gravy = gravy_score(seq)
        pos, pos_partial, neg = charge_counts(seq)
        comp = aa_composition(seq)

        # BASIC CARD
        basic_card = BoxLayout(
            orientation="vertical",
            padding=dp(8),
            spacing=dp(4),
            size_hint_y=None,
            height=dp(110),
        )
        with basic_card.canvas.before:
            Color(0.10, 0.17, 0.30, 1)
            basic_card._rect = RoundedRectangle(
                radius=[dp(16)] * 4,
                pos=basic_card.pos,
                size=basic_card.size,
            )
        basic_card.bind(pos=self._update_card_rect, size=self._update_card_rect)

        basic_card.add_widget(Label(
            text=f"Length: {n} aa   •   MW ≈ {mw:,.1f} Da",
            font_size="14sp",
            color=(0.93, 0.98, 1.0, 1),
            size_hint_y=None,
            height=dp(24),
        ))

        basic_card.add_widget(Label(
            text=f"GRAVY (hydropathy): {gravy:+.2f}   •   +charged: {pos}+({pos_partial}H)   •   -charged: {neg}",
            font_size="13sp",
            color=(0.82, 0.92, 1.0, 1),
            size_hint_y=None,
            height=dp(26),
        ))

        preview = seq[:60] + ("…" if len(seq) > 60 else "")
        basic_card.add_widget(Label(
            text=f"N-term → {preview}",
            font_size="13sp",
            color=(0.78, 0.90, 1.0, 1),
            size_hint_y=None,
            height=dp(40),
        ))

        self.results_container.add_widget(basic_card)

        # COMPOSITION CARD
        comp_card = BoxLayout(
            orientation="vertical",
            padding=dp(8),
            spacing=dp(4),
            size_hint_y=None,
            height=dp(40 + 22 * 5),  # ~5 rows
        )
        with comp_card.canvas.before:
            Color(0.11, 0.18, 0.33, 1)
            comp_card._rect = RoundedRectangle(
                radius=[dp(16)] * 4,
                pos=comp_card.pos,
                size=comp_card.size,
            )
        comp_card.bind(pos=self._update_card_rect, size=self._update_card_rect)

        comp_card.add_widget(Label(
            text="Amino-acid composition (percent)",
            font_size="14sp",
            color=(0.93, 0.98, 1.0, 1),
            size_hint_y=None,
            height=dp(24),
        ))

        # display composition in 3–4 columns per row
        sorted_aa = sorted(comp.items(), key=lambda kv: kv[0])
        row = None
        per_row = 5
        for idx, (aa, pct) in enumerate(sorted_aa):
            if idx % per_row == 0:
                if row is not None:
                    comp_card.add_widget(row)
                row = BoxLayout(
                    orientation="horizontal",
                    size_hint_y=None,
                    height=dp(22),
                    spacing=dp(6),
                )
            lbl = Label(
                text=f"{aa}: {pct:4.1f} %",
                font_size="12sp",
                color=(0.88, 0.96, 1.0, 1),
            )
            row.add_widget(lbl)

        if row is not None:
            comp_card.add_widget(row)

        self.results_container.add_widget(comp_card)
