"""games/sudoku.py — SudokuScene (Phase 10)

Features
--------
  3 difficulties  (Easy 45 givens / Medium 34 / Hard 25)
  Backtracking puzzle generator with uniqueness guarantee
  Cell highlighting (same row / col / box / value)
  Pencil mode — candidate numbers per cell
  Mistake counter (max 3 → game over)
  Timer (counts up)
  Auto-clear pencil marks when a digit is placed
  N key — new puzzle  |  H key — hint (reveal one cell)
  Stats + achievement integration on completion
"""

import random
import time
import pygame

from engine import (
    BaseScene, Theme, RenderManager, FontCache,
    draw_text, draw_card, draw_overlay, draw_footer_hint,
)
from engine.engine import SCREEN_WIDTH as W, SCREEN_HEIGHT as H

# ─── Layout constants ────────────────────────────────────────────────
CELL      = 62
GRID_SZ   = CELL * 9
GRID_X    = (W - GRID_SZ) // 2
GRID_Y    = (H - GRID_SZ) // 2 + 12

DIFFICULTIES = [
    {"name": "Easy",   "givens": 45},
    {"name": "Medium", "givens": 34},
    {"name": "Hard",   "givens": 25},
]

MAX_MISTAKES = 3

# ─── Pure puzzle logic ────────────────────────────────────────────────

def _valid(board, r, c, n):
    if n in board[r]: return False
    if any(board[rr][c] == n for rr in range(9)): return False
    br, bc = (r // 3) * 3, (c // 3) * 3
    for dr in range(3):
        for dc in range(3):
            if board[br+dr][bc+dc] == n: return False
    return True


def _solve(board, shuffle=False):
    """Backtracking solver. Returns True if solved (board modified in place)."""
    for r in range(9):
        for c in range(9):
            if board[r][c] == 0:
                nums = list(range(1, 10))
                if shuffle: random.shuffle(nums)
                for n in nums:
                    if _valid(board, r, c, n):
                        board[r][c] = n
                        if _solve(board, shuffle): return True
                        board[r][c] = 0
                return False
    return True


def _count_solutions(board, limit=2):
    """Count solutions up to limit (stops early)."""
    count = [0]
    def _bt(b):
        if count[0] >= limit: return
        for r in range(9):
            for c in range(9):
                if b[r][c] == 0:
                    for n in range(1, 10):
                        if _valid(b, r, c, n):
                            b[r][c] = n
                            _bt(b)
                            b[r][c] = 0
                    return
        count[0] += 1
    _bt([row[:] for row in board])
    return count[0]


def generate_puzzle(n_givens: int):
    """Generate a (puzzle, solution) pair with a unique solution."""
    # 1. Build a complete solved board
    solution = [[0]*9 for _ in range(9)]
    _solve(solution, shuffle=True)

    # 2. Remove cells one by one, checking uniqueness
    puzzle = [row[:] for row in solution]
    cells = [(r, c) for r in range(9) for c in range(9)]
    random.shuffle(cells)

    removed = 0
    target  = 81 - n_givens
    for r, c in cells:
        if removed >= target:
            break
        old = puzzle[r][c]
        puzzle[r][c] = 0
        if _count_solutions(puzzle) == 1:
            removed += 1
        else:
            puzzle[r][c] = old  # restore if not unique

    return puzzle, solution


# ─── SudokuScene ─────────────────────────────────────────────────────

class SudokuScene(BaseScene):
    GAME_ID = "sudoku"

    # ── Lifecycle ──────────────────────────────────────────────────

    def on_enter(self):
        self._phase    = "select"
        self._sel      = 0
        self._anim_t   = 0.0

    def _start(self, diff_i: int):
        self._diff_i   = diff_i
        self._diff     = DIFFICULTIES[diff_i]
        self._loading  = True   # show spinner one frame
        self._phase    = "loading"

    def _generate_and_start(self):
        puzzle, solution = generate_puzzle(self._diff["givens"])
        self._puzzle    = puzzle          # original givens (never changes)
        self._solution  = solution
        self._board     = [row[:] for row in puzzle]   # player's working copy
        self._pencil    = [[set() for _ in range(9)] for _ in range(9)]
        self._sel_r     = 4
        self._sel_c     = 4
        self._mistakes  = 0
        self._hints     = 0
        self._pencil_mode = False
        self._start_time  = time.monotonic()
        self._elapsed     = 0.0
        self._paused      = False
        self._won         = False
        self._lost        = False
        self._session_t   = 0.0
        self._flash: list[tuple] = []   # [(r,c,color,ttl)]
        self._phase = "game"

    # ── Update ────────────────────────────────────────────────────

    def update(self, dt: float):
        self._anim_t += dt

        if self._phase == "loading":
            self._generate_and_start()
            return

        if self._phase != "game":
            return

        if self._won or self._lost or self._paused:
            return

        self._session_t += dt
        self._elapsed = time.monotonic() - self._start_time

        # Tick flash animations
        self._flash = [(r,c,col,ttl-dt) for r,c,col,ttl in self._flash if ttl > 0]

    # ── Draw ──────────────────────────────────────────────────────

    def draw(self, screen: pygame.Surface):
        screen.blit(RenderManager.get_background(W, H), (0,0))
        if self._phase == "select":
            self._draw_select(screen)
        elif self._phase == "loading":
            self._draw_loading(screen)
        elif self._phase == "game":
            self._draw_game(screen)

    def _draw_select(self, screen):
        draw_text(screen, "SUDOKU",
                  FontCache.get("Segoe UI", 60, bold=True), Theme.TEXT_PRIMARY,
                  W//2, 100, align="center")
        draw_text(screen, "Fill the 9x9 grid - each row, column and box must contain 1-9",
                  FontCache.get("Segoe UI", 14), Theme.TEXT_MUTED,
                  W//2, 158, align="center")
        bf = FontCache.get("Segoe UI", 24, bold=True)
        for i, d in enumerate(DIFFICULTIES):
            x = (W - 340)//2
            y = 220 + i * 88
            selected = (i == self._sel)
            col = Theme.ACCENT_PURPLE if selected else Theme.CARD_BG
            border = Theme.ACCENT_PURPLE if selected else Theme.CARD_BORDER
            pygame.draw.rect(screen, col, (x, y, 340, 68), border_radius=14)
            pygame.draw.rect(screen, border, (x, y, 340, 68), 2, border_radius=14)
            # Pulse on selected
            if selected:
                pulse = abs(pygame.math.Vector2(1,0).rotate(self._anim_t*180).x) * 0.3 + 0.7
                pygame.draw.rect(screen, (*Theme.ACCENT_PURPLE[:3], int(60*pulse)),
                                 (x-3, y-3, 346, 74), 2, border_radius=16)
            lc = Theme.TEXT_PRIMARY if selected else Theme.TEXT_SECONDARY
            draw_text(screen, d["name"], bf, lc, W//2, y+34, align="center")
            gf = FontCache.get("Segoe UI", 11)
            draw_text(screen, f"{d['givens']} givens", gf, Theme.TEXT_MUTED,
                      W//2, y+52, align="center")
        draw_footer_hint(screen, "Up/Dn Select  |  Enter Start  |  Q Menu", y_offset=26)

    def _draw_loading(self, screen):
        draw_text(screen, "Generating puzzle...",
                  FontCache.get("Segoe UI", 28, bold=True), Theme.TEXT_MUTED,
                  W//2, H//2, align="center")

    def _draw_game(self, screen):
        self._draw_grid(screen)
        self._draw_hud(screen)
        self._draw_numpad(screen)
        if self._won:
            self._draw_win(screen)
        elif self._lost:
            self._draw_lose(screen)
        elif self._paused:
            self._draw_pause(screen)
        else:
            draw_footer_hint(screen,
                "Arrows Move  |  1-9 Place  |  Del Clear  |  P Pencil  |  H Hint  |  Q Menu",
                y_offset=26)

    def _draw_grid(self, screen: pygame.Surface):
        sr, sc = self._sel_r, self._sel_c
        sv = self._board[sr][sc]

        # Build highlight sets
        highlight_cells = set()
        same_val_cells  = set()
        for r in range(9):
            for c in range(9):
                # Same row/col/box as selection
                if r == sr or c == sc or (r//3 == sr//3 and c//3 == sc//3):
                    highlight_cells.add((r,c))
                # Same value (non-zero)
                if sv and self._board[r][c] == sv:
                    same_val_cells.add((r,c))

        # Flash lookup
        flash_map = {}
        for r, c, col, _ in self._flash:
            flash_map[(r,c)] = col

        for r in range(9):
            for c in range(9):
                x = GRID_X + c * CELL
                y = GRID_Y + r * CELL
                rect = (x, y, CELL, CELL)

                # Cell background
                if (r, c) in flash_map:
                    bg = flash_map[(r,c)]
                elif (r, c) == (sr, sc):
                    bg = Theme.ACCENT_PURPLE
                elif (r, c) in same_val_cells:
                    bg = (80, 55, 110)
                elif (r, c) in highlight_cells:
                    bg = (38, 42, 60)
                else:
                    bg = Theme.CARD_BG

                pygame.draw.rect(screen, bg, rect)

                val = self._board[r][c]
                is_given = (self._puzzle[r][c] != 0)
                is_error = (val != 0 and not is_given and val != self._solution[r][c])

                if val:
                    fc = Theme.TEXT_MUTED if is_given else (Theme.ACCENT_RED if is_error else Theme.ACCENT_CYAN)
                    fw = not is_given
                    nf = FontCache.get("Segoe UI", 34, bold=True)
                    draw_text(screen, str(val), nf, fc,
                              x + CELL//2, y + CELL//2 - 4, align="center")
                elif self._pencil[r][c] and not (self._won or self._lost):
                    pf = FontCache.get("Segoe UI", 11)
                    for n in self._pencil[r][c]:
                        pr = (n-1) // 3
                        pc2 = (n-1) % 3
                        px = x + 4 + pc2 * (CELL//3) + CELL//9
                        py = y + 3 + pr * (CELL//3) + CELL//9
                        draw_text(screen, str(n), pf, (100,110,140), px, py)

        # Grid lines
        for i in range(10):
            thick = 3 if i % 3 == 0 else 1
            col   = Theme.TEXT_SECONDARY if i % 3 == 0 else Theme.CARD_BORDER
            # Vertical
            pygame.draw.line(screen, col,
                             (GRID_X + i*CELL, GRID_Y),
                             (GRID_X + i*CELL, GRID_Y + GRID_SZ), thick)
            # Horizontal
            pygame.draw.line(screen, col,
                             (GRID_X,          GRID_Y + i*CELL),
                             (GRID_X + GRID_SZ, GRID_Y + i*CELL), thick)

    def _draw_hud(self, screen):
        # Top bar
        hf  = FontCache.get("Segoe UI", 14, bold=True)
        sf  = FontCache.get("Segoe UI", 11)
        lf  = FontCache.get("Segoe UI", 22, bold=True)

        # Title + difficulty
        draw_text(screen, "SUDOKU", FontCache.get("Segoe UI", 20, bold=True),
                  Theme.TEXT_MUTED, GRID_X, GRID_Y - 38)
        draw_text(screen, self._diff["name"],
                  FontCache.get("Segoe UI", 14), Theme.ACCENT_PURPLE,
                  GRID_X + 90, GRID_Y - 36)

        # Timer
        elapsed = int(self._elapsed)
        tstr = f"{elapsed//60:02d}:{elapsed%60:02d}"
        draw_text(screen, tstr, lf, Theme.ACCENT_CYAN,
                  GRID_X + GRID_SZ, GRID_Y - 34, align="right")

        # Mistakes
        mx = GRID_X + GRID_SZ - 4
        for i in range(MAX_MISTAKES):
            col = Theme.ACCENT_RED if i < self._mistakes else Theme.CARD_BORDER
            pygame.draw.circle(screen, col,
                               (GRID_X + GRID_SZ//2 - (MAX_MISTAKES-1)*14 + i*28,
                                GRID_Y - 16), 7)

        # Pencil indicator
        if self._pencil_mode:
            draw_text(screen, "PENCIL ON", FontCache.get("Segoe UI",11,bold=True),
                      Theme.ACCENT_YELLOW, GRID_X, GRID_Y + GRID_SZ + 10)

    def _draw_numpad(self, screen):
        """Vertical number pad to the right of the grid."""
        px = GRID_X + GRID_SZ + 28
        py = GRID_Y + 40
        bw, bh = 52, 52
        gap    = 10
        nf = FontCache.get("Segoe UI", 24, bold=True)
        sf = FontCache.get("Segoe UI", 10)

        draw_text(screen, "NUMPAD", FontCache.get("Segoe UI",10,bold=True),
                  Theme.TEXT_MUTED, px + bw//2, py - 18, align="center")

        # Count how many of each digit remain (max 9)
        placed = [0] * 10
        for r in range(9):
            for c in range(9):
                v = self._board[r][c]
                if v: placed[v] += 1

        for n in range(1, 10):
            by = py + (n-1) * (bh + gap)
            remaining = 9 - placed[n]
            done = remaining <= 0
            bg = (25, 28, 42) if done else Theme.CARD_BG
            border = Theme.CARD_BORDER if done else Theme.ACCENT_PURPLE
            pygame.draw.rect(screen, bg, (px, by, bw, bh), border_radius=8)
            pygame.draw.rect(screen, border, (px, by, bw, bh), 1, border_radius=8)
            nc = Theme.TEXT_MUTED if done else Theme.TEXT_PRIMARY
            draw_text(screen, str(n), nf, nc, px + bw//2, by + bh//2 - 5, align="center")
            if not done:
                draw_text(screen, f"x{remaining}", sf, Theme.TEXT_MUTED,
                          px + bw//2, by + bh - 12, align="center")

        # Hints remaining indicator
        draw_text(screen, f"Hints: {max(0, 3 - self._hints)}",
                  FontCache.get("Segoe UI",11), Theme.ACCENT_YELLOW,
                  px + bw//2, py + 9*(bh+gap) + 8, align="center")

    def _draw_win(self, screen):
        draw_overlay(screen, 180)
        cw, ch = 440, 240
        cx, cy = (W-cw)//2, (H-ch)//2
        draw_card(screen, (cx, cy, cw, ch))
        pygame.draw.rect(screen, Theme.ACCENT_GREEN, (cx, cy, cw, 4), border_radius=4)
        draw_text(screen, "PUZZLE SOLVED!", FontCache.get("Segoe UI",36,bold=True),
                  Theme.ACCENT_GREEN, W//2, cy+50, align="center")
        elapsed = int(self._elapsed)
        draw_text(screen, f"Time: {elapsed//60:02d}:{elapsed%60:02d}",
                  FontCache.get("Segoe UI",20), Theme.TEXT_PRIMARY,
                  W//2, cy+100, align="center")
        draw_text(screen, f"Mistakes: {self._mistakes}  |  Hints: {self._hints}",
                  FontCache.get("Segoe UI",15), Theme.TEXT_SECONDARY,
                  W//2, cy+132, align="center")
        draw_text(screen, "N New Game  |  Q Menu",
                  FontCache.get("Segoe UI",13), Theme.TEXT_MUTED,
                  W//2, cy+178, align="center")

    def _draw_lose(self, screen):
        draw_overlay(screen, 180)
        cw, ch = 420, 210
        cx, cy = (W-cw)//2, (H-ch)//2
        draw_card(screen, (cx, cy, cw, ch))
        pygame.draw.rect(screen, Theme.ACCENT_RED, (cx, cy, cw, 4), border_radius=4)
        draw_text(screen, "TOO MANY MISTAKES", FontCache.get("Segoe UI",30,bold=True),
                  Theme.ACCENT_RED, W//2, cy+48, align="center")
        draw_text(screen, f"{MAX_MISTAKES} errors — better luck next time!",
                  FontCache.get("Segoe UI",15), Theme.TEXT_SECONDARY,
                  W//2, cy+95, align="center")
        draw_text(screen, "N New Game  |  Q Menu",
                  FontCache.get("Segoe UI",13), Theme.TEXT_MUTED,
                  W//2, cy+148, align="center")

    def _draw_pause(self, screen):
        draw_overlay(screen, 150)
        draw_text(screen, "PAUSED", FontCache.get("Segoe UI",48,bold=True),
                  Theme.TEXT_PRIMARY, W//2, H//2 - 20, align="center")
        draw_text(screen, "P to resume", FontCache.get("Segoe UI",16),
                  Theme.TEXT_MUTED, W//2, H//2 + 32, align="center")

    # ── Input ─────────────────────────────────────────────────────

    def handle_event(self, event: pygame.event.Event):
        if event.type != pygame.KEYDOWN:
            return
        k = event.key

        if self._phase == "select":
            n = len(DIFFICULTIES)
            if k == pygame.K_UP:    self._sel = (self._sel - 1) % n
            if k == pygame.K_DOWN:  self._sel = (self._sel + 1) % n
            if k in (pygame.K_RETURN, pygame.K_SPACE):
                self._start(self._sel)
            if k in (pygame.K_q, pygame.K_ESCAPE):
                self.engine.pop_scene()
            return

        if self._phase != "game":
            return

        if k in (pygame.K_q, pygame.K_ESCAPE):
            self._save_stats()
            self.engine.pop_scene()
            return

        if k == pygame.K_n:
            self._save_stats()
            self._phase = "select"
            return

        if self._won or self._lost:
            return

        if k == pygame.K_p:
            self._paused = not self._paused
            if self._paused:
                self._start_time -= (time.monotonic() - self._start_time - self._elapsed)
            return

        if self._paused:
            return

        # Navigation
        if k == pygame.K_UP:    self._sel_r = max(0, self._sel_r - 1)
        if k == pygame.K_DOWN:  self._sel_r = min(8, self._sel_r + 1)
        if k == pygame.K_LEFT:  self._sel_c = max(0, self._sel_c - 1)
        if k == pygame.K_RIGHT: self._sel_c = min(8, self._sel_c + 1)

        # Pencil toggle
        if k == pygame.K_m or k == pygame.K_BACKQUOTE:
            self._pencil_mode = not self._pencil_mode
            return

        # Hint
        if k == pygame.K_h and self._hints < 3:
            self._give_hint()
            return

        # Digit entry
        digit = None
        if pygame.K_1 <= k <= pygame.K_9:
            digit = k - pygame.K_0
        elif pygame.K_KP1 <= k <= pygame.K_KP9:
            digit = k - pygame.K_KP0

        r, c = self._sel_r, self._sel_c
        if digit is not None:
            if self._puzzle[r][c] != 0:
                return  # given cell, immutable
            if self._pencil_mode:
                if digit in self._pencil[r][c]:
                    self._pencil[r][c].discard(digit)
                else:
                    self._pencil[r][c].add(digit)
            else:
                self._place_digit(r, c, digit)

        # Clear
        if k in (pygame.K_DELETE, pygame.K_BACKSPACE, pygame.K_0, pygame.K_KP0):
            if self._puzzle[r][c] == 0:
                self._board[r][c] = 0
                self._pencil[r][c].clear()

    def _place_digit(self, r, c, digit):
        correct = self._solution[r][c]
        self._board[r][c] = digit
        self._pencil[r][c].clear()

        # Clear pencil marks in same row/col/box
        for i in range(9):
            self._pencil[r][i].discard(digit)
            self._pencil[i][c].discard(digit)
        br, bc = (r//3)*3, (c//3)*3
        for dr in range(3):
            for dc in range(3):
                self._pencil[br+dr][bc+dc].discard(digit)

        if digit == correct:
            # Flash green
            self._flash.append((r, c, (30, 90, 50), 0.35))
            # Check win
            if all(self._board[rr][cc] == self._solution[rr][cc]
                   for rr in range(9) for cc in range(9)):
                self._won = True
                self._save_stats(won=True)
        else:
            # Wrong answer
            self._mistakes += 1
            self._flash.append((r, c, (100, 25, 25), 0.5))
            if self._mistakes >= MAX_MISTAKES:
                self._lost = True
                self._save_stats(won=False)

    def _give_hint(self):
        """Reveal one empty incorrect cell."""
        candidates = [
            (r, c) for r in range(9) for c in range(9)
            if self._board[r][c] == 0 and self._puzzle[r][c] == 0
        ]
        if not candidates:
            return
        r, c = random.choice(candidates)
        self._board[r][c] = self._solution[r][c]
        self._pencil[r][c].clear()
        self._hints += 1
        self._flash.append((r, c, (60, 80, 25), 0.5))
        # Check win after hint
        if all(self._board[rr][cc] == self._solution[rr][cc]
               for rr in range(9) for cc in range(9)):
            self._won = True
            self._save_stats(won=True)

    def _save_stats(self, won: bool = False):
        if not self.stats:
            return
        score = max(0, 1000 - self._mistakes * 100 - self._hints * 50
                    - int(self._elapsed))
        self.stats.record_game(
            self.GAME_ID,
            score=score,
            won=won,
            duration=self._session_t,
            extra={"difficulty": self._diff["name"],
                   "mistakes": self._mistakes,
                   "hints": self._hints,
                   "time_s": int(self._elapsed)},
        )
        if self.achievements:
            self.achievements.check_and_unlock({
                "game_id": self.GAME_ID,
                "score": score,
                "won": won,
                "new_best": score >= (self.stats.best_score(self.GAME_ID) or 0),
                "total_games_played": (
                    self.stats.global_summary()["total_games"] if self.stats else 1),
                "total_wins": (
                    self.stats.global_summary()["total_wins"] if self.stats else 0),
            })


# ─── Plugin metadata ──────────────────────────────────────────────────

GAME_META = {
    "id":          "sudoku",
    "name":        "Sudoku",
    "desc":        "Classic 9x9 number logic puzzle",
    "color":       lambda: Theme.ACCENT_PURPLE,
    "scene_class": SudokuScene,
}
