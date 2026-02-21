"""
systems/settings.py
-------------------
SettingsManager: Persists and validates all user preferences.

All settings have typed defaults.  Reading a missing key always returns
the default — the system never crashes on a corrupt or missing file.

Settings are written to disk immediately on change (no separate 'save'
call required) so nothing is lost if the process is killed.

Usage
-----
    from systems.settings import SettingsManager

    s = SettingsManager()

    # Read
    vol = s.get("music_volume")          # → 0.8

    # Write (auto-saves to disk)
    s.set("music_volume", 0.5)

    # Convenience typed accessors
    s.music_volume   # float 0.0–1.0
    s.sfx_volume     # float 0.0–1.0
    s.theme          # str
    s.show_particles # bool
    s.show_bg_anim   # bool
    s.fps_cap        # int
    s.show_fps       # bool

Settings file: data/settings.json
"""

import json
import os
from copy import deepcopy
from typing import Any


# ---------------------------------------------------------------------------
# Default settings schema
# ---------------------------------------------------------------------------

DEFAULTS: dict[str, Any] = {
    # Audio
    "music_volume":    0.8,    # float 0.0–1.0
    "sfx_volume":      0.9,    # float 0.0–1.0
    "music_enabled":   True,
    "sfx_enabled":     True,

    # Display
    "theme":           "modern_dark",
    "show_particles":  True,
    "show_bg_anim":    True,
    "show_fps":        False,
    "fps_cap":         60,     # int: 30 | 60 | 120 | 0 (unlimited)

    # Gameplay
    "show_ghost_piece":       True,   # Tetris ghost piece
    "auto_clear_annotations": False,  # Chess: clear arrows on move
    "chess_show_hints":       True,   # Chess: show legal move dots

    # Data
    "reset_on_start": False,
}

# Allowed fps_cap values
VALID_FPS_CAPS = {0, 30, 60, 120}

# Allowed theme names (populated at runtime by Theme.AVAILABLE)
_VALID_THEMES: set[str] | None = None

DATA_DIR  = os.path.join(os.path.dirname(__file__), "..", "data")
SAVE_PATH = os.path.join(DATA_DIR, "settings.json")


# ---------------------------------------------------------------------------
# SettingsManager
# ---------------------------------------------------------------------------

class SettingsManager:
    """
    Single-instance settings manager.  Reads from / writes to data/settings.json.
    Always returns a valid typed value — never raises on bad data.
    """

    def __init__(self, path: str = SAVE_PATH) -> None:
        self._path = path
        self._data: dict[str, Any] = deepcopy(DEFAULTS)
        self._load()

    # ------------------------------------------------------------------
    # Core API
    # ------------------------------------------------------------------

    def get(self, key: str, default: Any = None) -> Any:
        """
        Return the value for *key*.
        Falls back to DEFAULTS[key], then to *default* if key is unknown.
        """
        if key in self._data:
            return self._data[key]
        if key in DEFAULTS:
            return DEFAULTS[key]
        return default

    def set(self, key: str, value: Any) -> None:
        """
        Set *key* to *value*, validate it, then immediately persist to disk.
        Unknown keys are accepted (forward-compatibility for plugins).
        """
        value = self._validate(key, value)
        self._data[key] = value
        self._save()

        # Side-effects for certain settings
        self._apply_side_effects(key, value)

    def reset_to_defaults(self) -> None:
        """Restore all settings to factory defaults and save."""
        self._data = deepcopy(DEFAULTS)
        self._save()

    # ------------------------------------------------------------------
    # Typed convenience properties (read-only shortcuts)
    # ------------------------------------------------------------------

    @property
    def music_volume(self) -> float:
        return float(self.get("music_volume"))

    @property
    def sfx_volume(self) -> float:
        return float(self.get("sfx_volume"))

    @property
    def music_enabled(self) -> bool:
        return bool(self.get("music_enabled"))

    @property
    def sfx_enabled(self) -> bool:
        return bool(self.get("sfx_enabled"))

    @property
    def theme(self) -> str:
        return str(self.get("theme"))

    @property
    def show_particles(self) -> bool:
        return bool(self.get("show_particles"))

    @property
    def show_bg_anim(self) -> bool:
        return bool(self.get("show_bg_anim"))

    @property
    def show_fps(self) -> bool:
        return bool(self.get("show_fps"))

    @property
    def fps_cap(self) -> int:
        return int(self.get("fps_cap"))

    @property
    def show_ghost_piece(self) -> bool:
        return bool(self.get("show_ghost_piece"))

    @property
    def auto_clear_annotations(self) -> bool:
        return bool(self.get("auto_clear_annotations"))

    @property
    def chess_show_hints(self) -> bool:
        return bool(self.get("chess_show_hints"))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _validate(self, key: str, value: Any) -> Any:
        """Coerce and clamp value to a valid type for the given key."""
        expected = DEFAULTS.get(key)

        if expected is None:
            return value  # unknown key — pass through

        if isinstance(expected, bool):
            return bool(value)

        if isinstance(expected, float):
            try:
                v = float(value)
            except (TypeError, ValueError):
                return expected
            return max(0.0, min(1.0, v))  # clamp volumes to 0–1

        if isinstance(expected, int):
            try:
                v = int(value)
            except (TypeError, ValueError):
                return expected
            if key == "fps_cap":
                return v if v in VALID_FPS_CAPS else 60
            return v

        if isinstance(expected, str):
            v = str(value)
            if key == "theme":
                # Validate lazily (Theme imported at runtime)
                try:
                    from engine.theme import Theme
                    if v not in Theme.AVAILABLE:
                        return expected
                except ImportError:
                    pass
            return v

        return value

    def _apply_side_effects(self, key: str, value: Any) -> None:
        """Apply immediate runtime effects for certain settings."""
        if key == "theme":
            try:
                from engine.theme import Theme
                Theme.set_theme(value)
            except (ImportError, ValueError):
                pass

        elif key in ("music_volume", "music_enabled"):
            try:
                import pygame
                if pygame.mixer.get_init():
                    vol = self.music_volume if self.music_enabled else 0.0
                    pygame.mixer.music.set_volume(vol)
            except Exception:
                pass

    def _load(self) -> None:
        """Load settings from disk.  Silently uses defaults on any error."""
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            # Merge loaded values into defaults (new keys in DEFAULTS are kept)
            for key, value in raw.items():
                validated = self._validate(key, value)
                self._data[key] = validated
        except FileNotFoundError:
            pass  # First run — defaults are already set
        except (json.JSONDecodeError, IOError):
            pass  # Corrupt file — keep defaults, will overwrite on next save

    def _save(self) -> None:
        """Write current settings to disk atomically."""
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        tmp = self._path + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2)
            os.replace(tmp, self._path)
        except IOError:
            pass  # Non-fatal — settings just won't persist this write

    def __repr__(self) -> str:
        return f"SettingsManager({self._data})"
