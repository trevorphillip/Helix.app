"""Helix core package exposing shared genetics utilities.

This package re-exports the legacy single-file modules that ship with the
project so that both the Streamlit desktop app and the mobile Kivy port can
import a stable ``helix_core.<module>`` namespace.
"""

from importlib import import_module
from types import ModuleType
from typing import Dict

__all__: list[str] = []

# Map of friendly module name -> underlying legacy module.
_LEGACY_MODULES: Dict[str, str] = {
    "ai_stub": "ai_stub",
    "ai_helper": "ai_helper",
    "codon": "codon",
    "crisprutils": "crisprutils",
    "editor": "editor",
    "io_utils": "io_utils",
    "motifs": "motifs",
    "msa_utils": "msa_utils",
    "peptidebuilder": "peptidebuilder",
    "primer": "primer",
    "protein_tools": "protein_tools",
    "stylekit": "stylekit",
    "sonify": "sonify",
    "structure_viewer": "structure_viewer",
    "variants": "variants",
    "visuals": "visuals",
}

# Lazily import legacy modules so ``helix_core`` can act as a namespace package.

def __getattr__(name: str) -> ModuleType:
    if name in _LEGACY_MODULES:
        module = import_module(_LEGACY_MODULES[name])
        globals()[name] = module
        __all__.append(name)
        return module
    raise AttributeError(f"module 'helix_core' has no attribute {name!r}")