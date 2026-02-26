import { useEffect, useRef, useState } from "react";
import MobileControls from "../../components/ui/MobileControls";
import { useGameSession } from "../../services/progression/useGameSession";
import type { ControlScheme } from "../../types/settings";
import "./runner.css";

const W = 540;
const H = 900;
const GY = H - 52;

interface NeonBlobDashGameProps {
  onExit: () => void;
  controlScheme: ControlScheme;
}

function NeonBlobDashGame({ onExit, controlScheme }: NeonBlobDashGameProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const frameRef = useRef<number | null>(null);
  const keysRef = useRef<Set<string>>(new Set());

  const [y, setY] = useState(GY - 50);
  const [vy, setVy] = useState(0);
  const [duck, setDuck] = useState(false);
  const [obs, setObs] = useState<Array<{ x: number; y: number; w: number; h: number }>>([]);
  const [score, setScore] = useState(0);
  const [dead, setDead] = useState(false);
  const session = useGameSession("neon_blob_dash");
  const exitToMenu = () => {
    session.recordPlaytimeOnly();
    onExit();
  };

  const reset = () => { session.restartSession(); setY(GY - 50); setVy(0); setDuck(false); setObs([]); setScore(0); setDead(false); };

  useEffect(() => {
    const kd = (e: KeyboardEvent) => {
      keysRef.current.add(e.key);
      if (e.key === "q" || e.key === "Escape") exitToMenu();
      if (e.key === "r") reset();
      if ((e.key === " " || e.key === "ArrowUp") && y >= GY - (duck ? 30 : 50) - 1 && !dead) setVy(-15.8);
    };
    const ku = (e: KeyboardEvent) => keysRef.current.delete(e.key);
    window.addEventListener("keydown", kd); window.addEventListener("keyup", ku);
    return () => { window.removeEventListener("keydown", kd); window.removeEventListener("keyup", ku); };
  }, [dead, duck, exitToMenu, y]);

  useEffect(() => {
    if (!dead) {
      return;
    }
    session.recordResult({
      score: Math.floor(score / 6),
      won: score >= 600
    });
  }, [dead, score, session]);

  useEffect(() => {
    const tick = () => {
      if (!dead) {
        const d = keysRef.current.has("ArrowDown") || keysRef.current.has("s");
        setDuck(d && y >= GY - 50 - 1);
        setVy((v) => Math.min(18, v + 0.92));
        setY((py) => {
          const nh = duck ? 30 : 50;
          const ny = py + vy;
          if (ny + nh >= GY) return GY - nh;
          return ny;
        });

        setObs((prev) => {
          const moved = prev.map((o) => ({ ...o, x: o.x - 8 }));
          const kept = moved.filter((o) => o.x + o.w > -40);
          if (Math.random() < 0.02) kept.push({ x: W + 20, y: GY - (Math.random()<0.7?52:70), w: 34, h: Math.random()<0.7?52:26 });
          const dino = { x: 92, y, w: duck ? 60 : 44, h: duck ? 30 : 50 };
          if (kept.some((o) => overlap(dino, o))) setDead(true);
          return kept;
        });

        setScore((s) => s + 1);
      }
      drawRunner(canvasRef.current, { y, duck, obs, score, dead, title: "NEON BLOB DASH" });
      frameRef.current = requestAnimationFrame(tick);
    };
    frameRef.current = requestAnimationFrame(tick);
    return () => { if (frameRef.current != null) cancelAnimationFrame(frameRef.current); };
  }, [dead, duck, obs, score, vy, y]);

  return (
    <section className="runner-screen">
      <header className="runner-header"><div><h1>Neon Blob Dash</h1><p>Jump and survive.</p></div><button type="button" onClick={exitToMenu}>Back to Menu</button></header>
      <canvas ref={canvasRef} className="runner-canvas" width={W} height={H} />
      {controlScheme === "buttons" && <MobileControls actions={[{ label: "Jump", onPress: () => { if (!dead && y >= GY - (duck?30:50)-1) setVy(-15.8); } }, { label: "Duck", onPress: () => setDuck((d)=>!d) }, { label: "Reset", onPress: reset }, { label: "Menu", onPress: exitToMenu }]} />}
    </section>
  );
}

function drawRunner(canvas: HTMLCanvasElement | null, s: any){
  if(!canvas)return; const ctx=canvas.getContext("2d"); if(!ctx)return;
  ctx.fillStyle="#070c1a"; ctx.fillRect(0,0,W,H);
  ctx.fillStyle="#232b3c"; ctx.fillRect(0,GY,W,H-GY);
  ctx.fillStyle="#4cc9f0"; ctx.fillRect(92,s.y,s.duck?60:44,s.duck?30:50);
  for(const o of s.obs){ ctx.fillStyle="#70e000"; ctx.fillRect(o.x,o.y,o.w,o.h); }
  ctx.fillStyle="#8d99ae"; ctx.font="bold 18px Trebuchet MS"; ctx.fillText(`${s.title}  Score ${Math.floor(s.score/6)}`,16,28);
  if(s.dead){ ctx.fillStyle="rgba(0,0,0,0.58)"; ctx.fillRect(0,0,W,H); ctx.fillStyle="#ff4d6d"; ctx.font="bold 48px Trebuchet MS"; ctx.textAlign="center"; ctx.fillText("GAME OVER",W/2,H/2); ctx.textAlign="left"; }
}

function overlap(a:any,b:any){ return a.x < b.x+b.w && a.x+a.w > b.x && a.y < b.y+b.h && a.y+a.h > b.y; }

export default NeonBlobDashGame;
