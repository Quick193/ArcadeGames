import { useEffect, useRef, useState, type MutableRefObject } from "react";
import MobileControls from "../../components/ui/MobileControls";
import { useGameSession } from "../../services/progression/useGameSession";
import type { ControlScheme } from "../../types/settings";
import "./runner.css";

const W = 540;
const H = 900;

const GROUND_Y = Math.floor(H * 0.856);
const GRAVITY = 0.92;
const JUMP_POWER = -15.8;
const MAX_FALL = 18;
const BASE_SPEED = 6.9;

interface Obstacle {
  type: "cactus" | "bird";
  x: number;
  y: number;
  w: number;
  h: number;
  phase: number;
}

interface PlayerRect {
  x: number;
  y: number;
  w: number;
  h: number;
}

interface NeonBlobDashGameProps {
  onExit: () => void;
  controlScheme: ControlScheme;
}

function NeonBlobDashGame({ onExit, controlScheme }: NeonBlobDashGameProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const frameRef = useRef<number | null>(null);
  const lastRef = useRef<number | null>(null);

  const keysRef = useRef<Set<string>>(new Set());
  const downHeldRef = useRef(false);
  const manualDuckRef = useRef(false);

  const dinoRef = useRef<PlayerRect>({ x: 130, y: GROUND_Y - 50, w: 44, h: 50 });
  const onGroundRef = useRef(true);
  const vyRef = useRef(0);
  const speedRef = useRef(BASE_SPEED);
  const scoreRef = useRef(0);
  const groundScrollRef = useRef(0);
  const spawnCdRef = useRef(1050);
  const obstaclesRef = useRef<Obstacle[]>([]);
  const hitFlashRef = useRef(0);

  const pausedRef = useRef(false);
  const deadRef = useRef(false);
  const newBestRef = useRef(false);

  const [score, setScore] = useState(0);
  const [bestScore, setBestScore] = useState(() => readBestScore());
  const [paused, setPaused] = useState(false);
  const [dead, setDead] = useState(false);
  const [ducking, setDucking] = useState(false);

  const session = useGameSession("neon_blob_dash");

  const exitToMenu = () => {
    session.recordPlaytimeOnly();
    onExit();
  };

  const applyPaused = (value: boolean) => {
    pausedRef.current = value;
    setPaused(value);
  };

  const applyDead = (value: boolean) => {
    deadRef.current = value;
    setDead(value);
  };

  const reset = () => {
    session.restartSession();
    dinoRef.current = { x: 130, y: GROUND_Y - 50, w: 44, h: 50 };
    onGroundRef.current = true;
    vyRef.current = 0;
    speedRef.current = BASE_SPEED;
    scoreRef.current = 0;
    groundScrollRef.current = 0;
    spawnCdRef.current = 1050;
    obstaclesRef.current = [];
    hitFlashRef.current = 0;
    manualDuckRef.current = false;
    newBestRef.current = false;
    applyPaused(false);
    applyDead(false);
    setScore(0);
    setDucking(false);
  };

  const setDuckState = (value: boolean) => {
    setDucking(value);
  };

  const tryJump = () => {
    if (deadRef.current || pausedRef.current || !onGroundRef.current || manualDuckRef.current || downHeldRef.current) {
      return;
    }
    onGroundRef.current = false;
    vyRef.current = JUMP_POWER;
  };

  const commitScore = () => {
    const finalScore = Math.floor(scoreRef.current);
    const nextBest = Math.max(bestScore, finalScore);
    if (nextBest > bestScore) {
      setBestScore(nextBest);
      writeBestScore(nextBest);
      newBestRef.current = true;
    } else {
      newBestRef.current = false;
    }
    applyDead(true);
  };

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      keysRef.current.add(event.key);

      if (["ArrowUp", "ArrowDown", " ", "Spacebar"].includes(event.key)) {
        event.preventDefault();
      }

      if (event.key === "q" || event.key === "Escape") {
        exitToMenu();
        return;
      }

      if (event.key === "r") {
        reset();
        return;
      }

      if ((event.key === "p" || event.key === "P") && !deadRef.current) {
        applyPaused(!pausedRef.current);
        return;
      }

      if (event.key === "ArrowDown" || event.key === "s" || event.key === "S") {
        downHeldRef.current = true;
      }

      if (event.key === " " || event.key === "Spacebar" || event.key === "ArrowUp") {
        tryJump();
      }
    };

    const onKeyUp = (event: KeyboardEvent) => {
      keysRef.current.delete(event.key);
      if (event.key === "ArrowDown" || event.key === "s" || event.key === "S") {
        downHeldRef.current = false;
      }
    };

    window.addEventListener("keydown", onKeyDown);
    window.addEventListener("keyup", onKeyUp);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      window.removeEventListener("keyup", onKeyUp);
    };
  }, [bestScore, exitToMenu]);

  useEffect(() => {
    if (!dead) {
      return;
    }
    const finalScore = Math.floor(scoreRef.current);
    session.recordResult({
      score: finalScore,
      won: finalScore >= 600
    });
  }, [dead, session]);

  useEffect(() => {
    const tick = (time: number) => {
      if (lastRef.current == null) {
        lastRef.current = time;
      }

      const dt = Math.min(0.05, (time - lastRef.current) / 1000);
      lastRef.current = time;

      updateFrame(dt, {
        dinoRef,
        onGroundRef,
        vyRef,
        speedRef,
        scoreRef,
        groundScrollRef,
        spawnCdRef,
        obstaclesRef,
        hitFlashRef,
        downHeldRef,
        manualDuckRef,
        pausedRef,
        deadRef,
        onSetDucking: setDuckState,
        onSetScore: setScore,
        onDie: commitScore
      });

      drawRunner(canvasRef.current, {
        dino: dinoRef.current,
        obstacles: obstaclesRef.current,
        score: Math.floor(scoreRef.current),
        best: Math.max(bestScore, Math.floor(scoreRef.current)),
        groundScroll: groundScrollRef.current,
        paused: pausedRef.current,
        dead: deadRef.current,
        newBest: newBestRef.current,
        flash: hitFlashRef.current > 0 && Math.floor(hitFlashRef.current * 16) % 2 === 0
      });

      frameRef.current = window.requestAnimationFrame(tick);
    };

    frameRef.current = window.requestAnimationFrame(tick);
    return () => {
      if (frameRef.current != null) {
        window.cancelAnimationFrame(frameRef.current);
      }
    };
  }, [bestScore]);

  return (
    <section className="runner-screen">
      <header className="runner-header">
        <div>
          <h1>Neon Blob Dash</h1>
          <p>Jump, duck, survive. P pause, R restart, Q menu.</p>
        </div>
        <button type="button" onClick={exitToMenu}>Back to Menu</button>
      </header>

      <canvas ref={canvasRef} className="runner-canvas" width={W} height={H} />

      <div className="runner-hud-line">
        <span>Score: {score}</span>
        <span>Best: {bestScore}</span>
        <span>{ducking ? "Ducking" : "Standing"}</span>
        {paused && <span>Paused</span>}
      </div>

      {controlScheme === "buttons" && (
        <MobileControls
          actions={[
            { label: "Jump", onPress: tryJump },
            {
              label: manualDuckRef.current ? "Stand" : "Duck",
              onPress: () => {
                manualDuckRef.current = !manualDuckRef.current;
                if (!manualDuckRef.current) {
                  setDucking(false);
                }
              }
            },
            {
              label: paused ? "Resume" : "Pause",
              onPress: () => {
                if (deadRef.current) {
                  return;
                }
                applyPaused(!pausedRef.current);
              }
            },
            { label: "Restart", onPress: reset },
            { label: "Menu", onPress: exitToMenu }
          ]}
        />
      )}
    </section>
  );
}

interface UpdateFrameArgs {
  dinoRef: MutableRefObject<PlayerRect>;
  onGroundRef: MutableRefObject<boolean>;
  vyRef: MutableRefObject<number>;
  speedRef: MutableRefObject<number>;
  scoreRef: MutableRefObject<number>;
  groundScrollRef: MutableRefObject<number>;
  spawnCdRef: MutableRefObject<number>;
  obstaclesRef: MutableRefObject<Obstacle[]>;
  hitFlashRef: MutableRefObject<number>;
  downHeldRef: MutableRefObject<boolean>;
  manualDuckRef: MutableRefObject<boolean>;
  pausedRef: MutableRefObject<boolean>;
  deadRef: MutableRefObject<boolean>;
  onSetDucking: (value: boolean) => void;
  onSetScore: (value: number) => void;
  onDie: () => void;
}

function updateFrame(dt: number, args: UpdateFrameArgs): void {
  if (args.pausedRef.current || args.deadRef.current) {
    return;
  }

  const dts = dt * 60;
  const dino = args.dinoRef.current;
  const standingH = 50;
  const standingW = 44;
  const duckH = 30;
  const duckW = 60;

  const wantsDuck = (args.downHeldRef.current || args.manualDuckRef.current) && args.onGroundRef.current;
  if (wantsDuck) {
    dino.h = duckH;
    dino.w = duckW;
    dino.y = GROUND_Y - dino.h;
  } else {
    const bottom = dino.y + dino.h;
    dino.h = standingH;
    dino.w = standingW;
    dino.y = args.onGroundRef.current ? GROUND_Y - standingH : bottom - standingH;
  }
  args.onSetDucking(wantsDuck);

  args.speedRef.current = Math.min(12.2, args.speedRef.current + 0.08 * dt);
  args.scoreRef.current += dt * 25;
  args.groundScrollRef.current = (args.groundScrollRef.current + args.speedRef.current * dts) % 64;
  args.hitFlashRef.current = Math.max(0, args.hitFlashRef.current - dt);

  if (!args.onGroundRef.current) {
    args.vyRef.current = Math.min(args.vyRef.current + GRAVITY * dts, MAX_FALL);
    dino.y += args.vyRef.current * dts;
    if (dino.y + dino.h >= GROUND_Y) {
      dino.y = GROUND_Y - dino.h;
      args.vyRef.current = 0;
      args.onGroundRef.current = true;
    }
  }

  args.spawnCdRef.current -= dt * 1000;
  if (args.spawnCdRef.current <= 0) {
    spawnObstacle(args.obstaclesRef.current);
    const min = Math.max(620, Math.floor(1220 - args.speedRef.current * 22));
    const max = Math.max(800, Math.floor(1660 - args.speedRef.current * 24));
    args.spawnCdRef.current = randomInt(min, max);
  }

  const movePx = args.speedRef.current * dts;
  for (const obstacle of args.obstaclesRef.current) {
    obstacle.x -= movePx;
    if (obstacle.type === "bird") {
      obstacle.phase += 0.16 * dts;
      obstacle.y += Math.sin(obstacle.phase) * 1.25;
    }
  }

  args.obstaclesRef.current = args.obstaclesRef.current.filter((o) => o.x + o.w > -80);

  const dinoHitbox = shrinkRect(dino, 10, 8);
  for (const obstacle of args.obstaclesRef.current) {
    if (rectsOverlap(dinoHitbox, shrinkRect(obstacle, 6, 6))) {
      args.hitFlashRef.current = 0.5;
      args.onDie();
      break;
    }
  }

  args.onSetScore(Math.floor(args.scoreRef.current));
}

function spawnObstacle(obstacles: Obstacle[]): void {
  if (Math.random() < 0.7) {
    const w = pick([26, 34, 42]);
    const h = pick([42, 52, 62]);
    obstacles.push({
      type: "cactus",
      x: W + 20,
      y: GROUND_Y - h,
      w,
      h,
      phase: 0
    });
    return;
  }

  const y = pick([GROUND_Y - 90, GROUND_Y - 130, GROUND_Y - 55]);
  obstacles.push({
    type: "bird",
    x: W + 20,
    y,
    w: 42,
    h: 26,
    phase: 0
  });
}

interface DrawState {
  dino: PlayerRect;
  obstacles: Obstacle[];
  score: number;
  best: number;
  groundScroll: number;
  paused: boolean;
  dead: boolean;
  newBest: boolean;
  flash: boolean;
}

function drawRunner(canvas: HTMLCanvasElement | null, state: DrawState): void {
  if (!canvas) {
    return;
  }
  const ctx = canvas.getContext("2d");
  if (!ctx) {
    return;
  }

  const bg = ctx.createLinearGradient(0, 0, 0, H);
  bg.addColorStop(0, "#050d1b");
  bg.addColorStop(1, "#030811");
  ctx.fillStyle = bg;
  ctx.fillRect(0, 0, W, H);

  for (let i = 0; i < 5; i += 1) {
    const y = 140 + i * 62;
    ctx.strokeStyle = `rgba(${26 + i * 8}, ${36 + i * 8}, ${56 + i * 10}, 0.55)`;
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(W, y);
    ctx.stroke();
  }

  ctx.fillStyle = "#232a38";
  ctx.fillRect(0, GROUND_Y, W, H - GROUND_Y);
  ctx.strokeStyle = "#2f3f5c";
  ctx.lineWidth = 2;
  for (let x = -64; x <= W + 64; x += 64) {
    const gx = Math.floor(x - state.groundScroll);
    ctx.beginPath();
    ctx.moveTo(gx, GROUND_Y + 16);
    ctx.lineTo(gx + 32, GROUND_Y + 16);
    ctx.stroke();
  }

  for (const obstacle of state.obstacles) {
    if (obstacle.type === "cactus") {
      ctx.fillStyle = "#56d36c";
      roundRect(ctx, obstacle.x, obstacle.y, obstacle.w, obstacle.h, 4);
      ctx.fill();

      ctx.strokeStyle = "rgba(237,242,244,0.65)";
      ctx.lineWidth = 1;
      roundRect(ctx, obstacle.x, obstacle.y, obstacle.w, obstacle.h, 4);
      ctx.stroke();

      const armY = obstacle.y + obstacle.h * 0.5;
      ctx.fillStyle = "#56d36c";
      roundRect(ctx, obstacle.x - 8, armY, 8, 10, 2);
      ctx.fill();
      roundRect(ctx, obstacle.x + obstacle.w, armY - 8, 8, 10, 2);
      ctx.fill();
    } else {
      ctx.fillStyle = "#ff9f43";
      ellipse(ctx, obstacle.x + obstacle.w / 2, obstacle.y + obstacle.h / 2, obstacle.w / 2, obstacle.h / 2);
      ctx.fill();
      ctx.strokeStyle = "#edf2f4";
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(obstacle.x + 5, obstacle.y + obstacle.h / 2);
      ctx.lineTo(obstacle.x + obstacle.w - 5, obstacle.y + obstacle.h / 2);
      ctx.stroke();
    }
  }

  const playerColor = state.flash ? "#ff5d73" : "#4cc9f0";
  ctx.fillStyle = playerColor;
  roundRect(ctx, state.dino.x, state.dino.y, state.dino.w, state.dino.h, 8);
  ctx.fill();
  ctx.strokeStyle = "#edf2f4";
  ctx.lineWidth = 1;
  roundRect(ctx, state.dino.x, state.dino.y, state.dino.w, state.dino.h, 8);
  ctx.stroke();
  ctx.fillStyle = "#02050d";
  ctx.beginPath();
  const eyeY = state.dino.y + (state.dino.h <= 32 ? 8 : 10);
  ctx.arc(state.dino.x + state.dino.w - 10, eyeY, 2, 0, Math.PI * 2);
  ctx.fill();

  ctx.fillStyle = "rgba(15, 24, 41, 0.92)";
  roundRect(ctx, 16, 16, 374, 52, 10);
  ctx.fill();
  ctx.strokeStyle = "#2b436a";
  ctx.lineWidth = 1;
  roundRect(ctx, 16, 16, 374, 52, 10);
  ctx.stroke();

  ctx.fillStyle = "#ffd166";
  ctx.font = "bold 18px Trebuchet MS, Segoe UI, sans-serif";
  ctx.fillText(`Score: ${state.score}`, 30, 48);
  ctx.fillStyle = "#4cc9f0";
  ctx.fillText(`Best: ${state.best}`, 178, 48);
  ctx.fillStyle = "#edf2f4";
  ctx.font = "bold 13px Trebuchet MS, Segoe UI, sans-serif";
  ctx.fillText("NEON BLOB DASH", 356, 32);

  ctx.fillStyle = "#8d99ae";
  ctx.font = "13px Trebuchet MS, Segoe UI, sans-serif";
  ctx.textAlign = "center";
  ctx.fillText("Space/^ jump | v duck | P pause | R restart | Q menu", W / 2, H - 24);
  ctx.textAlign = "left";

  if (state.paused || state.dead) {
    ctx.fillStyle = "rgba(0,0,0,0.62)";
    ctx.fillRect(0, 0, W, H);

    if (state.paused) {
      ctx.fillStyle = "#edf2f4";
      ctx.font = "bold 56px Trebuchet MS, Segoe UI, sans-serif";
      ctx.textAlign = "center";
      ctx.fillText("PAUSED", W / 2, H / 2 - 12);
      ctx.fillStyle = "#8d99ae";
      ctx.font = "15px Trebuchet MS, Segoe UI, sans-serif";
      ctx.fillText("P resume | Q menu", W / 2, H / 2 + 28);
      ctx.textAlign = "left";
      return;
    }

    ctx.fillStyle = "#ff4d6d";
    ctx.font = "bold 56px Trebuchet MS, Segoe UI, sans-serif";
    ctx.textAlign = "center";
    ctx.fillText("GAME OVER", W / 2, H / 2 - 24);

    ctx.fillStyle = "#edf2f4";
    ctx.font = "26px Trebuchet MS, Segoe UI, sans-serif";
    ctx.fillText(`Score: ${state.score}`, W / 2, H / 2 + 16);

    if (state.newBest) {
      ctx.fillStyle = "#ffd166";
      ctx.font = "bold 15px Trebuchet MS, Segoe UI, sans-serif";
      ctx.fillText("NEW BEST", W / 2, H / 2 + 44);
    }

    ctx.fillStyle = "#8d99ae";
    ctx.font = "14px Trebuchet MS, Segoe UI, sans-serif";
    ctx.fillText("R restart | Q menu", W / 2, H / 2 + 74);
    ctx.textAlign = "left";
  }
}

function readBestScore(): number {
  const raw = window.localStorage.getItem("arcade.neon_blob_dash.best");
  const parsed = Number(raw);
  return Number.isFinite(parsed) ? parsed : 0;
}

function writeBestScore(score: number): void {
  window.localStorage.setItem("arcade.neon_blob_dash.best", String(score));
}

function shrinkRect(rect: PlayerRect, x: number, y: number): PlayerRect {
  return {
    x: rect.x + x / 2,
    y: rect.y + y / 2,
    w: Math.max(1, rect.w - x),
    h: Math.max(1, rect.h - y)
  };
}

function rectsOverlap(a: PlayerRect, b: PlayerRect): boolean {
  return a.x < b.x + b.w && a.x + a.w > b.x && a.y < b.y + b.h && a.y + a.h > b.y;
}

function roundRect(ctx: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, r: number): void {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}

function ellipse(ctx: CanvasRenderingContext2D, x: number, y: number, rx: number, ry: number): void {
  ctx.beginPath();
  ctx.ellipse(x, y, rx, ry, 0, 0, Math.PI * 2);
}

function randomInt(min: number, max: number): number {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

function pick<T>(arr: T[]): T {
  return arr[Math.floor(Math.random() * arr.length)] as T;
}

export default NeonBlobDashGame;
