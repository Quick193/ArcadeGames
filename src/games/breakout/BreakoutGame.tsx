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
const BRICK_ROWS = 6;
const BRICK_COLS = 10;
const BRICK_MARGIN_X = 24;
const BRICK_TOP_Y = 110;
const BRICK_GAP = 6;
const MAX_LEVELS = 4;

interface BreakoutGameProps {
  onExit: () => void;
  controlScheme: ControlScheme;
}

function BreakoutGame({ onExit, controlScheme }: BreakoutGameProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const frameRef = useRef<number | null>(null);
  const keysRef = useRef<Set<string>>(new Set());
  const padXRef = useRef(W / 2 - PAD_W / 2);
  const ballRef = useRef(resetBallForLevel(1));
  const bricksRef = useRef<Array<{ x: number; y: number; w: number; h: number; hp: number; c: string }>>(buildBricks(1));
  const scoreRef = useRef(0);
  const livesRef = useRef(3);
  const deadRef = useRef(false);
  const wonRef = useRef(false);
  const levelRef = useRef(1);
  const pausedRef = useRef(false);

  const [padX, setPadX] = useState(W / 2 - PAD_W / 2);
  const [ball, setBall] = useState(resetBallForLevel(1));
  const [bricks, setBricks] = useState(() => buildBricks(1));
  const [score, setScore] = useState(0);
  const [lives, setLives] = useState(3);
  const [dead, setDead] = useState(false);
  const [won, setWon] = useState(false);
  const [level, setLevel] = useState(1);
  const [paused, setPaused] = useState(false);
  const session = useGameSession("breakout");
  const exitToMenu = () => {
    session.recordPlaytimeOnly();
    onExit();
  };

  const resetAll = () => {
    session.restartSession();
    padXRef.current = W / 2 - PAD_W / 2;
    levelRef.current = 1;
    pausedRef.current = false;
    ballRef.current = resetBallForLevel(1);
    bricksRef.current = buildBricks(1);
    scoreRef.current = 0;
    livesRef.current = 3;
    deadRef.current = false;
    wonRef.current = false;
    setPadX(W / 2 - PAD_W / 2);
    setBall(ballRef.current);
    setBricks(bricksRef.current);
    setScore(0);
    setLives(3);
    setDead(false);
    setWon(false);
    setLevel(1);
    setPaused(false);
  };

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      keysRef.current.add(e.key);
      if (e.key === "q" || e.key === "Escape") exitToMenu();
      if (e.key === "r") resetAll();
      if (e.key === "p" && !deadRef.current && !wonRef.current) {
        setPaused((v) => {
          const next = !v;
          pausedRef.current = next;
          return next;
        });
      }
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
    padXRef.current = padX;
  }, [padX]);

  useEffect(() => {
    ballRef.current = ball;
  }, [ball]);

  useEffect(() => {
    bricksRef.current = bricks;
  }, [bricks]);

  useEffect(() => {
    scoreRef.current = score;
  }, [score]);

  useEffect(() => {
    livesRef.current = lives;
  }, [lives]);

  useEffect(() => {
    deadRef.current = dead;
  }, [dead]);

  useEffect(() => {
    wonRef.current = won;
  }, [won]);

  useEffect(() => {
    levelRef.current = level;
  }, [level]);

  useEffect(() => {
    pausedRef.current = paused;
  }, [paused]);

  useEffect(() => {
    const tick = () => {
      if (!deadRef.current && !wonRef.current && !pausedRef.current) {
        setPadX((p) => {
          let next = p;
          if (keysRef.current.has("ArrowLeft") || keysRef.current.has("a")) next -= 8;
          if (keysRef.current.has("ArrowRight") || keysRef.current.has("d")) next += 8;
          const clamped = Math.max(24, Math.min(W - PAD_W - 24, next));
          padXRef.current = clamped;
          return clamped;
        });

        setBall((prevBall) => {
          let vx = prevBall.vx;
          let vy = prevBall.vy;
          let x = prevBall.x;
          let y = prevBall.y;
          let nextBricks = [...bricksRef.current];
          let bricksChanged = false;
          let levelRespawn: { x: number; y: number; vx: number; vy: number } | null = null;
          const steps = Math.max(1, Math.floor((Math.abs(vx) + Math.abs(vy)) / 5));

          for (let step = 0; step < steps; step += 1) {
            x += vx / steps;
            y += vy / steps;

            if (x - BALL_R < 0) {
              x = BALL_R;
              vx = Math.abs(vx);
            }
            if (x + BALL_R > W) {
              x = W - BALL_R;
              vx = -Math.abs(vx);
            }
            if (y - BALL_R < 0) {
              y = BALL_R;
              vy = Math.abs(vy);
            }

            const px = padXRef.current;
            if (y + BALL_R >= PAD_Y && y - BALL_R <= PAD_Y + PAD_H && x >= px && x <= px + PAD_W && vy > 0) {
              vy = -Math.abs(vy);
              const hit = (x - px) / PAD_W;
              vx = (hit - 0.5) * 10.2;
            }

            let hitBrick = false;
            for (let i = 0; i < nextBricks.length; i += 1) {
              const b = nextBricks[i];
              if (x + BALL_R >= b.x && x - BALL_R <= b.x + b.w && y + BALL_R >= b.y && y - BALL_R <= b.y + b.h) {
                b.hp -= 1;
                setScore((s) => s + 10);
                if (b.hp <= 0) {
                  nextBricks.splice(i, 1);
                }
                vy *= -1;
                hitBrick = true;
                bricksChanged = true;
                break;
              }
            }

            if (nextBricks.length === 0) {
              if (levelRef.current >= MAX_LEVELS) {
                setWon(true);
                wonRef.current = true;
              } else {
                const nl = levelRef.current + 1;
                levelRef.current = nl;
                setLevel(nl);
                nextBricks = buildBricks(nl);
                levelRespawn = resetBallForLevel(nl);
              }
              bricksChanged = true;
              break;
            }
            if (hitBrick) {
              break;
            }
          }

          if (bricksChanged) {
            bricksRef.current = nextBricks;
            setBricks(nextBricks);
          }

          if (levelRespawn) {
            ballRef.current = levelRespawn;
            return levelRespawn;
          }

          if (y - BALL_R > H + 12) {
            setLives((l) => {
              const nl = l - 1;
              if (nl <= 0) {
                setDead(true);
                deadRef.current = true;
              }
              livesRef.current = nl;
              return nl;
            });
            const respawn = resetBallForLevel(levelRef.current);
            ballRef.current = respawn;
            return respawn;
          }

          const nextBall = { x, y, vx, vy };
          ballRef.current = nextBall;
          return nextBall;
        });
      }

      draw(canvasRef.current, {
        padX: padXRef.current,
        ball: ballRef.current,
        bricks: bricksRef.current,
        score: scoreRef.current,
        lives: livesRef.current,
        level: levelRef.current,
        paused: pausedRef.current,
        dead: deadRef.current,
        won: wonRef.current
      });
      frameRef.current = requestAnimationFrame(tick);
    };

    frameRef.current = requestAnimationFrame(tick);
    return () => {
      if (frameRef.current != null) cancelAnimationFrame(frameRef.current);
    };
  }, []);

  return (
    <section className="breakout-screen">
      <header className="breakout-header">
        <div>
          <h1>Breakout</h1>
          <p>Break all bricks across waves. P pause, R restart, Q menu.</p>
        </div>
        <button type="button" onClick={exitToMenu}>Back to Menu</button>
      </header>

      <canvas ref={canvasRef} className="breakout-canvas" width={W} height={H} />

      {controlScheme === "buttons" && (
        <MobileControls
          dpad={{ left: () => setPadX((p) => Math.max(24, p - 22)), right: () => setPadX((p) => Math.min(W - PAD_W - 24, p + 22)) }}
          actions={[{ label: paused ? "Resume" : "Pause", onPress: () => setPaused((v) => { const next = !v; pausedRef.current = next; return next; }) }, { label: "Restart", onPress: resetAll }, { label: "Menu", onPress: exitToMenu }]}
        />
      )}
    </section>
  );
}

function buildBricks(level: number) {
  const bricks: Array<{ x: number; y: number; w: number; h: number; hp: number; c: string }> = [];
  const bw = (W - BRICK_MARGIN_X * 2 - BRICK_GAP * (BRICK_COLS - 1)) / BRICK_COLS;
  const colors = ["#4cc9f0", "#4895ef", "#70e000", "#ffd166", "#fb8500", "#f72585"];

  for (let r = 0; r < BRICK_ROWS; r += 1) {
    for (let c = 0; c < BRICK_COLS; c += 1) {
      const hp = level >= 3 && r < 2 ? 2 : 1;
      bricks.push({ x: BRICK_MARGIN_X + c * (bw + BRICK_GAP), y: BRICK_TOP_Y + r * (24 + BRICK_GAP), w: bw, h: 24, hp, c: colors[r % colors.length] });
    }
  }
  return bricks;
}

function resetBallForLevel(level: number) {
  const spd = 4.8 + (level - 1) * 0.4;
  return { x: W / 2, y: PAD_Y - 52, vx: spd * (Math.random() < 0.5 ? -1 : 1), vy: -spd };
}

function draw(
  canvas: HTMLCanvasElement | null,
  state: {
    padX: number;
    ball: { x: number; y: number };
    bricks: Array<{ x: number; y: number; w: number; h: number; hp: number; c: string }>;
    score: number;
    lives: number;
    level: number;
    paused: boolean;
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
    ctx.fillStyle = b.hp > 1 ? darkenHex(b.c, 0.26) : b.c;
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
  ctx.fillText(`Level: ${state.level}`, 320, 36);

  if (state.paused || state.dead || state.won) {
    ctx.fillStyle = "rgba(0,0,0,0.6)";
    ctx.fillRect(0, 0, W, H);
    ctx.fillStyle = state.paused ? "#edf2f4" : state.won ? "#70e000" : "#ff4d6d";
    ctx.font = "bold 52px Trebuchet MS";
    ctx.textAlign = "center";
    ctx.fillText(state.paused ? "PAUSED" : state.won ? "YOU WIN" : "GAME OVER", W / 2, H / 2);
    ctx.textAlign = "left";
  }
}

function darkenHex(hex: string, ratio: number): string {
  const h = hex.replace("#", "");
  const n = Number.parseInt(h, 16);
  const r = Math.max(0, Math.floor(((n >> 16) & 255) * (1 - ratio)));
  const g = Math.max(0, Math.floor(((n >> 8) & 255) * (1 - ratio)));
  const b = Math.max(0, Math.floor((n & 255) * (1 - ratio)));
  return `rgb(${r}, ${g}, ${b})`;
}

export default BreakoutGame;
