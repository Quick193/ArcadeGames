"""games/asteroids.py — AsteroidsScene (Phase 10)

Features
--------
  Vector ship with rotate + thrust + friction physics
  3 asteroid sizes (Large → Medium → Small → destroyed)
  Bullets with lifetime
  Wave system — wave clear bonus, brief respite between waves
  Lives (3) + brief invincibility on respawn
  Shield powerup: absorbs one hit (appears every ~20 seconds)
  Progressive difficulty: more asteroids per wave, faster rotation
  High-score tracking, stats + achievement integration
"""

import math
import random
import pygame

from engine import (
    BaseScene, Theme, RenderManager, FontCache,
    draw_text, draw_card, draw_overlay, draw_footer_hint,
)
from engine.engine import SCREEN_WIDTH as W, SCREEN_HEIGHT as H

# ─── Constants ────────────────────────────────────────────────────────

BULLET_SPEED   = 520.0      # px/s
BULLET_LIFE    = 0.85       # seconds
BULLET_RATE    = 0.18       # min seconds between shots
SHIP_ACCEL     = 320.0      # px/s²
SHIP_FRICTION  = 0.985      # multiplied each frame (per dt at 60fps base)
SHIP_ROT_SPEED = 200.0      # deg/s
SHIP_MAX_SPEED = 380.0
INVULN_TIME    = 2.5        # seconds after respawn
WAVE_PAUSE     = 2.2        # seconds between waves

ASTEROID_SPEEDS = {
    "large":  (48, 80),
    "medium": (72, 120),
    "small":  (110, 180),
}
ASTEROID_RADII = {"large": 46, "medium": 26, "small": 13}
ASTEROID_SCORE = {"large": 20, "medium": 50, "small": 100}
ASTEROID_VERTS = {"large": 12, "medium": 9, "small": 7}

POWERUP_INTERVAL = 22.0     # seconds between shield spawns
POWERUP_LIFE     = 9.0      # seconds before it vanishes

# ─── Helper functions ─────────────────────────────────────────────────

def _wrap(x, y):
    return x % W, y % H

def _dist(ax, ay, bx, by):
    return math.hypot(ax - bx, ay - by)


def _make_asteroid(x, y, size):
    speed_range = ASTEROID_SPEEDS[size]
    angle = random.uniform(0, 360)
    speed = random.uniform(*speed_range)
    vx = math.cos(math.radians(angle)) * speed
    vy = math.sin(math.radians(angle)) * speed
    r = ASTEROID_RADII[size]
    # Random irregular polygon offsets (±30% of radius)
    n = ASTEROID_VERTS[size]
    offsets = [random.uniform(0.7, 1.3) * r for _ in range(n)]
    return {
        "x": x, "y": y, "vx": vx, "vy": vy,
        "size": size, "r": r,
        "angle": random.uniform(0, 360),
        "rot_speed": random.uniform(-30, 30),
        "offsets": offsets,
        "n": n,
    }


def _asteroid_points(a):
    pts = []
    n = a["n"]
    for i in range(n):
        ang = math.radians(a["angle"] + i * 360 / n)
        pts.append((
            a["x"] + math.cos(ang) * a["offsets"][i],
            a["y"] + math.sin(ang) * a["offsets"][i],
        ))
    return pts


def _ship_points(x, y, angle, size=20):
    """Returns (nose, left_wing, right_wing) as screen points."""
    rad = math.radians(angle)
    nose  = (x + math.cos(rad) * size,
             y + math.sin(rad) * size)
    left  = (x + math.cos(rad + 2.5) * size * 0.7,
             y + math.sin(rad + 2.5) * size * 0.7)
    right = (x + math.cos(rad - 2.5) * size * 0.7,
             y + math.sin(rad - 2.5) * size * 0.7)
    back  = (x + math.cos(rad + math.pi) * size * 0.4,
             y + math.sin(rad + math.pi) * size * 0.4)
    return nose, left, back, right


# ─── AsteroidsScene ───────────────────────────────────────────────────

class AsteroidsScene(BaseScene):
    GAME_ID = "asteroids"

    def on_enter(self):
        self._phase     = "game"
        self._session_t = 0.0
        self._saved     = False
        self._new_best  = False
        self._best      = self.stats.best_score(self.GAME_ID) if self.stats else 0
        self._new_game()

    def _new_game(self):
        self._score     = 0
        self._lives     = 3
        self._wave      = 0
        self._game_over = False
        self._wave_pause_t  = 0.0
        self._powerup_cd    = POWERUP_INTERVAL
        self._powerup: dict | None = None

        self._ship_x    = W / 2
        self._ship_y    = H / 2
        self._ship_vx   = 0.0
        self._ship_vy   = 0.0
        self._ship_ang  = -90.0    # pointing up
        self._invuln_t  = INVULN_TIME
        self._shield    = False

        self._bullets: list[dict] = []
        self._shot_cd   = 0.0
        self._asteroids: list[dict] = []
        self._particles: list[dict] = []
        self._thrusting = False

        self._start_wave()

    def _start_wave(self):
        self._wave += 1
        n = 3 + self._wave          # more asteroids each wave
        self._asteroids = []
        # Spawn large asteroids away from ship
        for _ in range(n):
            while True:
                x = random.uniform(0, W)
                y = random.uniform(0, H)
                if _dist(x, y, self._ship_x, self._ship_y) > 160:
                    break
            self._asteroids.append(_make_asteroid(x, y, "large"))

    def _respawn(self):
        self._ship_x   = W / 2
        self._ship_y   = H / 2
        self._ship_vx  = 0.0
        self._ship_vy  = 0.0
        self._ship_ang = -90.0
        self._invuln_t = INVULN_TIME
        self._shield   = False

    # ── Update ───────────────────────────────────────────────────

    def update(self, dt: float):
        self._session_t += dt
        if self._phase != "game" or self._game_over:
            return

        self._shot_cd    = max(0.0, self._shot_cd - dt)
        self._invuln_t   = max(0.0, self._invuln_t - dt)
        self._powerup_cd = max(0.0, self._powerup_cd - dt)

        # Wave clear pause
        if self._wave_pause_t > 0:
            self._wave_pause_t -= dt
            if self._wave_pause_t <= 0:
                self._start_wave()
            self._update_particles(dt)
            return

        keys = pygame.key.get_pressed()

        # Rotate
        if keys[pygame.K_LEFT]  or keys[pygame.K_a]:
            self._ship_ang -= SHIP_ROT_SPEED * dt
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self._ship_ang += SHIP_ROT_SPEED * dt

        # Thrust
        self._thrusting = keys[pygame.K_UP] or keys[pygame.K_w]
        if self._thrusting:
            rad = math.radians(self._ship_ang)
            self._ship_vx += math.cos(rad) * SHIP_ACCEL * dt
            self._ship_vy += math.sin(rad) * SHIP_ACCEL * dt
            # Clamp speed
            spd = math.hypot(self._ship_vx, self._ship_vy)
            if spd > SHIP_MAX_SPEED:
                self._ship_vx = self._ship_vx / spd * SHIP_MAX_SPEED
                self._ship_vy = self._ship_vy / spd * SHIP_MAX_SPEED
            # Exhaust particles
            if random.random() < 0.5:
                rad = math.radians(self._ship_ang + 180)
                px = self._ship_x + math.cos(rad) * 14
                py = self._ship_y + math.sin(rad) * 14
                self._particles.append({
                    "x": px, "y": py,
                    "vx": math.cos(rad)*random.uniform(60,120) + self._ship_vx*0.3,
                    "vy": math.sin(rad)*random.uniform(60,120) + self._ship_vy*0.3,
                    "life": random.uniform(0.18, 0.30),
                    "max_life": 0.30,
                    "color": random.choice([Theme.ACCENT_ORANGE, Theme.ACCENT_YELLOW]),
                    "size": random.randint(2,4),
                })

        # Friction
        fric = SHIP_FRICTION ** (dt * 60)
        self._ship_vx *= fric
        self._ship_vy *= fric

        # Move ship (wrap)
        self._ship_x, self._ship_y = _wrap(
            self._ship_x + self._ship_vx * dt,
            self._ship_y + self._ship_vy * dt,
        )

        # Shooting
        if keys[pygame.K_SPACE] and self._shot_cd <= 0:
            rad = math.radians(self._ship_ang)
            self._bullets.append({
                "x":    self._ship_x + math.cos(rad) * 22,
                "y":    self._ship_y + math.sin(rad) * 22,
                "vx":   math.cos(rad) * BULLET_SPEED + self._ship_vx * 0.4,
                "vy":   math.sin(rad) * BULLET_SPEED + self._ship_vy * 0.4,
                "life": BULLET_LIFE,
            })
            self._shot_cd = BULLET_RATE

        # Update bullets
        for b in self._bullets:
            b["x"], b["y"] = _wrap(b["x"] + b["vx"]*dt, b["y"] + b["vy"]*dt)
            b["life"] -= dt
        self._bullets = [b for b in self._bullets if b["life"] > 0]

        # Update asteroids
        for a in self._asteroids:
            a["x"], a["y"] = _wrap(a["x"] + a["vx"]*dt, a["y"] + a["vy"]*dt)
            a["angle"] += a["rot_speed"] * dt

        # Powerup
        if self._powerup_cd <= 0 and self._powerup is None:
            self._powerup = {
                "x": random.uniform(80, W-80),
                "y": random.uniform(80, H-80),
                "life": POWERUP_LIFE,
                "pulse": 0.0,
            }
            self._powerup_cd = POWERUP_INTERVAL
        if self._powerup:
            self._powerup["life"] -= dt
            self._powerup["pulse"] += dt * 4
            if self._powerup["life"] <= 0:
                self._powerup = None
            elif not self._shield and _dist(self._ship_x, self._ship_y,
                                            self._powerup["x"], self._powerup["y"]) < 22:
                self._shield = True
                self._powerup = None

        # Bullet–asteroid collisions
        new_asteroids = []
        bullets_hit   = set()
        for i, a in enumerate(self._asteroids):
            hit = False
            for j, b in enumerate(self._bullets):
                if j in bullets_hit: continue
                if _dist(b["x"], b["y"], a["x"], a["y"]) < a["r"]:
                    hit = True
                    bullets_hit.add(j)
                    self._score += ASTEROID_SCORE[a["size"]]
                    self._explode(a["x"], a["y"], a["size"])
                    # Split
                    if a["size"] == "large":
                        for _ in range(2):
                            new_asteroids.append(_make_asteroid(a["x"], a["y"], "medium"))
                    elif a["size"] == "medium":
                        for _ in range(2):
                            new_asteroids.append(_make_asteroid(a["x"], a["y"], "small"))
                    break
            if not hit:
                new_asteroids.append(a)

        self._bullets    = [b for j,b in enumerate(self._bullets) if j not in bullets_hit]
        self._asteroids  = new_asteroids

        # Ship–asteroid collision
        if self._invuln_t <= 0:
            for a in self._asteroids:
                if _dist(self._ship_x, self._ship_y, a["x"], a["y"]) < a["r"] - 4:
                    if self._shield:
                        self._shield   = False
                        self._invuln_t = 1.0
                        self._explode(a["x"], a["y"], a["size"])
                    else:
                        self._explode(self._ship_x, self._ship_y, "large")
                        self._lives -= 1
                        if self._lives <= 0:
                            self._game_over = True
                            self._finish()
                        else:
                            self._respawn()
                    break

        # Wave cleared?
        if not self._asteroids:
            self._score += self._wave * 200   # wave clear bonus
            self._wave_pause_t = WAVE_PAUSE

        self._update_particles(dt)

        # Track best
        if self._score > self._best:
            self._best = self._score
            self._new_best = True

    def _explode(self, x, y, size):
        n = {"large": 18, "medium": 12, "small": 7}[size]
        for _ in range(n):
            ang = random.uniform(0, 360)
            spd = random.uniform(40, 160)
            self._particles.append({
                "x": x, "y": y,
                "vx": math.cos(math.radians(ang)) * spd,
                "vy": math.sin(math.radians(ang)) * spd,
                "life": random.uniform(0.3, 0.9),
                "max_life": 0.9,
                "color": random.choice([Theme.ACCENT_ORANGE, Theme.ACCENT_YELLOW,
                                        Theme.TEXT_PRIMARY]),
                "size": random.randint(2, 5),
            })

    def _update_particles(self, dt):
        for p in self._particles:
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            p["life"] -= dt
        self._particles = [p for p in self._particles if p["life"] > 0]

    # ── Draw ─────────────────────────────────────────────────────

    def draw(self, screen: pygame.Surface):
        screen.fill((8, 10, 18))   # deep space black

        # Stars (static, seeded)
        rng = random.Random(42)
        for _ in range(90):
            sx = rng.randint(0, W)
            sy = rng.randint(0, H)
            br = rng.randint(60, 200)
            pygame.draw.circle(screen, (br, br, br+20), (sx, sy), rng.randint(1,2))

        # Particles
        for p in self._particles:
            alpha = min(1.0, max(0.0, p["life"] / p["max_life"]))
            r2, g2, b2 = p["color"][:3]
            col = (min(255, int(r2*alpha)), min(255, int(g2*alpha)), min(255, int(b2*alpha)))
            pygame.draw.circle(screen, col,
                               (int(p["x"]) % W, int(p["y"]) % H), p["size"])

        # Asteroids
        for a in self._asteroids:
            pts = _asteroid_points(a)
            # Draw wrapped copies if near edge
            for ox, oy in self._wrap_offsets(a["x"], a["y"], a["r"]):
                shifted = [(px+ox, py+oy) for px,py in pts]
                pygame.draw.polygon(screen, (60, 64, 80), shifted)
                pygame.draw.lines(screen, (130, 140, 160), True, shifted, 2)

        # Bullets
        for b in self._bullets:
            pygame.draw.circle(screen, Theme.ACCENT_YELLOW,
                               (int(b["x"]) % W, int(b["y"]) % H), 3)

        # Powerup (shield orb)
        if self._powerup:
            pu = self._powerup
            pulse = abs(math.sin(pu["pulse"])) * 5
            pygame.draw.circle(screen, (30, 60, 120),
                               (int(pu["x"]), int(pu["y"])), int(14 + pulse))
            pygame.draw.circle(screen, Theme.ACCENT_CYAN,
                               (int(pu["x"]), int(pu["y"])), int(14 + pulse), 2)
            draw_text(screen, "S", FontCache.get("Segoe UI", 14, bold=True),
                      Theme.ACCENT_CYAN, int(pu["x"]), int(pu["y"]) - 5, align="center")

        # Ship
        if not self._game_over:
            show = self._invuln_t <= 0 or int(self._invuln_t * 1000 / 80) % 2 == 0
            if show:
                pts = _ship_points(self._ship_x, self._ship_y, self._ship_ang)
                sc = Theme.ACCENT_CYAN if not self._shield else Theme.ACCENT_GREEN
                pygame.draw.polygon(screen, (20, 30, 50), pts)
                pygame.draw.lines(screen, sc, True, pts, 2)
                # Thrust flame
                if self._thrusting:
                    rad = math.radians(self._ship_ang + 180)
                    fl  = random.uniform(10, 20)
                    fx  = self._ship_x + math.cos(rad) * (14 + fl)
                    fy  = self._ship_y + math.sin(rad) * (14 + fl)
                    pygame.draw.line(screen, Theme.ACCENT_ORANGE,
                                     (int(self._ship_x), int(self._ship_y)),
                                     (int(fx), int(fy)), 3)
                # Shield bubble
                if self._shield:
                    a_val = int(abs(math.sin(self._session_t*3)) * 60 + 40)
                    surf = pygame.Surface((60, 60), pygame.SRCALPHA)
                    pygame.draw.circle(surf, (*Theme.ACCENT_GREEN[:3], a_val), (30,30), 28)
                    pygame.draw.circle(surf, (*Theme.ACCENT_GREEN[:3], 180), (30,30), 28, 2)
                    screen.blit(surf, (int(self._ship_x)-30, int(self._ship_y)-30))

        # HUD
        hf = FontCache.get("Segoe UI", 20, bold=True)
        draw_text(screen, f"SCORE  {self._score}", hf, Theme.ACCENT_YELLOW, 20, 20)
        draw_text(screen, f"BEST   {max(self._best, self._score)}",
                  FontCache.get("Segoe UI",13), Theme.TEXT_MUTED, 20, 46)
        draw_text(screen, f"WAVE {self._wave}",
                  FontCache.get("Segoe UI",16,bold=True), Theme.ACCENT_CYAN,
                  W//2, 18, align="center")
        # Lives (small triangles)
        for i in range(self._lives):
            lx = W - 30 - i * 28
            ly = 28
            pts = _ship_points(lx, ly, -90, size=10)
            pygame.draw.lines(screen, Theme.ACCENT_CYAN, True, pts, 2)

        # Wave pause banner
        if self._wave_pause_t > 0:
            draw_text(screen, f"WAVE {self._wave + 1} INCOMING",
                      FontCache.get("Segoe UI", 32, bold=True), Theme.ACCENT_GREEN,
                      W//2, H//2, align="center")
            draw_text(screen, f"+{self._wave*200} wave bonus",
                      FontCache.get("Segoe UI", 16), Theme.ACCENT_YELLOW,
                      W//2, H//2 + 44, align="center")

        # Game over
        if self._game_over:
            draw_overlay(screen, 170)
            draw_text(screen, "GAME OVER",
                      FontCache.get("Segoe UI", 52, bold=True), Theme.ACCENT_RED,
                      W//2, H//2 - 50, align="center")
            draw_text(screen, f"Score: {self._score}",
                      FontCache.get("Segoe UI", 24), Theme.TEXT_PRIMARY,
                      W//2, H//2 + 10, align="center")
            draw_text(screen, f"Wave {self._wave}  |  Best: {self._best}",
                      FontCache.get("Segoe UI", 16), Theme.TEXT_SECONDARY,
                      W//2, H//2 + 46, align="center")
            if self._new_best:
                draw_text(screen, "NEW BEST!",
                          FontCache.get("Segoe UI", 18, bold=True), Theme.ACCENT_YELLOW,
                          W//2, H//2 + 80, align="center")
            draw_text(screen, "R Restart  |  Q Menu",
                      FontCache.get("Segoe UI", 14), Theme.TEXT_MUTED,
                      W//2, H//2 + 118, align="center")
        else:
            draw_footer_hint(screen,
                "Arrows/WASD Rotate+Thrust  |  Space Shoot  |  S=Shield powerup  |  Q Menu",
                y_offset=26)

    def _wrap_offsets(self, x, y, r):
        """Return (ox, oy) offsets for wrapping copies near edges."""
        offsets = [(0, 0)]
        if x - r < 0:    offsets.append((W, 0))
        if x + r > W:    offsets.append((-W, 0))
        if y - r < 0:    offsets.append((0, H))
        if y + r > H:    offsets.append((0, -H))
        return offsets

    # ── Input ────────────────────────────────────────────────────

    def handle_event(self, event: pygame.event.Event):
        if event.type != pygame.KEYDOWN:
            return
        k = event.key
        if k in (pygame.K_q, pygame.K_ESCAPE):
            self._finish()
            self.engine.pop_scene()
        elif k == pygame.K_r and self._game_over:
            self._saved = False
            self._new_best = False
            self._new_game()

    def _finish(self):
        if self._saved:
            return
        self._saved = True
        if self.stats:
            self.stats.record_game(self.GAME_ID, score=self._score,
                won=False, duration=self._session_t,
                extra={"wave": self._wave})
        if self.achievements:
            games_played = (self.stats.global_summary()["total_games"]
                            if self.stats else 1)
            self.achievements.check_and_unlock({
                "game_id":            self.GAME_ID,
                "score":              self._score,
                "wave":               self._wave,
                "won":                False,
                "new_best":           self._new_best,
                "games_played":       games_played,
                "total_games_played": games_played,
                "total_wins": (
                    self.stats.global_summary()["total_wins"]
                    if self.stats else 0),
            })


# ─── Plugin metadata ─────────────────────────────────────────────────

GAME_META = {
    "id":          "asteroids",
    "name":        "Asteroids",
    "desc":        "Destroy all rocks. Don't get hit.",
    "color":       lambda: Theme.ACCENT_CYAN,
    "scene_class": AsteroidsScene,
}
