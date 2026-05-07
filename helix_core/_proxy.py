# helix_core/_proxy.py
from importlib import import_module

def export(module_name: str, target_globals: dict, names: list[str] | None = None) -> None:
    """
    Try to import a legacy top-level module (e.g. 'crisprutils') and copy its
    public symbols into the current module's globals. If the legacy module
    isn't installed, quietly do nothing.
    """
    try:
        legacy = import_module(module_name)
    except Exception:
        # Legacy module not available — that's fine in the new package layout.
        return

    for name, obj in legacy.__dict__.items():
        if name.startswith("_"):
            continue
        if names is not None and name not in names:
            continue
        if name in target_globals:
            # Don't overwrite symbols defined in the new module.
            continue
        target_globals[name] = obj
