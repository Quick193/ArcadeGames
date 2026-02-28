import { useEffect, useRef, useState } from "react";
import MobileControls from "../../components/ui/MobileControls";
import { useGameSession } from "../../services/progression/useGameSession";
import type { ControlScheme } from "../../types/settings";
import {
  BIRD_R,
  HEIGHT,
  PIPE_W,
  WIDTH,
  type Difficulty,
  type FlappyState,
  createInitialState,
  flap,
  startGame,
  stepGame
} from "./flappy.logic";
import "./flappy.css";

interface FlappyGameProps {
  onExit: () => void;
  controlScheme: ControlScheme;
}

function FlappyGame({ onExit, controlScheme }: FlappyGameProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const frameRef = useRef<number | null>(null);
  const lastRef = useRef<number | null>(null);

  const [state, setState] = useState<FlappyState>(() => createInitialState());
  const [bestScore, setBestScore] = useState<number>(() => readBestScore());
  const session = useGameSession("flappy");
  const exitToMenu = () => {
    session.recordPlaytimeOnly();
    onExit();
  };

  const selectUp = () => {
    setState((prev) => ({ ...prev, selection: (prev.selection + 2) % 3 }));
  };

  const selectDown = () => {
    setState((prev) => ({ ...prev, selection: (prev.selection + 1) % 3 }));
  };

  const selectPlay = () => {
    setState((prev) => startGame(prev, ["easy", "medium", "hard"][prev.selection] as Difficulty));
  };

  const chooseDifficulty = (index: number) => {
    const diff = (["easy", "medium", "hard"] as Difficulty[])[index] ?? "medium";
    setState((prev) => startGame(prev, diff));
  };

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "q" || event.key === "Escape") {
        exitToMenu();
        return;
      }

      if (state.phase === "select") {
        if (event.key === "ArrowUp") {
          selectUp();
          return;
        }
        if (event.key === "ArrowDown") {
          selectDown();
          return;
        }
        if (event.key === "Enter") {
          selectPlay();
        }
        return;
      }

      if (event.key === "r" && state.diff) {
        session.restartSession();
        setState((prev) => startGame(prev, prev.diff as Difficulty));
        return;
      }

      if (event.key === "p" && !state.dead) {
        setState((prev) => ({ ...prev, paused: !prev.paused }));
        return;
      }

      if ((event.key === " " || event.key === "Spacebar") && !state.dead && !state.paused) {
        event.preventDefault();
        setState((prev) => flap(prev));
      }
    };

    window.addEventListener("keydown", onKeyDown);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
    };
  }, [exitToMenu, session, state.dead, state.diff, state.paused, state.phase]);

  useEffect(() => {
    if (!state.dead) {
      return;
    }
    session.recordResult({
      score: state.score,
      won: false
    });
  }, [session, state.dead, state.score]);

  useEffect(() => {
    const tick = (time: number) => {
      if (lastRef.current == null) {
        lastRef.current = time;
      }

      const dt = Math.min(0.05, (time - lastRef.current) / 1000);
      lastRef.current = time;

      setState((prev) => stepGame(prev, dt));
      frameRef.current = window.requestAnimationFrame(tick);
    };

    frameRef.current = window.requestAnimationFrame(tick);

    return () => {
      if (frameRef.current != null) {
        window.cancelAnimationFrame(frameRef.current);
      }
    };
  }, []);

  useEffect(() => {
    if (!state.dead || state.score <= bestScore) {
      return;
    }

    setBestScore(state.score);
    writeBestScore(state.score);
  }, [bestScore, state.dead, state.score]);

  useEffect(() => {
    drawFrame(canvasRef.current, state, bestScore);
  }, [bestScore, state]);

  return (
    <section className="flappy-screen">
      <header className="flappy-header">
        <div>
          <h1>Flappy Bird</h1>
          <p>Select difficulty, then Space to flap through pipes.</p>
        </div>
        <button type="button" onClick={exitToMenu}>
          Back to Menu
        </button>
      </header>

      {state.phase === "select" && (
        <section className="flappy-select">
          <button type="button" className={state.selection === 0 ? "active" : ""} onClick={() => chooseDifficulty(0)}>Easy</button>
          <button type="button" className={state.selection === 1 ? "active" : ""} onClick={() => chooseDifficulty(1)}>Medium</button>
          <button type="button" className={state.selection === 2 ? "active" : ""} onClick={() => chooseDifficulty(2)}>Hard</button>
        </section>
      )}

      {state.phase === "game" && (
        <canvas
          ref={canvasRef}
          width={WIDTH}
          height={HEIGHT}
          className="flappy-canvas"
        />
      )}

      {controlScheme === "buttons" && state.phase === "select" ? (
        <MobileControls
          dpad={{ up: selectUp, down: selectDown }}
          actions={[
            { label: "Play", onPress: () => chooseDifficulty(state.selection) },
            { label: "Menu", onPress: exitToMenu }
          ]}
        />
      ) : controlScheme === "buttons" ? (
        <MobileControls
          actions={[
            { label: "Flap", onPress: () => setState((prev) => flap(prev)) },
            { label: state.paused ? "Resume" : "Pause", onPress: () => setState((prev) => ({ ...prev, paused: !prev.paused })) },
            {
              label: "Restart",
              onPress: () => {
                if (!state.diff) {
                  return;
                }
                session.restartSession();
                setState((prev) => startGame(prev, prev.diff as Difficulty));
              }
            },
            { label: "Menu", onPress: exitToMenu }
          ]}
        />
      ) : null}
    </section>
  );
}

function drawFrame(canvas: HTMLCanvasElement | null, state: FlappyState, bestScore: number): void {
  if (!canvas) {
    return;
  }

  const ctx = canvas.getContext("2d");
  if (!ctx) {
    return;
  }

  ctx.clearRect(0, 0, WIDTH, HEIGHT);

  const bg = ctx.createLinearGradient(0, 0, 0, HEIGHT);
  bg.addColorStop(0, "#0a1630");
  bg.addColorStop(1, "#041022");
  ctx.fillStyle = bg;
  ctx.fillRect(0, 0, WIDTH, HEIGHT);

  const params = state.params;
  if (!params) {
    return;
  }

  for (const pipe of state.pipes) {
    drawPipe(ctx, pipe.x, 0, PIPE_W, pipe.y, true);

    const bottomY = pipe.y + params.gap;
    drawPipe(ctx, pipe.x, bottomY, PIPE_W, HEIGHT - bottomY, false);
  }

  drawBird(ctx, state.birdX, state.birdY);

  drawHud(ctx, state.score, state.diff ?? "medium", bestScore);

  ctx.fillStyle = "#8d99ae";
  ctx.font = "13px Trebuchet MS, Segoe UI, sans-serif";
  ctx.textAlign = "center";
  ctx.fillText("Space flap | P pause | R restart | Q menu", WIDTH / 2, HEIGHT - 24);

  if (state.paused || state.dead) {
    ctx.fillStyle = "rgba(0,0,0,0.6)";
    ctx.fillRect(0, 0, WIDTH, HEIGHT);

    ctx.fillStyle = state.dead ? "#ff4d6d" : "#edf2f4";
    ctx.font = "bold 48px Trebuchet MS, Segoe UI, sans-serif";
    ctx.fillText(state.dead ? "CRASHED!" : "Paused", WIDTH / 2, HEIGHT / 2 - 20);

    ctx.fillStyle = "#edf2f4";
    ctx.font = "24px Trebuchet MS, Segoe UI, sans-serif";
    ctx.fillText(`Score: ${state.score}`, WIDTH / 2, HEIGHT / 2 + 18);

    if (state.dead && state.score >= bestScore && state.score > 0) {
      ctx.fillStyle = "#ffd166";
      ctx.font = "bold 14px Trebuchet MS, Segoe UI, sans-serif";
      ctx.fillText("NEW BEST", WIDTH / 2, HEIGHT / 2 + 46);
    }

    ctx.fillStyle = "#8d99ae";
    ctx.font = "14px Trebuchet MS, Segoe UI, sans-serif";
    ctx.fillText("R restart | Q menu", WIDTH / 2, HEIGHT / 2 + 74);
  }

  ctx.textAlign = "left";
}

function drawPipe(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  w: number,
  h: number,
  top: boolean
): void {
  if (h <= 0) {
    return;
  }

  const grad = ctx.createLinearGradient(x, y, x, y + h);
  if (top) {
    grad.addColorStop(0, "#2e8f3f");
    grad.addColorStop(1, "#49b05a");
  } else {
    grad.addColorStop(0, "#49b05a");
    grad.addColorStop(1, "#2e8f3f");
  }

  ctx.fillStyle = grad;
  ctx.fillRect(x, y, w, h);

  ctx.strokeStyle = "rgba(0,0,0,0.4)";
  ctx.lineWidth = 2;
  ctx.strokeRect(x + 1, y + 1, w - 2, h - 2);
}

function drawBird(ctx: CanvasRenderingContext2D, x: number, y: number): void {
  const grad = ctx.createRadialGradient(x - 4, y - 4, 2, x, y, BIRD_R + 2);
  grad.addColorStop(0, "#fff1a8");
  grad.addColorStop(1, "#ffd166");

  ctx.fillStyle = grad;
  ctx.beginPath();
  ctx.arc(x, y, BIRD_R, 0, Math.PI * 2);
  ctx.fill();

  ctx.fillStyle = "#1f2d3d";
  ctx.beginPath();
  ctx.arc(x + 6, y - 3, 3, 0, Math.PI * 2);
  ctx.fill();

  ctx.fillStyle = "#edf2f4";
  ctx.beginPath();
  ctx.arc(x + 7, y - 3, 1, 0, Math.PI * 2);
  ctx.fill();
}

function drawHud(ctx: CanvasRenderingContext2D, score: number, diff: string, best: number): void {
  ctx.fillStyle = "rgba(20, 33, 55, 0.9)";
  roundedRect(ctx, 16, 16, 182, 76, 10);
  ctx.fill();

  ctx.strokeStyle = "#2b436a";
  ctx.lineWidth = 1;
  roundedRect(ctx, 16, 16, 182, 76, 10);
  ctx.stroke();

  ctx.fillStyle = "#8d99ae";
  ctx.font = "bold 11px Trebuchet MS, Segoe UI, sans-serif";
  ctx.fillText("SCORE", 32, 36);
  ctx.fillText("BEST", 32, 52);
  ctx.fillText(diff.toUpperCase(), 128, 36);

  ctx.fillStyle = "#ffd166";
  ctx.font = "bold 24px Trebuchet MS, Segoe UI, sans-serif";
  ctx.fillText(String(score), 80, 40);

  ctx.fillStyle = "#4cc9f0";
  ctx.font = "bold 18px Trebuchet MS, Segoe UI, sans-serif";
  ctx.fillText(String(best), 80, 54);
}

function roundedRect(ctx: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, r: number): void {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}

function readBestScore(): number {
  const raw = window.localStorage.getItem("arcade.flappy.best");
  const parsed = Number(raw);
  return Number.isFinite(parsed) ? parsed : 0;
}

function writeBestScore(score: number): void {
  window.localStorage.setItem("arcade.flappy.best", String(score));
}

export default FlappyGame;
