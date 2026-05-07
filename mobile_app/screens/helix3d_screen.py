from math import sin, cos, pi

from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.metrics import dp
from kivy.graphics import Color, RoundedRectangle, Line, Rectangle


class HelixPreview(BoxLayout):
    """
    Simple 2D '3D-like' helix drawing using Kivy canvas.
    Not real 3D, but looks much nicer than a raw Matplotlib plot
    and actually updates on button press.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.n_bp = 50  # number of "base pairs" to draw
        self.phase_offset = 0.0

        with self.canvas.before:
            # background for the preview area
            Color(0.09, 0.13, 0.22, 1)
            self._bg_rect = RoundedRectangle(radius=[dp(18)] * 4,
                                             pos=self.pos, size=self.size)

        with self.canvas:
            # main strands
            Color(0.40, 0.85, 0.50, 1)  # greenish
            self._strand1 = Line(width=1.8)
            Color(0.40, 0.65, 0.95, 1)  # bluish
            self._strand2 = Line(width=1.8)
            # rungs; we’ll reuse one Line object with many segments
            Color(1, 1, 1, 0.6)
            self._rungs = Line(width=1.1)

        self.bind(pos=self._update_canvas, size=self._update_canvas)

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------
    def set_preset(self, preset: str):
        """
        Change how many bp we 'draw' and phase it slightly
        so each preset looks a bit different.
        """
        if preset == "short":
            self.n_bp = 40
            self.phase_offset = 0.0
        elif preset == "medium":
            self.n_bp = 90
            self.phase_offset = pi / 4
        else:  # long
            self.n_bp = 160
            self.phase_offset = pi / 2

        self._update_canvas()

    # ------------------------------------------------------------------
    # drawing helpers
    # ------------------------------------------------------------------
    def _update_canvas(self, *args):
        # update background rect
        self._bg_rect.pos = self.pos
        self._bg_rect.size = self.size

        w, h = self.size
        if w <= 0 or h <= 0:
            return

        # margins
        left = self.x + dp(20)
        right = self.right - dp(20)
        top = self.top - dp(20)
        bottom = self.y + dp(20)

        # helix parameters
        n = max(10, int(self.n_bp))
        height = top - bottom
        center_x = (left + right) / 2.0
        radius = min((right - left) / 4.0, height / 5.0)

        # strands and rungs
        points1 = []
        points2 = []
        rung_points = []

        for i in range(n):
            t = i / float(n - 1) if n > 1 else 0.0
            # y goes from bottom to top
            y = bottom + t * height

            # angle for the twist
            angle = 2.5 * pi * t + self.phase_offset
            dx = radius * cos(angle)
            depth = 0.6 + 0.4 * sin(angle)  # fake depth shading

            x1 = center_x - dx
            x2 = center_x + dx

            # store points for lines
            points1.extend([x1, y])
            points2.extend([x2, y])

            # small probability-like thinning of rungs on "back" side
            if depth > 0.5:
                rung_points.extend([x1, y, x2, y])

        self._strand1.points = points1
        self._strand2.points = points2
        self._rungs.points = rung_points


class Helix3DScreen(Screen):
    """
    Helix Mobile — 3D Helix Playground (Duolingo-ish look)
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # === ROOT BACKGROUND ==================================================
        root = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(12))
        with root.canvas.before:
            # dark base background
            Color(0.07, 0.10, 0.18, 1)
            self._bg_rect = Rectangle(pos=self.pos, size=self.size)
        root.bind(pos=self._update_bg, size=self._update_bg)
        self.add_widget(root)

        # === HEADER ===========================================================
        header = BoxLayout(orientation="vertical",
                           size_hint_y=None, height=dp(80), spacing=dp(4))

        title = Label(
            text="🧬 3D Helix Playground",
            font_size="24sp",
            bold=True,
        )
        subtitle = Label(
            text="See your DNA as a double helix — mobile edition",
            font_size="13sp",
            color=(0.8, 0.8, 0.9, 1),
        )
        header.add_widget(title)
        header.add_widget(subtitle)
        root.add_widget(header)

        # === CARD WITH PREVIEW ===============================================
        card_container = AnchorLayout(size_hint_y=None, height=dp(260))
        card = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(8),
                         size_hint=(0.98, 1))
        # card background
        with card.canvas.before:
            Color(0.13, 0.18, 0.30, 1)
            card._rect = RoundedRectangle(radius=[dp(16)] * 4,
                                          pos=card.pos, size=card.size)
        card.bind(pos=self._update_card_rect, size=self._update_card_rect)

        card_title = Label(
            text="Current Preview",
            font_size="16sp",
            size_hint_y=None,
            height=dp(22),
        )
        card.add_widget(card_title)

        # our custom helix preview widget
        self.preview_widget = HelixPreview()
        card.add_widget(self.preview_widget)

        self.caption = Label(
            text="Pick a length preset and tap ✨ Generate 3D Preview.",
            font_size="12sp",
            size_hint_y=None,
            height=dp(24),
            color=(0.8, 0.8, 0.9, 1),
        )
        card.add_widget(self.caption)

        card_container.add_widget(card)
        root.add_widget(card_container)

        # === PRESET BUTTONS ROW ==============================================
        root.add_widget(Label(
            text="Choose region length",
            font_size="15sp",
            size_hint_y=None,
            height=dp(24),
        ))

        presets_row = BoxLayout(orientation="horizontal",
                                size_hint_y=None, height=dp(40), spacing=dp(8))

        self.preset_short = self._pill_button("Short (≈50 bp)", selected=True)
        self.preset_med = self._pill_button("Medium (≈150 bp)")
        self.preset_long = self._pill_button("Long (≈300 bp)")

        self.preset_short.bind(on_press=lambda *_: self._select_preset("short"))
        self.preset_med.bind(on_press=lambda *_: self._select_preset("medium"))
        self.preset_long.bind(on_press=lambda *_: self._select_preset("long"))

        presets_row.add_widget(self.preset_short)
        presets_row.add_widget(self.preset_med)
        presets_row.add_widget(self.preset_long)
        root.add_widget(presets_row)

        # === MAIN ACTION BUTTON ==============================================
        action_btn = Button(
            text="✨ Generate 3D Preview",
            size_hint_y=None,
            height=dp(52),
            background_normal="",
            background_color=(0.35, 0.80, 0.45, 1),
            color=(0, 0, 0, 1),
            bold=True,
            on_press=self.on_generate_preview,
        )
        root.add_widget(action_btn)

        # === BACK BUTTON + FOOTER ============================================
        back_btn = Button(
            text="← Back to DNA tools",
            size_hint_y=None,
            height=dp(40),
            background_normal="",
            background_color=(0.16, 0.22, 0.33, 1),
            color=(1, 1, 1, 1),
            on_press=self._go_back,
        )
        root.add_widget(back_btn)

        foot = Label(
            text="Mobile helix is a simplified visual — full 3D lives in desktop Helix.",
            font_size="11sp",
            size_hint_y=None,
            height=dp(20),
            color=(0.7, 0.7, 0.8, 1),
        )
        root.add_widget(foot)

        # state
        self.selected_preset = "short"
        # initialize preview
        self.preview_widget.set_preset("short")

    # =====================================================================
    #  DRAW HELPERS
    # =====================================================================
    def _update_bg(self, instance, value):
        if hasattr(self, "_bg_rect"):
            self._bg_rect.pos = instance.pos
            self._bg_rect.size = instance.size

    def _update_card_rect(self, instance, value):
        if hasattr(instance, "_rect"):
            instance._rect.pos = instance.pos
            instance._rect.size = instance.size

    # =====================================================================
    #  UI HELPERS
    # =====================================================================
    def _pill_button(self, text, selected: bool = False) -> Button:
        btn = Button(
            text=text,
            size_hint=(1, 1),
            background_normal="",
            font_size="13sp",
        )
        if selected:
            btn.background_color = (0.35, 0.80, 0.45, 1)
            btn.color = (0, 0, 0, 1)
        else:
            btn.background_color = (0.16, 0.22, 0.33, 1)
            btn.color = (1, 1, 1, 1)
        return btn

    def _select_preset(self, which: str):
        self.selected_preset = which
        # reset colors
        for btn in [self.preset_short, self.preset_med, self.preset_long]:
            btn.background_color = (0.16, 0.22, 0.33, 1)
            btn.color = (1, 1, 1, 1)

        # highlight chosen preset
        if which == "short":
            btn = self.preset_short
        elif which == "medium":
            btn = self.preset_med
        else:
            btn = self.preset_long

        btn.background_color = (0.35, 0.80, 0.45, 1)
        btn.color = (0, 0, 0, 1)

    # =====================================================================
    #  LOGIC
    # =====================================================================
    def on_generate_preview(self, *args):
        """
        Now this actually updates the helix drawing on screen,
        not just prints to console.
        """
        self.preview_widget.set_preset(self.selected_preset)
        if self.selected_preset == "short":
            msg = "Previewing a short fragment (≈50 bp)."
        elif self.selected_preset == "medium":
            msg = "Previewing a medium fragment (≈150 bp)."
        else:
            msg = "Previewing a long fragment (≈300 bp)."

        self.caption.text = msg

    def _go_back(self, *args):
        if self.manager:
            self.manager.current = "dna"
