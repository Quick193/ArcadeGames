"""
games/endless_metro_run.py  -  EndlessMetroRunScene  (Phase 9)
==============================================================
Full port of endless_platformer_game() from games.py.

Preserved from original
-----------------------
  3 difficulties  (Easy / Medium / Hard)
  Variable-gravity player physics with coyote-time + jump-buffer
  Camera scroll system (right/left anchors, sub-pixel carry)
  Procedural platform generation  (ground + elevated)
  Spike hazards on ground platforms
  Enemy patrol (bound to spawning platform)
  Stomp mechanic with chain bonus
  Coin collection  (+10 pts each)
  5 powerups: Shield · 2× Score · Jump Boost · Blaster · Star
  Blaster shots  (F / Ctrl)
  Boss fights every ~3 800 px  (stomp or shoot to damage, HP bar)
  Safe-run checkpoint system (respawn near last safe ground)
  Damage: shield first, then lives; invulnerability + blink
  Score multiplier display  (2× banner)
  Full HUD: Score · Best · Lives · Difficulty · Powerup status
  Game-over overlay with final score

New in scene version
--------------------
  BaseScene  (no inner event loop)
  dt-based physics:  dt_scale = dt * 60  (identical to original at 60 fps)
  All timers in seconds  (was ms)
  Stats/achievement integration on run end
"""

import math
import random
import pygame

from engine import (
    BaseScene, Theme, RenderManager, FontCache,
    draw_text, draw_card, draw_overlay, draw_button, draw_footer_hint,
)
from engine.engine import SCREEN_WIDTH as W, SCREEN_HEIGHT as H

# ─────────────────────────────────────────────────────────────
# Difficulty table
# ─────────────────────────────────────────────────────────────
DIFFICULTIES = [
    {"name": "Easy",
     "base_speed": 4.6, "max_speed":  7.1, "gravity": 0.72, "jump_power": -16.4,
     "gap_min": 55, "gap_max": 115, "enemy_chance": 0.30, "spike_chance": 0.28,
     "boss_hp": 3, "boss_interval": 3800},
    {"name": "Medium",
     "base_speed": 5.2, "max_speed":  8.1, "gravity": 0.78, "jump_power": -15.5,
     "gap_min": 70, "gap_max": 145, "enemy_chance": 0.45, "spike_chance": 0.38,
     "boss_hp": 4, "boss_interval": 3350},
    {"name": "Hard",
     "base_speed": 5.9, "max_speed":  9.2, "gravity": 0.84, "jump_power": -14.6,
     "gap_min": 85, "gap_max": 170, "enemy_chance": 0.58, "spike_chance": 0.48,
     "boss_hp": 5, "boss_interval": 2900},
]

GROUND_Y    = 590
MAX_FALL    = 18.0
COYOTE_T    = 8 / 60.0    # seconds  (~8 frames)
JUMP_BUF_T  = 8 / 60.0    # seconds
INVULN_T    = 1.2
HIT_FLASH_T = 0.26
STOMP_INVULN = 0.22
BOSS_INVULN = 0.32
SAFE_LOCK_T = 0.9
DOUBLE_T    = 9.0
JUMPBOOST_T = 8.0
STAR_T      = 7.0
SHOT_CD     = 0.15
BOSS_CD     = 0.22


class EndlessMetroRunScene(BaseScene):
    GAME_ID = "endless_metro_run"

    # ── Lifecycle ──────────────────────────────────────────────

    def on_enter(self):
        self._phase   = "select"
        self._sel     = 1          # default Medium
        self._anim_t  = 0.0
        self._diff_i  = 1
        self._session_t = 0.0
        self._game_over_saved = False

    def _start(self):
        """Initialise a fresh run."""
        d = DIFFICULTIES[self._diff_i]
        self._d      = d
        self._speed  = float(d["base_speed"])
        self._score  = 0
        self._lives  = 3
        self._dist   = 0.0            # total scroll distance
        self._coins  = 0

        # Player rect + sub-pixel position
        self._player  = pygame.Rect(190, GROUND_Y - 56, 42, 56)
        self._px      = 190.0
        self._py      = float(GROUND_Y - 56)
        self._vx      = 0.0
        self._vy      = 0.0
        self._facing  = 1
        self._on_ground = False

        # Timers (all seconds)
        self._coyote_t    = 0.0
        self._jump_buf_t  = 0.0
        self._invuln_t    = 0.0
        self._hit_flash_t = 0.0
        self._stomp_grace = 0.0
        self._boss_cd_t   = 0.0
        self._safe_lock_t = 0.0
        self._double_t    = 0.0
        self._jumpboost_t = 0.0
        self._star_t      = 0.0
        self._star_hit_cd = 0.0
        self._shot_cd     = 0.0

        # Powerup state
        self._shields    = 0
        self._blaster    = False
        self._stomp_chain = 0

        # Blaster projectiles
        self._shots: list[dict] = []

        # World objects
        self._platforms: list[pygame.Rect] = []
        self._spikes:    list[pygame.Rect] = []
        self._coin_list: list[dict] = []
        self._enemies:   list[dict] = []
        self._powerups:  list[dict] = []
        self._boss: dict | None = None

        # Scroll bookkeeping
        self._ground_scroll = 0.0
        self._scroll_carry  = 0.0
        self._next_spawn_x  = W + 120.0
        self._last_spawn_y  = GROUND_Y

        # Boss scheduling
        self._boss_next_dist = float(d["boss_interval"])

        # Safe-run checkpoint
        self._safe_x = self._px
        self._safe_y = self._py
        self._safe_dist = 0.0

        # Misc
        self._game_over = False
        self._new_best  = False
        self._best      = 0
        if self.stats:
            self._best = self.stats.best_score(self.GAME_ID)
        self._coin_cd  = 0.9
        self._powerup_cd = 6.2

        # Initial platform + coin — large safe ground to start
        self._platforms = [
            pygame.Rect(0, GROUND_Y, 500, H - GROUND_Y),
            pygame.Rect(560, GROUND_Y, 340, H - GROUND_Y),
        ]
        self._coin_list = [{"x": 650.0, "y": float(GROUND_Y - 86), "alive": True}]
        self._safe_lock_t = SAFE_LOCK_T
        self._next_spawn_x = 900.0
        self._consec_elevated = 0

        self._phase = "game"
        self._session_t = 0.0
        self._game_over_saved = False

    # ── Update ─────────────────────────────────────────────────

    def update(self, dt: float):
        self._anim_t += dt
        if self._phase != "game":
            return
        if not self._game_over:
            self._session_t += dt

        dts = dt * 60.0   # dt_scale: physics identical to original at 60 fps

        # Tick all timers
        def tick(attr):
            v = getattr(self, attr)
            if v > 0: setattr(self, attr, max(0.0, v - dt))

        for t in ('_coyote_t','_jump_buf_t','_invuln_t','_hit_flash_t',
                  '_stomp_grace','_boss_cd_t','_safe_lock_t',
                  '_double_t','_jumpboost_t','_star_t','_star_hit_cd','_shot_cd'):
            tick(t)

        if self._game_over:
            return

        # Speed ramp
        self._speed = min(self._d["max_speed"], self._speed + 0.00009 * dts)

        # Keyboard input
        keys = pygame.key.get_pressed()
        left  = keys[pygame.K_LEFT]  or keys[pygame.K_a]
        right = keys[pygame.K_RIGHT] or keys[pygame.K_d]
        move  = -1 if left and not right else (1 if right and not left else 0)
        if move: self._facing = move
        running   = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
        run_mult  = 1.28 if running else 1.0

        # Horizontal velocity
        if self._on_ground:
            target_vx = move * 6.2 * run_mult; accel = 0.32
        else:
            target_vx = move * 7.0 * run_mult; accel = 0.28
        self._vx += (target_vx - self._vx) * accel
        self._px += self._vx * dts
        self._px  = max(70, min(W - 96, self._px))
        self._player.x = int(self._px)

        # Camera scroll
        boss_active = self._boss is not None
        if not boss_active:
            scroll = 0.0
            r_anchor = 445 if running else 430
            l_anchor = 205
            if move > 0 and self._px > r_anchor:
                scroll = self._px - r_anchor; self._px = float(r_anchor)
            elif move < 0 and self._px < l_anchor:
                back = min(l_anchor - self._px, self._dist)
                scroll = -back; self._px = float(l_anchor)
            self._player.x = int(self._px)

            if scroll != 0:
                self._scroll_carry += scroll
                si = math.floor(self._scroll_carry) if self._scroll_carry >= 0 else math.ceil(self._scroll_carry)
                self._scroll_carry -= si
                applied = float(si)
                if applied:
                    for p in self._platforms:  p.x -= si
                    for s in self._spikes:     s.x -= si
                    for c in self._coin_list:  c["x"] -= applied
                    for pu in self._powerups:  pu["x"] -= applied
                    for e in self._enemies:
                        e["rect"].x -= si; e["min_x"] -= applied; e["max_x"] -= applied
                    for sh in self._shots:     sh["x"] -= applied
                    # CRITICAL: keep spawn cursor in sync with scrolling world
                    self._next_spawn_x -= applied
                    if applied > 0:
                        self._dist += applied
                        self._ground_scroll = (self._ground_scroll + applied) % 60
                    else:
                        self._dist = max(0.0, self._dist + applied)
                        self._ground_scroll = (self._ground_scroll + applied) % 60

        # Enemy patrol
        if not boss_active:
            for e in self._enemies:
                e["rect"].x += int(e["dir"] * e["speed"])
                if e["rect"].x <= e["min_x"] or e["rect"].x >= e["max_x"]:
                    e["dir"] *= -1

        # Cull off-screen objects
        if not boss_active:
            self._platforms = [p for p in self._platforms if p.right > -140]
            self._spikes    = [s for s in self._spikes    if s.right  > -90 ]
            self._coin_list = [c for c in self._coin_list if c["x"]   > -90 and c["alive"]]
            self._powerups  = [pu for pu in self._powerups if pu["x"] > -90 and pu["alive"]]
            self._enemies   = [e for e in self._enemies  if e["rect"].right > -90]

            # Spawn ahead
            while self._next_spawn_x < W + 260:
                self._spawn_chunk()

            # Boss trigger
            if self._dist >= self._boss_next_dist:
                self._spawn_boss()
                self._boss_next_dist += self._d["boss_interval"]
                boss_active = True

            # Coin spawn
            self._coin_cd -= dt
            if self._coin_cd <= 0 and len(self._coin_list) < 4:
                self._coin_cd = random.uniform(1.3, 2.2)
                min_x = int(max(self._player.x + 150, 300))
                max_x = W - 90
                if min_x <= max_x:
                    sx = random.randint(min_x, max_x)
                    ly = GROUND_Y - random.choice([72, 86, 102])
                    if all(abs(sx - c["x"]) > 130 for c in self._coin_list if c["alive"]):
                        self._coin_list.append({"x": float(sx), "y": float(ly), "alive": True})

            # Powerup spawn
            self._powerup_cd -= dt
            if self._powerup_cd <= 0 and len(self._powerups) < 1:
                self._powerup_cd = random.uniform(8.2, 12.0)
                min_x = int(max(self._player.x + 210, 360))
                max_x = W - 120
                if min_x <= max_x:
                    sx = random.randint(min_x, max_x)
                    sy = GROUND_Y - random.choice([114, 128])
                    if all(abs(sx - pu["x"]) > 220 for pu in self._powerups if pu["alive"]):
                        self._spawn_powerup(sx, sy)

        else:
            # Boss movement
            b = self._boss
            if b["stun"] > 0:
                b["stun"] -= dt; b["recover"] = max(b["recover"], 0.26)
            elif b["recover"] > 0:
                b["recover"] -= dt
            else:
                b["rect"].x += int(b["dir"] * b["speed"])
                if b["rect"].left <= 520: b["dir"] = 1
                if b["rect"].right >= W - 70: b["dir"] = -1

        # Blaster shots
        for sh in self._shots:
            if not sh["alive"]: continue
            sh["x"] += sh["vx"] * dts
            br = pygame.Rect(int(sh["x"]), int(sh["y"]), 18, 4)
            if self._boss and br.colliderect(self._boss["rect"]) and self._boss["stun"] <= 0:
                sh["alive"] = False
                self._hit_boss()
                continue
            for e in self._enemies:
                if br.colliderect(e["rect"]):
                    sh["alive"] = False; e["rect"].x = -2000
                    self._add_pts(40); break
        self._shots = [sh for sh in self._shots if -40 < sh["x"] < W + 80 and sh["alive"]]

        # Jump buffer / coyote
        if self._on_ground:
            self._coyote_t = COYOTE_T
        if self._jump_buf_t > 0 and self._coyote_t > 0:
            jp = self._d["jump_power"] - (1.8 if self._jumpboost_t > 0 else 0.0)
            self._vy = jp
            self._on_ground = False
            self._coyote_t  = 0.0
            self._jump_buf_t = 0.0

        # Variable jump height (release = shorter arc)
        if self._vy < 0 and not (keys[pygame.K_SPACE] or keys[pygame.K_UP] or keys[pygame.K_w]):
            self._vy += 0.62 * dts

        # Gravity + terminal velocity
        self._vy += self._d["gravity"] * dts
        self._vy  = min(self._vy, MAX_FALL)

        prev_bottom = self._player.bottom
        prev_vy     = self._vy
        self._py   += self._vy * dts
        self._player.y = int(self._py)
        self._on_ground = False

        # Platform collisions
        for p in self._platforms:
            if self._player.colliderect(p):
                if self._vy >= 0 and prev_bottom <= p.top + 8:
                    self._player.bottom = p.top
                    self._py = float(self._player.y); self._vy = 0.0
                    self._on_ground = True
                elif self._vy < 0:
                    self._player.top = p.bottom
                    self._py = float(self._player.y); self._vy = 0.0

        # Boss floor during boss phase
        if self._boss and self._player.bottom >= GROUND_Y:
            self._player.bottom = GROUND_Y
            self._py = float(self._player.y); self._vy = 0.0
            self._on_ground = True

        if self._on_ground:
            self._stomp_chain = 0

        # Fell off bottom
        if self._player.top > H + 90:
            self._damage("hazard")

        # Spike collisions
        if not self._boss:
            for s in self._spikes:
                if self._player.colliderect(s):
                    self._damage("hazard"); break

        # Enemy collisions
        if not self._boss:
            for e in self._enemies:
                if not self._player.colliderect(e["rect"]): continue
                if self._star_t > 0:
                    e["rect"].x = -2000; self._add_pts(70); continue
                ow = min(self._player.right, e["rect"].right) - max(self._player.left, e["rect"].left)
                stomp = (prev_vy > 0 and prev_bottom <= e["rect"].top + 24
                         and self._player.bottom >= e["rect"].top and ow >= 8)
                if stomp:
                    self._stomp_chain += 1
                    bonus = 40 + min(4, self._stomp_chain - 1) * 20
                    self._player.bottom = e["rect"].top - 1
                    self._py = float(self._player.y); self._vy = -9.0
                    self._stomp_grace = max(self._stomp_grace, STOMP_INVULN)
                    e["rect"].x = -2000; self._add_pts(bonus)
                else:
                    self._stomp_chain = 0; self._damage("enemy"); break

        # Boss collisions
        if self._boss:
            b = self._boss; brect = b["rect"]
            if self._player.colliderect(brect):
                if self._star_t > 0 and self._star_hit_cd <= 0 and b["stun"] <= 0:
                    self._hit_boss(); self._star_hit_cd = 0.24
                    self._add_pts(120)
                else:
                    stomp = (prev_vy > 0 and prev_bottom <= brect.top + 22
                             and self._player.bottom >= brect.top
                             and brect.left+2 <= self._player.centerx <= brect.right-2)
                    if stomp and b["stun"] <= 0:
                        self._player.bottom = brect.top - 1
                        self._py = float(self._player.y); self._vy = -10.3
                        self._stomp_grace = max(self._stomp_grace, BOSS_INVULN)
                        self._boss_cd_t = BOSS_CD
                        b["stun"] = 0.52; b["recover"] = 0.32; b["dir"] *= -1
                        self._hit_boss()
                    elif b["stun"] <= 0 and b["recover"] <= 0 and self._stomp_grace <= 0 and self._boss_cd_t <= 0:
                        push_dir = -1 if self._player.centerx < brect.centerx else 1
                        if push_dir < 0: self._player.right = brect.left - 1
                        else:            self._player.left  = brect.right + 1
                        self._px = float(self._player.x); self._vx *= -0.35
                        self._damage("enemy"); self._boss_cd_t = BOSS_CD

            # Prevent overlap
            if self._boss and self._player.colliderect(brect):
                ox = min(self._player.right,brect.right)-max(self._player.left,brect.left)
                oy = min(self._player.bottom,brect.bottom)-max(self._player.top,brect.top)
                if oy <= ox and prev_bottom <= brect.top + 26:
                    self._player.bottom = brect.top - 1
                    self._py = float(self._player.y)
                    if self._vy > 0: self._vy = 0.0
                    self._on_ground = True
                else:
                    if self._player.centerx < brect.centerx: self._player.right = brect.left - 1
                    else: self._player.left = brect.right + 1
                    self._px = float(self._player.x)

        # Safe-run checkpoint update
        if self._on_ground:
            danger = any(self._player.colliderect(s.inflate(8,8)) for s in self._spikes)
            if not danger and self._boss and self._player.colliderect(self._boss["rect"]):
                danger = True
            if not danger:
                danger = any(self._player.colliderect(e["rect"]) for e in self._enemies)
            if (not danger and self._safe_lock_t <= 0 and self._invuln_t <= 0
                    and abs(self._vy) < 0.01
                    and self._dist >= self._safe_dist + 130):
                self._safe_x = float(self._player.x)
                self._safe_y = float(self._player.y)
                self._safe_dist = self._dist

        # Coin pickups
        for c in self._coin_list:
            if c["alive"] and self._player.colliderect(pygame.Rect(int(c["x"])-10, int(c["y"])-10, 20, 20)):
                c["alive"] = False; self._coins += 1; self._add_pts(10)

        # Powerup pickups
        for pu in self._powerups:
            if pu["alive"] and self._player.colliderect(pygame.Rect(int(pu["x"])-11, int(pu["y"])-11, 22, 22)):
                pu["alive"] = False
                t = pu["type"]
                if   t == "shield":  self._shields += 1
                elif t == "double":  self._double_t = DOUBLE_T
                elif t == "jump":    self._jumpboost_t = JUMPBOOST_T
                elif t == "blaster": self._blaster = True
                elif t == "star":    self._star_t = STAR_T; self._star_hit_cd = 0.0

        # Track best
        if self._score > self._best:
            self._best = self._score
            self._new_best = True

    # ── Helpers ────────────────────────────────────────────────

    def _add_pts(self, base):
        self._score += int(base * (2 if self._double_t > 0 else 1))

    def _hit_boss(self):
        b = self._boss
        b["hp"] -= 1; b["stun"] = 0.52; b["recover"] = 0.32; b["dir"] *= -1
        if b["hp"] <= 0:
            self._add_pts(280)
            if random.random() < 0.75:
                self._spawn_powerup(b["rect"].centerx, b["rect"].y - 40, blaster=False)
            self._boss = None

    def _spawn_powerup(self, x, y, blaster=True):
        if self._blaster or not blaster:
            pt = random.choice(["shield","double","jump","star"])
        else:
            pt = random.choice(["shield","double","jump","blaster","star"])
        self._powerups.append({"x": float(x), "y": float(y), "type": pt, "alive": True})

    def _spawn_chunk(self):
        """Spawn the next platform segment. Guarantees the player can always reach it.

        Rules:
        - Gaps are small enough to jump across (gap_min..gap_max, clamped to safe range)
        - Ground platforms appear at least 65% of the time
        - Elevated platforms are always 'steppable': within one jump of ground or nearby platform
        - If last 2 platforms were elevated, force a ground platform
        - Minimum ground platform width 240 to allow landing room
        """
        d = self._d

        # Alternate between ground and elevated, with bias toward ground
        force_ground = getattr(self, '_consec_elevated', 0) >= 2

        gap = random.randint(d["gap_min"], min(d["gap_max"], 130))  # cap gap for safety
        x   = self._next_spawn_x + gap

        # Decide platform type
        choose_ground = force_ground or (random.random() < 0.65)

        if choose_ground:
            y = GROUND_Y
            w = random.randint(240, 420)
            h = H - y
            self._consec_elevated = 0
        else:
            # Elevated — pick a height reachable in one jump from ground or prev platform
            # Max jump height ≈ jump_power² / (2*gravity) in pixels at 60fps
            jp = abs(d["jump_power"])
            grav = d["gravity"]
            max_rise_px = int((jp * jp) / (2.0 * grav))  # ≈ 195 px for easy
            max_rise_px = min(max_rise_px, 155)           # cap for safety

            prev_y = self._last_spawn_y
            if prev_y == GROUND_Y:
                # Jump from ground: can reach up to max_rise_px above ground
                min_elev_y = GROUND_Y - max_rise_px
                max_elev_y = GROUND_Y - 55
            else:
                # Jump from elevated: similar range relative to that platform
                min_elev_y = max(GROUND_Y - max_rise_px, prev_y - 120)
                max_elev_y = min(GROUND_Y - 40, prev_y + 80)

            min_elev_y = max(min_elev_y, GROUND_Y - 150)
            max_elev_y = max(max_elev_y, min_elev_y + 10)

            y = random.randint(int(min_elev_y), int(max_elev_y))
            w = random.randint(180, 300)
            h = 20
            self._consec_elevated = getattr(self, '_consec_elevated', 0) + 1

        seg = pygame.Rect(int(x), int(y), int(w), int(h))
        self._platforms.append(seg)

        # Spikes only on ground platforms, not too close to edges
        if y == GROUND_Y and w > 240 and random.random() < d["spike_chance"]:
            sw = random.randint(28, 52)
            sx = random.randint(seg.x + 50, seg.right - sw - 50)
            if sx + sw <= seg.right - 20:
                self._spikes.append(pygame.Rect(sx, GROUND_Y - 18, sw, 18))

        # Enemies only on elevated platforms with enough room
        if y < GROUND_Y and w > 200 and random.random() < d["enemy_chance"]:
            ex = random.randint(seg.x + 26, seg.right - 56)
            self._enemies.append({
                "rect": pygame.Rect(ex, y - 30, 30, 30),
                "min_x": float(seg.x + 12), "max_x": float(seg.right - 42),
                "dir": random.choice([-1, 1]),
                "speed": random.uniform(1.2, 2.0),
            })

        self._next_spawn_x = float(seg.right)
        self._last_spawn_y = y

    def _spawn_boss(self):
        self._spikes = []; self._enemies = []; self._powerups = []
        hp = self._d["boss_hp"]
        self._boss = {
            "rect": pygame.Rect(W-190, GROUND_Y-86, 86, 86),
            "hp": hp, "max_hp": hp, "dir": -1,
            "speed": 2.6 + self._diff_i * 0.4,
            "stun": 0.0, "recover": 0.0,
        }

    def _damage(self, source="hazard"):
        if self._invuln_t > 0 or self._stomp_grace > 0 or self._game_over:
            return
        if self._star_t > 0:
            return
        if source == "enemy" and self._blaster:
            self._blaster = False; self._invuln_t = INVULN_T
            self._hit_flash_t = HIT_FLASH_T; self._safe_lock_t = max(self._safe_lock_t, SAFE_LOCK_T)
            return
        if self._shields > 0:
            self._shields -= 1; self._invuln_t = 1.0
            self._hit_flash_t = HIT_FLASH_T; self._safe_lock_t = max(self._safe_lock_t, SAFE_LOCK_T)
            return
        self._lives -= 1; self._hit_flash_t = HIT_FLASH_T
        if self._lives <= 0:
            self._game_over = True; self._finish(); return
        self._invuln_t   = INVULN_T
        self._safe_lock_t = max(self._safe_lock_t, SAFE_LOCK_T)
        # Respawn near last safe position
        sx, sy = self._safe_x, self._safe_y
        best_cand = None; best_score = float("inf")
        desired_cx = sx + self._player.width * 0.5
        for p in self._platforms:
            if p.width < self._player.width + 24: continue
            cx = max(p.left+8, min(desired_cx - self._player.width*0.5, p.right - self._player.width - 8))
            cr = pygame.Rect(int(cx), int(p.top - self._player.height), self._player.width, self._player.height)
            if any(cr.colliderect(s.inflate(8,8)) for s in self._spikes):
                found = False
                for dx in (-24,24,-48,48,-72,72):
                    ex = max(p.left+8, min(cx+dx, p.right-self._player.width-8))
                    er = pygame.Rect(int(ex), int(p.top-self._player.height), self._player.width, self._player.height)
                    if not any(er.colliderect(s.inflate(8,8)) for s in self._spikes):
                        cx = ex; cr = er; found = True; break
                if not found: continue
            sc = abs(cr.centerx - desired_cx) + abs(p.top - GROUND_Y)*0.35
            if sc < best_score: best_score = sc; best_cand = (float(cr.x), float(cr.y))
        if best_cand:
            sx, sy = best_cand
        else:
            sx, sy = 190.0, float(GROUND_Y - self._player.height)
        self._px = sx; self._py = sy
        self._safe_x = sx; self._safe_y = sy
        self._player.x = int(self._px); self._player.y = int(self._py)
        self._vx = 0.0; self._vy = -2.0
        self._spikes[:] = [s for s in self._spikes if s.x > 500]
        self._enemies[:] = [e for e in self._enemies if e["rect"].x > 500]

    def _finish(self):
        if not self._game_over_saved:
            self._game_over_saved = True
            if self.stats:
                self.stats.record_game(self.GAME_ID, score=self._score,
                    won=False, duration=self._session_t,
                    extra={"difficulty": self._d["name"],
                           "distance": int(self._dist),
                           "coins": self._coins})
            if self.achievements:
                self.achievements.check_and_unlock({
                    "game_id": self.GAME_ID,
                    "score": self._score,
                    "won": False,
                    "new_best": self._score >= self._best,
                    "total_games_played": self.stats.global_summary()["total_games"] if self.stats else 1,
                    "total_wins": self.stats.global_summary()["total_wins"] if self.stats else 0,
                })

    # ── Draw ───────────────────────────────────────────────────

    def draw(self, screen):
        screen.blit(RenderManager.get_background(W, H), (0, 0))
        if self._phase == "select":
            self._draw_select(screen)
        else:
            self._draw_game(screen)

    def _draw_select(self, screen):
        draw_text(screen, "ENDLESS METRO RUN",
                  FontCache.get("Segoe UI", 52, bold=True), Theme.TEXT_PRIMARY,
                  W//2, 110, align="center")
        draw_text(screen, "Choose Difficulty",
                  FontCache.get("Segoe UI", 18), Theme.TEXT_MUTED,
                  W//2, 162, align="center")
        bf = FontCache.get("Segoe UI", 24, bold=True)
        for i, d in enumerate(DIFFICULTIES):
            draw_button(screen, ((W-360)//2, 240+i*82, 360, 62), d["name"],
                        bf, i==self._sel, Theme.ACCENT_CYAN, self._anim_t*60)
        draw_footer_hint(screen, "^v Select  |  Enter Start  |  Q Menu", y_offset=26)

    def _draw_game(self, screen):
        # Scanline lines for atmosphere
        for i in range(5):
            y = 120 + i*54
            pygame.draw.line(screen, (24+i*6, 30+i*6, 44+i*7), (0,y), (W,y), 1)

        # Ground fill
        pygame.draw.rect(screen, (36,42,56), (0, GROUND_Y, W, H-GROUND_Y))
        for x in range(-60, W+60, 60):
            gx = int(x - self._ground_scroll)
            pygame.draw.line(screen, Theme.CARD_BORDER, (gx, GROUND_Y+15), (gx+30, GROUND_Y+15), 2)

        # Platforms
        for p in self._platforms:
            pygame.draw.rect(screen, Theme.CARD_BG, p, border_radius=6)
            pygame.draw.rect(screen, Theme.CARD_BORDER, p, 1, border_radius=6)

        # Spikes
        for s in self._spikes:
            for sx in range(s.left, s.right, 10):
                pygame.draw.polygon(screen, Theme.ACCENT_RED,
                    [(sx,s.bottom),(sx+5,s.top),(sx+10,s.bottom)])

        # Coins
        for c in self._coin_list:
            if c["alive"]:
                cx,cy = int(c["x"]),int(c["y"])
                pygame.draw.circle(screen, Theme.ACCENT_YELLOW, (cx,cy), 8)
                pygame.draw.circle(screen, Theme.TEXT_PRIMARY, (cx-2,cy-2), 2)

        # Powerups
        for pu in self._powerups:
            if not pu["alive"]: continue
            px,py = int(pu["x"]),int(pu["y"])
            t = pu["type"]
            if t == "shield":
                pygame.draw.circle(screen, Theme.ACCENT_BLUE, (px,py), 10)
                pygame.draw.circle(screen, Theme.TEXT_PRIMARY, (px,py), 10, 1)
            elif t == "double":
                pygame.draw.rect(screen, Theme.ACCENT_PURPLE, (px-9,py-9,18,18), border_radius=4)
                draw_text(screen, "x2", FontCache.get("Segoe UI",10,bold=True),
                          Theme.TEXT_PRIMARY, px, py, align="center")
            elif t == "jump":
                pygame.draw.polygon(screen, Theme.ACCENT_GREEN,
                    [(px,py-10),(px+10,py),(px,py+10),(px-10,py)])
            elif t == "star":
                pygame.draw.polygon(screen, Theme.ACCENT_YELLOW,
                    [(px,py-12),(px+5,py-3),(px+13,py-3),(px+7,py+4),
                     (px+10,py+12),(px,py+7),(px-10,py+12),(px-7,py+4),
                     (px-13,py-3),(px-5,py-3)])
                pygame.draw.circle(screen, Theme.TEXT_PRIMARY, (px-4,py), 1)
                pygame.draw.circle(screen, Theme.TEXT_PRIMARY, (px+4,py), 1)
            else:  # blaster
                pygame.draw.rect(screen, Theme.ACCENT_ORANGE, (px-11,py-6,22,12), border_radius=4)
                pygame.draw.rect(screen, Theme.TEXT_PRIMARY, (px-11,py-6,22,12), 1, border_radius=4)
                pygame.draw.rect(screen, Theme.TEXT_PRIMARY, (px+10,py-2,6,4), border_radius=2)

        # Shots
        for sh in self._shots:
            sx,sy = int(sh["x"]),int(sh["y"])
            pygame.draw.rect(screen, Theme.ACCENT_YELLOW, (sx,sy,18,4), border_radius=2)
            pygame.draw.rect(screen, Theme.TEXT_PRIMARY, (sx,sy,18,4), 1, border_radius=2)

        # Enemies
        for e in self._enemies:
            pygame.draw.rect(screen, Theme.ACCENT_ORANGE, e["rect"], border_radius=8)
            pygame.draw.rect(screen, Theme.TEXT_PRIMARY, e["rect"], 1, border_radius=8)
            pygame.draw.circle(screen, Theme.BG_PRIMARY, (e["rect"].left+8,e["rect"].top+10), 2)
            pygame.draw.circle(screen, Theme.BG_PRIMARY, (e["rect"].right-8,e["rect"].top+10), 2)

        # Boss
        if self._boss:
            b = self._boss["rect"]
            pygame.draw.rect(screen, Theme.ACCENT_RED, b, border_radius=10)
            pygame.draw.rect(screen, Theme.TEXT_PRIMARY, b, 2, border_radius=10)
            hw = 120; hx = b.centerx - hw//2; hy = b.y - 16
            pygame.draw.rect(screen, (40,20,20), (hx,hy,hw,10), border_radius=4)
            fw = int(hw * (self._boss["hp"]/self._boss["max_hp"]))
            pygame.draw.rect(screen, Theme.ACCENT_ORANGE, (hx,hy,fw,10), border_radius=4)
            draw_text(screen, "BOSS", FontCache.get("Segoe UI",9,bold=True),
                      Theme.ACCENT_RED, b.centerx, hy-12, align="center")

        # Player
        show = (self._invuln_t == 0 or int(self._invuln_t*1000/70)%2 == 0)
        if show:
            ms = pygame.time.get_ticks()
            if self._hit_flash_t > 0 and int(self._hit_flash_t*1000/45)%2 == 0:
                pc = Theme.ACCENT_RED
            elif self._star_t > 0:
                pc = Theme.ACCENT_YELLOW if (ms//90)%2==0 else Theme.ACCENT_ORANGE
            elif self._blaster:
                pc = Theme.ACCENT_ORANGE
            else:
                pc = Theme.ACCENT_CYAN
            pygame.draw.rect(screen, pc, self._player, border_radius=8)
            pygame.draw.rect(screen, Theme.TEXT_PRIMARY, self._player, 1, border_radius=8)
            ex = self._player.right-10 if self._facing>=0 else self._player.left+10
            pygame.draw.circle(screen, Theme.BG_PRIMARY, (ex, self._player.y+12), 2)
            if self._blaster:
                cx = self._player.right-2 if self._facing>=0 else self._player.left-10
                pygame.draw.rect(screen, Theme.TEXT_PRIMARY,
                    (cx, self._player.centery-5, 12, 10), border_radius=3)

        # HUD
        draw_card(screen, (16,14,540,60))
        hf = FontCache.get("Segoe UI",18,bold=True)
        draw_text(screen, f"Score: {self._score}", hf, Theme.ACCENT_YELLOW, 28, 33)
        draw_text(screen, f"Best: {max(self._best, self._score)}", hf, Theme.ACCENT_CYAN, 185, 33)
        draw_text(screen, f"Lives: {self._lives}", hf, Theme.ACCENT_RED, 328, 33)
        draw_text(screen, self._d["name"], FontCache.get("Segoe UI",16,bold=True),
                  Theme.ACCENT_PURPLE, 460, 34)
        # Powerup bar
        status = []
        if self._shields  > 0:    status.append(f"Shield:{self._shields}")
        if self._double_t > 0:    status.append("2×Score")
        if self._jumpboost_t > 0: status.append("Jump+")
        if self._blaster:          status.append("Blaster")
        if self._star_t > 0:       status.append("Star")
        draw_text(screen, "  ".join(status) if status else "No Powerups",
                  FontCache.get("Segoe UI",12), Theme.TEXT_SECONDARY, 28, 58)

        draw_footer_hint(screen,
            "Space/^ Jump  |  Shift Run  |  F/Ctrl Shoot  |  R Restart  |  Q Menu",
            y_offset=26)

        # Game over overlay
        if self._game_over:
            draw_overlay(screen, 170)
            draw_text(screen, "GAME OVER",
                      FontCache.get("Segoe UI",52,bold=True), Theme.ACCENT_RED,
                      W//2, H//2-34, align="center")
            draw_text(screen, f"Final Score: {self._score}",
                      FontCache.get("Segoe UI",22), Theme.TEXT_PRIMARY,
                      W//2, H//2+20, align="center")
            if self._new_best:
                draw_text(screen, "NEW BEST!",
                          FontCache.get("Segoe UI",16,bold=True), Theme.ACCENT_YELLOW,
                          W//2, H//2+52, align="center")
            draw_text(screen, "R Restart  |  Q Menu",
                      FontCache.get("Segoe UI",14), Theme.TEXT_MUTED,
                      W//2, H//2+82, align="center")

    # ── Input ───────────────────────────────────────────────────

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return
        k = event.key

        if self._phase == "select":
            n = len(DIFFICULTIES)
            if k == pygame.K_UP:    self._sel = (self._sel-1) % n
            if k == pygame.K_DOWN:  self._sel = (self._sel+1) % n
            if k in (pygame.K_RETURN, pygame.K_SPACE):
                self._diff_i = self._sel; self._start()
            if k in (pygame.K_q, pygame.K_ESCAPE):
                self.engine.pop_scene()

        elif self._phase == "game":
            if k in (pygame.K_q, pygame.K_ESCAPE):
                self._finish(); self.engine.pop_scene()
            elif k == pygame.K_r:
                self._finish(); self._diff_i = self._sel; self._start()
            elif k in (pygame.K_SPACE, pygame.K_UP, pygame.K_w):
                self._jump_buf_t = JUMP_BUF_T
            elif k in (pygame.K_f, pygame.K_LCTRL, pygame.K_RCTRL):
                if self._blaster and self._shot_cd <= 0 and not self._game_over:
                    self._shots.append({
                        "x": float(self._player.right - 2),
                        "y": float(self._player.centery - 4),
                        "vx": 11.5 + self._speed * 0.25,
                        "alive": True,
                    })
                    self._shot_cd = SHOT_CD


# ─────────────────────────────────────────────────────────────
# Plugin metadata
# ─────────────────────────────────────────────────────────────

GAME_META = {
    "id":          "endless_metro_run",
    "name":        "Endless Metro Run",
    "desc":        "Side-scrolling runner with bosses",
    "color":       lambda: Theme.ACCENT_CYAN,
    "scene_class": EndlessMetroRunScene,
}
