# screens/sequence_tools_screen.py

from __future__ import annotations

from typing import Optional, List

from kivy.uix.scrollview import ScrollView
from kivy.metrics import dp

from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.textfield import MDTextField
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.slider import MDSlider
from kivymd.uix.card import MDCard

from utils.dna_utils import (
    clean_dna,
    is_valid_dna,
    gc_content,
    translate_dna,
    find_orfs,
)


class SequenceToolsScreen(MDScreen):
    """
    Mobile DNA tools screen:
      - DNA input
      - Length + GC% + validation
      - Translation (choose reading frame)
      - Simple ORF finder (forward strand)
    """

    def __init__(self, **kwargs):
        super().__init__(name="sequence_tools", **kwargs)
        self._built = False

        # widgets we'll need to access later
        self.input_field: Optional[MDTextField] = None
        self.length_label: Optional[MDLabel] = None
        self.gc_label: Optional[MDLabel] = None
        self.valid_label: Optional[MDLabel] = None

        self.frame_slider: Optional[MDSlider] = None
        self.min_orf_slider: Optional[MDSlider] = None
        self.translation_label: Optional[MDLabel] = None
        self.orf_label: Optional[MDLabel] = None

    # Kivy calls this when the screen is about to be shown
    def on_pre_enter(self, *args):
        if not self._built:
            self.build_ui()
            self._built = True
        return super().on_pre_enter(*args)

    def build_ui(self):
        root = MDBoxLayout(
            orientation="vertical",
            padding=dp(12),
            spacing=dp(8),
        )

        # Scrollable content (so long translations / ORF lists don't overflow)
        scroll = ScrollView()
        content = MDBoxLayout(
            orientation="vertical",
            spacing=dp(10),
            size_hint_y=None,
        )
        content.bind(minimum_height=content.setter("height"))

        # ---------------------------------------------------------------------
        # 1) TITLE
        # ---------------------------------------------------------------------
        title = MDLabel(
            text="Sequence Tools",
            halign="left",
            font_style="H5",
            size_hint_y=None,
            height=dp(40),
        )
        subtitle = MDLabel(
            text="Basic QC, translation & ORF finder (forward strand, educational only).",
            halign="left",
            theme_text_color="Secondary",
            size_hint_y=None,
            height=dp(32),
        )
        content.add_widget(title)
        content.add_widget(subtitle)

        # ---------------------------------------------------------------------
        # 2) DNA INPUT
        # ---------------------------------------------------------------------
        self.input_field = MDTextField(
            hint_text="Paste DNA sequence (A/C/G/T)...",
            helper_text="Non-ACGT characters will be removed automatically.",
            helper_text_mode="on_focus",
            multiline=True,
            size_hint_y=None,
            height=dp(140),
        )
        content.add_widget(self.input_field)

        btn = MDRaisedButton(
            text="Analyze sequence",
            size_hint_y=None,
            height=dp(40),
            on_release=self.on_analyze_pressed,
        )
        content.add_widget(btn)

        # ---------------------------------------------------------------------
        # 3) BASIC STATS CARD
        # ---------------------------------------------------------------------
        stats_card = MDCard(
            orientation="vertical",
            padding=dp(12),
            spacing=dp(6),
            size_hint_y=None,
            height=dp(120),
            radius=[dp(12)],
        )

        self.length_label = MDLabel(
            text="Length: –",
            halign="left",
            size_hint_y=None,
            height=dp(24),
        )
        self.gc_label = MDLabel(
            text="GC%: –",
            halign="left",
            size_hint_y=None,
            height=dp(24),
        )
        self.valid_label = MDLabel(
            text="Validity: –",
            halign="left",
            size_hint_y=None,
            height=dp(24),
        )

        stats_card.add_widget(MDLabel(
            text="[b]Basic QC[/b]",
            markup=True,
            halign="left",
            size_hint_y=None,
            height=dp(26),
        ))
        stats_card.add_widget(self.length_label)
        stats_card.add_widget(self.gc_label)
        stats_card.add_widget(self.valid_label)

        content.add_widget(stats_card)

        # ---------------------------------------------------------------------
        # 4) TRANSLATION + ORF CARD
        # ---------------------------------------------------------------------
        orf_card = MDCard(
            orientation="vertical",
            padding=dp(12),
            spacing=dp(8),
            size_hint_y=None,
            height=dp(340),
            radius=[dp(12)],
        )

        orf_card.add_widget(MDLabel(
            text="[b]Translation & ORFs[/b]",
            markup=True,
            halign="left",
            size_hint_y=None,
            height=dp(26),
        ))

        # Reading frame slider
        frame_row = MDBoxLayout(
            orientation="horizontal",
            spacing=dp(8),
            size_hint_y=None,
            height=dp(44),
        )
        frame_label = MDLabel(
            text="Reading frame:",
            halign="left",
            size_hint_y=None,
            height=dp(24),
        )
        self.frame_slider = MDSlider(
            min=1,
            max=3,
            value=1,
            step=1,
            size_hint_x=0.6,
        )
        frame_value_label = MDLabel(
            text="1",
            halign="center",
            size_hint=(None, None),
            size=(dp(24), dp(24)),
        )

        def _update_frame_label(slider, value):
            frame_value_label.text = str(int(value))

        self.frame_slider.bind(value=_update_frame_label)

        frame_row.add_widget(frame_label)
        frame_row.add_widget(self.frame_slider)
        frame_row.add_widget(frame_value_label)

        orf_card.add_widget(frame_row)

        # Min ORF len slider
        min_row = MDBoxLayout(
            orientation="horizontal",
            spacing=dp(8),
            size_hint_y=None,
            height=dp(44),
        )
        min_label = MDLabel(
            text="Min ORF length (aa):",
            halign="left",
            size_hint_y=None,
            height=dp(24),
        )
        self.min_orf_slider = MDSlider(
            min=10,
            max=300,
            value=60,
            step=10,
            size_hint_x=0.6,
        )
        min_value_label = MDLabel(
            text="60",
            halign="center",
            size_hint=(None, None),
            size=(dp(36), dp(24)),
        )

        def _update_min_label(slider, value):
            min_value_label.text = str(int(value))

        self.min_orf_slider.bind(value=_update_min_label)

        min_row.add_widget(min_label)
        min_row.add_widget(self.min_orf_slider)
        min_row.add_widget(min_value_label)

        orf_card.add_widget(min_row)

        # Translation output
        self.translation_label = MDLabel(
            text="Protein (+1 frame): –",
            halign="left",
            theme_text_color="Secondary",
            size_hint_y=None,
            height=dp(90),
            shorten=True,
            shorten_from="right",
        )
        orf_card.add_widget(self.translation_label)

        # ORF output
        self.orf_label = MDLabel(
            text="ORFs: –",
            halign="left",
            theme_text_color="Secondary",
            size_hint_y=None,
            height=dp(120),
        )
        orf_card.add_widget(self.orf_label)

        content.add_widget(orf_card)

        # Put scroll content into scroll view
        scroll.add_widget(content)
        root.add_widget(scroll)
        self.add_widget(root)

    # -------------------------------------------------------------------------
    # CALLBACK
    # -------------------------------------------------------------------------
    def on_analyze_pressed(self, *_):
        raw_seq = self.input_field.text if self.input_field else ""
        cleaned = clean_dna(raw_seq)

        # BASIC STATS
        length = len(cleaned)
        gc = gc_content(cleaned) if cleaned else 0.0
        valid = is_valid_dna(cleaned)

        self.length_label.text = f"Length: {length} bp" if self.length_label else ""
        self.gc_label.text = f"GC%: {gc:.1f}%" if self.gc_label else ""
        self.valid_label.text = (
            "Validity: ✅ A/C/G/T only"
            if valid and length > 0
            else "Validity: ⚠ contains non-ACGT or empty"
        )

        # If no valid sequence, clear advanced outputs
        if not valid or length == 0:
            if self.translation_label:
                self.translation_label.text = "Protein: –"
            if self.orf_label:
                self.orf_label.text = "ORFs: –"
            return

        # TRANSLATION
        frame = int(self.frame_slider.value) if self.frame_slider else 1
        frame_idx = frame - 1  # 0,1,2

        protein = translate_dna(cleaned, frame=frame_idx, stop_symbol="*")
        # Truncate for display on phone
        if len(protein) > 160:
            prot_display = protein[:160] + "…"
        else:
            prot_display = protein

        if self.translation_label:
            self.translation_label.text = (
                f"Protein (+{frame} frame): {prot_display}"
            )

        # ORF FINDER (forward strand, all 3 frames)
        min_aa = int(self.min_orf_slider.value) if self.min_orf_slider else 60
        orfs = find_orfs(cleaned, min_aa_len=min_aa)

        if not orfs:
            if self.orf_label:
                self.orf_label.text = "ORFs: none ≥ selected length."
            return

        lines: List[str] = []
        for idx, orf in enumerate(orfs[:6], start=1):
            start_nt = orf["start_nt"]
            end_nt = orf["end_nt"]
            length_aa = orf["length_aa"]
            frame = orf["frame"] + 1  # 1/2/3
            lines.append(
                f"{idx}) frame +{frame} | {start_nt}–{end_nt} (aa: {length_aa})"
            )

        if len(orfs) > 6:
            lines.append(f"... + {len(orfs) - 6} more ORFs")

        if self.orf_label:
            self.orf_label.text = "ORFs:\n" + "\n".join(lines)
