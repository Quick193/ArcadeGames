"""
games/tetris.py
---------------
TetrisScene: Complete Tetris refactored from games.py tetris_main().

Preserved from original
-----------------------
  | All 7 tetrominoes (I J L O S T Z) with correct shapes and colors
  | Grid collision logic  (valid_space)
  | Row clearing with gravity  (clear_rows)
  | Score formula: 100 × cleared²
  | Level-up every 10 lines, speed increase
  | Soft drop (v), hard drop (Space)
  | Rotate CW (^/X), CCW (Z)
  | Pause (P), Restart (R), Quit (Q/Esc)

New features
------------
  | Ghost piece - shows where the piece will land
  | Hold piece  - C or Shift to hold/swap (once per piece)
  | Wall kicks  - 3-position kick on rotation failure
  | Line-clear flash - rows flash white before clearing
  | dt-based fall timing - frame-rate independent
  | DAS / ARR key-repeat handled by engine (pygame.key.set_repeat)
  | Stats recording + achievement checking on game over
  | New Best score banner on game over screen
  | Scoring: Single=100, Double=300, Triple=500, Tetris=800 × level
"""

import math
import random
import pygame
from copy import deepcopy

from engine import (
    BaseScene, Theme, RenderManager, FontCache,
    draw_text, draw_card, draw_stat_card, draw_panel_title,
    draw_key_badge, draw_overlay, draw_footer_hint,
)
from engine.engine import SCREEN_WIDTH, SCREEN_HEIGHT


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ROWS, COLS   = 20, 10
BLOCK_SIZE   = 30          # px per cell

PLAY_W = COLS * BLOCK_SIZE          # 300
PLAY_H = ROWS * BLOCK_SIZE          # 600
SIDE_W = 190                        # sidebar width
PADDING = 20

# Playfield is centred; sidebar is to its right
PLAY_X = (SCREEN_WIDTH - PLAY_W - SIDE_W - PADDING) // 2
PLAY_Y = (SCREEN_HEIGHT - PLAY_H) // 2
SIDE_X = PLAY_X + PLAY_W + PADDING
SIDE_Y = PLAY_Y

# Hold panel sits to the LEFT of the playfield
HOLD_W = 130
HOLD_X = PLAY_X - HOLD_W - PADDING
HOLD_Y = PLAY_Y

# Fall speeds (seconds per row) by level
BASE_FALL   = 0.50
SPEED_DELTA = 0.045
MIN_SPEED   = 0.05

# Line-clear flash duration in seconds
FLASH_DURATION = 0.22

# Scoring table: lines cleared > base points
SCORE_TABLE = {1: 100, 2: 300, 3: 500, 4: 800}

# Wall kick offsets tried when rotation fails: [offset_x, ...]
WALL_KICKS = [-1, 1, -2, 2]

# Empty cell sentinel
EMPTY = (0, 0, 0)


# ---------------------------------------------------------------------------
# Tetrominoes
# ---------------------------------------------------------------------------

SHAPES = [
    [[1, 1, 1, 1]],           # I
    [[1, 0, 0],
     [1, 1, 1]],              # J
    [[0, 0, 1],
     [1, 1, 1]],              # L
    [[1, 1],
     [1, 1]],                 # O
    [[0, 1, 1],
     [1, 1, 0]],              # S
    [[0, 1, 0],
     [1, 1, 1]],              # T
    [[1, 1, 0],
     [0, 1, 1]],              # Z
]

# Shape index > theme color (7 pieces, 7 accent colors)
PIECE_COLOR_IDX = list(range(7))


def _rotate_cw(shape: list) -> list:
    """Rotate a shape matrix 90° clockwise."""
    return [list(row) for row in zip(*shape[::-1])]


def _rotate_ccw(shape: list) -> list:
    return _rotate_cw(_rotate_cw(_rotate_cw(shape)))


# ---------------------------------------------------------------------------
# Piece
# ---------------------------------------------------------------------------

class Piece:
    """A single active tetromino."""

    __slots__ = ("x", "y", "shape", "color", "_shape_idx")

    def __init__(self, shape_idx: int = -1):
        if shape_idx < 0:
            shape_idx = random.randrange(len(SHAPES))
        self._shape_idx = shape_idx
        self.shape = deepcopy(SHAPES[shape_idx])
        self.color = Theme.piece_color(shape_idx)
        # Spawn position
        self.x = COLS // 2 - len(self.shape[0]) // 2
        self.y = 0

    def reset_color(self) -> None:
        """Refresh color from theme (called on theme change)."""
        self.color = Theme.piece_color(self._shape_idx)


# ---------------------------------------------------------------------------
# Grid helpers (pure functions - no side effects)
# ---------------------------------------------------------------------------

def _make_grid(locked: dict) -> list:
    """Build a 2-D color grid from locked positions."""
    grid = [[EMPTY] * COLS for _ in range(ROWS)]
    for (x, y), color in locked.items():
        if 0 <= y < ROWS:
            grid[y][x] = color
    return grid


def _valid(shape: list, locked: dict, ox: int, oy: int) -> bool:
    """Return True if shape at offset (ox, oy) is a legal position."""
    for r, row in enumerate(shape):
        for c, cell in enumerate(row):
            if cell:
                nx, ny = c + ox, r + oy
                if nx < 0 or nx >= COLS or ny >= ROWS:
                    return False
                if ny >= 0 and locked.get((nx, ny), EMPTY) != EMPTY:
                    return False
    return True


def _ghost_y(piece: Piece, locked: dict) -> int:
    """Return the lowest y the piece can reach (for ghost rendering)."""
    gy = piece.y
    while _valid(piece.shape, locked, piece.x, gy + 1):
        gy += 1
    return gy


def _lock(piece: Piece, locked: dict) -> None:
    """Write all cells of *piece* into *locked*."""
    for r, row in enumerate(piece.shape):
        for c, cell in enumerate(row):
            if cell:
                locked[(c + piece.x, r + piece.y)] = piece.color


def _find_full_rows(locked: dict) -> list[int]:
    return [y for y in range(ROWS) if all((x, y) in locked for x in range(COLS))]


def _clear_rows(locked: dict, rows: list[int]) -> None:
    """Remove completed rows and drop everything above down."""
    for y in rows:
        for x in range(COLS):
            locked.pop((x, y), None)
    # Sort remaining keys top>bottom so we shift correctly
    for (x, y) in sorted(locked.keys(), key=lambda k: k[1]):
        shift = sum(1 for ry in rows if y < ry)
        if shift:
            locked[(x, y + shift)] = locked.pop((x, y))


# ---------------------------------------------------------------------------
# Rendering helpers
# ---------------------------------------------------------------------------

def _draw_block(surface: pygame.Surface,
                px: int, py: int, color: tuple,
                size: int = BLOCK_SIZE, alpha: int = 255) -> None:
    """Draw a single gradient block at pixel position (px, py)."""
    w = h = size - 2
    surf = RenderManager.get_block_surface(size, color)
    if alpha < 255:
        surf = surf.copy()
        surf.set_alpha(alpha)
    surface.blit(surf, (px, py))


def _draw_mini_piece(surface: pygame.Surface,
                     shape: list, color: tuple,
                     panel_x: int, panel_y: int,
                     panel_w: int, panel_h: int,
                     block_size: int = 20) -> None:
    """Draw a piece centred inside a panel rectangle."""
    sw = len(shape[0]) * block_size
    sh = len(shape)    * block_size
    ox = panel_x + (panel_w - sw) // 2
    oy = panel_y + (panel_h - sh) // 2
    for r, row in enumerate(shape):
        for c, cell in enumerate(row):
            if cell:
                _draw_block(surface,
                            ox + c * block_size,
                            oy + r * block_size,
                            color, block_size)


# ---------------------------------------------------------------------------
# TetrisScene
# ---------------------------------------------------------------------------

class TetrisScene(BaseScene):
    """
    Full Tetris game scene.

    State is initialised in on_enter() so restarting reuses the same
    scene object cleanly (engine.replace_scene is NOT needed for restart).
    """

    GAME_ID = "tetris"

    def __init__(self, engine):
        super().__init__(engine)
        pygame.key.set_repeat(170, 65)   # DAS / ARR

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def on_enter(self) -> None:
        self._reset()

    def on_exit(self) -> None:
        pygame.key.set_repeat(0, 0)   # disable key repeat for other scenes

    # ------------------------------------------------------------------
    # Core game reset
    # ------------------------------------------------------------------

    def _reset(self) -> None:
        self._locked:  dict  = {}
        self._current: Piece = Piece()
        self._next:    Piece = Piece()
        self._held:    Piece | None = None
        self._can_hold: bool = True

        self._score  = 0
        self._level  = 1
        self._lines  = 0
        self._best   = self.stats.best_score(self.GAME_ID) if self.stats else 0

        # Cumulative stats for this session
        self._tetris_count = 0   # 4-line clears
        self._session_lines = 0

        # Timing
        self._fall_timer   = 0.0
        self._fall_speed   = BASE_FALL
        self._session_time = 0.0

        # Flash state
        self._flash_rows:  list[int] = []
        self._flash_timer: float     = 0.0
        self._flashing:    bool      = False

        # Game state
        self._paused    = False
        self._game_over = False
        self._new_best  = False

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def update(self, dt: float) -> None:
        if self._paused or self._game_over:
            return

        self._session_time += dt

        # --- Flash countdown ---
        if self._flashing:
            self._flash_timer -= dt
            if self._flash_timer <= 0:
                _clear_rows(self._locked, self._flash_rows)
                self._flash_rows  = []
                self._flashing    = False
                # Spawn next piece
                self._current = self._next
                self._next    = Piece()
                self._can_hold = True
                if not _valid(self._current.shape, self._locked,
                              self._current.x, self._current.y):
                    self._trigger_game_over()
            return   # freeze piece movement during flash

        # --- Gravity ---
        self._fall_timer += dt
        if self._fall_timer >= self._fall_speed:
            self._fall_timer = 0.0
            if _valid(self._current.shape, self._locked,
                      self._current.x, self._current.y + 1):
                self._current.y += 1
            else:
                self._place_piece()

    # ------------------------------------------------------------------
    # Draw
    # ------------------------------------------------------------------

    def draw(self, screen: pygame.Surface) -> None:
        w, h = screen.get_size()
        screen.blit(RenderManager.get_background(w, h), (0, 0))

        self._draw_board(screen)
        self._draw_hold_panel(screen)
        self._draw_sidebar(screen)
        draw_footer_hint(screen,
            "<> Move  |  ^/X Rotate CW  |  Z CCW  |  Space Hard Drop  |  C Hold  |  P Pause  |  Q Menu",
            y_offset=22)

        if self._paused:
            self._draw_pause(screen)
        elif self._game_over:
            self._draw_game_over(screen)

    # ------------------------------------------------------------------
    # Input
    # ------------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type != pygame.KEYDOWN:
            return

        key = event.key

        # Always available
        if key in (pygame.K_q, pygame.K_ESCAPE):
            self.engine.pop_scene()
            return
        if key == pygame.K_p and not self._game_over:
            self._paused = not self._paused
            return
        if key == pygame.K_r:
            self._reset()
            return

        # Game-over only
        if self._game_over:
            return

        # Pause gate
        if self._paused or self._flashing:
            return

        locked = self._locked
        cur    = self._current

        if key in (pygame.K_LEFT, pygame.K_a):
            if _valid(cur.shape, locked, cur.x - 1, cur.y):
                cur.x -= 1

        elif key in (pygame.K_RIGHT, pygame.K_d):
            if _valid(cur.shape, locked, cur.x + 1, cur.y):
                cur.x += 1

        elif key in (pygame.K_DOWN, pygame.K_s):
            if _valid(cur.shape, locked, cur.x, cur.y + 1):
                cur.y += 1
                self._fall_timer = 0.0   # reset gravity on soft drop

        elif key in (pygame.K_UP, pygame.K_x):
            self._try_rotate(cw=True)

        elif key == pygame.K_z:
            self._try_rotate(cw=False)

        elif key == pygame.K_SPACE:
            self._hard_drop()

        elif key in (pygame.K_c, pygame.K_LSHIFT, pygame.K_RSHIFT):
            self._hold()

    # ------------------------------------------------------------------
    # Game mechanics
    # ------------------------------------------------------------------

    def _try_rotate(self, cw: bool) -> None:
        cur = self._current
        new_shape = _rotate_cw(cur.shape) if cw else _rotate_ccw(cur.shape)
        # Try base position first, then wall kicks
        for dx in [0] + WALL_KICKS:
            if _valid(new_shape, self._locked, cur.x + dx, cur.y):
                cur.shape = new_shape
                cur.x    += dx
                return

    def _hard_drop(self) -> None:
        cur = self._current
        while _valid(cur.shape, self._locked, cur.x, cur.y + 1):
            cur.y += 1
        # Bonus: 2 pts per row dropped
        drop_bonus = _ghost_y(cur, self._locked) - cur.y
        self._score += drop_bonus * 2
        self._place_piece()

    def _hold(self) -> None:
        if not self._can_hold:
            return
        self._can_hold = False
        if self._held is None:
            self._held    = Piece(self._current._shape_idx)
            self._current = self._next
            self._next    = Piece()
        else:
            old_idx        = self._held._shape_idx
            self._held     = Piece(self._current._shape_idx)
            self._current  = Piece(old_idx)

    def _place_piece(self) -> None:
        """Lock the current piece, check for clears, spawn next."""
        _lock(self._current, self._locked)
        full = _find_full_rows(self._locked)

        if full:
            n = len(full)
            base = SCORE_TABLE.get(n, n * 100)
            self._score += base * self._level
            self._lines += n
            self._session_lines += n
            if n == 4:
                self._tetris_count += 1
            # Level up every 10 lines
            new_level = self._lines // 10 + 1
            if new_level > self._level:
                self._level      = new_level
                self._fall_speed = max(MIN_SPEED, BASE_FALL - (self._level - 1) * SPEED_DELTA)
            # Start flash
            self._flash_rows  = full
            self._flash_timer = FLASH_DURATION
            self._flashing    = True
        else:
            # No clear - spawn immediately
            self._current = self._next
            self._next    = Piece()
            self._can_hold = True
            if not _valid(self._current.shape, self._locked,
                          self._current.x, self._current.y):
                self._trigger_game_over()

    def _trigger_game_over(self) -> None:
        self._game_over = True
        # Check for new best
        if self.stats:
            self._new_best = self._score > self.stats.best_score(self.GAME_ID)
            result = self.stats.record_game(
                self.GAME_ID,
                score    = self._score,
                won      = False,
                duration = self._session_time,
                extra    = {
                    "lines":         self._session_lines,
                    "level":         self._level,
                    "tetris_clears": self._tetris_count,
                    "total_lines":   self.stats.extra_stat(self.GAME_ID, "lines")
                                     + self._session_lines,
                },
            )
        if self.achievements:
            snap = {
                "game_id":           self.GAME_ID,
                "score":             self._score,
                "games_played":      self.stats.games_played(self.GAME_ID) if self.stats else 1,
                "lines":             self._session_lines,
                "tetris_clears":     self._tetris_count,
                "total_lines":       self.stats.extra_stat(self.GAME_ID, "lines") if self.stats else 0,
                "total_games_played": self.stats.global_summary()["total_games"] if self.stats else 1,
                "total_wins":        self.stats.global_summary()["total_wins"] if self.stats else 0,
            }
            self.achievements.check_and_unlock(snap)

    # ------------------------------------------------------------------
    # Draw helpers
    # ------------------------------------------------------------------

    def _draw_board(self, screen: pygame.Surface) -> None:
        # Card border
        draw_card(screen, (PLAY_X - 8, PLAY_Y - 8, PLAY_W + 16, PLAY_H + 16))
        pygame.draw.rect(screen, Theme.CARD_BORDER,
                         (PLAY_X, PLAY_Y, PLAY_W, PLAY_H), 1)

        locked  = self._locked
        cur     = self._current
        ghost_y = _ghost_y(cur, locked) if not self._game_over else cur.y

        # Build display grid: locked cells
        for (x, y), color in locked.items():
            if 0 <= y < ROWS:
                px = PLAY_X + x * BLOCK_SIZE
                py = PLAY_Y + y * BLOCK_SIZE
                # Flash: override color with white
                if self._flashing and y in self._flash_rows:
                    flash_ratio = self._flash_timer / FLASH_DURATION
                    white = (255, 255, 255)
                    fc = tuple(int(color[i] + (255 - color[i]) * flash_ratio)
                               for i in range(3))
                    _draw_block(screen, px, py, fc)
                else:
                    _draw_block(screen, px, py, color)
            # Grid dots for empty cells
        for ry in range(ROWS):
            for cx in range(COLS):
                if locked.get((cx, ry), EMPTY) == EMPTY:
                    px = PLAY_X + cx * BLOCK_SIZE + BLOCK_SIZE // 2
                    py = PLAY_Y + ry * BLOCK_SIZE + BLOCK_SIZE // 2
                    pygame.draw.circle(screen, (38, 44, 58), (px, py), 1)

        # Ghost piece
        if not self._flashing and not self._game_over:
            for r, row in enumerate(cur.shape):
                for c, cell in enumerate(row):
                    if cell:
                        gx = PLAY_X + (c + cur.x) * BLOCK_SIZE
                        gy = PLAY_Y + (r + ghost_y) * BLOCK_SIZE
                        if gy >= PLAY_Y:
                            ghost_surf = pygame.Surface((BLOCK_SIZE - 2, BLOCK_SIZE - 2),
                                                        pygame.SRCALPHA)
                            pygame.draw.rect(ghost_surf,
                                             (*cur.color[:3], 55),
                                             (0, 0, BLOCK_SIZE - 2, BLOCK_SIZE - 2),
                                             border_radius=3)
                            pygame.draw.rect(ghost_surf,
                                             (*cur.color[:3], 130),
                                             (0, 0, BLOCK_SIZE - 2, BLOCK_SIZE - 2),
                                             1, border_radius=3)
                            screen.blit(ghost_surf, (gx, gy))

        # Active piece
        if not self._flashing:
            for r, row in enumerate(cur.shape):
                for c, cell in enumerate(row):
                    if cell:
                        px = PLAY_X + (c + cur.x) * BLOCK_SIZE
                        py = PLAY_Y + (r + cur.y) * BLOCK_SIZE
                        if py >= PLAY_Y:
                            _draw_block(screen, px, py, cur.color)

    def _draw_hold_panel(self, screen: pygame.Surface) -> None:
        panel_h = 110
        draw_card(screen, (HOLD_X, HOLD_Y, HOLD_W, panel_h))
        draw_panel_title(screen, HOLD_X + 14, HOLD_Y + 12, "HOLD")

        # Dim if can't hold
        alpha = 255 if self._can_hold else 90

        if self._held:
            s = pygame.Surface((HOLD_W, panel_h - 30), pygame.SRCALPHA)
            _draw_mini_piece(s, self._held.shape, self._held.color,
                             0, 0, HOLD_W, panel_h - 30, block_size=18)
            if alpha < 255:
                s.set_alpha(alpha)
            screen.blit(s, (HOLD_X, HOLD_Y + 30))

        # "C / SHIFT" hint
        hint_font = FontCache.get("Segoe UI", 10)
        draw_text(screen, "C / Shift", hint_font, Theme.TEXT_MUTED,
                  HOLD_X + HOLD_W // 2, HOLD_Y + panel_h - 10, align="center")

    def _draw_sidebar(self, screen: pygame.Surface) -> None:
        cy = SIDE_Y

        # NEXT piece panel
        next_h = 118
        draw_card(screen, (SIDE_X, cy, SIDE_W, next_h))
        draw_panel_title(screen, SIDE_X + 14, cy + 12, "NEXT")
        _draw_mini_piece(screen, self._next.shape, self._next.color,
                         SIDE_X, cy + 28, SIDE_W, next_h - 32)
        cy += next_h + 14

        # Score / Level / Lines
        stats_data = [
            ("SCORE", f"{self._score:,}", Theme.ACCENT_GREEN),
            ("LEVEL", str(self._level),  Theme.ACCENT_CYAN),
            ("LINES", str(self._lines),  Theme.ACCENT_ORANGE),
        ]
        for label, value, color in stats_data:
            draw_card(screen, (SIDE_X, cy, SIDE_W, 58))
            label_font = FontCache.get("Segoe UI", 10, bold=True)
            value_font = FontCache.get("Segoe UI", 24, bold=True)
            draw_text(screen, label, label_font, Theme.TEXT_MUTED, SIDE_X + 14, cy + 10)
            draw_text(screen, value, value_font, color, SIDE_X + 14, cy + 26)
            cy += 66

        # Best score
        draw_card(screen, (SIDE_X, cy, SIDE_W, 46))
        best_label = FontCache.get("Segoe UI", 10, bold=True)
        best_val   = FontCache.get("Segoe UI", 16, bold=True)
        best_score = max(self._score, self.stats.best_score(self.GAME_ID) if self.stats else 0)
        draw_text(screen, "BEST", best_label, Theme.TEXT_MUTED, SIDE_X + 14, cy + 8)
        draw_text(screen, f"{best_score:,}", best_val, Theme.ACCENT_YELLOW,
                  SIDE_X + 14, cy + 22)
        cy += 54

        # Controls card
        ctrl_h = 160
        draw_card(screen, (SIDE_X, cy, SIDE_W, ctrl_h))
        draw_panel_title(screen, SIDE_X + 14, cy + 12, "CONTROLS")
        controls = [
            ("<>",    "Move"),
            ("^ / X", "Rotate CW"),
            ("Z",      "Rotate CCW"),
            ("Space",  "Hard Drop"),
            ("C",      "Hold"),
            ("P",      "Pause"),
        ]
        cf = FontCache.get("Segoe UI", 10)
        for i, (key, action) in enumerate(controls):
            ky = cy + 32 + i * 21
            kw = cf.size(key)[0] + 10
            pygame.draw.rect(screen, Theme.BG_TERTIARY,
                             (SIDE_X + 14, ky, kw, 16), border_radius=3)
            draw_text(screen, key, cf, Theme.TEXT_PRIMARY, SIDE_X + 19, ky + 2)
            draw_text(screen, action, cf, Theme.TEXT_SECONDARY,
                      SIDE_X + 14 + kw + 6, ky + 2)

    def _draw_pause(self, screen: pygame.Surface) -> None:
        from engine.ui import draw_pause_card
        draw_pause_card(screen)

    def _draw_game_over(self, screen: pygame.Surface) -> None:
        w, h = screen.get_size()
        draw_overlay(screen, 210)

        card_w, card_h = 440, 280
        cx = (w - card_w) // 2
        cy = (h - card_h) // 2
        draw_card(screen, (cx, cy, card_w, card_h))

        # Title
        title_font = FontCache.get("Segoe UI", 44, bold=True)
        draw_text(screen, "GAME OVER", title_font, Theme.ACCENT_RED,
                  w // 2, cy + 52, align="center")

        # Score
        score_font = FontCache.get("Segoe UI", 26, bold=True)
        draw_text(screen, f"{self._score:,}", score_font, Theme.TEXT_PRIMARY,
                  w // 2, cy + 108, align="center")

        # New best banner
        if self._new_best:
            best_font = FontCache.get("Segoe UI", 13, bold=True)
            draw_text(screen, "** NEW BEST **", best_font, Theme.ACCENT_YELLOW,
                      w // 2, cy + 140, align="center")

        # Stats row
        sf = FontCache.get("Segoe UI", 13)
        draw_text(screen,
                  f"Level {self._level}   |   {self._lines} lines   |   {self._tetris_count}x Tetris",
                  sf, Theme.TEXT_SECONDARY, w // 2, cy + 168, align="center")

        # Hint
        hint_font = FontCache.get("Segoe UI", 13)
        draw_text(screen, "R  Restart   |   Q  Menu",
                  hint_font, Theme.TEXT_MUTED, w // 2, cy + 228, align="center")


# ---------------------------------------------------------------------------
# Plugin metadata - read by MainMenuScene's GAME_REGISTRY and plugin loader
# ---------------------------------------------------------------------------

GAME_META = {
    "id":          "tetris",
    "name":        "Tetris",
    "desc":        "Stack and clear lines",
    "color":       lambda: Theme.ACCENT_CYAN,
    "scene_class": TetrisScene,
}
