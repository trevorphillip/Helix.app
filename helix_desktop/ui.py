"""Utility widgets shared by the Streamlit desktop build."""

from __future__ import annotations

import importlib
from functools import lru_cache
from typing import Iterable, Optional


_BASE_CSS = """
<style>
body {
    font-family: "Inter", "Segoe UI", system-ui, sans-serif;
    background-color: #0b1220;
    color: #f8fafc;
}
</style>
"""


@lru_cache(maxsize=1)
def _st():
    return importlib.import_module("streamlit")


def inject_base_css() -> None:
    _st().markdown(_BASE_CSS, unsafe_allow_html=True)


def inject_neon_theme() -> None:
    _st().markdown(
        """
        <style>
        .stButton>button {
            background: linear-gradient(135deg, #38bdf8, #9333ea);
            color: white;
            border: none;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def hero_header(title: str, subtitle: str) -> None:
    st = _st()
    st.title(title)
    st.caption(subtitle)


def stat_row(metrics: Iterable[dict]) -> None:
    metrics = list(metrics)
    st = _st()
    cols = st.columns(len(metrics)) if metrics else []
    for col, metric in zip(cols, metrics):
        col.metric(metric.get("label", ""), metric.get("value", ""))


def sticky_toolbar(items: Iterable[dict]) -> Optional[str]:
    items = list(items)
    st = _st()
    cols = st.columns(len(items)) if items else []
    clicked: Optional[str] = None
    for col, item in zip(cols, items):
        if col.button(item.get("label", "")):
            clicked = item.get("key")
    return clicked


def command_palette() -> Optional[str]:
    return None


def handle_command(command: str, sequence: str, start: int, end: int) -> None:
    del command, sequence, start, end
    return None

