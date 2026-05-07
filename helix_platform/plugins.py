from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Protocol, Any, Optional

class AppPlugin(Protocol):
    slug: str; title: str; version: str; icon: Optional[str]
    def get_viewmodel(self) -> Dict[str, Any]: ...
    def run_cli(self, **kwargs) -> int: ...

@dataclass
class _Reg: plugin: AppPlugin
_REGISTRY: Dict[str, _Reg] = {}

def register(p: AppPlugin) -> None:
    if p.slug in _REGISTRY: raise ValueError(f"Duplicate plugin: {p.slug}")
    _REGISTRY[p.slug] = _Reg(plugin=p)

def list_plugins() -> Dict[str, AppPlugin]:
    return {k: v.plugin for k, v in _REGISTRY.items()}

def get(slug: str) -> AppPlugin:
    return _REGISTRY[slug].plugin

def bootstrap() -> None:
    import helix_apps.crispr_sandbox.app_api  # noqa
    import helix_apps.med_prep.app_api        # noqa   <-- add this line

