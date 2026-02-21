"""
scenes/main_menu.py
-------------------
MainMenuScene: The arcade's home screen.

Improvements over games.py main_menu():
  | Scene-based - no own while-loop
  | dt-driven animations (frame-rate independent)
  | Animated floating particle background
  | Right sidebar: player profile + global stats
  | Game cards show best score from StatsTracker
  | Achievement unlock popups (drains AchievementSystem queue)
  | All 13 games registered (original had 10)
  | Keyboard + mouse navigation
  | S = Settings  |  P = Profile  |  A = Achievements (Phase 5 screens)
  | Plugin-ready: reads game list from games/__init__.py GAME_REGISTRY
"""

import math
import random
import pygame

from engine import (
    BaseScene, Theme, RenderManager, FontCache,
    draw_text, draw_card, draw_footer_hint,
)
from engine.engine import SCREEN_WIDTH, SCREEN_HEIGHT


# ---------------------------------------------------------------------------
# Game registry  (until Phase 5 plugin loader, we define it here)
# ---------------------------------------------------------------------------

GAME_REGISTRY = [
    {
        "id":    "tetris",
        "name":  "Tetris",
        "desc":  "Stack and clear lines",
        "color": lambda: Theme.ACCENT_CYAN,
        "scene": "games.tetris:TetrisScene",
    },
    {
        "id":    "snake",
        "name":  "Snake",
        "desc":  "Grow and survive",
        "color": lambda: Theme.ACCENT_GREEN,
        "scene": "games.snake:SnakeScene",
    },
    {
        "id":    "pong",
        "name":  "Pong",
        "desc":  "Classic paddle duel",
        "color": lambda: Theme.ACCENT_PINK,
        "scene": "games.pong:PongScene",
    },
    {
        "id":    "flappy",
        "name":  "Flappy Bird",
        "desc":  "Thread the pipes",
        "color": lambda: Theme.ACCENT_YELLOW,
        "scene": "games.flappy:FlappyScene",
    },
    {
        "id":    "chess",
        "name":  "Chess",
        "desc":  "Tactical battles",
        "color": lambda: Theme.ACCENT_PURPLE,
        "scene": "games.chess:ChessScene",
    },
    {
        "id":    "breakout",
        "name":  "Breakout",
        "desc":  "Break every brick",
        "color": lambda: Theme.ACCENT_ORANGE,
        "scene": "games.breakout:BreakoutScene",
    },
    {
        "id":    "memory_match",
        "name":  "Memory Match",
        "desc":  "Find all pairs",
        "color": lambda: Theme.ACCENT_GREEN,
        "scene": "games.memory_match:MemoryMatchScene",
    },
    {
        "id":    "neon_blob_dash",
        "name":  "Neon Blob Dash",
        "desc":  "Dash and survive",
        "color": lambda: Theme.ACCENT_CYAN,
        "scene": "games.neon_blob_dash:NeonBlobDashScene",
    },
    {
        "id":    "endless_metro_run",
        "name":  "Endless Metro Run",
        "desc":  "Endless platform run",
        "color": lambda: Theme.ACCENT_BLUE,
        "scene": "games.endless_metro_run:EndlessMetroRunScene",
    },
    {
        "id":    "space_invaders",
        "name":  "Space Invaders",
        "desc":  "Defend against waves",
        "color": lambda: Theme.ACCENT_ORANGE,
        "scene": "games.space_invaders:SpaceInvadersScene",
    },
    {
        "id":    "game_2048",
        "name":  "2048",
        "desc":  "Merge to the top",
        "color": lambda: Theme.ACCENT_YELLOW,
        "scene": "games.game_2048:Game2048Scene",
    },
    {
        "id":    "minesweeper",
        "name":  "Minesweeper",
        "desc":  "Clear the minefield",
        "color": lambda: Theme.ACCENT_RED,
        "scene": "games.minesweeper:MinesweeperScene",
    },
    {
        "id":    "connect4",
        "name":  "Connect 4",
        "desc":  "Four in a row wins",
        "color": lambda: Theme.ACCENT_PINK,
        "scene": "games.connect4:Connect4Scene",
    },
]


# ---------------------------------------------------------------------------
# Floating background particle
# ---------------------------------------------------------------------------

class _MenuParticle:
    __slots__ = ("x", "y", "vx", "vy", "radius", "alpha", "color", "fade_speed")

    def __init__(self, w: int, h: int):
        self.x      = random.uniform(0, w)
        self.y      = random.uniform(0, h)
        self.vx     = random.uniform(-12, 12)
        self.vy     = random.uniform(-18, -4)
        self.radius = random.randint(1, 3)
        self.alpha  = random.randint(40, 140)
        accents = [
            Theme.ACCENT_BLUE, Theme.ACCENT_CYAN, Theme.ACCENT_PURPLE,
            Theme.ACCENT_PINK, Theme.ACCENT_GREEN,
        ]
        self.color      = random.choice(accents)
        self.fade_speed = random.uniform(15, 35)

    def update(self, dt: float, w: int, h: int) -> bool:
        """Return False when the particle should be removed."""
        self.x     += self.vx * dt
        self.y     += self.vy * dt
        self.alpha -= self.fade_speed * dt
        return self.alpha > 0 and 0 <= self.x <= w

    def draw(self, surface: pygame.Surface) -> None:
        a = max(0, min(255, int(self.alpha)))
        s = pygame.Surface((self.radius * 2, self.radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*self.color[:3], a),
                           (self.radius, self.radius), self.radius)
        surface.blit(s, (int(self.x) - self.radius, int(self.y) - self.radius))


# ---------------------------------------------------------------------------
# Achievement popup renderer
# ---------------------------------------------------------------------------

class _AchievementToast:
    """Renders a single achievement unlock toast that slides in, holds, fades."""

    HEIGHT   = 64
    WIDTH    = 340
    SLIDE_T  = 0.35   # seconds to slide in
    HOLD_T   = 2.8    # seconds to hold
    FADE_T   = 0.55   # seconds to fade out

    def __init__(self, popup, screen_w: int, screen_h: int):
        self.popup    = popup
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.elapsed  = 0.0
        self.total    = self.SLIDE_T + self.HOLD_T + self.FADE_T

    def update(self, dt: float) -> bool:
        self.elapsed += dt
        return self.elapsed < self.total

    def draw(self, surface: pygame.Surface, slot: int) -> None:
        """slot = vertical stack position (0 = bottom-most)."""
        t  = self.elapsed
        sw = self.screen_w
        sh = self.screen_h

        # X position - slides in from right
        target_x = sw - self.WIDTH - 18
        if t < self.SLIDE_T:
            progress = t / self.SLIDE_T
            ease     = 1 - (1 - progress) ** 3   # ease-out cubic
            x = sw + (target_x - sw) * ease
        else:
            x = target_x

        # Alpha - fades out at end
        if t > self.SLIDE_T + self.HOLD_T:
            fade_progress = (t - self.SLIDE_T - self.HOLD_T) / self.FADE_T
            alpha = int(255 * (1 - fade_progress))
        else:
            alpha = 255

        y = sh - self.HEIGHT - 18 - slot * (self.HEIGHT + 10)

        # Card background
        card = pygame.Surface((self.WIDTH, self.HEIGHT), pygame.SRCALPHA)
        ach  = self.popup.achievement
        pygame.draw.rect(card, (20, 25, 38, min(alpha, 230)),
                         (0, 0, self.WIDTH, self.HEIGHT), border_radius=10)
        pygame.draw.rect(card, (*ach.color[:3], min(alpha, 180)),
                         (0, 0, self.WIDTH, self.HEIGHT), 2, border_radius=10)

        # Left accent bar
        pygame.draw.rect(card, (*ach.color[:3], min(alpha, 220)),
                         (0, 0, 5, self.HEIGHT), border_radius=5)

        surface.blit(card, (int(x), y))

        # Icon
        icon_font = FontCache.get("Segoe UI", 24)
        draw_text(surface, ach.icon, icon_font, (*ach.color[:3],),
                  int(x) + 20, y + self.HEIGHT // 2, align="center")

        # "Achievement Unlocked" label
        label_font = FontCache.get("Segoe UI", 10, bold=True)
        draw_text(surface, "ACHIEVEMENT UNLOCKED",
                  label_font, Theme.TEXT_MUTED,
                  int(x) + 42, y + 10)

        # Achievement name
        name_font = FontCache.get("Segoe UI", 14, bold=True)
        draw_text(surface, ach.name, name_font,
                  (*Theme.TEXT_PRIMARY[:3],),
                  int(x) + 42, y + 26)

        # Description (truncated)
        desc = ach.description
        if len(desc) > 42:
            desc = desc[:39] + "..."
        desc_font = FontCache.get("Segoe UI", 11)
        draw_text(surface, desc, desc_font, Theme.TEXT_SECONDARY,
                  int(x) + 42, y + 43)


# ---------------------------------------------------------------------------
# Game icon renderer  (ported from games.py draw_game_icon, dt-based)
# ---------------------------------------------------------------------------

def _draw_game_icon(surface: pygame.Surface,
                    name: str, x: int, y: int,
                    size: int, t: float) -> None:
    """
    Draw a small animated icon for each game.
    *t* is elapsed time in seconds (replaces the old frame-counter pulse).
    """
    cx = x + size // 2
    cy = y + size // 2

    if name == "Tetris":
        block = size // 4
        colors = [Theme.ACCENT_CYAN, Theme.ACCENT_YELLOW, Theme.ACCENT_PURPLE]
        positions = [(0, 0), (1, 0), (1, 1), (2, 1)]
        ox = (size - 3 * block) // 2
        oy = (size - 2 * block) // 2
        for i, (bx, by) in enumerate(positions):
            c = colors[i % len(colors)]
            pygame.draw.rect(surface, c,
                (x + ox + bx * block, y + oy + by * block, block - 2, block - 2),
                border_radius=3)

    elif name == "Snake":
        seg = size // 5
        for i in range(4):
            off = int(math.sin(t * 5.0 + i * 0.5) * 2)
            a   = 255 - i * 40
            s   = pygame.Surface((seg - 2, seg - 2), pygame.SRCALPHA)
            pygame.draw.rect(s, (*Theme.ACCENT_GREEN[:3], a),
                             (0, 0, seg - 2, seg - 2), border_radius=2)
            surface.blit(s, (x + i * seg, cy - seg // 2 + off))

    elif name == "Pong":
        pygame.draw.rect(surface, Theme.ACCENT_CYAN,
                         (x + 2, y + 6, 3, size - 12), border_radius=2)
        pygame.draw.rect(surface, Theme.ACCENT_PINK,
                         (x + size - 5, y + 6, 3, size - 12), border_radius=2)
        bx = cx + int(math.sin(t * 5.0) * 8)
        pygame.draw.circle(surface, Theme.TEXT_PRIMARY, (bx, cy), 3)

    elif name == "Flappy Bird":
        by = cy + int(math.sin(t * 7.5) * 3)
        pygame.draw.circle(surface, Theme.ACCENT_YELLOW, (cx, by), size // 4)
        pygame.draw.circle(surface, Theme.BG_PRIMARY, (cx + 3, by - 2), 2)

    elif name == "Chess":
        s = size // 3
        pygame.draw.rect(surface, Theme.TEXT_PRIMARY,
                         (cx - s // 2, cy, s, s // 2))
        pygame.draw.circle(surface, Theme.TEXT_PRIMARY,
                           (cx, cy - s // 3), s // 3)

    elif name == "Breakout":
        pygame.draw.rect(surface, Theme.ACCENT_ORANGE,
                         (x + 4, y + 4, size - 8, 6), border_radius=2)
        pygame.draw.rect(surface, Theme.ACCENT_CYAN,
                         (x + 8, y + size - 10, size - 16, 4), border_radius=2)
        bx = cx + int(math.sin(t * 5.0) * 6)
        pygame.draw.circle(surface, Theme.TEXT_PRIMARY, (bx, cy + 2), 3)

    elif name == "Memory Match":
        s = size // 2 - 3
        pygame.draw.rect(surface, Theme.ACCENT_GREEN,
                         (x + 1, y + 1, s, s), border_radius=3)
        pygame.draw.rect(surface, Theme.ACCENT_PURPLE,
                         (x + s + 5, y + 1, s, s), border_radius=3)
        pygame.draw.rect(surface, Theme.ACCENT_YELLOW,
                         (x + 1, y + s + 5, s, s), border_radius=3)
        pygame.draw.rect(surface, Theme.ACCENT_PINK,
                         (x + s + 5, y + s + 5, s, s), border_radius=3)

    elif name == "Neon Blob Dash":
        pygame.draw.rect(surface, Theme.ACCENT_GREEN,
                         (x + 3, y + size - 10, size - 6, 6), border_radius=2)
        bx = x + size // 2 - 4 + int(math.sin(t * 4) * 3)
        pygame.draw.rect(surface, Theme.ACCENT_CYAN,
                         (bx, y + size // 2 - 8, 8, 8), border_radius=2)

    elif name == "Endless Metro Run":
        pygame.draw.rect(surface, Theme.ACCENT_BLUE,
                         (x + 2, y + size - 11, size - 4, 7), border_radius=2)
        rx = x + size // 2 - 5 + int(t * 30) % (size - 4) - size // 4
        pygame.draw.rect(surface, Theme.ACCENT_CYAN,
                         (rx, y + size // 2 - 9, 10, 10), border_radius=2)

    elif name == "Space Invaders":
        pygame.draw.polygon(surface, Theme.ACCENT_CYAN,
            [(cx, y + 4), (x + 6, y + size - 4), (x + size - 6, y + size - 4)])
        pulse_r = 3 + int(math.sin(t * 6) * 1.5)
        pygame.draw.circle(surface, Theme.ACCENT_ORANGE,
                           (x + size - 8, y + 8), pulse_r)

    elif name == "2048":
        font = FontCache.get("Segoe UI", size // 3, bold=True)
        draw_text(surface, "2048", font, Theme.ACCENT_YELLOW, cx, cy, align="center")

    elif name == "Minesweeper":
        # Grid of dots with one highlighted
        dot_sz = size // 4
        for row in range(3):
            for col in range(3):
                dx = x + col * dot_sz + dot_sz // 2
                dy = y + row * dot_sz + dot_sz // 2 + 2
                c = Theme.ACCENT_RED if (row == 1 and col == 1) else Theme.TEXT_MUTED
                pygame.draw.circle(surface, c, (dx, dy), 2)

    elif name == "Connect 4":
        cols_c, rows_c = 4, 3
        for row in range(rows_c):
            for col in range(cols_c):
                cx2 = x + col * (size // cols_c) + size // (cols_c * 2)
                cy2 = y + row * (size // rows_c) + size // (rows_c * 2)
                c = Theme.ACCENT_RED if col == 2 and row < 2 else Theme.ACCENT_YELLOW
                pygame.draw.circle(surface, c, (cx2, cy2), size // 10)


# ---------------------------------------------------------------------------
# MainMenuScene
# ---------------------------------------------------------------------------

class MainMenuScene(BaseScene):
    """
    The main hub screen.  Displays all games in a 3-column card grid,
    shows the player profile in a right sidebar, and handles navigation.
    """

    # Layout constants
    GRID_COLS  = 3
    CARD_W     = 255
    CARD_H     = 100
    GAP_X      = 18
    GAP_Y      = 14
    GRID_Y     = 182
    SIDEBAR_W  = 200
    SIDEBAR_PAD = 14

    MAX_PARTICLES = 55

    def __init__(self, engine):
        super().__init__(engine)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def on_enter(self) -> None:
        self._selected    = 0
        self._time        = 0.0          # elapsed seconds (for animations)
        self._particles: list[_MenuParticle] = []
        self._particle_timer = 0.0
        self._toasts: list[_AchievementToast] = []

        # Pre-compute grid origin
        w, h = self.screen_size
        cols   = self.GRID_COLS
        grid_w = cols * self.CARD_W + (cols - 1) * self.GAP_X
        # Push grid left to leave room for sidebar
        content_w = grid_w + self.SIDEBAR_W + self.SIDEBAR_PAD
        self._grid_x = (w - content_w) // 2
        self._grid_y = self.GRID_Y

        # Vertical scroll
        self._scroll_y   = 0.0
        rows = math.ceil(len(GAME_REGISTRY) / self.GRID_COLS)
        total_h = rows * (self.CARD_H + self.GAP_Y)
        visible_h = h - self.GRID_Y - 40
        self._max_scroll = max(0.0, total_h - visible_h)

        # Mouse hover
        self._hover = -1

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def update(self, dt: float) -> None:
        w, h = self.screen_size
        self._time += dt

        # Particles - only when enabled in settings
        _show_p = (self.settings.show_particles if self.settings else True)
        if _show_p:
            self._particle_timer += dt
            if self._particle_timer > 0.12 and len(self._particles) < self.MAX_PARTICLES:
                self._particle_timer = 0.0
                for _ in range(random.randint(1, 3)):
                    self._particles.append(_MenuParticle(w, h))
            self._particles = [p for p in self._particles if p.update(dt, w, h)]
        else:
            self._particles.clear()

        # Achievement toasts - drain queue from system
        if self.achievements:
            for popup in self.achievements.get_pending_popups():
                self._toasts.append(
                    _AchievementToast(popup, w, h)
                )
        self._toasts = [t for t in self._toasts if t.update(dt)]

        # Mouse hover detection
        mx, my = pygame.mouse.get_pos()
        self._hover = self._card_at(mx, my)

    # ------------------------------------------------------------------
    # Draw
    # ------------------------------------------------------------------

    def draw(self, screen: pygame.Surface) -> None:
        w, h = screen.get_size()

        # Background
        screen.blit(RenderManager.get_background(w, h), (0, 0))

        # Floating particles
        for p in self._particles:
            p.draw(screen)

        # Header
        self._draw_header(screen, w)

        # Game grid
        self._draw_grid(screen)

        # Right sidebar
        self._draw_sidebar(screen, w, h)

        # Footer hint
        draw_footer_hint(screen,
            "^v<> Navigate  |  Enter Play  |  S Settings  |  A Achievements  |  Q Quit",
            y_offset=26)

        # Achievement toasts (on top of everything)
        for i, toast in enumerate(self._toasts):
            toast.draw(screen, i)

    def _draw_header(self, screen: pygame.Surface, w: int) -> None:
        # Title
        title_font = FontCache.get("Segoe UI", 62, bold=True)
        draw_text(screen, "ARCADE", title_font, Theme.TEXT_PRIMARY,
                  w // 2, 52, align="center")

        # Animated accent line
        line_w = int(180 + 30 * math.sin(self._time * 1.2))
        cx = w // 2
        pygame.draw.line(screen, Theme.ACCENT_CYAN,
                         (cx - line_w // 2, 128),
                         (cx + line_w // 2, 128), 3)

        # Subtitle
        sub_font = FontCache.get("Segoe UI", 15)
        draw_text(screen, "Select a game to play", sub_font, Theme.TEXT_MUTED,
                  w // 2, 145, align="center")

    def _draw_grid(self, screen: pygame.Surface) -> None:
        name_font  = FontCache.get("Segoe UI", 18, bold=True)
        desc_font  = FontCache.get("Segoe UI", 11)
        score_font = FontCache.get("Segoe UI", 11)

        w, h = screen.get_size()
        clip = pygame.Rect(0, self.GRID_Y - 4, w, h - self.GRID_Y - 36)
        screen.set_clip(clip)

        for i, game in enumerate(GAME_REGISTRY):
            row = i // self.GRID_COLS
            col = i % self.GRID_COLS
            x   = self._grid_x + col * (self.CARD_W + self.GAP_X)
            y   = self._grid_y + row * (self.CARD_H + self.GAP_Y) - int(self._scroll_y)

            # Skip fully off-screen cards
            if y + self.CARD_H < self.GRID_Y or y > h:
                continue

            is_sel   = (i == self._selected)
            is_hover = (i == self._hover) and not is_sel
            color    = game["color"]()

            # Card
            alpha = 255 if is_sel else (235 if is_hover else 210)
            draw_card(screen, (x, y, self.CARD_W, self.CARD_H), alpha)

            # Selection border
            if is_sel:
                pygame.draw.rect(screen, color,
                    (x - 2, y - 2, self.CARD_W + 4, self.CARD_H + 4),
                    2, border_radius=13)
            elif is_hover:
                pygame.draw.rect(screen, (*color[:3], 120),
                    (x - 1, y - 1, self.CARD_W + 2, self.CARD_H + 2),
                    1, border_radius=13)

            # Animated icon
            icon_t = self._time if is_sel else 0.0
            _draw_game_icon(screen, game["name"], x + 12, y + 12, 44, icon_t)

            # Colour tag bar on icon area right edge
            pygame.draw.rect(screen, (*color[:3], 80),
                             (x, y, 4, self.CARD_H), border_radius=4)

            # Game name
            name_color = Theme.TEXT_PRIMARY if is_sel else Theme.TEXT_SECONDARY
            draw_text(screen, game["name"], name_font, name_color,
                      x + 64, y + 16)

            # Description
            draw_text(screen, game["desc"], desc_font, Theme.TEXT_MUTED,
                      x + 64, y + 40)

            # Best score (from stats system)
            if self.stats:
                best = self.stats.best_score(game["id"])
                if best > 0:
                    score_str = f"Best: {best:,}"
                    draw_text(screen, score_str, score_font,
                              (*color[:3],),
                              x + 64, y + 60)

            # Played count badge (top-right corner of card)
            if self.stats:
                played = self.stats.games_played(game["id"])
                if played > 0:
                    badge_font = FontCache.get("Segoe UI", 10, bold=True)
                    badge_text = f"x{played}"
                    bw = badge_font.size(badge_text)[0] + 10
                    bx = x + self.CARD_W - bw - 6
                    by = y + 6
                    pygame.draw.rect(screen, Theme.BG_TERTIARY,
                                     (bx, by, bw, 16), border_radius=4)
                    draw_text(screen, badge_text, badge_font,
                              Theme.TEXT_MUTED, bx + 5, by + 2)

        screen.set_clip(None)

        # Scroll indicator (thin line on right edge of grid area)
        if self._max_scroll > 0:
            track_x = self._grid_x + self.GRID_COLS * (self.CARD_W + self.GAP_X) + 4
            track_h = h - self.GRID_Y - 40
            pct     = self._scroll_y / self._max_scroll
            thumb_h = max(20, int(track_h * (track_h / (track_h + self._max_scroll))))
            thumb_y = self.GRID_Y + int(pct * (track_h - thumb_h))
            pygame.draw.rect(screen, Theme.BG_TERTIARY,
                             (track_x, self.GRID_Y, 3, track_h), border_radius=2)
            pygame.draw.rect(screen, Theme.ACCENT_PURPLE,
                             (track_x, thumb_y, 3, thumb_h), border_radius=2)

    def _draw_sidebar(self, screen: pygame.Surface, w: int, h: int) -> None:
        sb_x = self._grid_x + self.GRID_COLS * (self.CARD_W + self.GAP_X) + self.SIDEBAR_PAD
        sb_y = self._grid_y
        sb_w = self.SIDEBAR_W
        sb_h = h - sb_y - 40

        draw_card(screen, (sb_x, sb_y, sb_w, sb_h), 230)

        # Accent top bar
        pygame.draw.rect(screen, Theme.ACCENT_BLUE,
                         (sb_x, sb_y, sb_w, 4), border_radius=4)

        pad = 14
        cy  = sb_y + 22

        # Player name
        name_font = FontCache.get("Segoe UI", 16, bold=True)
        player_name = "Player 1"
        if self.profile:
            player_name = self.profile.display_name
        draw_text(screen, player_name, name_font, Theme.TEXT_PRIMARY,
                  sb_x + sb_w // 2, cy, align="center")
        cy += 28

        # Thin divider
        pygame.draw.line(screen, Theme.CARD_BORDER,
                         (sb_x + pad, cy), (sb_x + sb_w - pad, cy))
        cy += 14

        # Stats rows
        stats_rows = []
        if self.profile:
            snap = self.profile.full_snapshot()
            stats_rows = [
                ("PLAYTIME",   snap["playtime_formatted"],  Theme.ACCENT_CYAN),
                ("GAMES",      str(snap["total_games"]),    Theme.ACCENT_GREEN),
                ("WIN RATE",   snap["overall_win_rate"],    Theme.ACCENT_YELLOW),
                ("FAVOURITE",  snap["favourite_game"],      Theme.ACCENT_PURPLE),
            ]
        else:
            stats_rows = [
                ("PLAYTIME",  "-", Theme.ACCENT_CYAN),
                ("GAMES",     "-", Theme.ACCENT_GREEN),
                ("WIN RATE",  "-", Theme.ACCENT_YELLOW),
                ("FAVOURITE", "-", Theme.ACCENT_PURPLE),
            ]

        label_font = FontCache.get("Segoe UI", 10, bold=True)
        value_font = FontCache.get("Segoe UI", 15, bold=True)
        for label, value, color in stats_rows:
            draw_text(screen, label, label_font, Theme.TEXT_MUTED,
                      sb_x + pad, cy)
            cy += 15
            draw_text(screen, str(value), value_font, color,
                      sb_x + pad, cy)
            cy += 22

        # Thin divider
        pygame.draw.line(screen, Theme.CARD_BORDER,
                         (sb_x + pad, cy), (sb_x + sb_w - pad, cy))
        cy += 14

        # Achievement progress
        if self.achievements:
            unlocked = self.achievements.unlocked_count()
            total    = self.achievements.total_count()
            points   = self.achievements.total_points()
            progress = unlocked / total if total > 0 else 0.0

            ach_font  = FontCache.get("Segoe UI", 10, bold=True)
            ach_font2 = FontCache.get("Segoe UI", 13, bold=True)
            draw_text(screen, "ACHIEVEMENTS", ach_font,
                      Theme.TEXT_MUTED, sb_x + pad, cy)
            cy += 16
            draw_text(screen, f"{unlocked} / {total}",
                      ach_font2, Theme.ACCENT_YELLOW,
                      sb_x + pad, cy)
            cy += 20

            # Progress bar
            bar_w = sb_w - pad * 2
            pygame.draw.rect(screen, Theme.BG_TERTIARY,
                             (sb_x + pad, cy, bar_w, 8), border_radius=4)
            fill_w = int(bar_w * progress)
            if fill_w > 0:
                pygame.draw.rect(screen, Theme.ACCENT_YELLOW,
                                 (sb_x + pad, cy, fill_w, 8), border_radius=4)
            cy += 20

            draw_text(screen, f"{points} pts",
                      FontCache.get("Segoe UI", 11),
                      Theme.TEXT_MUTED, sb_x + pad, cy)
            cy += 28

        # Nav hint buttons
        nav_font = FontCache.get("Segoe UI", 11)
        nav_items = [
            ("[S] Settings",      Theme.ACCENT_BLUE),
            ("[A] Achievements",  Theme.ACCENT_YELLOW),
            ("[P] Profile",       Theme.ACCENT_GREEN),
        ]
        for label, color in nav_items:
            draw_text(screen, label, nav_font, color, sb_x + pad, cy)
            cy += 20

    # ------------------------------------------------------------------
    # Input
    # ------------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event) -> None:
        n = len(GAME_REGISTRY)
        cols = self.GRID_COLS
        _, h = self.screen_size

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RIGHT:
                self._selected = (self._selected + 1) % n
            elif event.key == pygame.K_LEFT:
                self._selected = (self._selected - 1) % n
            elif event.key == pygame.K_DOWN:
                target = self._selected + cols
                if target >= n:
                    # Wrap to same column on row 0 (or col 0 if no same-col on row 0)
                    target = self._selected % cols
                self._selected = target
            elif event.key == pygame.K_UP:
                target = self._selected - cols
                if target < 0:
                    # Wrap to last row - clamp to final game if last row is partial
                    last_row_first = (n // cols) * cols
                    target = last_row_first + (self._selected % cols)
                    if target >= n:
                        target = n - 1
                self._selected = target

            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._launch_selected()

            elif event.key == pygame.K_q:
                self.engine.pop_scene()

            # Hub screens
            elif event.key == pygame.K_s:
                from scenes.settings_screen     import SettingsScene
                self.engine.push_scene(SettingsScene(self.engine))
            elif event.key == pygame.K_a:
                from scenes.achievements_screen import AchievementsScene
                self.engine.push_scene(AchievementsScene(self.engine))
            elif event.key == pygame.K_p:
                from scenes.profile_screen      import ProfileScene
                self.engine.push_scene(ProfileScene(self.engine))

            # Auto-scroll selected card into view
            row = self._selected // cols
            card_top = self._grid_y + row * (self.CARD_H + self.GAP_Y) - int(self._scroll_y)
            card_bot = card_top + self.CARD_H
            visible_bot = h - 40
            if card_bot > visible_bot:
                self._scroll_y = min(self._max_scroll,
                    self._scroll_y + (card_bot - visible_bot) + 4)
            elif card_top < self._grid_y:
                self._scroll_y = max(0.0,
                    self._scroll_y - (self._grid_y - card_top) - 4)

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                idx = self._card_at(*event.pos)
                if idx >= 0:
                    if idx == self._selected:
                        self._launch_selected()
                    else:
                        self._selected = idx
            elif event.button == 4:   # scroll wheel up
                self._scroll_y = max(0.0, self._scroll_y - 80)
            elif event.button == 5:   # scroll wheel down
                self._scroll_y = min(self._max_scroll, self._scroll_y + 80)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _card_at(self, mx: int, my: int) -> int:
        """Return the index of the game card under (mx, my), or -1."""
        for i in range(len(GAME_REGISTRY)):
            row = i // self.GRID_COLS
            col = i % self.GRID_COLS
            x   = self._grid_x + col * (self.CARD_W + self.GAP_X)
            y   = self._grid_y + row * (self.CARD_H + self.GAP_Y)
            if x <= mx <= x + self.CARD_W and y <= my <= y + self.CARD_H:
                return i
        return -1

    def _launch_selected(self) -> None:
        """Dynamically import and push the selected game's Scene."""
        game = GAME_REGISTRY[self._selected]
        module_path, class_name = game["scene"].split(":")
        try:
            import importlib
            mod   = importlib.import_module(module_path)
            klass = getattr(mod, class_name)
            self.engine.push_scene(klass(self.engine))
        except (ImportError, AttributeError) as e:
            # Game not yet implemented - show a placeholder scene
            self._push_placeholder(game["name"], str(e))

    def _push_placeholder(self, game_name: str, error: str) -> None:
        """Temporary: push a 'coming soon' scene for unbuilt games."""
        engine = self.engine

        class PlaceholderScene(BaseScene):
            def on_enter(self):
                self._t = 0.0

            def update(self, dt):
                self._t += dt

            def draw(self, screen):
                w, h = screen.get_size()
                screen.blit(RenderManager.get_background(w, h), (0, 0))
                title_font = FontCache.get("Segoe UI", 42, bold=True)
                draw_text(screen, game_name, title_font,
                          Theme.TEXT_PRIMARY, w // 2, h // 2 - 50, align="center")
                sub_font = FontCache.get("Segoe UI", 18)
                draw_text(screen, "Coming in a future phase",
                          sub_font, Theme.TEXT_MUTED,
                          w // 2, h // 2 + 10, align="center")
                hint_font = FontCache.get("Segoe UI", 13)
                draw_text(screen, "Press Q or Backspace to go back",
                          hint_font, Theme.TEXT_SECONDARY,
                          w // 2, h // 2 + 55, align="center")

            def handle_event(self, event):
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_q, pygame.K_BACKSPACE, pygame.K_ESCAPE):
                        self.engine.pop_scene()

        engine.push_scene(PlaceholderScene(engine))

    def _push_if_available(self, module_path: str, class_name: str) -> None:
        """Push a scene from a module if it exists, silently skip if not yet built."""
        try:
            import importlib
            mod   = importlib.import_module(module_path)
            klass = getattr(mod, class_name)
            self.engine.push_scene(klass(self.engine))
        except (ImportError, AttributeError):
            pass   # Screen not built yet - no-op
