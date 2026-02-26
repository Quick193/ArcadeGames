import { useEffect, useRef, useState } from "react";
import MobileControls from "../../components/ui/MobileControls";
import { useGameSession } from "../../services/progression/useGameSession";
import type { ControlScheme } from "../../types/settings";
import "./breakout.css";

const W = 540;
const H = 900;
const PAD_W = 110;
const PAD_H = 14;
const PAD_Y = H - 72;
const BALL_R = 9;

interface BreakoutGameProps {
  onExit: () => void;
  controlScheme: ControlScheme;
}

function BreakoutGame({ onExit, controlScheme }: BreakoutGameProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const frameRef = useRef<number | null>(null);
  const keysRef = useRef<Set<string>>(new Set());

  const [padX, setPadX] = useState(W / 2 - PAD_W / 2);
  const [ball, setBall] = useState({ x: W / 2, y: PAD_Y - 52, vx: 4.6, vy: -4.6 });
  const [bricks, setBricks] = useState(() => buildBricks());
  const [score, setScore] = useState(0);
  const [lives, setLives] = useState(3);
  const [dead, setDead] = useState(false);
  const [won, setWon] = useState(false);
  const session = useGameSession("breakout");
  const exitToMenu = () => {
    session.recordPlaytimeOnly();
    onExit();
  };

  const resetAll = () => {
    session.restartSession();
    setPadX(W / 2 - PAD_W / 2);
    setBall({ x: W / 2, y: PAD_Y - 52, vx: 4.6 * (Math.random() < 0.5 ? -1 : 1), vy: -4.6 });
    setBricks(buildBricks());
    setScore(0);
    setLives(3);
    setDead(false);
    setWon(false);
  };

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      keysRef.current.add(e.key);
      if (e.key === "q" || e.key === "Escape") exitToMenu();
      if (e.key === "r") resetAll();
    };
    const onKeyUp = (e: KeyboardEvent) => {
      keysRef.current.delete(e.key);
    };
    window.addEventListener("keydown", onKeyDown);
    window.addEventListener("keyup", onKeyUp);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      window.removeEventListener("keyup", onKeyUp);
    };
  }, [exitToMenu]);

  useEffect(() => {
    if (!dead && !won) {
      return;
    }
    session.recordResult({
      score,
      won
    });
  }, [dead, score, session, won]);

  useEffect(() => {
    const tick = () => {
      if (!dead && !won) {
        setPadX((p) => {
          let next = p;
          if (keysRef.current.has("ArrowLeft") || keysRef.current.has("a")) next -= 8;
          if (keysRef.current.has("ArrowRight") || keysRef.current.has("d")) next += 8;
          return Math.max(24, Math.min(W - PAD_W - 24, next));
        });

        setBall((prevBall) => {
          let x = prevBall.x + prevBall.vx;
          let y = prevBall.y + prevBall.vy;
          let vx = prevBall.vx;
          let vy = prevBall.vy;

          if (x < 10) {
            x = 10;
            vx = Math.abs(vx);
          }
          if (x > W - 10) {
            x = W - 10;
            vx = -Math.abs(vx);
          }
          if (y < 10) {
            y = 10;
            vy = Math.abs(vy);
          }

          if (y >= PAD_Y - 2 && y <= PAD_Y + PAD_H + 4 && x >= padX && x <= padX + PAD_W && vy > 0) {
            vy = -Math.abs(vy);
            const hit = (x - padX) / PAD_W;
            vx = (hit - 0.5) * 10.2;
          }

          setBricks((prev) => {
            const next = [...prev];
            for (let i = 0; i < next.length; i += 1) {
              const b = next[i];
              if (x >= b.x && x <= b.x + b.w && y >= b.y && y <= b.y + b.h) {
                next.splice(i, 1);
                setScore((s) => s + 10);
                vy *= -1;
                break;
              }
            }
            if (next.length === 0) {
              setWon(true);
            }
            return next;
          });

          if (y > H + 12) {
            setLives((l) => {
              const nl = l - 1;
              if (nl <= 0) setDead(true);
              return nl;
            });
            return { x: W / 2, y: PAD_Y - 52, vx: 4.6 * (Math.random() < 0.5 ? -1 : 1), vy: -4.6 };
          }

          return { x, y, vx, vy };
        });
      }

      draw(canvasRef.current, { padX, ball, bricks, score, lives, dead, won });
      frameRef.current = requestAnimationFrame(tick);
    };

    frameRef.current = requestAnimationFrame(tick);
    return () => {
      if (frameRef.current != null) cancelAnimationFrame(frameRef.current);
    };
  }, [ball, bricks, dead, lives, padX, score, won]);

  return (
    <section className="breakout-screen">
      <header className="breakout-header">
        <div>
          <h1>Breakout</h1>
          <p>Break all bricks. R restart, Q menu.</p>
        </div>
        <button type="button" onClick={exitToMenu}>Back to Menu</button>
      </header>

      <canvas ref={canvasRef} className="breakout-canvas" width={W} height={H} />

      {controlScheme === "buttons" && (
        <MobileControls
          dpad={{ left: () => setPadX((p) => Math.max(24, p - 22)), right: () => setPadX((p) => Math.min(W - PAD_W - 24, p + 22)) }}
          actions={[{ label: "Restart", onPress: resetAll }, { label: "Menu", onPress: exitToMenu }]}
        />
      )}
    </section>
  );
}

function buildBricks() {
  const bricks: Array<{ x: number; y: number; w: number; h: number; c: string }> = [];
  const cols = 7;
  const rows = 8;
  const marginX = 24;
  const gap = 6;
  const bw = (W - marginX * 2 - gap * (cols - 1)) / cols;
  const colors = ["#4cc9f0", "#4895ef", "#70e000", "#ffd166", "#fb8500", "#f72585"];

  for (let r = 0; r < rows; r += 1) {
    for (let c = 0; c < cols; c += 1) {
      bricks.push({ x: marginX + c * (bw + gap), y: 110 + r * 30, w: bw, h: 24, c: colors[r % colors.length] });
    }
  }
  return bricks;
}

function draw(
  canvas: HTMLCanvasElement | null,
  state: {
    padX: number;
    ball: { x: number; y: number };
    bricks: Array<{ x: number; y: number; w: number; h: number; c: string }>;
    score: number;
    lives: number;
    dead: boolean;
    won: boolean;
  }
): void {
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  if (!ctx) return;

  ctx.clearRect(0, 0, W, H);
  const g = ctx.createLinearGradient(0, 0, 0, H);
  g.addColorStop(0, "#091325");
  g.addColorStop(1, "#040812");
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, W, H);

  for (const b of state.bricks) {
    ctx.fillStyle = b.c;
    ctx.fillRect(b.x, b.y, b.w, b.h);
    ctx.strokeStyle = "rgba(255,255,255,0.4)";
    ctx.strokeRect(b.x, b.y, b.w, b.h);
  }

  ctx.fillStyle = "#b5179e";
  ctx.fillRect(state.padX, PAD_Y, PAD_W, PAD_H);

  ctx.fillStyle = "#edf2f4";
  ctx.beginPath();
  ctx.arc(state.ball.x, state.ball.y, BALL_R, 0, Math.PI * 2);
  ctx.fill();

  ctx.fillStyle = "#8d99ae";
  ctx.font = "bold 20px Trebuchet MS";
  ctx.fillText(`Score: ${state.score}`, 20, 36);
  ctx.fillText(`Lives: ${state.lives}`, 180, 36);

  if (state.dead || state.won) {
    ctx.fillStyle = "rgba(0,0,0,0.6)";
    ctx.fillRect(0, 0, W, H);
    ctx.fillStyle = state.won ? "#70e000" : "#ff4d6d";
    ctx.font = "bold 52px Trebuchet MS";
    ctx.textAlign = "center";
    ctx.fillText(state.won ? "YOU WIN" : "GAME OVER", W / 2, H / 2);
    ctx.textAlign = "left";
  }
}

export default BreakoutGame;
