"""
games/__init__.py
-----------------
Plugin loader: auto-discovers any game file placed in /games that exports
a GAME_META dict.  Called by MainMenuScene to build its GAME_REGISTRY.

Usage
-----
    from games import load_game_registry
    registry = load_game_registry()   # list of GAME_META dicts
"""

import importlib
from pathlib import Path


def load_game_registry() -> list[dict]:
    """
    Scan the games/ folder for modules exporting GAME_META.
    Returns them sorted by 'name'.  Falls back gracefully on import errors.
    """
    here    = Path(__file__).parent
    results = []
    for path in sorted(here.glob("*.py")):
        if path.stem.startswith("_"):
            continue
        try:
            mod = importlib.import_module(f"games.{path.stem}")
            if hasattr(mod, "GAME_META"):
                results.append(mod.GAME_META)
        except Exception:
            pass
    return results


__all__ = ["load_game_registry"]
