"""games/snake.py - SnakeScene"""
import math, random, pygame
from engine import BaseScene, Theme, RenderManager, FontCache, draw_text, draw_card, draw_overlay, draw_footer_hint
from engine.engine import SCREEN_WIDTH, SCREEN_HEIGHT

TILE = 20
COLS = SCREEN_WIDTH  // TILE
ROWS = SCREEN_HEIGHT // TILE
BASE_INTERVAL = 0.10   # seconds per step at start
MIN_INTERVAL  = 0.048

class SnakeScene(BaseScene):
    GAME_ID = "snake"

    def on_enter(self):
        self._reset()

    def _reset(self):
        cx, cy = COLS // 2, ROWS // 2
        self._snake     = [(cx, cy)]
        self._dir       = (1, 0)
        self._next_dir  = (1, 0)
        self._food      = self._spawn_food()
        self._score     = 0
        self._interval  = BASE_INTERVAL
        self._step_timer = 0.0
        self._time      = 0.0
        self._session_t = 0.0
        self._paused    = False
        self._dead      = False
        self._show_grid = True
        self._new_best  = False

    def _spawn_food(self):
        while True:
            pos = (random.randint(0, COLS-1), random.randint(0, ROWS-1))
            if pos not in getattr(self, '_snake', []):
                return pos

    def update(self, dt):
        if self._paused or self._dead: return
        self._time      += dt
        self._session_t += dt
        self._step_timer += dt
        if self._step_timer >= self._interval:
            self._step_timer = 0.0
            self._step()

    def _step(self):
        self._dir = self._next_dir
        hx, hy = self._snake[0]
        nx, ny = (hx + self._dir[0]) % COLS, (hy + self._dir[1]) % ROWS
        if (nx, ny) in self._snake:
            self._trigger_death(); return
        self._snake.insert(0, (nx, ny))
        if (nx, ny) == self._food:
            self._score += 10
            self._interval = max(MIN_INTERVAL, BASE_INTERVAL - self._score * 0.0012)
            self._food = self._spawn_food()
        else:
            self._snake.pop()

    def _trigger_death(self):
        self._dead = True
        if self.stats:
            self._new_best = self._score > self.stats.best_score(self.GAME_ID)
            self.stats.record_game(self.GAME_ID, score=self._score, won=False, duration=self._session_t)
        if self.achievements:
            self.achievements.check_and_unlock({
                "game_id": self.GAME_ID, "score": self._score,
                "games_played": self.stats.games_played(self.GAME_ID) if self.stats else 1,
                "total_games_played": self.stats.global_summary()["total_games"] if self.stats else 1,
                "total_wins": self.stats.global_summary()["total_wins"] if self.stats else 0,
            })

    def draw(self, screen):
        w, h = screen.get_size()
        screen.blit(RenderManager.get_background(w, h), (0, 0))
        if self._show_grid:
            for x in range(0, w, TILE):
                pygame.draw.line(screen, (38, 44, 58), (x, 0), (x, h))
            for y in range(0, h, TILE):
                pygame.draw.line(screen, (38, 44, 58), (0, y), (w, y))
        # Food pulse
        fx, fy = self._food[0]*TILE+TILE//2, self._food[1]*TILE+TILE//2
        r = int(6 + 2*math.sin(self._time*6))
        pygame.draw.circle(screen, (*Theme.ACCENT_RED[:3], 80), (fx, fy), r+4)
        pygame.draw.circle(screen, Theme.ACCENT_RED, (fx, fy), r)
        # Snake
        for i, (sx, sy) in enumerate(self._snake):
            px, py = sx*TILE+1, sy*TILE+1
            if i == 0:
                surf = pygame.Surface((TILE-2, TILE-2), pygame.SRCALPHA)
                for j in range(TILE-2):
                    ratio = j/(TILE-2)
                    c = tuple(int(Theme.ACCENT_GREEN[k]*(1-0.3*ratio)) for k in range(3))
                    pygame.draw.line(surf, c, (0,j), (TILE-2,j))
                pygame.draw.rect(surf, (255,255,255,60), (0,0,TILE-2,TILE-2), 1, border_radius=4)
                screen.blit(surf, (px, py))
                pygame.draw.circle(screen, Theme.BG_PRIMARY, (px+6, py+6), 2)
                pygame.draw.circle(screen, Theme.BG_PRIMARY, (px+TILE-8, py+6), 2)
            else:
                c = tuple(int(Theme.ACCENT_GREEN[k]*0.7) for k in range(3))
                pygame.draw.rect(screen, c, (px+1, py+1, TILE-4, TILE-4), border_radius=3)
        # HUD
        draw_card(screen, (16, 16, 160, 56))
        sf = FontCache.get("Segoe UI", 11, bold=True)
        vf = FontCache.get("Segoe UI", 22, bold=True)
        draw_text(screen, "SCORE", sf, Theme.TEXT_MUTED, 32, 22)
        draw_text(screen, str(self._score), vf, Theme.ACCENT_GREEN, 32, 38)
        best = self.stats.best_score(self.GAME_ID) if self.stats else 0
        draw_card(screen, (184, 16, 160, 56))
        draw_text(screen, "BEST", sf, Theme.TEXT_MUTED, 200, 22)
        draw_text(screen, str(best), vf, Theme.ACCENT_CYAN, 200, 38)
        draw_footer_hint(screen, "Arrows Move  |  G Grid  |  P Pause  |  Q Menu", y_offset=26)
        if self._paused: self._draw_pause(screen)
        elif self._dead: self._draw_gameover(screen)

    def _draw_pause(self, screen):
        from engine.ui import draw_pause_card
        draw_pause_card(screen)

    def _draw_gameover(self, screen):
        w, h = screen.get_size()
        draw_overlay(screen, 200)
        cw, ch = 420, 240
        cx, cy = (w-cw)//2, (h-ch)//2
        draw_card(screen, (cx, cy, cw, ch))
        draw_text(screen, "GAME OVER", FontCache.get("Segoe UI",44,bold=True), Theme.ACCENT_RED, w//2, cy+52, align="center")
        draw_text(screen, f"{self._score}", FontCache.get("Segoe UI",28,bold=True), Theme.TEXT_PRIMARY, w//2, cy+110, align="center")
        if self._new_best:
            draw_text(screen, "** NEW BEST **", FontCache.get("Segoe UI",13,bold=True), Theme.ACCENT_YELLOW, w//2, cy+148, align="center")
        draw_text(screen, "R Restart  |  Q Menu", FontCache.get("Segoe UI",13), Theme.TEXT_MUTED, w//2, cy+196, align="center")

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN: return
        k = event.key
        if k in (pygame.K_q, pygame.K_ESCAPE): self.engine.pop_scene(); return
        if k == pygame.K_r: self._reset(); return
        if k == pygame.K_p and not self._dead: self._paused = not self._paused; return
        if k == pygame.K_g: self._show_grid = not self._show_grid; return
        if self._dead or self._paused: return
        d = self._dir
        if k == pygame.K_UP    and d != (0,1):  self._next_dir = (0,-1)
        elif k == pygame.K_DOWN  and d != (0,-1): self._next_dir = (0,1)
        elif k == pygame.K_LEFT  and d != (1,0):  self._next_dir = (-1,0)
        elif k == pygame.K_RIGHT and d != (-1,0): self._next_dir = (1,0)

GAME_META = {"id":"snake","name":"Snake","desc":"Grow and survive","color":lambda:Theme.ACCENT_GREEN,"scene_class":SnakeScene}
