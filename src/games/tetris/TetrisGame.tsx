import { useEffect, useRef, useState } from "react";
import MobileControls from "../../components/ui/MobileControls";
import { useGameSession } from "../../services/progression/useGameSession";
import type { ControlScheme } from "../../types/settings";
import {
  CELL_SIZE,
  COLS,
  ROWS,
  advance,
  createInitialState,
  getGhostY,
  hardDrop,
  hold,
  moveHorizontal,
  rotate,
  softDrop,
  type Piece,
  type TetrisState
} from "./tetris.logic";
import "./tetris.css";

const BOARD_W = COLS * CELL_SIZE;
const BOARD_H = ROWS * CELL_SIZE;
const SIDE_W = 180;
const HOLD_W = 130;
const CANVAS_W = HOLD_W + 20 + BOARD_W + 20 + SIDE_W;
const CANVAS_H = BOARD_H;

interface TetrisGameProps {
  onExit: () => void;
  controlScheme: ControlScheme;
}

function TetrisGame({ onExit, controlScheme }: TetrisGameProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const frameRef = useRef<number | null>(null);
  const lastTimeRef = useRef<number | null>(null);
  const fallAccumulatorRef = useRef(0);
  const touchStartRef = useRef<{ x: number; y: number } | null>(null);

  const [state, setState] = useState<TetrisState>(() => createInitialState());
  const [isPaused, setIsPaused] = useState(false);
  const [bestScore, setBestScore] = useState<number>(() => readBestScore());
  const session = useGameSession("tetris");
  const exitToMenu = () => {
    session.recordPlaytimeOnly();
    onExit();
  };

  const performAction = (action: "left" | "right" | "down" | "cw" | "ccw" | "drop" | "hold") => {
    if (isPaused || state.gameOver) {
      return;
    }
    setState((prev) => {
      if (action === "left") {
        return moveHorizontal(prev, -1);
      }
      if (action === "right") {
        return moveHorizontal(prev, 1);
      }
      if (action === "down") {
        return softDrop(prev);
      }
      if (action === "cw") {
        return rotate(prev, true);
      }
      if (action === "ccw") {
        return rotate(prev, false);
      }
      if (action === "drop") {
        return hardDrop(prev);
      }
      return hold(prev);
    });
  };

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      const key = event.key;

      if (["ArrowLeft", "ArrowRight", "ArrowDown", "ArrowUp", " "].includes(key)) {
        event.preventDefault();
      }

      if (key === "q" || key === "Escape") {
        exitToMenu();
        return;
      }

      if (key === "r") {
        setState(createInitialState());
        session.restartSession();
        setIsPaused(false);
        fallAccumulatorRef.current = 0;
        lastTimeRef.current = null;
        return;
      }

      if (key === "p" && !state.gameOver) {
        setIsPaused((prev) => !prev);
        return;
      }

      if (isPaused || state.gameOver) {
        return;
      }

      if (key === "ArrowLeft" || key === "a") {
        performAction("left");
      } else if (key === "ArrowRight" || key === "d") {
        performAction("right");
      } else if (key === "ArrowDown" || key === "s") {
        performAction("down");
      } else if (key === "ArrowUp" || key === "x") {
        performAction("cw");
      } else if (key === "z") {
        performAction("ccw");
      } else if (key === " ") {
        performAction("drop");
      } else if (key === "c" || key === "Shift") {
        performAction("hold");
      }
    };

    window.addEventListener("keydown", onKeyDown);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
    };
  }, [exitToMenu, isPaused, session, state.gameOver]);

  useEffect(() => {
    if (!state.gameOver) {
      return;
    }
    session.recordResult({
      score: state.score,
      won: false,
      extra: {
        lines: state.lines
      }
    });
  }, [session, state.gameOver, state.lines, state.score]);

  useEffect(() => {
    const run = (time: number) => {
      if (lastTimeRef.current == null) {
        lastTimeRef.current = time;
      }

      const deltaMs = Math.min(48, time - lastTimeRef.current);
      lastTimeRef.current = time;

      if (!isPaused) {
        fallAccumulatorRef.current += deltaMs;

        setState((prev) => {
          let next = advance(prev, deltaMs, false);

          if (next.flashMs > 0) {
            fallAccumulatorRef.current = 0;
            return next;
          }

          while (fallAccumulatorRef.current >= next.fallMs && !next.gameOver && next.flashMs <= 0) {
            fallAccumulatorRef.current -= next.fallMs;
            next = advance(next, 0, true);
          }

          return next;
        });
      }

      frameRef.current = window.requestAnimationFrame(run);
    };

    frameRef.current = window.requestAnimationFrame(run);

    return () => {
      if (frameRef.current != null) {
        window.cancelAnimationFrame(frameRef.current);
      }
    };
  }, [isPaused]);

  useEffect(() => {
    if (!state.gameOver || state.score <= bestScore) {
      return;
    }

    setBestScore(state.score);
    writeBestScore(state.score);
  }, [bestScore, state.gameOver, state.score]);

  useEffect(() => {
    drawFrame(canvasRef.current, state, isPaused, bestScore);
  }, [bestScore, isPaused, state]);

  return (
    <section className="tetris-screen">
      <header className="tetris-header">
        <div>
          <h1>Tetris</h1>
          <p>Arrows move. X/Up rotate CW, Z rotate CCW, Space hard drop, C hold.</p>
        </div>
        <button type="button" onClick={exitToMenu}>
          Back to Menu
        </button>
      </header>

      <div className="tetris-hud">
        <span>Score: {state.score}</span>
        <span>Level: {state.level}</span>
        <span>Lines: {state.lines}</span>
        <span>Best: {bestScore}</span>
        {isPaused && <span>Paused</span>}
        {state.gameOver && <span>Game Over</span>}
      </div>

      <canvas
        ref={canvasRef}
        width={CANVAS_W}
        height={CANVAS_H}
        className="tetris-canvas"
        onTouchStart={(event) => {
          if (controlScheme !== "gestures") {
            return;
          }
          event.preventDefault();
          const touch = event.touches[0];
          touchStartRef.current = { x: touch.clientX, y: touch.clientY };
        }}
        onTouchEnd={(event) => {
          if (controlScheme !== "gestures" || !touchStartRef.current) {
            return;
          }
          event.preventDefault();
          const touch = event.changedTouches[0];
          const dx = touch.clientX - touchStartRef.current.x;
          const dy = touch.clientY - touchStartRef.current.y;
          touchStartRef.current = null;

          if (Math.abs(dx) < 18 && Math.abs(dy) < 18) {
            performAction("cw");
            return;
          }
          if (Math.abs(dx) > Math.abs(dy)) {
            performAction(dx > 0 ? "right" : "left");
          } else if (dy > 0) {
            performAction("down");
          } else {
            performAction("drop");
          }
        }}
      />

      {controlScheme === "buttons" ? (
        <MobileControls
          dpad={{
            left: () => performAction("left"),
            right: () => performAction("right"),
            down: () => performAction("down")
          }}
          actions={[
            { label: "Rotate", onPress: () => performAction("cw") },
            { label: "Rotate CCW", onPress: () => performAction("ccw") },
            { label: "Hard Drop", onPress: () => performAction("drop") },
            { label: "Hold", onPress: () => performAction("hold") },
            { label: isPaused ? "Resume" : "Pause", onPress: () => setIsPaused((prev) => !prev) },
            {
              label: "Restart",
              onPress: () => {
                setState(createInitialState());
                session.restartSession();
                setIsPaused(false);
                fallAccumulatorRef.current = 0;
                lastTimeRef.current = null;
              }
            },
            { label: "Menu", onPress: exitToMenu }
          ]}
        />
      ) : (
        <MobileControls
          actions={[
            { label: "Hold", onPress: () => performAction("hold") },
            { label: "Rotate CCW", onPress: () => performAction("ccw") },
            { label: isPaused ? "Resume" : "Pause", onPress: () => setIsPaused((prev) => !prev) },
            {
              label: "Restart",
              onPress: () => {
                setState(createInitialState());
                session.restartSession();
                setIsPaused(false);
                fallAccumulatorRef.current = 0;
                lastTimeRef.current = null;
              }
            },
            { label: "Menu", onPress: exitToMenu }
          ]}
        />
      )}
    </section>
  );
}

function drawFrame(canvas: HTMLCanvasElement | null, state: TetrisState, isPaused: boolean, bestScore: number): void {
  if (!canvas) {
    return;
  }

  const ctx = canvas.getContext("2d");
  if (!ctx) {
    return;
  }

  const boardX = HOLD_W + 20;
  const boardY = 0;
  const sideX = boardX + BOARD_W + 20;

  ctx.clearRect(0, 0, canvas.width, canvas.height);

  const bg = ctx.createLinearGradient(0, 0, 0, canvas.height);
  bg.addColorStop(0, "#071124");
  bg.addColorStop(1, "#020711");
  ctx.fillStyle = bg;
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  drawPanel(ctx, 0, 0, HOLD_W, 120, "HOLD");
  drawPanel(ctx, sideX, 0, SIDE_W, 150, "NEXT");
  drawPanel(ctx, sideX, 160, SIDE_W, 210, "STATS");

  drawMiniPiece(ctx, state.held, 0, 28, HOLD_W, 92);
  drawMiniPiece(ctx, state.next, sideX, 28, SIDE_W, 122);

  ctx.fillStyle = "#8d99ae";
  ctx.font = "12px Trebuchet MS, Segoe UI, sans-serif";
  ctx.fillText("SCORE", sideX + 14, 188);
  ctx.fillText("LEVEL", sideX + 14, 248);
  ctx.fillText("LINES", sideX + 14, 308);

  ctx.font = "bold 28px Trebuchet MS, Segoe UI, sans-serif";
  ctx.fillStyle = "#70e000";
  ctx.fillText(String(state.score), sideX + 14, 220);
  ctx.fillStyle = "#4cc9f0";
  ctx.fillText(String(state.level), sideX + 14, 280);
  ctx.fillStyle = "#f77f00";
  ctx.fillText(String(state.lines), sideX + 14, 340);

  drawBoard(ctx, boardX, boardY, state);

  if (isPaused || state.gameOver) {
    ctx.fillStyle = "rgba(0, 0, 0, 0.58)";
    ctx.fillRect(boardX, boardY, BOARD_W, BOARD_H);
    ctx.fillStyle = "#f8f9fa";
    ctx.textAlign = "center";
    ctx.font = "bold 44px Trebuchet MS, Segoe UI, sans-serif";
    ctx.fillText(isPaused ? "Paused" : "Game Over", boardX + BOARD_W / 2, 280);
    ctx.font = "16px Trebuchet MS, Segoe UI, sans-serif";
    ctx.fillStyle = "#cdd3df";
    ctx.fillText(`Score ${state.score} | Best ${Math.max(bestScore, state.score)}`, boardX + BOARD_W / 2, 315);
    ctx.textAlign = "left";
  }
}

function drawPanel(ctx: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, title: string): void {
  ctx.fillStyle = "rgba(20, 33, 55, 0.92)";
  roundedRect(ctx, x, y, w, h, 10);
  ctx.fill();

  ctx.strokeStyle = "#2b436a";
  ctx.lineWidth = 1;
  roundedRect(ctx, x, y, w, h, 10);
  ctx.stroke();

  ctx.fillStyle = "#8d99ae";
  ctx.font = "bold 12px Trebuchet MS, Segoe UI, sans-serif";
  ctx.fillText(title, x + 12, y + 18);
}

function drawBoard(ctx: CanvasRenderingContext2D, boardX: number, boardY: number, state: TetrisState): void {
  roundedRect(ctx, boardX - 8, boardY - 8, BOARD_W + 16, BOARD_H + 16, 12);
  ctx.fillStyle = "rgba(20, 33, 55, 0.9)";
  ctx.fill();

  ctx.fillStyle = "#030711";
  ctx.fillRect(boardX, boardY, BOARD_W, BOARD_H);

  for (let y = 0; y < ROWS; y += 1) {
    for (let x = 0; x < COLS; x += 1) {
      const px = boardX + x * CELL_SIZE;
      const py = boardY + y * CELL_SIZE;
      const lockedColor = state.grid[y][x];

      if (lockedColor != null) {
        const flashing = state.flashRows.includes(y) && state.flashMs > 0;
        const color = flashing ? "#f8f9fa" : lockedColor;
        drawCell(ctx, px, py, color);
      } else {
        ctx.fillStyle = "rgba(120, 140, 170, 0.22)";
        ctx.beginPath();
        ctx.arc(px + CELL_SIZE / 2, py + CELL_SIZE / 2, 1.2, 0, Math.PI * 2);
        ctx.fill();
      }
    }
  }

  const ghostY = getGhostY(state.current, state.grid);

  if (state.flashMs <= 0) {
    if (!state.gameOver) {
      drawPiece(ctx, state.current, boardX, boardY, ghostY, true);
    }
    drawPiece(ctx, state.current, boardX, boardY, state.current.y, false);
  }

  ctx.strokeStyle = "#2b436a";
  ctx.lineWidth = 1;
  ctx.strokeRect(boardX, boardY, BOARD_W, BOARD_H);
}

function drawPiece(
  ctx: CanvasRenderingContext2D,
  piece: Piece,
  boardX: number,
  boardY: number,
  offsetY: number,
  ghost: boolean
): void {
  for (let r = 0; r < piece.shape.length; r += 1) {
    for (let c = 0; c < piece.shape[r].length; c += 1) {
      if (piece.shape[r][c] === 0) {
        continue;
      }

      const x = boardX + (piece.x + c) * CELL_SIZE;
      const y = boardY + (offsetY + r) * CELL_SIZE;
      if (y < boardY) {
        continue;
      }

      if (ghost) {
        ctx.fillStyle = applyAlpha(piece.color, 0.28);
        roundedRect(ctx, x + 1, y + 1, CELL_SIZE - 2, CELL_SIZE - 2, 3);
        ctx.fill();
      } else {
        drawCell(ctx, x, y, piece.color);
      }
    }
  }
}

function drawMiniPiece(
  ctx: CanvasRenderingContext2D,
  piece: Piece | null,
  panelX: number,
  panelY: number,
  panelW: number,
  panelH: number
): void {
  if (!piece) {
    return;
  }

  const size = 18;
  const sw = piece.shape[0].length * size;
  const sh = piece.shape.length * size;
  const ox = panelX + (panelW - sw) / 2;
  const oy = panelY + (panelH - sh) / 2;

  for (let r = 0; r < piece.shape.length; r += 1) {
    for (let c = 0; c < piece.shape[r].length; c += 1) {
      if (piece.shape[r][c] === 1) {
        drawCell(ctx, ox + c * size, oy + r * size, piece.color, size);
      }
    }
  }
}

function drawCell(ctx: CanvasRenderingContext2D, x: number, y: number, color: string, size = CELL_SIZE): void {
  const grad = ctx.createLinearGradient(x, y, x, y + size);
  grad.addColorStop(0, lighten(color, 0.16));
  grad.addColorStop(1, color);

  ctx.fillStyle = grad;
  roundedRect(ctx, x + 1, y + 1, size - 2, size - 2, 3);
  ctx.fill();

  ctx.strokeStyle = "rgba(255,255,255,0.22)";
  ctx.lineWidth = 1;
  roundedRect(ctx, x + 1, y + 1, size - 2, size - 2, 3);
  ctx.stroke();
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

function lighten(hex: string, amount: number): string {
  const rgb = hexToRgb(hex);
  if (!rgb) {
    return hex;
  }
  const r = Math.min(255, Math.round(rgb.r + (255 - rgb.r) * amount));
  const g = Math.min(255, Math.round(rgb.g + (255 - rgb.g) * amount));
  const b = Math.min(255, Math.round(rgb.b + (255 - rgb.b) * amount));
  return `rgb(${r}, ${g}, ${b})`;
}

function applyAlpha(hex: string, alpha: number): string {
  const rgb = hexToRgb(hex);
  if (!rgb) {
    return `rgba(255, 255, 255, ${alpha})`;
  }
  return `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, ${alpha})`;
}

function hexToRgb(hex: string): { r: number; g: number; b: number } | null {
  const cleaned = hex.replace("#", "");
  if (cleaned.length !== 6) {
    return null;
  }

  const value = Number.parseInt(cleaned, 16);
  if (Number.isNaN(value)) {
    return null;
  }

  return {
    r: (value >> 16) & 255,
    g: (value >> 8) & 255,
    b: value & 255
  };
}

function readBestScore(): number {
  const raw = window.localStorage.getItem("arcade.tetris.best");
  const parsed = Number(raw);
  return Number.isFinite(parsed) ? parsed : 0;
}

function writeBestScore(score: number): void {
  window.localStorage.setItem("arcade.tetris.best", String(score));
}

export default TetrisGame;
