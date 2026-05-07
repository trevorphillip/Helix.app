from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.metrics import dp
from kivy.graphics import Color, RoundedRectangle, Rectangle


class HomeScreen(Screen):
    """
    Helix Mobile — Home
    - Neon dark UI, like the web app
    - Quick nav to DNA / Protein / 3D Helix
    - Shows summary of last DNA analysis
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.last_length = 0
        self.last_pam_count = 0
        self.last_grna_count = 0

        # Root container with dark background
        root = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(12))
        with root.canvas.before:
            # dark navy background
            Color(0.05, 0.08, 0.14, 1)
            self._bg_rect = Rectangle(pos=root.pos, size=root.size)
        root.bind(pos=self._update_bg, size=self._update_bg)
        self.add_widget(root)

        # ─────────────────────────────────────
        # HEADER
        # ─────────────────────────────────────
        header = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            height=dp(90),
            spacing=dp(4),
        )

        title = Label(
            text="🧬 Helix Mobile",
            font_size="26sp",
            bold=True,
            color=(0.93, 0.98, 1.0, 1),
        )
        subtitle = Label(
            text="CRISPR • DNA • Protein — in your pocket",
            font_size="14sp",
            color=(0.70, 0.82, 0.98, 1),
        )

        # little "chip row"
        chip_row = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(26),
            spacing=dp(6),
        )

        chip_row.add_widget(self._make_chip("Offline"))
        chip_row.add_widget(self._make_chip("Student-friendly"))
        chip_row.add_widget(self._make_chip("Prototype"))

        header.add_widget(title)
        header.add_widget(subtitle)
        header.add_widget(chip_row)
        root.add_widget(header)

        # ─────────────────────────────────────
        # STATS CARDS
        # ─────────────────────────────────────
        stats_row = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(90),
            spacing=dp(10),
        )

        self.card_len = self._make_stat_card("Last DNA length", "—")
        self.card_pam = self._make_stat_card("PAM sites (NGG)", "—")
        self.card_grna = self._make_stat_card("gRNAs", "—")

        stats_row.add_widget(self.card_len)
        stats_row.add_widget(self.card_pam)
        stats_row.add_widget(self.card_grna)

        root.add_widget(stats_row)

        # ─────────────────────────────────────
        # SECTION TITLE
        # ─────────────────────────────────────
        root.add_widget(Label(
            text="Tools",
            font_size="17sp",
            bold=True,
            color=(0.90, 0.96, 1.0, 1),
            size_hint_y=None,
            height=dp(26),
        ))

        # ─────────────────────────────────────
        # NAV BUTTONS (big, rounded, neon-ish)
        # ─────────────────────────────────────
        # DNA button
        dna_btn = Button(
            text="🧬 DNA / CRISPR Tools",
            size_hint_y=None,
            height=dp(52),
            background_normal="",
            background_color=(0.22, 0.72, 0.55, 1),
            color=(0.02, 0.04, 0.06, 1),
            bold=True,
            font_size="15sp",
        )
        dna_btn.bind(on_press=self.on_open_dna)
        root.add_widget(dna_btn)

        # Protein button
        prot_btn = Button(
            text="🧪 Protein Tools",
            size_hint_y=None,
            height=dp(52),
            background_normal="",
            background_color=(0.25, 0.60, 0.95, 1),
            color=(0.02, 0.04, 0.06, 1),
            bold=True,
            font_size="15sp",
        )
        prot_btn.bind(on_press=self.on_open_protein)
        root.add_widget(prot_btn)

        # 3D Helix button
        helix3d_btn = Button(
            text="🧱 3D Helix (beta)",
            size_hint_y=None,
            height=dp(50),
            background_normal="",
            background_color=(0.40, 0.28, 0.80, 1),
            color=(0.98, 0.99, 1.0, 1),
            bold=True,
            font_size="14sp",
        )
        helix3d_btn.bind(on_press=self.on_open_helix3d)
        root.add_widget(helix3d_btn)

        # Spacer
        root.add_widget(Label(size_hint_y=1))

        # Footer
        footer = Label(
            text="Helix Genetics Suite — mobile prototype",
            font_size="11sp",
            color=(0.55, 0.66, 0.82, 1),
            size_hint_y=None,
            height=dp(22),
        )
        root.add_widget(footer)

    # ─────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────
    def _update_bg(self, instance, value):
        if hasattr(self, "_bg_rect"):
            self._bg_rect.pos = instance.pos
            self._bg_rect.size = instance.size

    def _make_chip(self, text: str) -> BoxLayout:
        box = BoxLayout(
            orientation="horizontal",
            size_hint_x=None,
            width=dp(110),
            padding=(dp(8), dp(2)),
        )
        with box.canvas.before:
            Color(0.16, 0.24, 0.40, 1)
            box._rect = RoundedRectangle(
                radius=[dp(999)] * 4,
                pos=box.pos,
                size=box.size,
            )
        box.bind(pos=self._update_chip_rect, size=self._update_chip_rect)
        lbl = Label(
            text=text,
            font_size="11sp",
            color=(0.78, 0.90, 1.0, 1),
        )
        box.add_widget(lbl)
        return box

    def _update_chip_rect(self, instance, value):
        if hasattr(instance, "_rect"):
            instance._rect.pos = instance.pos
            instance._rect.size = instance.size

    def _make_stat_card(self, label_text: str, value_text: str) -> BoxLayout:
        box = BoxLayout(
            orientation="vertical",
            padding=dp(8),
            spacing=dp(4),
        )
        with box.canvas.before:
            # subtle card with neon border
            Color(0.10, 0.16, 0.28, 1)
            box._rect = RoundedRectangle(
                radius=[dp(14)] * 4,
                pos=box.pos,
                size=box.size,
            )
        box.bind(pos=self._update_card_rect, size=self._update_card_rect)

        lbl = Label(
            text=label_text,
            font_size="11sp",
            color=(0.70, 0.82, 0.98, 1),
            size_hint_y=None,
            height=dp(18),
        )
        val = Label(
            text=value_text,
            font_size="18sp",
            bold=True,
            color=(0.95, 1.0, 0.95, 1),
            size_hint_y=None,
            height=dp(26),
        )
        box.label = lbl
        box.value = val
        box.add_widget(lbl)
        box.add_widget(val)
        return box

    def _update_card_rect(self, instance, value):
        if hasattr(instance, "_rect"):
            instance._rect.pos = instance.pos
            instance._rect.size = instance.size

    # this is called from DNAScreen after analysis
    def update_sequence_summary(self, length_bp: int, pam_count: int, grna_count: int):
        self.last_length = length_bp
        self.last_pam_count = pam_count
        self.last_grna_count = grna_count

        self.card_len.value.text = f"{length_bp} bp"
        self.card_pam.value.text = str(pam_count)
        self.card_grna.value.text = str(grna_count)

    # ─────────────────────────────────────
    # Navigation callbacks
    # ─────────────────────────────────────
    def on_open_dna(self, *args):
        if self.manager:
            self.manager.current = "dna"

    def on_open_protein(self, *args):
        if self.manager:
            self.manager.current = "protein"

    def on_open_helix3d(self, *args):
        if self.manager:
            self.manager.current = "helix3d"
