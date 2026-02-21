"""
scenes/achievements_screen.py
------------------------------
AchievementsScene: Full achievements browser.

Layout
------
  Header  - title, total unlocked / total, points earned, progress bar
  Grid    - 2-column card grid, scrollable with ^v or mouse wheel
            Unlocked cards: colored border, icon, name, desc, unlock date
            Locked cards:   dim, grey border, name shown, desc hidden (if secret)
  Footer  - navigation hint

Controls
--------
  ^ v / Mouse wheel  - scroll
  Q / Esc / Backspace - back to menu
"""

import math
import pygame

from engine import (
    BaseScene, Theme, RenderManager, FontCache,
    draw_text, draw_card, draw_overlay, draw_footer_hint,
)
from engine.engine import SCREEN_WIDTH, SCREEN_HEIGHT


def _draw_ach_icon(screen, tag: str, x: int, y: int, color, unlocked: bool) -> None:
    """Draw a 36×32 colored pill with a 3-char tag - no emoji needed."""
    w, h = 36, 32
    alpha = 220 if unlocked else 80
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    bg = (*color[:3], alpha)
    pygame.draw.rect(surf, bg, (0, 0, w, h), border_radius=6)
    if unlocked:
        pygame.draw.rect(surf, (*color[:3], 255), (0, 0, w, h), 1, border_radius=6)
    screen.blit(surf, (x, y))
    tf = FontCache.get("Segoe UI", 10, bold=True)
    tc = (255, 255, 255) if unlocked else (160, 160, 170)
    draw_text(screen, tag[:3], tf, tc, x + w // 2, y + h // 2, align="center")


class AchievementsScene(BaseScene):

    COLS       = 2
    CARD_W     = 420
    CARD_H     = 88
    GAP_X      = 24
    GAP_Y      = 12
    GRID_TOP   = 168        # y where first card starts
    SCROLL_SPD = 220        # pixels per second for keyboard scroll
    SIDE_PAD   = 60

    def on_enter(self) -> None:
        self._scroll     = 0.0      # current scroll offset (pixels)
        self._max_scroll = 0.0
        self._time       = 0.0
        self._rows: list = []       # (AchievementDef, unlocked_bool, date_or_None)
        self._build_rows()

    # ------------------------------------------------------------------
    # Build row data
    # ------------------------------------------------------------------

    def _build_rows(self) -> None:
        if self.achievements:
            self._rows = self.achievements.all_achievements()
        else:
            self._rows = []

        n          = len(self._rows)
        row_count  = math.ceil(n / self.COLS)
        total_h    = row_count * (self.CARD_H + self.GAP_Y)
        visible_h  = SCREEN_HEIGHT - self.GRID_TOP - 40
        self._max_scroll = max(0.0, total_h - visible_h)

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def update(self, dt: float) -> None:
        self._time += dt
        keys = pygame.key.get_pressed()
        if keys[pygame.K_DOWN]:
            self._scroll = min(self._max_scroll,
                               self._scroll + self.SCROLL_SPD * dt)
        if keys[pygame.K_UP]:
            self._scroll = max(0, self._scroll - self.SCROLL_SPD * dt)

    # ------------------------------------------------------------------
    # Draw
    # ------------------------------------------------------------------

    def draw(self, screen: pygame.Surface) -> None:
        w, h = screen.get_size()
        screen.blit(RenderManager.get_background(w, h), (0, 0))

        self._draw_header(screen, w)
        self._draw_grid(screen, w, h)
        draw_footer_hint(screen, "^v / Scroll  |  Q Back", y_offset=26)

    def _draw_header(self, screen: pygame.Surface, w: int) -> None:
        # Title
        title_font = FontCache.get("Segoe UI", 46, bold=True)
        draw_text(screen, "ACHIEVEMENTS", title_font, Theme.TEXT_PRIMARY,
                  w // 2, 46, align="center")

        if not self.achievements:
            return

        unlocked = self.achievements.unlocked_count()
        total    = self.achievements.total_count()
        points   = self.achievements.total_points()
        progress = unlocked / total if total else 0.0

        # Subtitle stats
        sub_font = FontCache.get("Segoe UI", 14)
        draw_text(screen,
                  f"{unlocked} / {total} unlocked   |   {points} pts earned",
                  sub_font, Theme.TEXT_MUTED, w // 2, 100, align="center")

        # Progress bar
        bar_w = 500
        bar_x = (w - bar_w) // 2
        bar_y = 122
        pygame.draw.rect(screen, Theme.BG_TERTIARY,
                         (bar_x, bar_y, bar_w, 10), border_radius=5)
        fill = int(bar_w * progress)
        if fill > 0:
            pygame.draw.rect(screen, Theme.ACCENT_YELLOW,
                             (bar_x, bar_y, fill, 10), border_radius=5)
        # Glow end cap
        if fill > 4:
            glow = pygame.Surface((12, 10), pygame.SRCALPHA)
            pygame.draw.rect(glow, (*Theme.ACCENT_YELLOW[:3], 120),
                             (0, 0, 12, 10), border_radius=5)
            screen.blit(glow, (bar_x + fill - 6, bar_y))

        pct_font = FontCache.get("Segoe UI", 11, bold=True)
        draw_text(screen, f"{int(progress * 100)}%",
                  pct_font, Theme.ACCENT_YELLOW,
                  bar_x + bar_w + 10, bar_y)

        # Separator line
        pygame.draw.line(screen, Theme.CARD_BORDER,
                         (self.SIDE_PAD, 148),
                         (w - self.SIDE_PAD, 148))

    def _draw_grid(self, screen: pygame.Surface, w: int, h: int) -> None:
        if not self._rows:
            no_font = FontCache.get("Segoe UI", 18)
            draw_text(screen, "No achievements found", no_font,
                      Theme.TEXT_MUTED, w // 2, h // 2, align="center")
            return

        grid_w = self.COLS * self.CARD_W + (self.COLS - 1) * self.GAP_X
        grid_x = (w - grid_w) // 2

        # Clip area
        clip = pygame.Rect(0, self.GRID_TOP, w, h - self.GRID_TOP - 40)
        screen.set_clip(clip)

        for i, (ach, is_unlocked, unlock_date) in enumerate(self._rows):
            col = i % self.COLS
            row = i // self.COLS
            cx  = grid_x + col * (self.CARD_W + self.GAP_X)
            cy  = self.GRID_TOP + row * (self.CARD_H + self.GAP_Y) - int(self._scroll)

            # Skip cards fully outside viewport
            if cy + self.CARD_H < self.GRID_TOP or cy > h:
                continue

            self._draw_card(screen, cx, cy, ach, is_unlocked, unlock_date)

        screen.set_clip(None)

        # Fade gradient at top and bottom of scroll area
        self._draw_scroll_fade(screen, w, h)

    def _draw_card(self, screen: pygame.Surface,
                   x: int, y: int,
                   ach, is_unlocked: bool,
                   unlock_date) -> None:
        cw, ch = self.CARD_W, self.CARD_H

        draw_card(screen, (x, y, cw, ch),
                  alpha=240 if is_unlocked else 150)

        # Colored left accent bar
        bar_color = ach.color if is_unlocked else Theme.TEXT_MUTED
        pygame.draw.rect(screen, bar_color,
                         (x, y, 5, ch), border_radius=4)

        # Border - bright if unlocked, dim if locked
        border_color = (*ach.color[:3], 200) if is_unlocked else (*Theme.CARD_BORDER, 120)
        pygame.draw.rect(screen, border_color,
                         (x, y, cw, ch), 1, border_radius=12)

        # Icon - drawn as a small colored pill so no emoji/font issues
        icon_color = ach.color if is_unlocked else Theme.TEXT_MUTED
        _draw_ach_icon(screen, ach.icon, x + 6, y + ch // 2 - 16, icon_color, is_unlocked)

        # Name
        name_color = Theme.TEXT_PRIMARY if is_unlocked else Theme.TEXT_SECONDARY
        name_font  = FontCache.get("Segoe UI", 14, bold=True)
        draw_text(screen, ach.name, name_font, name_color, x + 50, y + 14)

        # Description (hidden if secret and locked)
        if is_unlocked or not ach.secret:
            desc_font = FontCache.get("Segoe UI", 11)
            desc = ach.description
            if len(desc) > 58:
                desc = desc[:55] + "..."
            draw_text(screen, desc, desc_font, Theme.TEXT_MUTED, x + 50, y + 35)
        else:
            hint_font = FontCache.get("Segoe UI", 11, italic=True)
            draw_text(screen, "Secret achievement - keep playing to unlock",
                      hint_font, Theme.TEXT_MUTED, x + 50, y + 35)

        # Points badge (top-right)
        pts_font = FontCache.get("Segoe UI", 10, bold=True)
        pts_text = f"{ach.points}pts"
        pts_w    = pts_font.size(pts_text)[0] + 10
        pts_c    = (*ach.color[:3], 180) if is_unlocked else (*Theme.TEXT_MUTED, 120)
        pts_surf = pygame.Surface((pts_w, 16), pygame.SRCALPHA)
        pygame.draw.rect(pts_surf, (0, 0, 0, 60), (0, 0, pts_w, 16), border_radius=4)
        screen.blit(pts_surf, (x + cw - pts_w - 8, y + 8))
        draw_text(screen, pts_text, pts_font, pts_c,
                  x + cw - pts_w - 3, y + 10)

        # Unlock date (bottom-right) or lock icon
        if is_unlocked and unlock_date:
            date_str  = unlock_date[:10]   # "YYYY-MM-DD"
            date_font = FontCache.get("Segoe UI", 10)
            draw_text(screen, f"OK  {date_str}", date_font,
                      (*ach.color[:3],), x + cw - 10, y + ch - 18, align="right")
        elif not is_unlocked:
            # Simple drawn lock: arc on top + rectangle body
            lx, ly = x + cw - 28, y + ch - 28
            pygame.draw.rect(screen, Theme.TEXT_MUTED, (lx, ly + 7, 14, 10), border_radius=2)
            pygame.draw.arc(screen, Theme.TEXT_MUTED,
                            pygame.Rect(lx + 2, ly, 10, 10), 0, 3.14159, 2)

        # Game tag (bottom-left)
        if ach.game_id:
            tag_font = FontCache.get("Segoe UI", 9, bold=True)
            tag = ach.game_id.replace("_", " ").upper()
            draw_text(screen, tag, tag_font, Theme.TEXT_MUTED, x + 50, y + ch - 18)
        else:
            tag_font = FontCache.get("Segoe UI", 9, bold=True)
            draw_text(screen, "GLOBAL", tag_font, Theme.ACCENT_BLUE, x + 50, y + ch - 18)

    def _draw_scroll_fade(self, screen: pygame.Surface, w: int, h: int) -> None:
        """Draw gradient fades at top and bottom of scroll area."""
        fade_h = 28

        # Top fade
        if self._scroll > 0:
            top_fade = pygame.Surface((w, fade_h), pygame.SRCALPHA)
            for i in range(fade_h):
                a = int(180 * (1 - i / fade_h))
                pygame.draw.line(top_fade, (15, 18, 25, a),
                                 (0, i), (w, i))
            screen.blit(top_fade, (0, self.GRID_TOP))

        # Bottom fade
        if self._scroll < self._max_scroll:
            bot_fade = pygame.Surface((w, fade_h), pygame.SRCALPHA)
            for i in range(fade_h):
                a = int(180 * (i / fade_h))
                pygame.draw.line(bot_fade, (15, 18, 25, a),
                                 (0, i), (w, i))
            screen.blit(bot_fade, (0, h - fade_h - 40))

    # ------------------------------------------------------------------
    # Input
    # ------------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_q, pygame.K_ESCAPE, pygame.K_BACKSPACE):
                self.engine.pop_scene()

        elif event.type == pygame.MOUSEWHEEL:
            self._scroll = max(0, min(self._max_scroll,
                                      self._scroll - event.y * 40))
