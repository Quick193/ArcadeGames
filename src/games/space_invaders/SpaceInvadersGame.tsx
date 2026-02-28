import { useEffect, useRef, useState } from "react";
import MobileControls from "../../components/ui/MobileControls";
import { useGameSession } from "../../services/progression/useGameSession";
import type { ControlScheme } from "../../types/settings";
import "./space.css";

const W = 540;
const H = 900;
const SHIP_Y = H - 78;
const INV_W = 40;
const INV_H = 26;
const SHIP_W = 44;
const SHIP_H = 28;
const SHOT_COOLDOWN_FRAMES = 10;

interface SpaceInvadersGameProps {
  onExit: () => void;
  controlScheme: ControlScheme;
}

type Invader = { x: number; y: number; dir: number };
type Bullet = { x: number; y: number };
type Shield = { x: number; y: number; w: number; h: number };

function SpaceInvadersGame({ onExit, controlScheme }: SpaceInvadersGameProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const frameRef = useRef<number | null>(null);
  const keysRef = useRef<Set<string>>(new Set());

  const shipXRef = useRef(W / 2 - 22);
  const waveRef = useRef(1);
  const scoreRef = useRef(0);
  const livesRef = useRef(3);
  const deadRef = useRef(false);
  const pausedRef = useRef(false);
  const invadersRef = useRef<Invader[]>(spawnWave(1));
  const bulletsRef = useRef<Bullet[]>([]);
  const enemyBulletsRef = useRef<Bullet[]>([]);
  const shieldsRef = useRef<Shield[]>(spawnShields());
  const shotCooldownRef = useRef(0);

  const [shipX, setShipX] = useState(W / 2 - 22);
  const [wave, setWave] = useState(1);
  const [score, setScore] = useState(0);
  const [lives, setLives] = useState(3);
  const [dead, setDead] = useState(false);
  const [paused, setPaused] = useState(false);
  const [invaders, setInvaders] = useState<Invader[]>(() => spawnWave(1));
  const [bullets, setBullets] = useState<Bullet[]>([]);
  const [enemyBullets, setEnemyBullets] = useState<Bullet[]>([]);

  const session = useGameSession("space_invaders");
  const exitToMenu = () => {
    session.recordPlaytimeOnly();
    onExit();
  };

  const resetAll = () => {
    session.restartSession();
    shipXRef.current = W / 2 - 22;
    waveRef.current = 1;
    scoreRef.current = 0;
    livesRef.current = 3;
    deadRef.current = false;
    pausedRef.current = false;
    invadersRef.current = spawnWave(1);
    bulletsRef.current = [];
    enemyBulletsRef.current = [];
    shieldsRef.current = spawnShields();
    shotCooldownRef.current = 0;
    setShipX(W / 2 - 22);
    setWave(1);
    setScore(0);
    setLives(3);
    setDead(false);
    setPaused(false);
    setInvaders(invadersRef.current);
    setBullets([]);
    setEnemyBullets([]);
  };

  const firePlayerShot = () => {
    if (deadRef.current || pausedRef.current || shotCooldownRef.current > 0) return;
    setBullets((prev) => {
      if (prev.length >= 6) return prev;
      const next = [...prev, { x: shipXRef.current + 20, y: SHIP_Y - 10 }];
      bulletsRef.current = next;
      shotCooldownRef.current = SHOT_COOLDOWN_FRAMES;
      return next;
    });
  };

  useEffect(() => {
    const kd = (e: KeyboardEvent) => {
      keysRef.current.add(e.key);
      if (e.key === "q" || e.key === "Escape") {
        exitToMenu();
        return;
      }
      if (e.key === "r") {
        resetAll();
        return;
      }
      if (e.key === "p" && !deadRef.current) {
        setPaused((v) => {
          const next = !v;
          pausedRef.current = next;
          return next;
        });
        return;
      }
      if (e.key === " " && !deadRef.current) {
        e.preventDefault();
        firePlayerShot();
      }
    };
    const ku = (e: KeyboardEvent) => keysRef.current.delete(e.key);
    window.addEventListener("keydown", kd);
    window.addEventListener("keyup", ku);
    return () => {
      window.removeEventListener("keydown", kd);
      window.removeEventListener("keyup", ku);
    };
  }, [exitToMenu]);

  useEffect(() => { shipXRef.current = shipX; }, [shipX]);
  useEffect(() => { waveRef.current = wave; }, [wave]);
  useEffect(() => { scoreRef.current = score; }, [score]);
  useEffect(() => { livesRef.current = lives; }, [lives]);
  useEffect(() => { deadRef.current = dead; }, [dead]);
  useEffect(() => { pausedRef.current = paused; }, [paused]);
  useEffect(() => { invadersRef.current = invaders; }, [invaders]);
  useEffect(() => { bulletsRef.current = bullets; }, [bullets]);
  useEffect(() => { enemyBulletsRef.current = enemyBullets; }, [enemyBullets]);

  useEffect(() => {
    if (!dead) return;
    session.recordResult({
      score,
      won: false,
      extra: {
        wave_reached: wave
      }
    });
  }, [dead, score, session, wave]);

  useEffect(() => {
    const tick = () => {
      if (!deadRef.current && !pausedRef.current) {
        if (shotCooldownRef.current > 0) {
          shotCooldownRef.current -= 1;
        }

        setShipX((x) => {
          let nx = x;
          if (keysRef.current.has("ArrowLeft") || keysRef.current.has("a")) nx -= 7;
          if (keysRef.current.has("ArrowRight") || keysRef.current.has("d")) nx += 7;
          const clamped = Math.max(8, Math.min(W - 52, nx));
          shipXRef.current = clamped;
          return clamped;
        });

        setBullets((prev) => {
          const next = prev.map((b) => ({ ...b, y: b.y - 10 })).filter((b) => b.y > -20);
          bulletsRef.current = next;
          return next;
        });

        setEnemyBullets((prev) => {
          const next = prev.map((b) => ({ ...b, y: b.y + 6 })).filter((b) => b.y < H + 20);
          enemyBulletsRef.current = next;
          return next;
        });

        setInvaders((prev) => {
          const step = 0.5 + waveRef.current * 0.08;
          let edge = false;
          const moved = prev.map((i) => {
            const nx = i.x + i.dir * step;
            if (nx < 16 || nx > W - 56) edge = true;
            return { ...i, x: nx };
          });
          if (edge) {
            const dropped = moved.map((i) => ({ ...i, y: i.y + 16, dir: -i.dir }));
            invadersRef.current = dropped;
            return dropped;
          }
          invadersRef.current = moved;
          return moved;
        });

        setInvaders((prevInv) => {
          const bulletsNow = [...bulletsRef.current];
          const survivors = prevInv.filter((inv) => {
            const hitIndex = bulletsNow.findIndex((b) => b.x >= inv.x && b.x <= inv.x + INV_W && b.y >= inv.y && b.y <= inv.y + INV_H);
            if (hitIndex >= 0) {
              bulletsNow.splice(hitIndex, 1);
              setScore((s) => s + 10);
              return false;
            }
            return true;
          });
          bulletsRef.current = bulletsNow;
          setBullets(bulletsNow);

          if (survivors.length === 0) {
            const nw = waveRef.current + 1;
            waveRef.current = nw;
            setWave(nw);
            const nextWave = spawnWave(nw);
            shieldsRef.current = spawnShields();
            invadersRef.current = nextWave;
            return nextWave;
          }
          invadersRef.current = survivors;
          return survivors;
        });

        if (Math.random() < 0.03 && invadersRef.current.length > 0) {
          const shooter = invadersRef.current[Math.floor(Math.random() * invadersRef.current.length)];
          if (shooter) setEnemyBullets((b) => [...b, { x: shooter.x + 20, y: shooter.y + 26 }]);
        }

        setEnemyBullets((prev) => {
          const sx = shipXRef.current;
          const hit = prev.some((b) => b.x >= sx && b.x <= sx + SHIP_W && b.y >= SHIP_Y && b.y <= SHIP_Y + SHIP_H);
          if (hit) {
            setLives((l) => {
              const nl = l - 1;
              if (nl <= 0) {
                setDead(true);
                deadRef.current = true;
              }
              return nl;
            });
            enemyBulletsRef.current = [];
            return [];
          }
          enemyBulletsRef.current = prev;
          return prev;
        });

        const shieldResult = applyShieldDamage(shieldsRef.current, bulletsRef.current, enemyBulletsRef.current);
        if (shieldResult.changed) {
          shieldsRef.current = shieldResult.shields;
          if (shieldResult.playerBullets.length !== bulletsRef.current.length) {
            bulletsRef.current = shieldResult.playerBullets;
            setBullets(shieldResult.playerBullets);
          }
          if (shieldResult.enemyBullets.length !== enemyBulletsRef.current.length) {
            enemyBulletsRef.current = shieldResult.enemyBullets;
            setEnemyBullets(shieldResult.enemyBullets);
          }
        }

        if (invadersRef.current.some((inv) => inv.y + INV_H >= SHIP_Y || (inv.x + INV_W >= shipXRef.current && inv.x <= shipXRef.current + SHIP_W && inv.y + INV_H >= SHIP_Y))) {
          setDead(true);
          deadRef.current = true;
        }
      }

      draw(canvasRef.current, {
        shipX: shipXRef.current,
        invaders: invadersRef.current,
        bullets: bulletsRef.current,
        enemyBullets: enemyBulletsRef.current,
        shields: shieldsRef.current,
        score: scoreRef.current,
        lives: livesRef.current,
        dead: deadRef.current,
        paused: pausedRef.current,
        wave: waveRef.current
      });

      frameRef.current = requestAnimationFrame(tick);
    };

    frameRef.current = requestAnimationFrame(tick);
    return () => {
      if (frameRef.current != null) cancelAnimationFrame(frameRef.current);
    };
  }, []);

  return (
    <section className="space-screen">
      <header className="space-header">
        <div>
          <h1>Space Invaders</h1>
          <p>Defend against waves. Space shoot, P pause, R reset.</p>
        </div>
        <button type="button" onClick={exitToMenu}>Back to Menu</button>
      </header>
      <canvas ref={canvasRef} width={W} height={H} className="space-canvas" />
      {controlScheme === "buttons" && (
        <MobileControls
          dpad={{ left: () => setShipX((x) => Math.max(8, x - 24)), right: () => setShipX((x) => Math.min(W - 52, x + 24)) }}
          actions={[
            { label: "Shoot", onPress: firePlayerShot },
            {
              label: paused ? "Resume" : "Pause",
              onPress: () => setPaused((v) => {
                const next = !v;
                pausedRef.current = next;
                return next;
              })
            },
            { label: "Reset", onPress: resetAll },
            { label: "Menu", onPress: exitToMenu }
          ]}
        />
      )}
    </section>
  );
}

function spawnWave(w: number): Invader[] {
  const out: Invader[] = [];
  const rows = Math.min(5, 2 + Math.floor(w / 2));
  const cols = Math.min(10, 6 + w);
  const step = 54;
  const gridW = cols * step;
  const sx = (W - gridW) / 2;
  for (let r = 0; r < rows; r += 1) {
    for (let c = 0; c < cols; c += 1) {
      out.push({ x: sx + c * step, y: 96 + r * 46, dir: 1 });
    }
  }
  return out;
}

function spawnShields(): Shield[] {
  const shieldW = 78;
  const shieldH = 26;
  const gap = 42;
  const total = shieldW * 4 + gap * 3;
  const startX = Math.floor((W - total) / 2);
  return Array.from({ length: 4 }, (_, i) => ({
    x: startX + i * (shieldW + gap),
    y: 540,
    w: shieldW,
    h: shieldH
  }));
}

function applyShieldDamage(shields: Shield[], playerBullets: Bullet[], enemyBullets: Bullet[]) {
  const nextShields = shields.map((s) => ({ ...s }));
  const nextPlayer = [...playerBullets];
  const nextEnemy = [...enemyBullets];
  let changed = false;

  for (const shield of nextShields) {
    for (let i = nextPlayer.length - 1; i >= 0; i -= 1) {
      const b = nextPlayer[i];
      if (b.x >= shield.x && b.x <= shield.x + shield.w && b.y >= shield.y && b.y <= shield.y + shield.h) {
        nextPlayer.splice(i, 1);
        shield.w -= 6;
        changed = true;
      }
    }
    for (let i = nextEnemy.length - 1; i >= 0; i -= 1) {
      const b = nextEnemy[i];
      if (b.x >= shield.x && b.x <= shield.x + shield.w && b.y >= shield.y && b.y <= shield.y + shield.h) {
        nextEnemy.splice(i, 1);
        shield.w -= 8;
        changed = true;
      }
    }
  }

  const alive = nextShields.filter((s) => s.w > 12);
  if (alive.length !== shields.length) {
    changed = true;
  }

  return {
    changed,
    shields: alive,
    playerBullets: nextPlayer,
    enemyBullets: nextEnemy
  };
}

function draw(
  canvas: HTMLCanvasElement | null,
  s: {
    shipX: number;
    invaders: Array<{ x: number; y: number }>;
    bullets: Array<{ x: number; y: number }>;
    enemyBullets: Array<{ x: number; y: number }>;
    shields: Array<{ x: number; y: number; w: number; h: number }>;
    score: number;
    lives: number;
    dead: boolean;
    paused: boolean;
    wave: number;
  }
): void {
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  if (!ctx) return;

  ctx.fillStyle = "#060b17";
  ctx.fillRect(0, 0, W, H);

  for (let i = 0; i < 120; i += 1) {
    ctx.fillStyle = "rgba(170,180,210,0.35)";
    ctx.fillRect((i * 47) % W, (i * 23) % H, 1, 1);
  }

  for (const shield of s.shields) {
    ctx.fillStyle = "rgba(37, 89, 153, 0.45)";
    ctx.fillRect(shield.x, shield.y, shield.w, shield.h);
    ctx.strokeStyle = "rgba(76, 201, 240, 0.7)";
    ctx.strokeRect(shield.x, shield.y, shield.w, shield.h);
  }

  for (const inv of s.invaders) {
    ctx.fillStyle = "#70e000";
    ctx.fillRect(inv.x, inv.y, INV_W, INV_H);
    ctx.strokeStyle = "rgba(255,255,255,0.5)";
    ctx.strokeRect(inv.x, inv.y, INV_W, INV_H);
  }

  ctx.fillStyle = "#4cc9f0";
  ctx.beginPath();
  ctx.moveTo(s.shipX + 22, SHIP_Y);
  ctx.lineTo(s.shipX + 2, SHIP_Y + SHIP_H);
  ctx.lineTo(s.shipX + 42, SHIP_Y + SHIP_H);
  ctx.closePath();
  ctx.fill();

  ctx.fillStyle = "#ffd166";
  for (const b of s.bullets) ctx.fillRect(b.x, b.y, 4, 12);
  ctx.fillStyle = "#ff5d73";
  for (const b of s.enemyBullets) ctx.fillRect(b.x, b.y, 4, 12);

  ctx.fillStyle = "#8d99ae";
  ctx.font = "bold 18px Trebuchet MS";
  ctx.fillText(`Score ${s.score}`, 16, 28);
  ctx.fillText(`Wave ${s.wave}`, 180, 28);
  ctx.fillText(`Lives ${s.lives}`, 290, 28);

  if (s.dead || s.paused) {
    ctx.fillStyle = "rgba(0,0,0,0.6)";
    ctx.fillRect(0, 0, W, H);
    ctx.fillStyle = s.paused ? "#edf2f4" : "#ff4d6d";
    ctx.font = "bold 52px Trebuchet MS";
    ctx.textAlign = "center";
    ctx.fillText(s.paused ? "PAUSED" : "GAME OVER", W / 2, H / 2);
    ctx.textAlign = "left";
  }
}

export default SpaceInvadersGame;
