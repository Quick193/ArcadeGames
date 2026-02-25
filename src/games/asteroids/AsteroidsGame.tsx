import { useEffect, useRef, useState } from "react";
import MobileControls from "../../components/ui/MobileControls";
import { useGameSession } from "../../services/progression/useGameSession";
import type { ControlScheme } from "../../types/settings";
import "./asteroids.css";

const W = 960;
const H = 600;

interface AsteroidsGameProps {
  onExit: () => void;
  controlScheme: ControlScheme;
}

function AsteroidsGame({ onExit, controlScheme }: AsteroidsGameProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const frameRef = useRef<number | null>(null);
  const keysRef = useRef<Set<string>>(new Set());

  const [ship, setShip] = useState({ x: W / 2, y: H / 2, vx: 0, vy: 0, ang: -90 });
  const [asteroids, setAsteroids] = useState(() => spawnAsteroids(4));
  const [bullets, setBullets] = useState<Array<{ x: number; y: number; vx: number; vy: number; life: number }>>([]);
  const [score, setScore] = useState(0);
  const [lives, setLives] = useState(3);
  const [dead, setDead] = useState(false);
  const [wave, setWave] = useState(1);
  const session = useGameSession("asteroids");
  const exitToMenu = () => {
    session.recordPlaytimeOnly();
    onExit();
  };

  const resetAll = () => {
    session.restartSession();
    setShip({ x: W / 2, y: H / 2, vx: 0, vy: 0, ang: -90 });
    setAsteroids(spawnAsteroids(4));
    setBullets([]);
    setScore(0);
    setLives(3);
    setDead(false);
    setWave(1);
  };

  useEffect(() => {
    const kd = (e: KeyboardEvent) => {
      keysRef.current.add(e.key);
      if (e.key === "q" || e.key === "Escape") exitToMenu();
      if (e.key === "r") resetAll();
      if (e.key === " " && !dead) {
        setBullets((prev) => {
          if (prev.length > 8) return prev;
          const rad = (ship.ang * Math.PI) / 180;
          return [...prev, { x: ship.x + Math.cos(rad) * 20, y: ship.y + Math.sin(rad) * 20, vx: Math.cos(rad) * 9 + ship.vx, vy: Math.sin(rad) * 9 + ship.vy, life: 60 }];
        });
      }
    };
    const ku = (e: KeyboardEvent) => keysRef.current.delete(e.key);
    window.addEventListener("keydown", kd);
    window.addEventListener("keyup", ku);
    return () => {
      window.removeEventListener("keydown", kd);
      window.removeEventListener("keyup", ku);
    };
  }, [dead, exitToMenu, ship]);

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
        setShip((s) => {
          let { x, y, vx, vy, ang } = s;
          if (keysRef.current.has("ArrowLeft") || keysRef.current.has("a")) ang -= 4;
          if (keysRef.current.has("ArrowRight") || keysRef.current.has("d")) ang += 4;
          if (keysRef.current.has("ArrowUp") || keysRef.current.has("w")) {
            const r = (ang * Math.PI) / 180;
            vx += Math.cos(r) * 0.22;
            vy += Math.sin(r) * 0.22;
          }
          vx *= 0.99;
          vy *= 0.99;
          x = wrap(x + vx, W);
          y = wrap(y + vy, H);
          return { x, y, vx, vy, ang };
        });

        setBullets((prev) => prev.map((b) => ({ ...b, x: wrap(b.x + b.vx, W), y: wrap(b.y + b.vy, H), life: b.life - 1 })).filter((b) => b.life > 0));
        setAsteroids((prev) => prev.map((a) => ({ ...a, x: wrap(a.x + a.vx, W), y: wrap(a.y + a.vy, H), ang: a.ang + a.rot })));

        setAsteroids((prev) => {
          let next = [...prev];
          let curBullets = [...bullets];
          for (let i = next.length - 1; i >= 0; i -= 1) {
            const a = next[i];
            const bi = curBullets.findIndex((b) => dist(a.x, a.y, b.x, b.y) < a.r);
            if (bi >= 0) {
              curBullets.splice(bi, 1);
              setScore((s) => s + a.pts);
              if (a.size > 1) {
                next.push(spawnChild(a, a.size - 1), spawnChild(a, a.size - 1));
              }
              next.splice(i, 1);
            }
          }
          if (next.length === 0) {
            setWave((w) => w + 1);
            next = spawnAsteroids(5);
          }
          setBullets(curBullets);
          return next;
        });

        setAsteroids((prev) => {
          if (prev.some((a) => dist(a.x, a.y, ship.x, ship.y) < a.r + 14)) {
            setLives((l) => {
              const nl = l - 1;
              if (nl <= 0) setDead(true);
              return nl;
            });
            setShip({ x: W / 2, y: H / 2, vx: 0, vy: 0, ang: -90 });
          }
          return prev;
        });
      }

      draw(canvasRef.current, { ship, asteroids, bullets, score, lives, dead });
      frameRef.current = requestAnimationFrame(tick);
    };

    frameRef.current = requestAnimationFrame(tick);
    return () => { if (frameRef.current != null) cancelAnimationFrame(frameRef.current); };
  }, [asteroids, bullets, dead, lives, score, ship, wave]);

  return (
    <section className="aster-screen">
      <header className="aster-header">
        <div>
          <h1>Asteroids</h1>
          <p>Rotate, thrust, and blast rocks.</p>
        </div>
        <button type="button" onClick={exitToMenu}>Back to Menu</button>
      </header>
      <canvas ref={canvasRef} width={W} height={H} className="aster-canvas" />
      {controlScheme === "buttons" && (
        <MobileControls
          dpad={{ left: () => setShip((s) => ({ ...s, ang: s.ang - 10 })), right: () => setShip((s) => ({ ...s, ang: s.ang + 10 })), up: () => setShip((s) => ({ ...s, vx: s.vx + Math.cos((s.ang * Math.PI) / 180) * 0.8, vy: s.vy + Math.sin((s.ang * Math.PI) / 180) * 0.8 })) }}
          actions={[{ label: "Shoot", onPress: () => setBullets((prev) => [...prev, { x: ship.x, y: ship.y, vx: Math.cos((ship.ang*Math.PI)/180) * 9, vy: Math.sin((ship.ang*Math.PI)/180) * 9, life: 60 }]) }, { label: "Reset", onPress: resetAll }, { label: "Menu", onPress: exitToMenu }]}
        />
      )}
    </section>
  );
}

function spawnAsteroids(n: number) {
  const out: Array<{ x: number; y: number; vx: number; vy: number; r: number; size: number; ang: number; rot: number; pts: number }> = [];
  for (let i = 0; i < n; i += 1) {
    out.push({ x: Math.random() * W, y: Math.random() * H, vx: rand(-2,2), vy: rand(-2,2), r: 40, size: 3, ang: Math.random() * 360, rot: rand(-1,1), pts: 20 });
  }
  return out;
}

function spawnChild(a: { x: number; y: number }, size: number) {
  const map: Record<number, { r: number; pts: number }> = { 2: { r: 24, pts: 50 }, 1: { r: 12, pts: 100 } };
  const m = map[size] ?? { r: 12, pts: 100 };
  return { x: a.x, y: a.y, vx: rand(-3,3), vy: rand(-3,3), r: m.r, size, ang: Math.random()*360, rot: rand(-1.5,1.5), pts: m.pts };
}

function draw(canvas: HTMLCanvasElement | null, s: any): void {
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  ctx.fillStyle = "#070b16";
  ctx.fillRect(0,0,W,H);

  for (let i=0;i<100;i+=1){ ctx.fillStyle="rgba(200,210,230,0.3)"; ctx.fillRect((i*41)%W,(i*67)%H,1,1); }

  for (const a of s.asteroids){
    ctx.strokeStyle = "#8b93a7";
    ctx.beginPath();
    for (let i=0;i<9;i+=1){
      const r = a.r * (0.75 + (i%3)*0.12);
      const ang = ((a.ang + i*40) * Math.PI)/180;
      const x = a.x + Math.cos(ang)*r;
      const y = a.y + Math.sin(ang)*r;
      if (i===0) ctx.moveTo(x,y); else ctx.lineTo(x,y);
    }
    ctx.closePath();
    ctx.stroke();
  }

  ctx.fillStyle="#ffd166";
  for (const b of s.bullets){ ctx.beginPath(); ctx.arc(b.x,b.y,3,0,Math.PI*2); ctx.fill(); }

  const rad=(s.ship.ang*Math.PI)/180;
  const nose=[s.ship.x+Math.cos(rad)*16,s.ship.y+Math.sin(rad)*16];
  const l=[s.ship.x+Math.cos(rad+2.5)*12,s.ship.y+Math.sin(rad+2.5)*12];
  const r=[s.ship.x+Math.cos(rad-2.5)*12,s.ship.y+Math.sin(rad-2.5)*12];
  ctx.strokeStyle="#4cc9f0";
  ctx.beginPath(); ctx.moveTo(nose[0],nose[1]); ctx.lineTo(l[0],l[1]); ctx.lineTo(r[0],r[1]); ctx.closePath(); ctx.stroke();

  ctx.fillStyle="#8d99ae"; ctx.font="bold 18px Trebuchet MS";
  ctx.fillText(`Score ${s.score}`, 16, 28); ctx.fillText(`Lives ${s.lives}`, 160, 28);

  if (s.dead){ ctx.fillStyle="rgba(0,0,0,0.6)"; ctx.fillRect(0,0,W,H); ctx.fillStyle="#ff4d6d"; ctx.font="bold 52px Trebuchet MS"; ctx.textAlign="center"; ctx.fillText("GAME OVER",W/2,H/2); ctx.textAlign="left"; }
}

function wrap(v:number,max:number){ if(v<0)return v+max; if(v>max)return v-max; return v; }
function rand(a:number,b:number){ return a + Math.random()*(b-a); }
function dist(ax:number,ay:number,bx:number,by:number){ return Math.hypot(ax-bx,ay-by); }

export default AsteroidsGame;
