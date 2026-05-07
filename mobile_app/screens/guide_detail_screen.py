# mobile_app/screens/guide_detail_screen.py
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.metrics import dp
from kivy.graphics import Color, RoundedRectangle, Rectangle


def _sanitize_dna(seq: str) -> str:
    seq = (seq or "").upper()
    return "".join(ch for ch in seq if ch in "ACGT")


def _gc_pct(s: str) -> float:
    s = (s or "").upper()
    if not s:
        return 0.0
    return 100.0 * (s.count("G") + s.count("C")) / max(1, len(s))


class GuideDetailScreen(Screen):
    """
    Shows details for a selected gRNA:
    - sequence + PAM + strand
    - GC%
    - approximate cut position
    - context window (before/after)
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.genome = ""
        self.hit = None  # dict-like

        root = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(12))
        with root.canvas.before:
            Color(0.07, 0.10, 0.18, 1)
            self._bg = Rectangle(pos=root.pos, size=root.size)
        root.bind(pos=self._update_bg, size=self._update_bg)
        self.add_widget(root)

        # Top bar (Back)
        top = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(44), spacing=dp(10))
        back = Button(
            text="← Back",
            size_hint_x=None,
            width=dp(110),
            background_normal="",
            background_color=(0.20, 0.26, 0.40, 1),
            color=(1, 1, 1, 1),
        )
        back.bind(on_press=self.go_back)
        self.title_lbl = Label(text="gRNA details", font_size="18sp", bold=True)
        top.add_widget(back)
        top.add_widget(self.title_lbl)
        root.add_widget(top)

        # Scroll content
        scroll = ScrollView()
        self.stack = BoxLayout(orientation="vertical", spacing=dp(10), size_hint_y=None)
        self.stack.bind(minimum_height=self.stack.setter("height"))
        scroll.add_widget(self.stack)
        root.add_widget(scroll)

        # empty state
        self._render_empty()

    def _update_bg(self, instance, _):
        self._bg.pos = instance.pos
        self._bg.size = instance.size

    def _card(self, title: str, lines: list[str]):
        card = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(6), size_hint_y=None)
        # approximate height: title + lines
        card.height = dp(52 + 20 * max(1, len(lines)))
        with card.canvas.before:
            Color(0.13, 0.19, 0.32, 1)
            card._rect = RoundedRectangle(radius=[dp(16)] * 4, pos=card.pos, size=card.size)
        card.bind(pos=self._update_rect, size=self._update_rect)

        card.add_widget(Label(text=title, font_size="15sp", bold=True, size_hint_y=None, height=dp(24)))
        for ln in lines:
            card.add_widget(Label(text=ln, font_size="12.5sp", size_hint_y=None, height=dp(18)))
        self.stack.add_widget(card)

    def _update_rect(self, instance, _):
        instance._rect.pos = instance.pos
        instance._rect.size = instance.size

    def _render_empty(self):
        self.stack.clear_widgets()
        self._card("No guide selected", ["Go back and tap a gRNA to view details."])

    def go_back(self, *_):
        if self.manager:
            self.manager.current = "dna"

    # ---------- Public API: called from DNAScreen ----------
    def set_guide(self, genome: str, hit: dict):
        """
        hit is a dict like:
        {
          "guide": "....",
          "pam": "....",
          "strand": "+"/"-",
          "pos": int,       # guide start position on forward coordinate system
          "pam_side": "3prime"/"5prime",
          "guide_len": int,
          "pam_len": int
        }
        """
        self.genome = _sanitize_dna(genome)
        self.hit = hit
        self._render()

    def _render(self):
        if not self.hit or not self.genome:
            return self._render_empty()

        self.stack.clear_widgets()

        guide = self.hit.get("guide", "")
        pam = self.hit.get("pam", "")
        strand = self.hit.get("strand", "+")
        pos = int(self.hit.get("pos", 0))
        pam_side = self.hit.get("pam_side", "3prime")
        guide_len = int(self.hit.get("guide_len", len(guide)))
        pam_len = int(self.hit.get("pam_len", len(pam)))

        guide = _sanitize_dna(guide)
        pam = _sanitize_dna(pam)

        gc = _gc_pct(guide)

        # Approx cut position (SpCas9 is ~3bp upstream of PAM on target strand).
        # We keep it simple: for 3' PAM, cut ≈ pos + guide_len - 3
        # for 5' PAM, cut ≈ pos + 3 (rough)
        if pam_side == "3prime":
            cut = pos + guide_len - 3
        else:
            cut = pos + 3

        cut = max(0, min(len(self.genome) - 1, cut))

        # Context window around guide
        left = max(0, pos - 18)
        right = min(len(self.genome), pos + guide_len + pam_len + 18)

        context = self.genome[left:right]
        # Mark guide region in context (simple brackets)
        g0 = pos - left
        g1 = g0 + guide_len
        context_marked = context[:g0] + "[" + context[g0:g1] + "]" + context[g1:]

        # Basic info card
        self._card("Guide overview", [
            f"Strand: {strand}   •   Start: {pos} bp",
            f"Guide ({guide_len}nt): {guide}",
            f"PAM ({pam_len}nt): {pam}   •   PAM side: {pam_side}",
            f"GC%: {gc:.1f}%",
            f"Approx cut position: {cut} bp",
        ])

        # Context card
        self._card("Sequence context", [
            f"{left} … {right} bp",
            context_marked[:90] + ("…" if len(context_marked) > 90 else ""),
        ])

        # “What it means” card (human-friendly)
        self._card("Meaning (simple)", [
            "Guide binds the matching DNA region.",
            "PAM is required for Cas enzyme recognition.",
            "Cut position is where edits/KO deletions would start.",
        ])
