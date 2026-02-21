"""games/breakout.py — BreakoutScene"""
import random, pygame
from engine import BaseScene, Theme, RenderManager, FontCache, draw_text, draw_card, draw_overlay, draw_footer_hint
from engine.engine import SCREEN_WIDTH as W, SCREEN_HEIGHT as H

PAD_W, PAD_H = 130, 16
PAD_Y  = H - 70
BALL_R = 10
BRICK_ROWS, BRICK_COLS = 6, 10
MARGIN_X = 130
TOP_Y    = 95
GAP      = 6
BRICK_W  = (W - MARGIN_X*2 - GAP*(BRICK_COLS-1)) // BRICK_COLS
BRICK_H  = 24
ROW_COLORS = [
    lambda: Theme.ACCENT_CYAN,
    lambda: Theme.ACCENT_BLUE,
    lambda: Theme.ACCENT_GREEN,
    lambda: Theme.ACCENT_YELLOW,
    lambda: Theme.ACCENT_ORANGE,
    lambda: Theme.ACCENT_PINK,
]
MAX_LEVELS = 4

def _build_bricks(level):
    bricks = []
    for r in range(BRICK_ROWS):
        hp = 1 + (1 if level >= 3 and r < 2 else 0)
        color = ROW_COLORS[r % len(ROW_COLORS)]()
        for c in range(BRICK_COLS):
            x = MARGIN_X + c*(BRICK_W+GAP)
            y = TOP_Y    + r*(BRICK_H+GAP)
            bricks.append({"rect": pygame.Rect(x,y,BRICK_W,BRICK_H), "hp":hp, "color":color})
    return bricks

def _reset_ball(level):
    spd = 5.2 + (level-1)*0.45
    return float(W//2), float(PAD_Y-22), random.choice([-1,1])*spd, -spd

class BreakoutScene(BaseScene):
    GAME_ID = "breakout"

    def on_enter(self):
        self._reset()

    def _reset(self):
        self._level   = 1
        self._lives   = 3
        self._score   = 0
        self._paused  = False
        self._dead    = False
        self._won     = False
        self._new_best = False
        self._session_t = 0.0
        self._pad_x   = float(W//2 - PAD_W//2)
        self._bricks  = _build_bricks(self._level)
        self._bx, self._by, self._vx, self._vy = _reset_ball(self._level)

    def update(self, dt):
        if self._paused or self._dead or self._won: return
        self._session_t += dt
        keys = pygame.key.get_pressed()
        spd  = 480 * dt
        if keys[pygame.K_LEFT]  or keys[pygame.K_a]: self._pad_x -= spd
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]: self._pad_x += spd
        self._pad_x = max(30, min(W-30-PAD_W, self._pad_x))
        px = int(self._pad_x)
        # Ball move (substepped for reliability)
        steps = max(1, int((abs(self._vx)+abs(self._vy))*dt*60 / 6))
        sdx, sdy = self._vx*dt*60/steps, self._vy*dt*60/steps
        for _ in range(steps):
            self._bx += sdx; self._by += sdy
            br = pygame.Rect(int(self._bx-BALL_R), int(self._by-BALL_R), BALL_R*2, BALL_R*2)
            pad_r = pygame.Rect(px, PAD_Y, PAD_W, PAD_H)
            if br.left <= 0:        self._bx = BALL_R;    self._vx =  abs(self._vx)
            if br.right >= W:       self._bx = W-BALL_R;  self._vx = -abs(self._vx)
            if br.top  <= 0:        self._by = BALL_R;    self._vy =  abs(self._vy)
            if br.colliderect(pad_r) and self._vy > 0:
                self._vy = -abs(self._vy)
                hit = (self._bx - px) / PAD_W
                self._vx = (hit - 0.5) * 10
            for brick in self._bricks:
                if br.colliderect(brick["rect"]):
                    brick["hp"] -= 1
                    self._score += 10
                    if abs(br.right - brick["rect"].left) < 8 or abs(br.left - brick["rect"].right) < 8:
                        self._vx *= -1
                    else:
                        self._vy *= -1
                    break
            self._bricks = [b for b in self._bricks if b["hp"] > 0]
            if br.bottom >= H:
                self._lives -= 1
                if self._lives <= 0: self._finish(won=False)
                else: self._bx,self._by,self._vx,self._vy = _reset_ball(self._level)
                break
        if not self._bricks and not self._dead:
            self._level += 1
            if self._level > MAX_LEVELS: self._finish(won=True)
            else:
                self._bricks = _build_bricks(self._level)
                self._bx,self._by,self._vx,self._vy = _reset_ball(self._level)

    def _finish(self, won):
        self._won = won; self._dead = not won
        if self.stats:
            self._new_best = self._score > self.stats.best_score(self.GAME_ID)
            self.stats.record_game(self.GAME_ID, score=self._score, won=won, duration=self._session_t)
        if self.achievements:
            self.achievements.check_and_unlock({
                "game_id": self.GAME_ID, "won": won, "score": self._score,
                "total_games_played": self.stats.global_summary()["total_games"] if self.stats else 1,
                "total_wins": self.stats.global_summary()["total_wins"] if self.stats else int(won),
            })

    def draw(self, screen):
        screen.blit(RenderManager.get_background(W, H), (0, 0))
        draw_text(screen, "BREAKOUT", FontCache.get("Segoe UI",52,bold=True), Theme.TEXT_PRIMARY, W//2, 36, align="center")
        hw = 700; hx = (W-hw)//2
        draw_card(screen, (hx, 52, hw, 50))
        hf = FontCache.get("Segoe UI",18,bold=True)
        draw_text(screen, f"Score: {self._score}", hf, Theme.ACCENT_CYAN, hx+24, 69)
        draw_text(screen, f"Lives: {'♥'*self._lives}", hf, Theme.ACCENT_RED, W//2-50, 69)
        draw_text(screen, f"Level: {self._level}", hf, Theme.ACCENT_YELLOW, hx+hw-120, 69)
        for b in self._bricks:
            c = b["color"] if b["hp"]==1 else tuple(max(0,v-60) for v in b["color"])
            pygame.draw.rect(screen, c, b["rect"], border_radius=5)
            pygame.draw.rect(screen, (0,0,0), b["rect"], 1, border_radius=5)
        pygame.draw.rect(screen, Theme.ACCENT_PURPLE, (int(self._pad_x),PAD_Y,PAD_W,PAD_H), border_radius=8)
        pygame.draw.rect(screen, Theme.TEXT_PRIMARY,  (int(self._pad_x),PAD_Y,PAD_W,PAD_H), 1, border_radius=8)
        pygame.draw.circle(screen, Theme.TEXT_PRIMARY, (int(self._bx),int(self._by)), BALL_R)
        draw_footer_hint(screen, "A/D Move  •  P Pause  •  R Restart  •  Q Menu", y_offset=26)
        if self._paused:
            from engine.ui import draw_pause_card; draw_pause_card(screen)
        elif self._won or self._dead:
            self._draw_end(screen)

    def _draw_end(self, screen):
        draw_overlay(screen, 180)
        cw,ch = 440,220; cx,cy = (W-cw)//2,(H-ch)//2
        draw_card(screen,(cx,cy,cw,ch))
        title = "YOU WIN!" if self._won else "GAME OVER"
        color = Theme.ACCENT_GREEN if self._won else Theme.ACCENT_RED
        draw_text(screen, title, FontCache.get("Segoe UI",44,bold=True), color, W//2, cy+52, align="center")
        draw_text(screen, f"Score: {self._score}", FontCache.get("Segoe UI",24,bold=True), Theme.TEXT_PRIMARY, W//2, cy+110, align="center")
        if self._new_best:
            draw_text(screen,"✦  NEW BEST  ✦",FontCache.get("Segoe UI",13,bold=True),Theme.ACCENT_YELLOW,W//2,cy+148,align="center")
        draw_text(screen,"R Restart  •  Q Menu",FontCache.get("Segoe UI",13),Theme.TEXT_MUTED,W//2,cy+186,align="center")

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN: return
        k = event.key
        if k in (pygame.K_q, pygame.K_ESCAPE): self.engine.pop_scene(); return
        if k == pygame.K_r: self._reset(); return
        if k == pygame.K_p and not self._dead and not self._won: self._paused = not self._paused

GAME_META = {"id":"breakout","name":"Breakout","desc":"Break every brick","color":lambda:Theme.ACCENT_ORANGE,"scene_class":BreakoutScene}
