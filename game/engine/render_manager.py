"""
engine/render_manager.py
------------------------
RenderManager: Cached surface generation for expensive background rendering.

The gradient background in the original games.py was rebuilt from scratch
every single frame — 700 per-pixel draw calls at 60fps.  This manager
generates each unique surface once and caches it indefinitely.

Usage
-----
    from engine.render_manager import RenderManager

    # In your draw() method:
    screen.blit(RenderManager.get_background(screen_w, screen_h), (0, 0))

    # If theme changes at runtime, flush the cache:
    RenderManager.clear()
"""

import pygame
from typing import Optional


class RenderManager:
    """
    Static-method cache for generated surfaces.

    All surfaces are stored in class-level dicts keyed by the parameters
    that define them.  Call clear() to flush all caches (e.g. on theme change).
    """

    _bg_cache:       dict[tuple, pygame.Surface] = {}
    _gradient_cache: dict[tuple, pygame.Surface] = {}

    # ------------------------------------------------------------------
    # Background
    # ------------------------------------------------------------------

    @classmethod
    def get_background(cls, width: int, height: int) -> pygame.Surface:
        """
        Return (and cache) a vertical-gradient background surface matching
        the active theme's BG_PRIMARY → BG_GRADIENT_END colors.
        """
        from engine.theme import Theme
        key = (width, height, Theme.name)

        if key not in cls._bg_cache:
            surface = pygame.Surface((width, height))
            start = Theme.BG_PRIMARY
            end   = Theme.BG_GRADIENT_END

            for y in range(height):
                t = y / height
                r = int(start[0] + (end[0] - start[0]) * t)
                g = int(start[1] + (end[1] - start[1]) * t)
                b = int(start[2] + (end[2] - start[2]) * t)
                pygame.draw.line(surface, (r, g, b), (0, y), (width, y))

            cls._bg_cache[key] = surface

        return cls._bg_cache[key]

    # ------------------------------------------------------------------
    # Gradient rectangles (reusable for cards, progress bars, etc.)
    # ------------------------------------------------------------------

    @classmethod
    def get_gradient_surface(
        cls,
        width: int,
        height: int,
        color_top: tuple,
        color_bottom: tuple,
        alpha: bool = False,
    ) -> pygame.Surface:
        """
        Return a cached vertical-gradient rectangle surface.

        Parameters
        ----------
        alpha : bool
            If True, surface has per-pixel alpha (SRCALPHA).
        """
        key = (width, height, color_top, color_bottom, alpha)

        if key not in cls._gradient_cache:
            flags = pygame.SRCALPHA if alpha else 0
            surface = pygame.Surface((width, height), flags)

            for y in range(height):
                t = y / height
                r = int(color_top[0] + (color_bottom[0] - color_top[0]) * t)
                g = int(color_top[1] + (color_bottom[1] - color_top[1]) * t)
                b = int(color_top[2] + (color_bottom[2] - color_top[2]) * t)
                a = 255
                if alpha:
                    if len(color_top) == 4 and len(color_bottom) == 4:
                        a = int(color_top[3] + (color_bottom[3] - color_top[3]) * t)
                    pygame.draw.line(surface, (r, g, b, a), (0, y), (width, y))
                else:
                    pygame.draw.line(surface, (r, g, b), (0, y), (width, y))

            cls._gradient_cache[key] = surface

        return cls._gradient_cache[key]

    # ------------------------------------------------------------------
    # Block surfaces (used by Tetris, Breakout, etc.)
    # ------------------------------------------------------------------

    @classmethod
    def get_block_surface(
        cls,
        size: int,
        color: tuple,
        radius: int = 3,
    ) -> pygame.Surface:
        """
        Return a cached (size-2) × (size-2) block surface with a gradient
        fill, top highlight, and border — same style as games.py Tetris blocks.
        """
        key = ("block", size, color, radius)

        if key not in cls._gradient_cache:
            w = h = size - 2
            surf = pygame.Surface((w, h), pygame.SRCALPHA)

            # Gradient fill (top = full color, bottom = 80%)
            for i in range(h):
                t = i / h
                c = tuple(int(color[j] * (1.0 - 0.2 * t)) for j in range(3))
                pygame.draw.line(surf, c, (0, i), (w, i))

            # Top highlight
            pygame.draw.line(surf, (255, 255, 255, 90), (0, 0), (w, 0), 2)

            # Border
            pygame.draw.rect(surf, (0, 0, 0, 70), (0, 0, w, h), 1,
                             border_radius=radius)

            cls._gradient_cache[key] = surf

        return cls._gradient_cache[key]

    # ------------------------------------------------------------------
    # Cache management
    # ------------------------------------------------------------------

    @classmethod
    def clear(cls) -> None:
        """Flush all caches.  Call when the theme changes."""
        cls._bg_cache.clear()
        cls._gradient_cache.clear()

    @classmethod
    def cache_stats(cls) -> dict[str, int]:
        """Return entry counts per cache (useful for debug overlay)."""
        return {
            "backgrounds": len(cls._bg_cache),
            "gradients":   len(cls._gradient_cache),
        }
