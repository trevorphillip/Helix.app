# helix_desktop/ui_plus.py
"""Extra Streamlit UI utilities shared by the desktop build."""

from __future__ import annotations
from functools import lru_cache
import importlib
from helix_desktop.stylekit import PLOTLY_TEMPLATE

_NEON_CSS = """
<style>
:root {
    --helix-bg: #0b1220;
    --helix-accent: #38bdf8;
}
body {
    background: var(--helix-bg);
}
</style>
"""

@lru_cache(maxsize=1)
def _st():
    return importlib.import_module("streamlit")

def inject_visual_theme(neon: bool = True) -> None:
    if neon:
        _st().markdown(_NEON_CSS, unsafe_allow_html=True)

def set_plotly_template(name: str = "neon") -> None:
    # keep simple; your visuals import PLOTLY_TEMPLATE directly
    # this function just exists so app.py's import works without errors
    return
