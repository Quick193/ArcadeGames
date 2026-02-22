"""games/flappy.py - FlappyScene"""
import random, math, pygame
from engine import BaseScene, Theme, RenderManager, FontCache, draw_text, draw_card, draw_button, draw_overlay, draw_footer_hint
from engine.engine import SCREEN_WIDTH as W, SCREEN_HEIGHT as H

DIFF = {
    "easy":   {"gap":250,"dist":2.8,"grav":0.45,"flap":-11,"spd":220},
    "medium": {"gap":210,"dist":2.2,"grav":0.55,"flap":-13,"spd":260},
    "hard":   {"gap":180,"dist":1.8,"grav":0.65,"flap":-15,"spd":300},
}
PIPE_W = 70

class FlappyScene(BaseScene):
    GAME_ID = "flappy"

    def on_enter(self):
        self._phase = "select"
        self._sel   = 1
        self._time  = 0.0
        self._session_t = 0.0

    def _start(self, diff_name):
        p = DIFF[diff_name]
        self._diff      = diff_name
        self._p         = p
        self._bird_x    = 150.0
        self._bird_y    = float(H//2)
        self._vel       = 0.0
        self._pipes     = []
        self._pipe_timer = 0.0
        self._score     = 0
        self._dead      = False
        self._paused    = False
        self._new_best  = False
        self._phase     = "game"

    def update(self, dt):
        self._time += dt
        if self._phase != "game" or self._paused or self._dead: return
        self._session_t += dt
        p = self._p
        self._vel = min(self._vel + p["grav"], 20)
        self._bird_y += self._vel
        # Pipes
        self._pipe_timer += dt
        if self._pipe_timer >= p["dist"]:
            self._pipe_timer = 0.0
            py = random.randint(90, H-90-p["gap"])
            self._pipes.append({"x": float(W), "y": py, "scored": False})
        for pipe in self._pipes:
            pipe["x"] -= p["spd"] * dt
            bx, by, br = self._bird_x, self._bird_y, 14
            if bx+br-6 > pipe["x"] and bx-br+6 < pipe["x"]+PIPE_W:
                if by-br+6 < pipe["y"] or by+br-6 > pipe["y"]+p["gap"]:
                    self._die()
            if pipe["x"]+PIPE_W < bx and not pipe["scored"]:
                pipe["scored"] = True
                self._score += 1
        self._pipes = [pp for pp in self._pipes if pp["x"] > -PIPE_W]
        if self._bird_y+14 > H or self._bird_y-14 < 0:
            self._die()

    def _die(self):
        if self._dead: return
        self._dead = True
        if self.stats:
            self._new_best = self._score > self.stats.best_score(self.GAME_ID)
            self.stats.record_game(self.GAME_ID, score=self._score, won=False, duration=self._session_t)
        if self.achievements:
            self.achievements.check_and_unlock({
                "game_id": self.GAME_ID, "score": self._score,
                "total_games_played": self.stats.global_summary()["total_games"] if self.stats else 1,
                "total_wins": self.stats.global_summary()["total_wins"] if self.stats else 0,
            })

    def draw(self, screen):
        screen.blit(RenderManager.get_background(W, H), (0, 0))
        if self._phase == "select":
            self._draw_select(screen)
        else:
            self._draw_game(screen)

    def _draw_select(self, screen):
        draw_text(screen, "FLAPPY BIRD", FontCache.get("Segoe UI",52,bold=True), Theme.TEXT_PRIMARY, W//2, 140, align="center")
        opts = ["Easy","Medium","Hard"]
        bf   = FontCache.get("Segoe UI", 22)
        for i, opt in enumerate(opts):
            draw_button(screen, ((W-300)//2, 280+i*82, 300, 58), opt, bf, i==self._sel, Theme.ACCENT_YELLOW, self._time*60)
        draw_footer_hint(screen, "^v Select  |  Enter Play  |  Q Back", y_offset=26)

    def _draw_game(self, screen):
        p = self._p
        # Pipes
        for pipe in self._pipes:
            px = int(pipe["x"])
            top_h = pipe["y"]
            if top_h > 0:
                ts = pygame.Surface((PIPE_W, top_h), pygame.SRCALPHA)
                for i in range(top_h):
                    r = i/max(top_h,1)
                    c = tuple(int(Theme.ACCENT_GREEN[j]*(0.6+0.4*r)) for j in range(3))
                    pygame.draw.line(ts, c, (0,i), (PIPE_W,i))
                pygame.draw.rect(ts, (0,0,0,70), (0,0,PIPE_W,top_h), 2, border_radius=4)
                screen.blit(ts, (px, 0))
            bot_y = pipe["y"]+p["gap"]
            bot_h = H - bot_y
            if bot_h > 0:
                bs = pygame.Surface((PIPE_W, bot_h), pygame.SRCALPHA)
                for i in range(bot_h):
                    r = i/max(bot_h,1)
                    c = tuple(int(Theme.ACCENT_GREEN[j]*(1-0.4*r)) for j in range(3))
                    pygame.draw.line(bs, c, (0,i), (PIPE_W,i))
                pygame.draw.rect(bs, (0,0,0,70), (0,0,PIPE_W,bot_h), 2, border_radius=4)
                screen.blit(bs, (px, bot_y))
        # Bird
        bx, by = int(self._bird_x), int(self._bird_y)
        bs2 = pygame.Surface((32,32), pygame.SRCALPHA)
        for i in range(32):
            c = tuple(int(Theme.ACCENT_YELLOW[j]*(1-0.3*i/32)) for j in range(3))
            pygame.draw.circle(bs2, c, (16,16), max(1,16-i//3))
        screen.blit(bs2, (bx-16, by-16))
        pygame.draw.circle(screen, Theme.BG_PRIMARY, (bx+6, by-3), 3)
        pygame.draw.circle(screen, Theme.TEXT_PRIMARY, (bx+7, by-3), 1)
        # HUD
        draw_card(screen, (16, 16, 130, 56))
        draw_text(screen, "SCORE", FontCache.get("Segoe UI",11,bold=True), Theme.TEXT_MUTED, 32, 22)
        draw_text(screen, str(self._score), FontCache.get("Segoe UI",22,bold=True), Theme.ACCENT_YELLOW, 32, 38)
        draw_footer_hint(screen, "Space Flap  |  P Pause  |  Q Menu", y_offset=26)
        if self._paused:
            from engine.ui import draw_pause_card; draw_pause_card(screen)
        elif self._dead:
            self._draw_dead(screen)

    def _draw_dead(self, screen):
        draw_overlay(screen, 200)
        cw, ch = 420, 240
        cx, cy = (W-cw)//2, (H-ch)//2
        draw_card(screen, (cx,cy,cw,ch))
        draw_text(screen, "CRASHED!", FontCache.get("Segoe UI",44,bold=True), Theme.ACCENT_RED, W//2, cy+52, align="center")
        draw_text(screen, f"Score: {self._score}", FontCache.get("Segoe UI",26,bold=True), Theme.TEXT_PRIMARY, W//2, cy+110, align="center")
        if self._new_best:
            draw_text(screen, "** NEW BEST **", FontCache.get("Segoe UI",13,bold=True), Theme.ACCENT_YELLOW, W//2, cy+148, align="center")
        draw_text(screen, "R Restart  |  Q Menu", FontCache.get("Segoe UI",13), Theme.TEXT_MUTED, W//2, cy+196, align="center")

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN: return
        k = event.key
        if k in (pygame.K_q, pygame.K_ESCAPE): self.engine.pop_scene(); return
        if self._phase == "select":
            if k == pygame.K_UP:    self._sel = (self._sel-1)%3
            if k == pygame.K_DOWN:  self._sel = (self._sel+1)%3
            if k == pygame.K_RETURN: self._start(["easy","medium","hard"][self._sel])
        else:
            if k == pygame.K_r: self._start(self._diff); self._session_t=0.0
            if k == pygame.K_p and not self._dead: self._paused = not self._paused
            if k == pygame.K_SPACE and not self._dead and not self._paused:
                self._vel = self._p["flap"]

GAME_META = {"id":"flappy","name":"Flappy Bird","desc":"Thread the pipes","color":lambda:Theme.ACCENT_YELLOW,"scene_class":FlappyScene}
