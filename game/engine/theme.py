"""
engine/theme.py
---------------
Theme registry for the arcade platform.

The active theme is selected via SettingsManager and applied globally.
All rendering code imports from here — never hardcodes raw RGB values.

Available themes
----------------
  "modern_dark"   — Original sleek dark theme (from games.py)
  "neon_cyber"    — Neon-heavy cyberpunk palette
  "retro_crt"     — Muted green phosphor + scanline overlay flag
  "minimal_light" — Clean light-mode palette
  "glass_ui"      — Frosted glass, translucent blues

Usage
-----
    from engine.theme import Theme

    # Read a color
    color = Theme.ACCENT_BLUE

    # Switch theme at runtime
    Theme.set_theme("neon_cyber")

    # Check if scanlines should be drawn
    if Theme.SCANLINES:
        draw_scanlines(screen)
"""

from dataclasses import dataclass, field
from typing import ClassVar
import pygame


# ---------------------------------------------------------------------------
# ThemeData: all color slots for one theme
# ---------------------------------------------------------------------------

@dataclass
class ThemeData:
    # Backgrounds
    BG_PRIMARY:   tuple = (15, 18, 25)
    BG_SECONDARY: tuple = (20, 24, 32)
    BG_TERTIARY:  tuple = (25, 30, 40)

    # Accent palette
    ACCENT_BLUE:   tuple = (99, 179, 237)
    ACCENT_PURPLE: tuple = (171, 99, 250)
    ACCENT_PINK:   tuple = (250, 99, 180)
    ACCENT_CYAN:   tuple = (79, 236, 255)
    ACCENT_GREEN:  tuple = (92, 219, 149)
    ACCENT_ORANGE: tuple = (255, 159, 67)
    ACCENT_RED:    tuple = (255, 107, 107)
    ACCENT_YELLOW: tuple = (255, 214, 102)

    # UI shell colors
    CARD_BG:        tuple = (28, 33, 45)
    CARD_BORDER:    tuple = (45, 52, 70)
    TEXT_PRIMARY:   tuple = (255, 255, 255)
    TEXT_SECONDARY: tuple = (156, 163, 175)
    TEXT_MUTED:     tuple = (107, 114, 128)

    # Tetris / block-game piece colors (order: I J L O S T Z)
    PIECE_COLORS: tuple = field(default_factory=lambda: (
        (79, 236, 255),   # I — cyan
        (99, 179, 237),   # J — blue
        (255, 159, 67),   # L — orange
        (255, 214, 102),  # O — yellow
        (92, 219, 149),   # S — green
        (171, 99, 250),   # T — purple
        (255, 107, 107),  # Z — red
    ))

    # Board / grid colors (Pong, Chess, etc.)
    BOARD_LIGHT: tuple = (230, 220, 200)
    BOARD_DARK:  tuple = (110, 80,  60)

    # Special flags
    SCANLINES: bool = False   # Retro CRT effect

    # Background gradient end color (used by RenderManager)
    BG_GRADIENT_END: tuple = (25, 30, 40)


# ---------------------------------------------------------------------------
# Built-in theme presets
# ---------------------------------------------------------------------------

_THEMES: dict[str, ThemeData] = {

    "modern_dark": ThemeData(),  # default — already defined above

    "neon_cyber": ThemeData(
        BG_PRIMARY   = (5, 5, 15),
        BG_SECONDARY = (8, 8, 22),
        BG_TERTIARY  = (12, 10, 28),
        ACCENT_BLUE   = (0, 200, 255),
        ACCENT_PURPLE = (200, 0, 255),
        ACCENT_PINK   = (255, 0, 150),
        ACCENT_CYAN   = (0, 255, 240),
        ACCENT_GREEN  = (0, 255, 100),
        ACCENT_ORANGE = (255, 100, 0),
        ACCENT_RED    = (255, 20, 60),
        ACCENT_YELLOW = (255, 230, 0),
        CARD_BG       = (10, 10, 25),
        CARD_BORDER   = (0, 200, 255),
        TEXT_PRIMARY   = (230, 255, 255),
        TEXT_SECONDARY = (0, 200, 200),
        TEXT_MUTED     = (0, 120, 140),
        PIECE_COLORS   = (
            (0, 255, 240),
            (0, 200, 255),
            (255, 100, 0),
            (255, 230, 0),
            (0, 255, 100),
            (200, 0, 255),
            (255, 20, 60),
        ),
        BOARD_LIGHT = (20, 60, 80),
        BOARD_DARK  = (10, 30, 50),
        BG_GRADIENT_END = (12, 10, 28),
    ),

    "retro_crt": ThemeData(
        BG_PRIMARY   = (5, 18, 5),
        BG_SECONDARY = (8, 22, 8),
        BG_TERTIARY  = (10, 28, 10),
        ACCENT_BLUE   = (80, 200, 80),
        ACCENT_PURPLE = (120, 220, 120),
        ACCENT_PINK   = (160, 240, 160),
        ACCENT_CYAN   = (60, 255, 60),
        ACCENT_GREEN  = (0, 230, 0),
        ACCENT_ORANGE = (200, 230, 0),
        ACCENT_RED    = (255, 80, 80),
        ACCENT_YELLOW = (220, 255, 100),
        CARD_BG       = (5, 20, 5),
        CARD_BORDER   = (0, 180, 0),
        TEXT_PRIMARY   = (180, 255, 180),
        TEXT_SECONDARY = (100, 200, 100),
        TEXT_MUTED     = (50, 130, 50),
        PIECE_COLORS   = (
            (60, 255, 60),
            (80, 200, 80),
            (200, 230, 0),
            (220, 255, 100),
            (0, 230, 0),
            (120, 220, 120),
            (255, 80, 80),
        ),
        BOARD_LIGHT = (30, 80, 30),
        BOARD_DARK  = (10, 40, 10),
        SCANLINES   = True,
        BG_GRADIENT_END = (10, 28, 10),
    ),

    "minimal_light": ThemeData(
        BG_PRIMARY   = (245, 246, 250),
        BG_SECONDARY = (235, 237, 245),
        BG_TERTIARY  = (225, 228, 240),
        ACCENT_BLUE   = (30, 120, 220),
        ACCENT_PURPLE = (130, 50, 200),
        ACCENT_PINK   = (220, 60, 140),
        ACCENT_CYAN   = (20, 180, 200),
        ACCENT_GREEN  = (30, 160, 100),
        ACCENT_ORANGE = (220, 120, 30),
        ACCENT_RED    = (210, 60, 60),
        ACCENT_YELLOW = (200, 160, 20),
        CARD_BG       = (255, 255, 255),
        CARD_BORDER   = (200, 205, 220),
        TEXT_PRIMARY   = (30, 35, 50),
        TEXT_SECONDARY = (80, 90, 110),
        TEXT_MUTED     = (150, 158, 175),
        PIECE_COLORS   = (
            (20, 180, 200),
            (30, 120, 220),
            (220, 120, 30),
            (200, 160, 20),
            (30, 160, 100),
            (130, 50, 200),
            (210, 60, 60),
        ),
        BOARD_LIGHT = (240, 230, 210),
        BOARD_DARK  = (160, 130, 100),
        BG_GRADIENT_END = (225, 228, 240),
    ),

    "glass_ui": ThemeData(
        BG_PRIMARY   = (15, 25, 45),
        BG_SECONDARY = (18, 30, 55),
        BG_TERTIARY  = (22, 35, 65),
        ACCENT_BLUE   = (80, 160, 255),
        ACCENT_PURPLE = (150, 100, 255),
        ACCENT_PINK   = (255, 100, 200),
        ACCENT_CYAN   = (100, 220, 255),
        ACCENT_GREEN  = (100, 240, 180),
        ACCENT_ORANGE = (255, 180, 80),
        ACCENT_RED    = (255, 100, 120),
        ACCENT_YELLOW = (255, 230, 120),
        CARD_BG       = (25, 40, 70),
        CARD_BORDER   = (80, 120, 200),
        TEXT_PRIMARY   = (240, 248, 255),
        TEXT_SECONDARY = (160, 190, 230),
        TEXT_MUTED     = (100, 130, 180),
        PIECE_COLORS   = (
            (100, 220, 255),
            (80, 160, 255),
            (255, 180, 80),
            (255, 230, 120),
            (100, 240, 180),
            (150, 100, 255),
            (255, 100, 120),
        ),
        BOARD_LIGHT = (60, 100, 160),
        BOARD_DARK  = (25, 50, 90),
        BG_GRADIENT_END = (22, 35, 65),
    ),
}


# ---------------------------------------------------------------------------
# Theme proxy — import this everywhere
# ---------------------------------------------------------------------------

class _ThemeProxy:
    """
    Module-level singleton proxy.  Delegates attribute access to the
    currently active ThemeData object.

    Importing code uses:
        from engine.theme import Theme
        color = Theme.ACCENT_BLUE

    Switching theme:
        Theme.set_theme("neon_cyber")
    """

    # Keep a class-level list of available names for the settings screen
    AVAILABLE: ClassVar[list[str]] = list(_THEMES.keys())

    def __init__(self) -> None:
        self._active: ThemeData = _THEMES["modern_dark"]
        self._name: str = "modern_dark"

    # Delegate all attribute reads to the active ThemeData
    def __getattr__(self, name: str):
        # Only triggered for names not found on _ThemeProxy itself
        try:
            return getattr(self._active, name)
        except AttributeError:
            raise AttributeError(f"ThemeData has no attribute '{name}'")

    def set_theme(self, name: str) -> None:
        """Switch to theme *name* (one of Theme.AVAILABLE)."""
        if name not in _THEMES:
            raise ValueError(f"Unknown theme '{name}'. Available: {list(_THEMES)}")
        self._active = _THEMES[name]
        self._name = name
        # Flush the render background cache so it regenerates with new colors
        try:
            from engine.render_manager import RenderManager
            RenderManager.clear()
        except ImportError:
            pass

    @property
    def name(self) -> str:
        return self._name

    @property
    def data(self) -> ThemeData:
        """Direct access to the raw ThemeData if needed."""
        return self._active

    # Convenience: piece color by index (wraps PIECE_COLORS tuple)
    def piece_color(self, index: int) -> tuple:
        return self._active.PIECE_COLORS[index % len(self._active.PIECE_COLORS)]

    # Expose PIECE_COLORS as the legacy 'COLORS' name (games.py compat)
    @property
    def COLORS(self) -> tuple:
        return self._active.PIECE_COLORS


# The single global Theme object — import this everywhere
Theme = _ThemeProxy()
