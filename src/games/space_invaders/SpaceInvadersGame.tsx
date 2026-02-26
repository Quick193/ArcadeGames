import { useEffect, useRef, useState } from "react";
import MobileControls from "../../components/ui/MobileControls";
import { useGameSession } from "../../services/progression/useGameSession";
import type { ControlScheme } from "../../types/settings";
import "./space.css";

const W = 540;
const H = 900;
const SHIP_Y = H - 78;

interface SpaceInvadersGameProps {
  onExit: () => void;
  controlScheme: ControlScheme;
}

function SpaceInvadersGame({ onExit, controlScheme }: SpaceInvadersGameProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const frameRef = useRef<number | null>(null);
  const keysRef = useRef<Set<string>>(new Set());

  const [shipX, setShipX] = useState(W / 2 - 22);
  const [wave, setWave] = useState(1);
  const [score, setScore] = useState(0);
  const [lives, setLives] = useState(3);
  const [dead, setDead] = useState(false);
  const [invaders, setInvaders] = useState(() => spawnWave(1));
  const [bullets, setBullets] = useState<Array<{ x: number; y: number }>>([]);
  const [enemyBullets, setEnemyBullets] = useState<Array<{ x: number; y: number }>>([]);
  const session = useGameSession("space_invaders");
  const exitToMenu = () => {
    session.recordPlaytimeOnly();
    onExit();
  };

  const resetAll = () => {
    session.restartSession();
    setShipX(W / 2 - 22);
    setWave(1);
    setScore(0);
    setLives(3);
    setDead(false);
    setInvaders(spawnWave(1));
    setBullets([]);
    setEnemyBullets([]);
  };

  useEffect(() => {
    const kd = (e: KeyboardEvent) => {
      keysRef.current.add(e.key);
      if (e.key === "q" || e.key === "Escape") exitToMenu();
      if (e.key === "r") resetAll();
      if (e.key === " " && !dead) {
        setBullets((b) => (b.length < 6 ? [...b, { x: shipX + 20, y: SHIP_Y - 10 }] : b));
      }
    };
    const ku = (e: KeyboardEvent) => keysRef.current.delete(e.key);
    window.addEventListener("keydown", kd);
    window.addEventListener("keyup", ku);
    return () => {
      window.removeEventListener("keydown", kd);
      window.removeEventListener("keyup", ku);
    };
  }, [dead, exitToMenu, shipX]);

  useEffect(() => {
    if (!dead) {
      return;
    }
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
      if (!dead) {
        setShipX((x) => {
          let nx = x;
          if (keysRef.current.has("ArrowLeft") || keysRef.current.has("a")) nx -= 7;
          if (keysRef.current.has("ArrowRight") || keysRef.current.has("d")) nx += 7;
          return Math.max(8, Math.min(W - 52, nx));
        });

        setBullets((prev) => prev.map((b) => ({ ...b, y: b.y - 10 })).filter((b) => b.y > -20));
        setEnemyBullets((prev) => prev.map((b) => ({ ...b, y: b.y + 6 })).filter((b) => b.y < H + 20));

        setInvaders((prev) => {
          const step = 0.5 + wave * 0.08;
          let edge = false;
          const moved = prev.map((i) => {
            const nx = i.x + i.dir * step;
            if (nx < 16 || nx > W - 56) edge = true;
            return { ...i, x: nx };
          });
          if (edge) {
            return moved.map((i) => ({ ...i, y: i.y + 16, dir: -i.dir }));
          }
          return moved;
        });

        setInvaders((prevInv) => {
          const bulletsNow = [...bullets];
          const survivors = prevInv.filter((inv) => {
            const hitIndex = bulletsNow.findIndex((b) => b.x >= inv.x && b.x <= inv.x + 40 && b.y >= inv.y && b.y <= inv.y + 26);
            if (hitIndex >= 0) {
              bulletsNow.splice(hitIndex, 1);
              setScore((s) => s + 10);
              return false;
            }
            return true;
          });
          setBullets(bulletsNow);
          if (survivors.length === 0) {
            const nw = wave + 1;
            setWave(nw);
            return spawnWave(nw);
          }
          return survivors;
        });

        if (Math.random() < 0.03 && invaders.length > 0) {
          const shooter = invaders[Math.floor(Math.random() * invaders.length)];
          if (shooter) setEnemyBullets((b) => [...b, { x: shooter.x + 20, y: shooter.y + 26 }]);
        }

        setEnemyBullets((prev) => {
          const hit = prev.some((b) => b.x >= shipX && b.x <= shipX + 44 && b.y >= SHIP_Y && b.y <= SHIP_Y + 28);
          if (hit) {
            setLives((l) => {
              const nl = l - 1;
              if (nl <= 0) setDead(true);
              return nl;
            });
            return [];
          }
          return prev;
        });
      }

      draw(canvasRef.current, { shipX, invaders, bullets, enemyBullets, score, lives, dead, wave });
      frameRef.current = requestAnimationFrame(tick);
    };

    frameRef.current = requestAnimationFrame(tick);
    return () => { if (frameRef.current != null) cancelAnimationFrame(frameRef.current); };
  }, [bullets, dead, enemyBullets, invaders, lives, score, shipX, wave]);

  return (
    <section className="space-screen">
      <header className="space-header">
        <div>
          <h1>Space Invaders</h1>
          <p>Defend against waves. Space shoot, R reset.</p>
        </div>
        <button type="button" onClick={exitToMenu}>Back to Menu</button>
      </header>
      <canvas ref={canvasRef} width={W} height={H} className="space-canvas" />
      {controlScheme === "buttons" && (
        <MobileControls
          dpad={{ left: () => setShipX((x) => Math.max(8, x - 24)), right: () => setShipX((x) => Math.min(W - 52, x + 24)) }}
          actions={[{ label: "Shoot", onPress: () => setBullets((b) => [...b, { x: shipX + 20, y: SHIP_Y - 10 }]) }, { label: "Reset", onPress: resetAll }, { label: "Menu", onPress: exitToMenu }]}
        />
      )}
    </section>
  );
}

function spawnWave(w: number) {
  const out: Array<{ x: number; y: number; dir: number }> = [];
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

function draw(
  canvas: HTMLCanvasElement | null,
  s: {
    shipX: number;
    invaders: Array<{ x: number; y: number }>;
    bullets: Array<{ x: number; y: number }>;
    enemyBullets: Array<{ x: number; y: number }>;
    score: number;
    lives: number;
    dead: boolean;
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

  for (const inv of s.invaders) {
    ctx.fillStyle = "#70e000";
    ctx.fillRect(inv.x, inv.y, 40, 26);
    ctx.strokeStyle = "rgba(255,255,255,0.5)";
    ctx.strokeRect(inv.x, inv.y, 40, 26);
  }

  ctx.fillStyle = "#4cc9f0";
  ctx.beginPath();
  ctx.moveTo(s.shipX + 22, SHIP_Y);
  ctx.lineTo(s.shipX + 2, SHIP_Y + 28);
  ctx.lineTo(s.shipX + 42, SHIP_Y + 28);
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

  if (s.dead) {
    ctx.fillStyle = "rgba(0,0,0,0.6)";
    ctx.fillRect(0,0,W,H);
    ctx.fillStyle = "#ff4d6d";
    ctx.font = "bold 52px Trebuchet MS";
    ctx.textAlign = "center";
    ctx.fillText("GAME OVER", W/2, H/2);
    ctx.textAlign = "left";
  }
}

export default SpaceInvadersGame;
