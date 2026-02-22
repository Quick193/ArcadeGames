"""games/neon_blob_dash.py - NeonBlobDashScene (Dino-runner style)"""
import random, math, pygame
from engine import BaseScene, Theme, RenderManager, FontCache, draw_text, draw_card, draw_overlay, draw_footer_hint
from engine.engine import SCREEN_WIDTH as W, SCREEN_HEIGHT as H

GROUND_Y   = 548
GRAVITY    = 0.92
JUMP_POWER = -15.8
MAX_FALL   = 18.0
BASE_SPEED = 6.9

class NeonBlobDashScene(BaseScene):
    GAME_ID = "neon_blob_dash"

    def on_enter(self): self._reset()

    def _reset(self):
        self._vy = 0.0; self._on_ground = True; self._ducking = False
        self._speed = BASE_SPEED; self._score = 0.0
        self._obstacles = []; self._spawn_cd = 1050.0
        self._dead = False; self._new_best = False
        self._ground_scroll = 0.0; self._session_t = 0.0
        self._hit_flash = 0.0; self._paused = False
        dw, dh = 44, 50
        self._dino = pygame.Rect(130, GROUND_Y-dh, dw, dh)
        self._dw_stand, self._dh_stand = 44, 50
        self._dw_duck,  self._dh_duck  = 60, 30

    def _spawn_obs(self):
        kind = "cactus" if random.random()<0.7 else "bird"
        if kind=="cactus":
            w=random.choice([26,34,42]); h=random.choice([42,52,62])
            rect=pygame.Rect(W+20, GROUND_Y-h, w, h)
        else:
            y=random.choice([GROUND_Y-90, GROUND_Y-130, GROUND_Y-55])
            rect=pygame.Rect(W+20, y, 42, 26)
        self._obstacles.append({"type":kind,"rect":rect,"phase":0.0})

    def update(self, dt):
        if self._paused or self._dead: return
        self._session_t += dt
        scale = dt * 60.0  # normalise to 60fps
        keys = pygame.key.get_pressed()
        want_duck = keys[pygame.K_DOWN] or keys[pygame.K_s]
        self._ducking = want_duck and self._on_ground
        if self._ducking:
            self._dino.width=self._dw_duck; self._dino.height=self._dh_duck; self._dino.bottom=GROUND_Y
        else:
            pb=self._dino.bottom; self._dino.width=self._dw_stand; self._dino.height=self._dh_stand
            self._dino.bottom=pb if not self._on_ground else GROUND_Y
        # Jump
        if (keys[pygame.K_SPACE] or keys[pygame.K_UP]) and self._on_ground and not self._ducking:
            self._vy=JUMP_POWER; self._on_ground=False
        # Physics
        self._speed = min(12.2, self._speed + 0.0002*dt)
        self._score += dt * 25.0
        self._ground_scroll = (self._ground_scroll + self._speed*scale) % 64
        self._hit_flash = max(0, self._hit_flash - dt)
        if not self._on_ground:
            self._vy = min(self._vy + GRAVITY*scale, MAX_FALL)
            self._dino.y += int(self._vy*scale)
            if self._dino.bottom >= GROUND_Y:
                self._dino.bottom=GROUND_Y; self._vy=0.0; self._on_ground=True
        # Spawn obstacles
        self._spawn_cd -= dt*1000
        if self._spawn_cd <= 0:
            self._spawn_obs()
            self._spawn_cd = random.randint(max(620,int(1220-self._speed*22)), max(800,int(1660-self._speed*24)))
        # Move obstacles
        move_px = int(self._speed*scale)
        for obs in self._obstacles:
            obs["rect"].x -= move_px
            if obs["type"]=="bird": obs["phase"]+=0.16*scale; obs["rect"].y+=int(math.sin(obs["phase"])*1.25)
        self._obstacles=[o for o in self._obstacles if o["rect"].right>-80]
        # Collision
        dino_hb = self._dino.inflate(-10,-8)
        for obs in self._obstacles:
            if dino_hb.colliderect(obs["rect"].inflate(-6,-6)):
                self._dead=True; self._hit_flash=0.5; self._commit_score(); break

    def _commit_score(self):
        sc = int(self._score)
        if self.stats:
            self._new_best = sc > self.stats.best_score(self.GAME_ID)
            self.stats.record_game(self.GAME_ID, score=sc, won=False, duration=self._session_t)
        if self.achievements:
            self.achievements.check_and_unlock({
                "game_id": self.GAME_ID, "score": sc,
                "total_games_played": self.stats.global_summary()["total_games"] if self.stats else 1,
                "total_wins": self.stats.global_summary()["total_wins"] if self.stats else 0,
            })

    def draw(self, screen):
        screen.blit(RenderManager.get_background(W, H), (0, 0))
        # Scanlines
        for i in range(5):
            y=130+i*52; pygame.draw.line(screen,(24+i*6,30+i*6,44+i*7),(0,y),(W,y),1)
        # Ground
        pygame.draw.rect(screen,(36,42,56),(0,GROUND_Y,W,H-GROUND_Y))
        for x in range(-64,W+64,64):
            gx=int(x-self._ground_scroll)
            pygame.draw.line(screen,Theme.CARD_BORDER,(gx,GROUND_Y+16),(gx+32,GROUND_Y+16),2)
        # Obstacles
        for obs in self._obstacles:
            r=obs["rect"]
            if obs["type"]=="cactus":
                pygame.draw.rect(screen,Theme.ACCENT_GREEN,r,border_radius=4)
                pygame.draw.rect(screen,Theme.TEXT_PRIMARY,r,1,border_radius=4)
                arm_y=r.y+r.h//2
                pygame.draw.rect(screen,Theme.ACCENT_GREEN,(r.x-8,arm_y,8,10),border_radius=2)
                pygame.draw.rect(screen,Theme.ACCENT_GREEN,(r.right,arm_y-8,8,10),border_radius=2)
            else:
                pygame.draw.ellipse(screen,Theme.ACCENT_ORANGE,r)
                pygame.draw.line(screen,Theme.TEXT_PRIMARY,(r.x+5,r.centery),(r.right-5,r.centery),2)
        # Dino
        flash = self._hit_flash>0 and (int(self._hit_flash*10)%2==0)
        dc = Theme.ACCENT_RED if flash else Theme.ACCENT_CYAN
        pygame.draw.rect(screen,dc,self._dino,border_radius=8)
        pygame.draw.rect(screen,Theme.TEXT_PRIMARY,self._dino,1,border_radius=8)
        eye_y=self._dino.y+(8 if self._ducking else 10)
        pygame.draw.circle(screen,Theme.BG_PRIMARY,(self._dino.x+self._dino.width-10,eye_y),2)
        # HUD
        draw_card(screen,(16,16,380,52))
        hf=FontCache.get("Segoe UI",17,bold=True)
        draw_text(screen,f"Score: {int(self._score)}",hf,Theme.ACCENT_YELLOW,32,32)
        best=self.stats.best_score(self.GAME_ID) if self.stats else 0
        draw_text(screen,f"Best: {max(best,int(self._score))}",hf,Theme.ACCENT_CYAN,200,32)
        draw_text(screen,"NEON BLOB DASH",FontCache.get("Segoe UI",13,bold=True),Theme.TEXT_PRIMARY,460,24)
        draw_footer_hint(screen,"Space/^ Jump  |  v Duck  |  P Pause  |  R Restart  |  Q Menu",y_offset=26)
        if self._paused:
            from engine.ui import draw_pause_card; draw_pause_card(screen)
        elif self._dead: self._draw_gameover(screen)

    def _draw_gameover(self,screen):
        draw_overlay(screen,180)
        cw,ch=420,230; cx,cy=(W-cw)//2,(H-ch)//2
        draw_card(screen,(cx,cy,cw,ch))
        draw_text(screen,"GAME OVER",FontCache.get("Segoe UI",44,bold=True),Theme.ACCENT_RED,W//2,cy+50,align="center")
        draw_text(screen,f"Score: {int(self._score)}",FontCache.get("Segoe UI",26,bold=True),Theme.TEXT_PRIMARY,W//2,cy+106,align="center")
        if self._new_best:
            draw_text(screen,"** NEW BEST **",FontCache.get("Segoe UI",13,bold=True),Theme.ACCENT_YELLOW,W//2,cy+144,align="center")
        draw_text(screen,"R Restart  |  Q Menu",FontCache.get("Segoe UI",13),Theme.TEXT_MUTED,W//2,cy+192,align="center")

    def handle_event(self,event):
        if event.type!=pygame.KEYDOWN: return
        k=event.key
        if k in(pygame.K_q,pygame.K_ESCAPE): self.engine.pop_scene(); return
        if k==pygame.K_r: self._reset(); return
        if k==pygame.K_p and not self._dead: self._paused=not self._paused

GAME_META={"id":"neon_blob_dash","name":"Neon Blob Dash","desc":"Dash and survive","color":lambda:Theme.ACCENT_CYAN,"scene_class":NeonBlobDashScene}
