"""games/space_invaders.py — SpaceInvadersScene"""
import random, math, pygame
from engine import BaseScene, Theme, RenderManager, FontCache, draw_text, draw_card, draw_overlay, draw_footer_hint
from engine.engine import SCREEN_WIDTH as W, SCREEN_HEIGHT as H

INV_W, INV_H = 40, 28
SHIP_W, SHIP_H = 44, 28
BULLET_SPD = 600  # px/s
ENEMY_SPD_BASE = 60
SHIP_SPD = 340

def _spawn_wave(wave):
    invaders = []
    rows, cols = min(4, 2+wave//2), min(10, 6+wave)
    for r in range(rows):
        for c in range(cols):
            hp = 1 + (1 if wave > 3 and r == 0 else 0)
            invaders.append({
                "rect": pygame.Rect(100 + c*(INV_W+14), 80 + r*(INV_H+14), INV_W, INV_H),
                "hp": hp,
            })
    return invaders

def _make_shields():
    return [pygame.Rect(x, 520, 95, 32) for x in [170, 355, 540, 725]]

class SpaceInvadersScene(BaseScene):
    GAME_ID = "space_invaders"

    def on_enter(self): self._reset()

    def _reset(self):
        self._ship       = pygame.Rect(W//2-SHIP_W//2, H-80, SHIP_W, SHIP_H)
        self._wave       = 1
        self._lives      = 3
        self._score      = 0
        self._paused     = False
        self._dead       = False
        self._direction  = 1
        self._invaders   = _spawn_wave(self._wave)
        self._shields    = _make_shields()
        self._bullets: list[pygame.Rect]   = []
        self._enemy_bullets: list[pygame.Rect] = []
        self._particles  = []
        self._shoot_cd   = 0.0
        self._enemy_shot_t = 0.0
        self._hit_flash  = 0.0
        self._hit_overlay = 0.0
        self._session_t  = 0.0
        self._new_best   = False

    def update(self, dt):
        if self._paused or self._dead: return
        self._session_t += dt
        self._shoot_cd   = max(0, self._shoot_cd - dt)
        self._hit_flash  = max(0, self._hit_flash - dt)
        self._hit_overlay = max(0, self._hit_overlay - dt)

        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self._ship.x = max(8, self._ship.x - int(SHIP_SPD*dt))
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self._ship.x = min(W-SHIP_W-8, self._ship.x + int(SHIP_SPD*dt))

        # Player bullets
        for b in self._bullets: b.y -= int(BULLET_SPD*dt)
        self._bullets = [b for b in self._bullets if b.bottom >= 0]

        # Invader movement
        spd = (ENEMY_SPD_BASE + self._wave*15) * dt
        edge = False
        for inv in self._invaders:
            inv["rect"].x += int(self._direction * spd)
            if inv["rect"].left <= 16 or inv["rect"].right >= W-16:
                edge = True
        if edge:
            self._direction *= -1
            for inv in self._invaders:
                inv["rect"].y += 18

        # Bullet vs invader
        survivors = []
        for inv in self._invaders:
            hit = False
            for b in self._bullets[:]:
                if inv["rect"].colliderect(b):
                    self._bullets.remove(b)
                    inv["hp"] -= 1
                    if inv["hp"] <= 0:
                        self._score += 10
                        self._spawn_particles(inv["rect"].centerx, inv["rect"].centery)
                        hit = True
                    break
            if not hit:
                survivors.append(inv)
        self._invaders = survivors

        # Enemy fire
        self._enemy_shot_t += dt
        interval = max(0.28, 1.0 - self._wave*0.06)
        if self._enemy_shot_t >= interval and self._invaders:
            self._enemy_shot_t = 0.0
            shooter = random.choice(self._invaders)
            self._enemy_bullets.append(pygame.Rect(shooter["rect"].centerx-2, shooter["rect"].bottom, 4, 12))

        for eb in self._enemy_bullets: eb.y += int(420*dt)
        self._enemy_bullets = [eb for eb in self._enemy_bullets if eb.top <= H+10]

        # Bullet vs shields
        for sh in self._shields[:]:
            for b in self._bullets[:]:
                if sh.colliderect(b): self._bullets.remove(b); sh.w -= 6
            for eb in self._enemy_bullets[:]:
                if sh.colliderect(eb): self._enemy_bullets.remove(eb); sh.w -= 8
            if sh.w <= 12: self._shields.remove(sh)

        # Enemy bullet vs player
        for eb in self._enemy_bullets[:]:
            if self._ship.colliderect(eb):
                self._enemy_bullets.remove(eb)
                self._lives -= 1
                self._hit_flash   = 0.6
                self._hit_overlay = 0.14
                self._spawn_particles(self._ship.centerx, self._ship.centery, n=16)
                if self._lives <= 0: self._finish()
                break

        # Invaders reach bottom
        for inv in self._invaders:
            if inv["rect"].bottom >= self._ship.y or inv["rect"].colliderect(self._ship):
                self._finish(); break

        # Wave clear
        if not self._invaders and not self._dead:
            self._wave += 1
            self._invaders = _spawn_wave(self._wave)
            self._shields  = _make_shields()

        # Particles
        for p in self._particles:
            p["x"] += p["vx"]*dt; p["y"] += p["vy"]*dt; p["vy"] += 60*dt; p["life"] -= dt
        self._particles = [p for p in self._particles if p["life"] > 0]

    def _spawn_particles(self, x, y, n=12):
        if self.settings and not self.settings.show_particles:
            return
        for _ in range(n):
            self._particles.append({"x":float(x),"y":float(y),
                "vx":random.uniform(-160,160),"vy":random.uniform(-220,-60),
                "life":random.uniform(0.35,0.80),"size":random.randint(2,4)})

    def _finish(self):
        if self._dead: return
        self._dead = True
        if self.stats:
            self._new_best = self._score > self.stats.best_score(self.GAME_ID)
            self.stats.record_game(self.GAME_ID, score=self._score, won=False,
                duration=self._session_t, extra={"wave": self._wave})
        if self.achievements:
            self.achievements.check_and_unlock({
                "game_id": self.GAME_ID, "score": self._score, "wave": self._wave,
                "total_games_played": self.stats.global_summary()["total_games"] if self.stats else 1,
                "total_wins": self.stats.global_summary()["total_wins"] if self.stats else 0,
            })

    def draw(self, screen):
        screen.blit(RenderManager.get_background(W, H), (0, 0))
        # Stars
        for i in range(90):
            screen.set_at(((i*47+self._score*2)%W, (i*29+self._wave*17)%H), (160,180,210))
        # Shields
        for sh in self._shields:
            pygame.draw.rect(screen, Theme.CARD_BG, sh, border_radius=5)
            pygame.draw.rect(screen, Theme.ACCENT_BLUE, sh, 2, border_radius=5)
        # Invaders
        for inv in self._invaders:
            c = Theme.ACCENT_GREEN if inv["hp"]==1 else Theme.ACCENT_ORANGE
            pygame.draw.rect(screen, c, inv["rect"], border_radius=5)
            pygame.draw.rect(screen, Theme.TEXT_PRIMARY, inv["rect"], 1, border_radius=5)
            # Antenna
            cx = inv["rect"].centerx
            pygame.draw.line(screen, c, (cx-6,inv["rect"].top), (cx-2,inv["rect"].top-6), 2)
            pygame.draw.line(screen, c, (cx+6,inv["rect"].top), (cx+2,inv["rect"].top-6), 2)
        # Bullets
        for b in self._bullets:       pygame.draw.rect(screen, Theme.ACCENT_CYAN, b, border_radius=2)
        for eb in self._enemy_bullets: pygame.draw.rect(screen, Theme.ACCENT_RED,  eb, border_radius=2)
        # Ship
        flash = self._hit_flash > 0 and (int(self._hit_flash*10)%2==0)
        sc = Theme.ACCENT_RED if flash else Theme.ACCENT_CYAN
        sx,sy = self._ship.centerx, self._ship.y
        pygame.draw.polygon(screen, sc, [(sx,sy),(self._ship.x+4,self._ship.bottom),(self._ship.right-4,self._ship.bottom)])
        pygame.draw.polygon(screen, Theme.TEXT_PRIMARY, [(sx,sy+4),(self._ship.x+9,self._ship.bottom-2),(self._ship.right-9,self._ship.bottom-2)], 1)
        # Particles (respects settings)
        if self.settings and not self.settings.show_particles:
            self._particles.clear()
        for p in self._particles:
            a = int(max(0,min(255,p["life"]/0.8*255)))
            ps = pygame.Surface((p["size"]*2+2,p["size"]*2+2), pygame.SRCALPHA)
            pygame.draw.circle(ps, (255,120,120,a), (p["size"]+1,p["size"]+1), p["size"])
            screen.blit(ps, (p["x"]-p["size"], p["y"]-p["size"]))
        if self._hit_overlay > 0:
            a = int(self._hit_overlay/0.14*80)
            fl = pygame.Surface((W,H), pygame.SRCALPHA)
            fl.fill((255,60,60,a)); screen.blit(fl,(0,0))
        # HUD
        draw_card(screen, (16,14,340,52))
        hf = FontCache.get("Segoe UI",17,bold=True)
        draw_text(screen, f"Score: {self._score}", hf, Theme.ACCENT_CYAN, 32, 32)
        draw_text(screen, f"{'♥'*self._lives}", hf, Theme.ACCENT_RED, 188, 32)
        draw_text(screen, f"Wave: {self._wave}", hf, Theme.ACCENT_YELLOW, 268, 32)
        draw_footer_hint(screen, "A/D Move  •  Space Shoot  •  P Pause  •  Q Menu", y_offset=26)
        if self._paused:
            from engine.ui import draw_pause_card; draw_pause_card(screen)
        elif self._dead: self._draw_gameover(screen)

    def _draw_gameover(self, screen):
        draw_overlay(screen,180)
        cw,ch=440,240; cx,cy=(W-cw)//2,(H-ch)//2
        draw_card(screen,(cx,cy,cw,ch))
        draw_text(screen,"GAME OVER",FontCache.get("Segoe UI",44,bold=True),Theme.ACCENT_RED,W//2,cy+52,align="center")
        draw_text(screen,f"Score: {self._score}   Wave: {self._wave}",FontCache.get("Segoe UI",22,bold=True),Theme.TEXT_PRIMARY,W//2,cy+108,align="center")
        if self._new_best:
            draw_text(screen,"✦  NEW BEST  ✦",FontCache.get("Segoe UI",13,bold=True),Theme.ACCENT_YELLOW,W//2,cy+148,align="center")
        draw_text(screen,"R Restart  •  Q Menu",FontCache.get("Segoe UI",13),Theme.TEXT_MUTED,W//2,cy+196,align="center")

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN: return
        k = event.key
        if k in (pygame.K_q, pygame.K_ESCAPE): self.engine.pop_scene(); return
        if k == pygame.K_r: self._reset(); return
        if k == pygame.K_p and not self._dead: self._paused = not self._paused; return
        if k == pygame.K_SPACE and not self._dead and not self._paused and self._shoot_cd <= 0:
            self._bullets.append(pygame.Rect(self._ship.centerx-2, self._ship.y-10, 4, 12))
            self._shoot_cd = 0.16

GAME_META = {"id":"space_invaders","name":"Space Invaders","desc":"Defend against waves","color":lambda:Theme.ACCENT_ORANGE,"scene_class":SpaceInvadersScene}
