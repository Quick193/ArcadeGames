"""
scenes/profile_screen.py
------------------------
ProfileScene: Player profile and per-game stats viewer.

Layout
------
  Left panel  — player identity (name, avatar placeholder, global numbers)
  Right panel — scrollable per-game stat table
                (Played / Won / Best Score / Best Streak / Win Rate / Playtime)

Controls
--------
  ↑ ↓ / Mouse wheel  — scroll game table
  Q / Esc            — back
"""

import math
import pygame

from engine import (
    BaseScene, Theme, RenderManager, FontCache,
    draw_text, draw_card, draw_footer_hint,
)
from engine.engine import SCREEN_WIDTH, SCREEN_HEIGHT
from systems.profile import GAME_DISPLAY_NAMES


# Avatar palette — 8 simple color blobs used as placeholder avatars
AVATAR_COLORS = [
    (79, 236, 255), (92, 219, 149), (171, 99, 250), (255, 159, 67),
    (255, 107, 107), (250, 99, 180), (255, 214, 102), (99, 179, 237),
]


class ProfileScene(BaseScene):

    # Left panel
    LP_X = 48
    LP_Y = 60
    LP_W = 280
    LP_H = SCREEN_HEIGHT - 120

    # Right panel (game table)
    RP_X = LP_X + LP_W + 28
    RP_Y = LP_Y
    RP_W = SCREEN_WIDTH - RP_X - 48
    TABLE_TOP = LP_Y + 56    # y where first game row starts
    ROW_H     = 52
    SCROLL_SPD = 200

    def on_enter(self) -> None:
        self._scroll     = 0.0
        self._max_scroll = 0.0
        self._time       = 0.0
        self._snapshot: dict = {}
        self._refresh()

    def _refresh(self) -> None:
        if self.profile:
            self._snapshot = self.profile.full_snapshot()
        n = len(GAME_DISPLAY_NAMES)
        total_h = n * self.ROW_H
        visible_h = SCREEN_HEIGHT - self.TABLE_TOP - 80
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

        self._draw_left_panel(screen)
        self._draw_right_panel(screen, w, h)
        draw_footer_hint(screen, "↑↓ Scroll  •  Q Back", y_offset=26)

    # ------------------------------------------------------------------
    # Left panel — identity + global stats
    # ------------------------------------------------------------------

    def _draw_left_panel(self, screen: pygame.Surface) -> None:
        x, y, w, h = self.LP_X, self.LP_Y, self.LP_W, self.LP_H
        draw_card(screen, (x, y, w, h))

        # Accent top bar
        avatar_color = AVATAR_COLORS[
            self._snapshot.get("avatar_index", 0) % len(AVATAR_COLORS)
        ]
        pygame.draw.rect(screen, avatar_color, (x, y, w, 5), border_radius=4)

        cy = y + 28

        # Avatar circle
        av_r = 36
        av_cx = x + w // 2
        pygame.draw.circle(screen, Theme.BG_TERTIARY, (av_cx, cy + av_r), av_r + 2)
        pygame.draw.circle(screen, avatar_color,       (av_cx, cy + av_r), av_r)
        init_font = FontCache.get("Segoe UI", 28, bold=True)
        name = self._snapshot.get("display_name", "P1")
        initial = name[0].upper()
        draw_text(screen, initial, init_font, Theme.BG_PRIMARY,
                  av_cx, cy + av_r, align="center")
        cy += av_r * 2 + 16

        # Name
        name_font = FontCache.get("Segoe UI", 18, bold=True)
        draw_text(screen, name, name_font, Theme.TEXT_PRIMARY,
                  av_cx, cy, align="center")
        cy += 28

        # Thin divider
        pygame.draw.line(screen, Theme.CARD_BORDER,
                         (x + 20, cy), (x + w - 20, cy))
        cy += 18

        # Global stat rows
        snap = self._snapshot
        rows = [
            ("Total Games",  str(snap.get("total_games", 0)),          Theme.ACCENT_CYAN),
            ("Total Wins",   str(snap.get("total_wins", 0)),            Theme.ACCENT_GREEN),
            ("Win Rate",     snap.get("overall_win_rate", "0%"),        Theme.ACCENT_YELLOW),
            ("Playtime",     snap.get("playtime_formatted", "0m"),      Theme.ACCENT_BLUE),
            ("Favourite",    snap.get("favourite_game", "—"),            Theme.ACCENT_PURPLE),
        ]
        label_font = FontCache.get("Segoe UI", 10, bold=True)
        value_font = FontCache.get("Segoe UI", 16, bold=True)
        for label, value, color in rows:
            draw_text(screen, label, label_font, Theme.TEXT_MUTED, x + 20, cy)
            cy += 16
            draw_text(screen, value, value_font, color, x + 20, cy)
            cy += 26

        # Achievement summary
        cy += 6
        pygame.draw.line(screen, Theme.CARD_BORDER,
                         (x + 20, cy), (x + w - 20, cy))
        cy += 14
        if self.achievements:
            unlocked = self.achievements.unlocked_count()
            total    = self.achievements.total_count()
            pts      = self.achievements.total_points()
            prog     = unlocked / total if total else 0.0

            draw_text(screen, "ACHIEVEMENTS", label_font, Theme.TEXT_MUTED, x + 20, cy)
            cy += 16
            ach_val = FontCache.get("Segoe UI", 16, bold=True)
            draw_text(screen, f"{unlocked}/{total}", ach_val,
                      Theme.ACCENT_YELLOW, x + 20, cy)
            draw_text(screen, f"{pts}pts",
                      FontCache.get("Segoe UI", 11), Theme.TEXT_MUTED,
                      x + 20 + ach_val.size(f"{unlocked}/{total}")[0] + 8, cy + 3)
            cy += 22

            bar_w = w - 40
            pygame.draw.rect(screen, Theme.BG_TERTIARY,
                             (x + 20, cy, bar_w, 8), border_radius=4)
            fill = int(bar_w * prog)
            if fill > 0:
                pygame.draw.rect(screen, Theme.ACCENT_YELLOW,
                                 (x + 20, cy, fill, 8), border_radius=4)

    # ------------------------------------------------------------------
    # Right panel — scrollable game table
    # ------------------------------------------------------------------

    def _draw_right_panel(self, screen: pygame.Surface, sw: int, sh: int) -> None:
        rx, ry = self.RP_X, self.RP_Y
        rw     = self.RP_W

        # Panel background card
        draw_card(screen, (rx, ry, rw, sh - ry - 48))
        pygame.draw.rect(screen, Theme.ACCENT_BLUE,
                         (rx, ry, rw, 5), border_radius=4)

        # Column header
        cy = ry + 16
        headers = [
            ("GAME",        0,    Theme.TEXT_MUTED),
            ("PLAYED",     220,   Theme.TEXT_MUTED),
            ("WON",        285,   Theme.TEXT_MUTED),
            ("BEST SCORE", 345,   Theme.TEXT_MUTED),
            ("STREAK",     460,   Theme.TEXT_MUTED),
            ("WIN RATE",   530,   Theme.TEXT_MUTED),
        ]
        hf = FontCache.get("Segoe UI", 10, bold=True)
        for label, ox, color in headers:
            draw_text(screen, label, hf, color, rx + 18 + ox, cy)
        cy += 18

        pygame.draw.line(screen, Theme.CARD_BORDER,
                         (rx + 10, cy), (rx + rw - 10, cy))
        cy += 4

        # Clip scrollable area
        clip_top = cy
        clip_h   = sh - clip_top - 50
        screen.set_clip(pygame.Rect(rx, clip_top, rw, clip_h))

        games_data = self._snapshot.get("games", {})
        gf  = FontCache.get("Segoe UI", 13, bold=True)
        vf  = FontCache.get("Segoe UI", 13)
        alt = False
        for gid, display_name in GAME_DISPLAY_NAMES.items():
            row_y = cy + list(GAME_DISPLAY_NAMES.keys()).index(gid) * self.ROW_H \
                    - int(self._scroll)

            if row_y + self.ROW_H < clip_top or row_y > clip_top + clip_h:
                continue

            # Alternating row background
            if alt:
                row_bg = pygame.Surface((rw - 20, self.ROW_H - 2), pygame.SRCALPHA)
                row_bg.fill((*Theme.BG_TERTIARY, 60))
                screen.blit(row_bg, (rx + 10, row_y + 1))
            alt = not alt

            gdata = games_data.get(gid, {})
            played   = gdata.get("played", 0)
            won      = gdata.get("won", 0)
            best     = gdata.get("best_score", 0)
            streak   = gdata.get("best_streak", 0)
            wr       = gdata.get("win_rate_pct", "0%")

            # Name color — bright if ever played
            name_col = Theme.TEXT_PRIMARY if played > 0 else Theme.TEXT_MUTED

            mid_y = row_y + self.ROW_H // 2 - 7

            draw_text(screen, display_name, gf,  name_col,          rx + 18, mid_y)
            draw_text(screen, str(played),  vf,  Theme.ACCENT_CYAN,  rx + 238, mid_y)
            draw_text(screen, str(won),     vf,  Theme.ACCENT_GREEN, rx + 303, mid_y)
            draw_text(screen, f"{best:,}" if best else "—",
                      vf, Theme.ACCENT_YELLOW, rx + 363, mid_y)
            draw_text(screen, str(streak) if streak else "—",
                      vf, Theme.ACCENT_ORANGE, rx + 478, mid_y)
            draw_text(screen, wr if played else "—",
                      vf, Theme.ACCENT_PURPLE, rx + 548, mid_y)

            # Bottom separator
            pygame.draw.line(screen, (*Theme.CARD_BORDER, 80),
                             (rx + 18, row_y + self.ROW_H - 1),
                             (rx + rw - 18, row_y + self.ROW_H - 1))

        screen.set_clip(None)

        # Scroll fade at bottom
        if self._max_scroll > 0 and self._scroll < self._max_scroll:
            fade_h = 30
            fade = pygame.Surface((rw, fade_h), pygame.SRCALPHA)
            for i in range(fade_h):
                a = int(160 * i / fade_h)
                pygame.draw.line(fade, (*Theme.BG_PRIMARY, a), (0, i), (rw, i))
            screen.blit(fade, (rx, clip_top + clip_h - fade_h))

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
