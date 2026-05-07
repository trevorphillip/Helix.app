from dataclasses import dataclass
from typing import Dict, Any
from helix_platform.plugins import register, AppPlugin
from mobile_app.viewmodel import (
    analyze_sequence, format_summary, format_guides, format_orfs,
    format_codon_usage, get_available_enzymes, get_example_library,
)

@dataclass
class CrisprSandbox(AppPlugin):
    slug: str = "crispr"
    title: str = "CRISPR Sandbox"
    version: str = "0.1.0"
    icon: str | None = None
    def get_viewmodel(self) -> Dict[str, Any]:
        return {
            "analyze_sequence": analyze_sequence,
            "format_summary": format_summary,
            "format_guides": format_guides,
            "format_orfs": format_orfs,
            "format_codon_usage": format_codon_usage,
            "get_available_enzymes": get_available_enzymes,
            "get_example_library": get_example_library,
        }
    def run_cli(self, **kwargs) -> int: return 0

register(CrisprSandbox())
