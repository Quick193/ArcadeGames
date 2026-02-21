"""
engine/__init__.py
------------------
Public API for the engine package.

Import from here rather than from submodules directly:

    from engine import ArcadeEngine, BaseScene, Theme, FontCache
    from engine import draw_text, draw_card, draw_button, draw_stat_card
    from engine import RenderManager
"""

from engine.engine        import ArcadeEngine, SCREEN_WIDTH, SCREEN_HEIGHT, TARGET_FPS
from engine.scene         import BaseScene
from engine.theme         import Theme
from engine.render_manager import RenderManager
from engine.ui import (
    FontCache,
    draw_text,
    draw_card,
    draw_button,
    draw_stat_card,
    draw_panel_title,
    draw_key_badge,
    draw_overlay,
    draw_game_over_card,
    draw_pause_card,
    draw_footer_hint,
)

__all__ = [
    "ArcadeEngine", "BaseScene", "SCREEN_WIDTH", "SCREEN_HEIGHT", "TARGET_FPS",
    "Theme", "RenderManager", "FontCache",
    "draw_text", "draw_card", "draw_button", "draw_stat_card",
    "draw_panel_title", "draw_key_badge", "draw_overlay",
    "draw_game_over_card", "draw_pause_card", "draw_footer_hint",
]
