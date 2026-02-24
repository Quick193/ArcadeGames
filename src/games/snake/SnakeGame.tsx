import { useEffect, useMemo, useRef, useState } from "react";
import MobileControls from "../../components/ui/MobileControls";
import type { ControlScheme } from "../../types/settings";
import {
  COLS,
  ROWS,
  TILE_SIZE,
  createInitialState,
  getUpdatedDirection,
  step,
  type SnakeState
} from "./snake.logic";
import "./snake.css";

const WIDTH = COLS * TILE_SIZE;
const HEIGHT = ROWS * TILE_SIZE;

interface SnakeGameProps {
  onExit: () => void;
  controlScheme: ControlScheme;
}

function SnakeGame({ onExit, controlScheme }: SnakeGameProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const accumulatorRef = useRef(0);
  const lastTickRef = useRef<number | null>(null);
  const touchStartRef = useRef<{ x: number; y: number } | null>(null);

  const [state, setState] = useState<SnakeState>(() => createInitialState());
  const [isPaused, setIsPaused] = useState(false);
  const [showGrid, setShowGrid] = useState(true);
  const [bestScore, setBestScore] = useState(() => readBestScore());

  const gameOver = state.dead;
  const speedLabel = useMemo(() => `${(1000 / state.stepIntervalMs).toFixed(1)} steps/s`, [state.stepIntervalMs]);

  const applyDirection = (key: string) => {
    if (isPaused || gameOver) {
      return;
    }
    setState((prev) => {
      const nextDir = getUpdatedDirection(prev.dir, key);
      if (!nextDir) {
        return prev;
      }
      return { ...prev, nextDir };
    });
  };

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "q" || event.key === "Escape") {
        onExit();
        return;
      }

      if (event.key === "r") {
        setState(createInitialState());
        setIsPaused(false);
        accumulatorRef.current = 0;
        lastTickRef.current = null;
        return;
      }

      if (event.key === "p" && !gameOver) {
        setIsPaused((prev) => !prev);
        return;
      }

      if (event.key === "g") {
        setShowGrid((prev) => !prev);
        return;
      }

      if (isPaused || gameOver) {
        return;
      }

      applyDirection(event.key);
    };

    window.addEventListener("keydown", onKeyDown);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
    };
  }, [gameOver, isPaused, onExit]);

  useEffect(() => {
    if (!gameOver || state.score <= bestScore) {
      return;
    }
    setBestScore(state.score);
    writeBestScore(state.score);
  }, [bestScore, gameOver, state.score]);

  useEffect(() => {
    let frameId = 0;

    const tick = (time: number) => {
      if (lastTickRef.current == null) {
        lastTickRef.current = time;
      }

      const dt = time - lastTickRef.current;
      lastTickRef.current = time;

      if (!isPaused && !gameOver) {
        accumulatorRef.current += dt;

        setState((prev) => {
          let next = prev;
          while (accumulatorRef.current >= next.stepIntervalMs && !next.dead) {
            accumulatorRef.current -= next.stepIntervalMs;
            next = step(next);
          }
          return next;
        });
      }

      drawFrame(canvasRef.current, state, showGrid, isPaused, bestScore);
      frameId = window.requestAnimationFrame(tick);
    };

    frameId = window.requestAnimationFrame(tick);

    return () => {
      window.cancelAnimationFrame(frameId);
    };
  }, [bestScore, gameOver, isPaused, showGrid, state]);

  return (
    <section className="snake-screen">
      <header className="snake-header">
        <div>
          <h1>Snake</h1>
          <p>Arrow keys move. P pause, G grid, R restart, Q exit.</p>
        </div>
        <button type="button" onClick={onExit}>
          Back to Menu
        </button>
      </header>

      <div className="snake-hud">
        <span>Score: {state.score}</span>
        <span>Best: {bestScore}</span>
        <span>{speedLabel}</span>
        {isPaused && <span>Paused</span>}
        {gameOver && <span>Game Over</span>}
      </div>

      <canvas
        ref={canvasRef}
        width={WIDTH}
        height={HEIGHT}
        className="snake-canvas"
        onTouchStart={(event) => {
          if (controlScheme !== "gestures") {
            return;
          }
          const touch = event.touches[0];
          touchStartRef.current = { x: touch.clientX, y: touch.clientY };
        }}
        onTouchEnd={(event) => {
          if (controlScheme !== "gestures" || !touchStartRef.current) {
            return;
          }
          const touch = event.changedTouches[0];
          const dx = touch.clientX - touchStartRef.current.x;
          const dy = touch.clientY - touchStartRef.current.y;
          touchStartRef.current = null;

          if (Math.abs(dx) < 20 && Math.abs(dy) < 20) {
            setIsPaused((prev) => !prev);
            return;
          }
          if (Math.abs(dx) > Math.abs(dy)) {
            applyDirection(dx > 0 ? "ArrowRight" : "ArrowLeft");
          } else {
            applyDirection(dy > 0 ? "ArrowDown" : "ArrowUp");
          }
        }}
      />

      {controlScheme === "buttons" ? (
        <MobileControls
          dpad={{
            up: () => applyDirection("ArrowUp"),
            down: () => applyDirection("ArrowDown"),
            left: () => applyDirection("ArrowLeft"),
            right: () => applyDirection("ArrowRight")
          }}
          actions={[
            { label: isPaused ? "Resume" : "Pause", onPress: () => setIsPaused((prev) => !prev) },
            {
              label: "Restart",
              onPress: () => {
                setState(createInitialState());
                setIsPaused(false);
                accumulatorRef.current = 0;
                lastTickRef.current = null;
              }
            },
            { label: "Menu", onPress: onExit }
          ]}
        />
      ) : (
        <p className="gesture-hint">Gestures: swipe to move, tap to pause.</p>
      )}
    </section>
  );
}

function drawFrame(
  canvas: HTMLCanvasElement | null,
  state: SnakeState,
  showGrid: boolean,
  isPaused: boolean,
  bestScore: number
): void {
  if (!canvas) {
    return;
  }

  const ctx = canvas.getContext("2d");
  if (!ctx) {
    return;
  }

  ctx.clearRect(0, 0, canvas.width, canvas.height);

  const bgGradient = ctx.createLinearGradient(0, 0, 0, canvas.height);
  bgGradient.addColorStop(0, "#09101d");
  bgGradient.addColorStop(1, "#030711");
  ctx.fillStyle = bgGradient;
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  if (showGrid) {
    ctx.strokeStyle = "rgba(120, 140, 170, 0.18)";
    ctx.lineWidth = 1;
    for (let x = 0; x <= canvas.width; x += TILE_SIZE) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, canvas.height);
      ctx.stroke();
    }
    for (let y = 0; y <= canvas.height; y += TILE_SIZE) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(canvas.width, y);
      ctx.stroke();
    }
  }

  const foodX = state.food.x * TILE_SIZE + TILE_SIZE / 2;
  const foodY = state.food.y * TILE_SIZE + TILE_SIZE / 2;
  ctx.fillStyle = "rgba(255, 77, 109, 0.35)";
  ctx.beginPath();
  ctx.arc(foodX, foodY, 9, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = "#ff4d6d";
  ctx.beginPath();
  ctx.arc(foodX, foodY, 5.5, 0, Math.PI * 2);
  ctx.fill();

  state.snake.forEach((segment, index) => {
    const x = segment.x * TILE_SIZE + 1;
    const y = segment.y * TILE_SIZE + 1;

    if (index === 0) {
      const headGradient = ctx.createLinearGradient(x, y, x, y + TILE_SIZE - 2);
      headGradient.addColorStop(0, "#a6ff4d");
      headGradient.addColorStop(1, "#4ac100");
      ctx.fillStyle = headGradient;
      ctx.fillRect(x, y, TILE_SIZE - 2, TILE_SIZE - 2);
      ctx.fillStyle = "#14213d";
      ctx.beginPath();
      ctx.arc(x + 6, y + 6, 2, 0, Math.PI * 2);
      ctx.arc(x + TILE_SIZE - 8, y + 6, 2, 0, Math.PI * 2);
      ctx.fill();
    } else {
      ctx.fillStyle = "#4ac100";
      ctx.fillRect(x + 2, y + 2, TILE_SIZE - 6, TILE_SIZE - 6);
    }
  });

  if (isPaused || state.dead) {
    ctx.fillStyle = "rgba(0, 0, 0, 0.5)";
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    ctx.fillStyle = "#f8f9fa";
    ctx.font = "bold 42px ui-sans-serif, system-ui, -apple-system";
    ctx.textAlign = "center";
    ctx.fillText(isPaused ? "Paused" : "Game Over", canvas.width / 2, canvas.height / 2 - 12);

    ctx.font = "16px ui-sans-serif, system-ui, -apple-system";
    ctx.fillStyle = "#cdd3df";
    ctx.fillText(`Score ${state.score} | Best ${bestScore}`, canvas.width / 2, canvas.height / 2 + 24);
  }
}

function readBestScore(): number {
  const raw = window.localStorage.getItem("arcade.snake.best");
  if (!raw) {
    return 0;
  }
  const parsed = Number(raw);
  return Number.isFinite(parsed) ? parsed : 0;
}

function writeBestScore(score: number): void {
  window.localStorage.setItem("arcade.snake.best", String(score));
}

export default SnakeGame;
