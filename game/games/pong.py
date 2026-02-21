"""games/pong.py — PongScene"""
import random, math, pygame
from engine import BaseScene, Theme, RenderManager, FontCache, draw_text, draw_card, draw_button, draw_overlay, draw_footer_hint
from engine.engine import SCREEN_WIDTH as W, SCREEN_HEIGHT as H

PAD_W, PAD_H = 12, 90
BALL_R = 8
WIN_SCORE = 7

AI_PARAMS = {
    "easy":   {"speed": 4.5, "error": 38, "react": 0.35},
    "medium": {"speed": 6.5, "error": 18, "react": 0.70},
    "hard":   {"speed": 9.2, "error":  4, "react": 1.00},
}

class PongScene(BaseScene):
    GAME_ID = "pong"

    def on_enter(self):
        self._phase = "mode"   # mode → difficulty → game
        self._mode  = None
        self._diff  = None
        self._sel   = 0
        self._time  = 0.0
        self._session_t = 0.0
        self._init_game()

    def _init_game(self):
        self._p1y = H//2 - PAD_H//2
        self._p2y = H//2 - PAD_H//2
        self._p1x, self._p2x = 40, W-52
        self._bx = float(W//2)
        self._by = float(H//2)
        self._bdx, self._bdy = 6.0, 5.0*random.choice([-1,1])
        self._p1s = self._p2s = 0
        self._paused  = False
        self._winner  = None

    def update(self, dt):
        self._time += dt
        if self._phase != "game" or self._paused or self._winner: return
        self._session_t += dt
        self._physics(dt)

    def _physics(self, dt):
        keys = pygame.key.get_pressed()
        spd  = 8
        if keys[pygame.K_UP]:   self._p1y = max(0, self._p1y - spd)
        if keys[pygame.K_DOWN]: self._p1y = min(H-PAD_H, self._p1y + spd)
        if self._mode == "2p":
            if keys[pygame.K_w]: self._p2y = max(0, self._p2y - spd)
            if keys[pygame.K_s]: self._p2y = min(H-PAD_H, self._p2y + spd)
        else:
            p = AI_PARAMS[self._diff]
            if self._bx > W*(1.0 - p["react"]):
                tgt = self._by - PAD_H//2 + random.randint(-p["error"], p["error"])
                if self._p2y < tgt:   self._p2y = min(self._p2y + p["speed"], H-PAD_H)
                elif self._p2y > tgt: self._p2y = max(self._p2y - p["speed"], 0)
        nx = self._bx + self._bdx
        ny = self._by + self._bdy
        if ny - BALL_R < 0:    ny = BALL_R;    self._bdy =  abs(self._bdy)
        if ny + BALL_R > H:    ny = H-BALL_R;  self._bdy = -abs(self._bdy)
        # P1 paddle
        if nx - BALL_R <= self._p1x + PAD_W and self._bx - BALL_R > self._p1x:
            if self._p1y <= ny <= self._p1y + PAD_H:
                self._bdx = abs(self._bdx) + 0.4
                nx = self._p1x + PAD_W + BALL_R
                self._bdy = ((ny - (self._p1y + PAD_H/2)) / (PAD_H/2)) * 8
        # P2 paddle
        if nx + BALL_R >= self._p2x and self._bx + BALL_R < self._p2x + PAD_W:
            if self._p2y <= ny <= self._p2y + PAD_H:
                self._bdx = -abs(self._bdx) - 0.4
                nx = self._p2x - BALL_R
                self._bdy = ((ny - (self._p2y + PAD_H/2)) / (PAD_H/2)) * 8
        self._bx, self._by = nx, ny
        # Score
        if self._bx < -20:
            self._p2s += 1; self._reset_ball(1)
            if self._p2s >= WIN_SCORE: self._end_game(p1_won=False)
        elif self._bx > W+20:
            self._p1s += 1; self._reset_ball(-1)
            if self._p1s >= WIN_SCORE: self._end_game(p1_won=True)

    def _reset_ball(self, dx_sign):
        self._bx, self._by = W//2, H//2
        self._bdx = 6.0 * dx_sign
        self._bdy = 5.0 * random.choice([-1,1])

    def _end_game(self, p1_won):
        self._winner = "P1" if p1_won else ("AI" if self._mode == "1p" else "P2")
        won = p1_won
        if self.stats:
            self.stats.record_game(self.GAME_ID, score=self._p1s, won=won, duration=self._session_t,
                extra={"opponent_score": self._p2s})
        if self.achievements:
            self.achievements.check_and_unlock({
                "game_id": self.GAME_ID, "won": won,
                "games_won": self.stats.games_won(self.GAME_ID) if self.stats else int(won),
                "opponent_score": self._p2s,
                "total_games_played": self.stats.global_summary()["total_games"] if self.stats else 1,
                "total_wins": self.stats.global_summary()["total_wins"] if self.stats else int(won),
            })

    def draw(self, screen):
        screen.blit(RenderManager.get_background(W, H), (0, 0))
        if self._phase == "mode":
            self._draw_select(screen, "PONG", ["1 Player vs AI", "2 Players Local"])
        elif self._phase == "difficulty":
            self._draw_select(screen, "Difficulty", ["Easy", "Medium", "Hard"])
        else:
            self._draw_game(screen)

    def _draw_select(self, screen, title, options):
        tf = FontCache.get("Segoe UI", 52, bold=True)
        draw_text(screen, title, tf, Theme.TEXT_PRIMARY, W//2, 140, align="center")
        bf = FontCache.get("Segoe UI", 22)
        for i, opt in enumerate(options):
            bx, by, bw, bh = (W-300)//2, 280+i*82, 300, 58
            draw_button(screen, (bx, by, bw, bh), opt, bf, i==self._sel, Theme.ACCENT_CYAN, self._time*60)
        draw_footer_hint(screen, "↑↓ Select  •  Enter Confirm  •  Q Back", y_offset=26)

    def _draw_game(self, screen):
        # Centre dashes
        for i in range(0, H, 30):
            pygame.draw.line(screen, Theme.CARD_BORDER, (W//2, i), (W//2, i+15), 2)
        # Paddles
        for px, py, color in [(self._p1x, self._p1y, Theme.ACCENT_CYAN),(self._p2x, self._p2y, Theme.ACCENT_PINK)]:
            surf = pygame.Surface((PAD_W, PAD_H), pygame.SRCALPHA)
            for i in range(PAD_H):
                r = i/PAD_H
                c = tuple(int(color[j]*(1-0.3*r)) for j in range(3))
                pygame.draw.line(surf, c, (0,i), (PAD_W,i))
            pygame.draw.rect(surf, (255,255,255,80), (0,0,PAD_W,PAD_H), 1, border_radius=6)
            screen.blit(surf, (px, py))
        # Ball glow + ball
        pygame.draw.circle(screen, (*Theme.TEXT_PRIMARY[:3], 70), (int(self._bx), int(self._by)), BALL_R+4)
        pygame.draw.circle(screen, Theme.TEXT_PRIMARY, (int(self._bx), int(self._by)), BALL_R)
        # Score card
        draw_card(screen, ((W-240)//2, 16, 240, 68))
        sf = FontCache.get("Segoe UI", 36, bold=True)
        draw_text(screen, str(self._p1s), sf, Theme.ACCENT_CYAN, W//2-55, 38)
        draw_text(screen, str(self._p2s), sf, Theme.ACCENT_PINK, W//2+55, 38)
        # Labels
        lf = FontCache.get("Segoe UI", 11, bold=True)
        p2_label = "AI" if self._mode == "1p" else "P2"
        draw_text(screen, "P1", lf, Theme.TEXT_MUTED, W//2-55, 22)
        draw_text(screen, p2_label, lf, Theme.TEXT_MUTED, W//2+55, 22)
        draw_footer_hint(screen, "↑↓ P1 Move  •  W/S P2 Move  •  P Pause  •  Q Menu", y_offset=26)
        if self._paused:
            from engine.ui import draw_pause_card
            draw_pause_card(screen)
        elif self._winner:
            self._draw_winner(screen)

    def _draw_winner(self, screen):
        draw_overlay(screen, 200)
        cw, ch = 420, 220
        cx, cy = (W-cw)//2, (H-ch)//2
        draw_card(screen, (cx, cy, cw, ch))
        color = Theme.ACCENT_CYAN if self._winner == "P1" else Theme.ACCENT_PINK
        draw_text(screen, f"{self._winner} WINS!", FontCache.get("Segoe UI",42,bold=True), color, W//2, cy+56, align="center")
        draw_text(screen, f"{self._p1s}  —  {self._p2s}", FontCache.get("Segoe UI",28,bold=True), Theme.TEXT_PRIMARY, W//2, cy+112, align="center")
        draw_text(screen, "R Rematch  •  Q Menu", FontCache.get("Segoe UI",13), Theme.TEXT_MUTED, W//2, cy+168, align="center")

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN: return
        k = event.key
        if k in (pygame.K_q, pygame.K_ESCAPE):
            if self._phase == "game": self.engine.pop_scene()
            elif self._phase == "difficulty": self._phase = "mode"; self._sel = 0
            else: self.engine.pop_scene()
            return
        if self._phase == "mode":
            if k == pygame.K_UP:    self._sel = (self._sel-1)%2
            if k == pygame.K_DOWN:  self._sel = (self._sel+1)%2
            if k == pygame.K_RETURN:
                if self._sel == 0: self._phase = "difficulty"; self._mode = "1p"; self._sel = 1
                else: self._mode = "2p"; self._diff = None; self._init_game(); self._phase = "game"
        elif self._phase == "difficulty":
            if k == pygame.K_UP:   self._sel = (self._sel-1)%3
            if k == pygame.K_DOWN: self._sel = (self._sel+1)%3
            if k == pygame.K_RETURN:
                self._diff = ["easy","medium","hard"][self._sel]
                self._init_game(); self._phase = "game"
        elif self._phase == "game":
            if k == pygame.K_p and not self._winner: self._paused = not self._paused
            if k == pygame.K_r: self._init_game(); self._session_t = 0.0

GAME_META = {"id":"pong","name":"Pong","desc":"Classic paddle duel","color":lambda:Theme.ACCENT_PINK,"scene_class":PongScene}
