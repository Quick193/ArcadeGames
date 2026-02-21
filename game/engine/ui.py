"""
engine/ui.py
------------
Shared UI rendering utilities used by every scene.

All draw_* functions are stateless — they take a surface and draw to it.
FontCache eliminates the #1 performance bug in the original games.py:
fonts were created fresh on every single draw call (every frame).

With FontCache, each unique (family, size, bold, italic) combination is
created exactly once and reused for the lifetime of the program.

Public API
----------
FontCache.get(family, size, bold, italic) -> pygame.font.Font

draw_text(surface, text, font, color, x, y, align) -> (w, h)
draw_card(surface, rect, alpha, radius) -> None
draw_button(surface, rect, text, font, selected, color, pulse) -> None
draw_stat_card(surface, rect, label, value, color) -> None
draw_panel_title(surface, x, y, text, color) -> None
draw_key_badge(surface, x, y, key_text, font) -> None
draw_overlay(surface, alpha) -> None
draw_game_over_card(surface, score_label, score_value, hint) -> None
draw_pause_card(surface) -> None
"""

import math
import pygame
from typing import Union


# ---------------------------------------------------------------------------
# Font Cache
# ---------------------------------------------------------------------------

class FontCache:
    """
    Singleton-style cache for pygame fonts.

    Usage
    -----
        font = FontCache.get("Segoe UI", 24, bold=True)
        font = FontCache.get("Consolas", 14)

    Falls back gracefully to pygame's default font if the named font
    is not available on the system.
    """

    _cache: dict[tuple, pygame.font.Font] = {}

    @classmethod
    def get(
        cls,
        family: str = "Segoe UI",
        size: int = 16,
        bold: bool = False,
        italic: bool = False,
    ) -> pygame.font.Font:
        key = (family.lower(), size, bold, italic)
        if key not in cls._cache:
            try:
                cls._cache[key] = pygame.font.SysFont(family, size, bold=bold, italic=italic)
            except Exception:
                cls._cache[key] = pygame.font.SysFont(None, size)
        return cls._cache[key]

    @classmethod
    def clear(cls) -> None:
        """Flush cache — call if you change display DPI at runtime."""
        cls._cache.clear()


# ---------------------------------------------------------------------------
# Core draw helpers
# ---------------------------------------------------------------------------

def draw_text(
    surface: pygame.Surface,
    text: str,
    font: pygame.font.Font,
    color: tuple,
    x: int,
    y: int,
    align: str = "left",
) -> tuple[int, int]:
    """
    Render *text* onto *surface*.

    Parameters
    ----------
    align : 'left' | 'center' | 'right'
        'left'   — (x, y) is the top-left corner of the text
        'center' — (x, y) is the centre of the text bounding box
        'right'  — (x, y) is the top-right corner

    Returns
    -------
    (width, height) of the rendered text surface.
    """
    surf = font.render(text, True, color)
    w, h = surf.get_size()

    if align == "center":
        blit_x, blit_y = x - w // 2, y - h // 2
    elif align == "right":
        blit_x, blit_y = x - w, y
    else:  # left
        blit_x, blit_y = x, y

    surface.blit(surf, (blit_x, blit_y))
    return w, h


def draw_card(
    surface: pygame.Surface,
    rect: tuple,
    alpha: int = 255,
    radius: int = 12,
) -> None:
    """
    Draw a modern rounded-rectangle card with a subtle drop shadow and border.

    Parameters
    ----------
    rect   : (x, y, width, height)
    alpha  : 0–255 opacity of the card body (shadow is always semi-transparent)
    radius : corner radius in pixels
    """
    x, y, w, h = rect

    # Drop shadow (drawn slightly offset, behind the card)
    shadow = pygame.Surface((w + 4, h + 4), pygame.SRCALPHA)
    pygame.draw.rect(shadow, (0, 0, 0, 50), (0, 0, w + 4, h + 4), border_radius=radius)
    surface.blit(shadow, (x + 2, y + 2))

    # Card body
    card = pygame.Surface((w, h), pygame.SRCALPHA)
    card_color = (28, 33, 45, alpha)
    pygame.draw.rect(card, card_color, (0, 0, w, h), border_radius=radius)

    # 1-px border
    border_color = (45, 52, 70, min(alpha, 255))
    pygame.draw.rect(card, border_color, (0, 0, w, h), 1, border_radius=radius)

    surface.blit(card, (x, y))


def draw_button(
    surface: pygame.Surface,
    rect: tuple,
    text: str,
    font: pygame.font.Font,
    is_selected: bool,
    color: tuple = (99, 179, 237),
    pulse: float = 0,
) -> None:
    """
    Draw a styled button.

    When selected, renders a gradient fill animated by *pulse* (a frame counter).
    When unselected, renders as a dim card with a border.
    """
    from engine.theme import Theme  # lazy import avoids circular dep

    x, y, w, h = rect

    # Drop shadow
    shadow = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(shadow, (0, 0, 0, 60), (0, 0, w, h), border_radius=8)
    surface.blit(shadow, (x + 2, y + 2))

    if is_selected:
        btn = pygame.Surface((w, h), pygame.SRCALPHA)
        for i in range(h):
            ratio = i / h
            alpha = int(180 + 40 * math.sin(pulse * 0.1))
            c = tuple(int(color[j] * (0.8 + 0.2 * (1 - ratio))) for j in range(3))
            pygame.draw.line(btn, (*c, alpha), (0, i), (w, i))
        pygame.draw.rect(btn, (255, 255, 255, 30), (0, 0, w, h), 1, border_radius=8)
        surface.blit(btn, (x, y))
        text_color = Theme.TEXT_PRIMARY
    else:
        pygame.draw.rect(surface, (*Theme.CARD_BG, 200), (x, y, w, h), border_radius=8)
        pygame.draw.rect(surface, Theme.CARD_BORDER, (x, y, w, h), 1, border_radius=8)
        text_color = Theme.TEXT_SECONDARY

    draw_text(surface, text, font, text_color, x + w // 2, y + h // 2, align="center")


def draw_stat_card(
    surface: pygame.Surface,
    rect: tuple,
    label: str,
    value: Union[int, float, str],
    color: tuple,
) -> None:
    """
    Draw a compact stat display card with a small label and large value.

    rect : (x, y, width, height)
    """
    from engine.theme import Theme

    x, y, w, h = rect
    draw_card(surface, rect)

    label_font = FontCache.get("Segoe UI", 11, bold=True)
    value_font = FontCache.get("Segoe UI", 28, bold=True)

    label_surf = label_font.render(label, True, Theme.TEXT_MUTED)
    value_surf = value_font.render(str(value), True, color)

    surface.blit(label_surf, (x + 16, y + 10))
    surface.blit(value_surf, (x + 16, y + 28))


def draw_panel_title(
    surface: pygame.Surface,
    x: int,
    y: int,
    text: str,
    color: tuple = None,
) -> None:
    """
    Draw a small all-caps panel section title (e.g. 'CONTROLS', 'NEXT').
    """
    from engine.theme import Theme
    c = color or Theme.TEXT_MUTED
    font = FontCache.get("Segoe UI", 11, bold=True)
    surf = font.render(text, True, c)
    surface.blit(surf, (x, y))


def draw_key_badge(
    surface: pygame.Surface,
    x: int,
    y: int,
    key_text: str,
    action_text: str,
) -> None:
    """
    Draw a key-badge + action label pair (used in control hint panels).

    Example output:  [Space]  Drop
    """
    from engine.theme import Theme

    font = FontCache.get("Segoe UI", 11)
    key_surf = font.render(key_text, True, Theme.TEXT_PRIMARY)
    key_w = key_surf.get_width()

    # Badge background
    badge_rect = (x, y, key_w + 12, 18)
    pygame.draw.rect(surface, Theme.BG_TERTIARY, badge_rect, border_radius=4)
    surface.blit(key_surf, (x + 6, y + 2))

    # Action label
    action_surf = font.render(action_text, True, Theme.TEXT_SECONDARY)
    surface.blit(action_surf, (x + key_w + 18, y + 2))


# ---------------------------------------------------------------------------
# Full-screen overlays and modal cards
# ---------------------------------------------------------------------------

def draw_overlay(surface: pygame.Surface, alpha: int = 180) -> None:
    """
    Draw a full-screen dark semi-transparent overlay.
    Call this before drawing any modal card on top.
    """
    w, h = surface.get_size()
    overlay = pygame.Surface((w, h), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, alpha))
    surface.blit(overlay, (0, 0))


def draw_game_over_card(
    surface: pygame.Surface,
    score_label: str = "Final Score",
    score_value: Union[int, str] = 0,
    hint: str = "Press R to restart  •  Q for menu",
) -> None:
    """
    Draw a centred game-over modal card.
    Draws its own overlay; call this last in your draw() method.
    """
    from engine.theme import Theme

    w, h = surface.get_size()
    draw_overlay(surface, 200)

    card_w, card_h = 420, 230
    cx = (w - card_w) // 2
    cy = (h - card_h) // 2
    draw_card(surface, (cx, cy, card_w, card_h))

    # "GAME OVER" title
    title_font = FontCache.get("Segoe UI", 44, bold=True)
    draw_text(surface, "GAME OVER", title_font, Theme.ACCENT_RED,
              w // 2, cy + 55, align="center")

    # Score
    score_font = FontCache.get("Segoe UI", 24)
    draw_text(surface, f"{score_label}: {score_value}", score_font,
              Theme.TEXT_PRIMARY, w // 2, cy + 120, align="center")

    # Hint
    hint_font = FontCache.get("Segoe UI", 13)
    draw_text(surface, hint, hint_font, Theme.TEXT_SECONDARY,
              w // 2, cy + 168, align="center")


def draw_pause_card(surface: pygame.Surface) -> None:
    """
    Draw a centred PAUSED modal card.
    Draws its own overlay; call this last in your draw() method.
    """
    from engine.theme import Theme

    w, h = surface.get_size()
    draw_overlay(surface, 180)

    card_w, card_h = 320, 160
    cx = (w - card_w) // 2
    cy = (h - card_h) // 2
    draw_card(surface, (cx, cy, card_w, card_h))

    title_font = FontCache.get("Segoe UI", 38, bold=True)
    draw_text(surface, "PAUSED", title_font, Theme.TEXT_PRIMARY,
              w // 2, cy + 48, align="center")

    hint_font = FontCache.get("Segoe UI", 14)
    draw_text(surface, "Press P to resume", hint_font, Theme.TEXT_SECONDARY,
              w // 2, cy + 108, align="center")


def draw_footer_hint(
    surface: pygame.Surface,
    text: str,
    y_offset: int = 30,
) -> None:
    """
    Draw a small hint line centred at the bottom of the screen.
    y_offset is measured from the bottom edge.
    """
    from engine.theme import Theme

    w, h = surface.get_size()
    font = FontCache.get("Segoe UI", 12)
    surf = font.render(text, True, Theme.TEXT_MUTED)
    surface.blit(surf, ((w - surf.get_width()) // 2, h - y_offset))
