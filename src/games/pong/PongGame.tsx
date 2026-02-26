import { useEffect, useRef, useState } from "react";
import MobileControls from "../../components/ui/MobileControls";
import { useGameSession } from "../../services/progression/useGameSession";
import type { ControlScheme } from "../../types/settings";
import {
  BALL_R,
  HEIGHT,
  PAD_H,
  PAD_W,
  WIDTH,
  type Difficulty,
  type InputState,
  type PongState,
  createInitialState,
  enterDifficultySelection,
  enterModeSelection,
  restartMatch,
  startGame,
  stepGame
} from "./pong.logic";
import "./pong.css";

interface PongGameProps {
  onExit: () => void;
  controlScheme: ControlScheme;
}

function PongGame({ onExit, controlScheme }: PongGameProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const frameRef = useRef<number | null>(null);
  const keysRef = useRef<Set<string>>(new Set());
  const touchInputRef = useRef<InputState>({ p1Up: false, p1Down: false, p2Up: false, p2Down: false });
  const menuTouchStartRef = useRef<{ x: number; y: number } | null>(null);

  const [state, setState] = useState<PongState>(() => createInitialState());
  const session = useGameSession("pong");
  const exitToMenu = () => {
    session.recordPlaytimeOnly();
    onExit();
  };

  const moveSelectionUp = (count: number) => {
    setState((prev) => ({ ...prev, selection: (prev.selection + count - 1) % count }));
  };

  const moveSelectionDown = (count: number) => {
    setState((prev) => ({ ...prev, selection: (prev.selection + 1) % count }));
  };

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      keysRef.current.add(event.key);

      if (state.phase === "game" && ["ArrowUp", "ArrowDown", " "].includes(event.key)) {
        event.preventDefault();
      }

      if (event.key === "q" || event.key === "Escape") {
        if (state.phase === "game") {
          exitToMenu();
        } else if (state.phase === "difficulty") {
          setState((prev) => enterModeSelection(prev));
        } else {
          exitToMenu();
        }
        return;
      }

      if (state.phase === "mode") {
        if (event.key === "ArrowUp") {
          moveSelectionUp(2);
          return;
        }
        if (event.key === "ArrowDown") {
          moveSelectionDown(2);
          return;
        }
        if (event.key === "Enter") {
          setState((prev) => (prev.selection === 0 ? enterDifficultySelection(prev) : startGame(prev, "2p", null)));
        }
        return;
      }

      if (state.phase === "difficulty") {
        if (event.key === "ArrowUp") {
          moveSelectionUp(3);
          return;
        }
        if (event.key === "ArrowDown") {
          moveSelectionDown(3);
          return;
        }
        if (event.key === "Enter") {
          setState((prev) => startGame(prev, "1p", ["easy", "medium", "hard"][prev.selection] as Difficulty));
        }
        return;
      }

      if (state.phase === "game") {
        if (event.key === "p" && !state.winner) {
          setState((prev) => ({ ...prev, paused: !prev.paused }));
          return;
        }
        if (event.key === "r") {
          session.restartSession();
          setState((prev) => restartMatch(prev));
        }
      }
    };

    const onKeyUp = (event: KeyboardEvent) => {
      keysRef.current.delete(event.key);
    };

    window.addEventListener("keydown", onKeyDown);
    window.addEventListener("keyup", onKeyUp);

    return () => {
      window.removeEventListener("keydown", onKeyDown);
      window.removeEventListener("keyup", onKeyUp);
    };
  }, [exitToMenu, session, state.phase, state.winner]);

  useEffect(() => {
    if (state.phase !== "game" || !state.winner) {
      return;
    }
    session.recordResult({
      score: state.p1s,
      won: state.winner === "P1",
      extra: {
        opponent_score: state.p2s
      }
    });
  }, [session, state.p1s, state.p2s, state.phase, state.winner]);

  useEffect(() => {
    const tick = () => {
      setState((prev) => {
        const touch = touchInputRef.current;
        const input: InputState = {
          p1Up: keysRef.current.has("ArrowUp") || touch.p1Up,
          p1Down: keysRef.current.has("ArrowDown") || touch.p1Down,
          p2Up: (keysRef.current.has("w") || keysRef.current.has("W")) || touch.p2Up,
          p2Down: (keysRef.current.has("s") || keysRef.current.has("S")) || touch.p2Down
        };

        return stepGame(prev, input);
      });

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
    drawFrame(canvasRef.current, state);
  }, [state]);

  return (
    <section className="pong-screen">
      <header className="pong-header">
        <div>
          <h1>Pong</h1>
          <p>Mode select, difficulty select, then play to 7 points.</p>
        </div>
        <button type="button" onClick={exitToMenu}>
          Back to Menu
        </button>
      </header>

      <canvas
        ref={canvasRef}
        width={WIDTH}
        height={HEIGHT}
        className="pong-canvas"
        onTouchStart={(event) => {
          if (controlScheme !== "gestures") {
            return;
          }
          event.preventDefault();
          if (state.phase === "game") {
            updateTouchInputFromTouches(event.touches, state, canvasRef.current, touchInputRef);
            return;
          }
          const touch = event.touches[0];
          menuTouchStartRef.current = { x: touch.clientX, y: touch.clientY };
        }}
        onTouchMove={(event) => {
          if (controlScheme === "gestures" && state.phase === "game") {
            event.preventDefault();
            updateTouchInputFromTouches(event.touches, state, canvasRef.current, touchInputRef);
          }
        }}
        onTouchEnd={(event) => {
          if (controlScheme !== "gestures") {
            return;
          }
          event.preventDefault();
          if (state.phase === "game") {
            updateTouchInputFromTouches(event.touches, state, canvasRef.current, touchInputRef);
            return;
          }
          if (!menuTouchStartRef.current) {
            return;
          }
          const touch = event.changedTouches[0];
          const dy = touch.clientY - menuTouchStartRef.current.y;
          menuTouchStartRef.current = null;

          if (Math.abs(dy) > 20) {
            if (state.phase === "mode") {
              dy > 0 ? moveSelectionDown(2) : moveSelectionUp(2);
            } else if (state.phase === "difficulty") {
              dy > 0 ? moveSelectionDown(3) : moveSelectionUp(3);
            }
            return;
          }

          if (state.phase === "mode") {
            setState((prev) => (prev.selection === 0 ? enterDifficultySelection(prev) : startGame(prev, "2p", null)));
          } else if (state.phase === "difficulty") {
            setState((prev) => startGame(prev, "1p", ["easy", "medium", "hard"][prev.selection] as Difficulty));
          }
        }}
      />

      {controlScheme === "buttons" && state.phase === "mode" && (
        <MobileControls
          dpad={{ up: () => moveSelectionUp(2), down: () => moveSelectionDown(2) }}
          actions={[
            {
              label: "Select",
              onPress: () => {
                setState((prev) => (prev.selection === 0 ? enterDifficultySelection(prev) : startGame(prev, "2p", null)));
              }
            },
            { label: "Menu", onPress: exitToMenu }
          ]}
        />
      )}

      {controlScheme === "buttons" && state.phase === "difficulty" && (
        <MobileControls
          dpad={{ up: () => moveSelectionUp(3), down: () => moveSelectionDown(3) }}
          actions={[
            {
              label: "Play",
              onPress: () => {
                setState((prev) => startGame(prev, "1p", ["easy", "medium", "hard"][prev.selection] as Difficulty));
              }
            },
            { label: "Back", onPress: () => setState((prev) => enterModeSelection(prev)) }
          ]}
        />
      )}

      {controlScheme === "buttons" && state.phase === "game" && (
        <MobileControls
          dpad={{
            up: () => {
              setState((prev) => stepGame(prev, { p1Up: true, p1Down: false, p2Up: false, p2Down: false }));
            },
            down: () => {
              setState((prev) => stepGame(prev, { p1Up: false, p1Down: true, p2Up: false, p2Down: false }));
            }
          }}
          actions={[
            ...(state.mode === "2p"
              ? [
                  {
                    label: "P2 Up",
                    onPress: () => setState((prev) => stepGame(prev, { p1Up: false, p1Down: false, p2Up: true, p2Down: false }))
                  },
                  {
                    label: "P2 Down",
                    onPress: () => setState((prev) => stepGame(prev, { p1Up: false, p1Down: false, p2Up: false, p2Down: true }))
                  }
                ]
              : []),
            { label: state.paused ? "Resume" : "Pause", onPress: () => setState((prev) => ({ ...prev, paused: !prev.paused })) },
            { label: "Restart", onPress: () => { session.restartSession(); setState((prev) => restartMatch(prev)); } },
            { label: "Menu", onPress: exitToMenu }
          ]}
        />
      )}

      {controlScheme === "gestures" && state.phase === "game" && (
        <MobileControls
          actions={[
            { label: state.paused ? "Resume" : "Pause", onPress: () => setState((prev) => ({ ...prev, paused: !prev.paused })) },
            { label: "Restart", onPress: () => { session.restartSession(); setState((prev) => restartMatch(prev)); } },
            { label: "Menu", onPress: exitToMenu }
          ]}
        />
      )}
    </section>
  );
}

function updateTouchInputFromTouches(
  touches: { length: number; [index: number]: { clientX: number; clientY: number } | undefined },
  state: PongState,
  canvas: HTMLCanvasElement | null,
  ref: { current: InputState }
): void {
  const next: InputState = { p1Up: false, p1Down: false, p2Up: false, p2Down: false };
  if (!canvas) {
    ref.current = next;
    return;
  }
  const rect = canvas.getBoundingClientRect();

  for (let i = 0; i < touches.length; i += 1) {
    const touch = touches[i];
    if (!touch) {
      continue;
    }
    const x = touch.clientX - rect.left;
    const y = touch.clientY - rect.top;

    if (state.mode === "2p") {
      if (x < rect.width / 2) {
        if (y < state.p1y + PAD_H / 2) {
          next.p1Up = true;
        } else {
          next.p1Down = true;
        }
      } else if (y < state.p2y + PAD_H / 2) {
        next.p2Up = true;
      } else {
        next.p2Down = true;
      }
    } else if (y < state.p1y + PAD_H / 2) {
      next.p1Up = true;
    } else {
      next.p1Down = true;
    }
  }

  ref.current = next;
}

function drawFrame(canvas: HTMLCanvasElement | null, state: PongState): void {
  if (!canvas) {
    return;
  }

  const ctx = canvas.getContext("2d");
  if (!ctx) {
    return;
  }

  ctx.clearRect(0, 0, WIDTH, HEIGHT);

  const bg = ctx.createLinearGradient(0, 0, 0, HEIGHT);
  bg.addColorStop(0, "#081322");
  bg.addColorStop(1, "#020811");
  ctx.fillStyle = bg;
  ctx.fillRect(0, 0, WIDTH, HEIGHT);

  if (state.phase === "mode") {
    drawSelection(ctx, "PONG", ["1 Player vs AI", "2 Players Local"], state.selection);
    return;
  }

  if (state.phase === "difficulty") {
    drawSelection(ctx, "Difficulty", ["Easy", "Medium", "Hard"], state.selection);
    return;
  }

  drawMatch(ctx, state);
}

function drawSelection(ctx: CanvasRenderingContext2D, title: string, options: string[], selected: number): void {
  ctx.textAlign = "center";
  ctx.fillStyle = "#edf2f4";
  ctx.font = "bold 58px Trebuchet MS, Segoe UI, sans-serif";
  ctx.fillText(title, WIDTH / 2, 140);

  options.forEach((opt, i) => {
    const x = (WIDTH - 340) / 2;
    const y = 250 + i * 86;
    const active = i === selected;

    ctx.fillStyle = active ? "#1f3f64" : "#13243e";
    roundedRect(ctx, x, y, 340, 60, 12);
    ctx.fill();

    ctx.strokeStyle = active ? "#4cc9f0" : "#2b436a";
    ctx.lineWidth = active ? 2 : 1;
    roundedRect(ctx, x, y, 340, 60, 12);
    ctx.stroke();

    ctx.fillStyle = "#edf2f4";
    ctx.font = "22px Trebuchet MS, Segoe UI, sans-serif";
    ctx.fillText(opt, WIDTH / 2, y + 39);
  });

  ctx.font = "13px Trebuchet MS, Segoe UI, sans-serif";
  ctx.fillStyle = "#8d99ae";
  ctx.fillText("Arrow keys select | Enter confirm | Q back", WIDTH / 2, HEIGHT - 24);
  ctx.textAlign = "left";
}

function drawMatch(ctx: CanvasRenderingContext2D, state: PongState): void {
  for (let y = 0; y < HEIGHT; y += 30) {
    ctx.strokeStyle = "#2b436a";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(WIDTH / 2, y);
    ctx.lineTo(WIDTH / 2, y + 14);
    ctx.stroke();
  }

  drawPaddle(ctx, state.p1x, state.p1y, "#4cc9f0");
  drawPaddle(ctx, state.p2x, state.p2y, "#f72585");

  ctx.fillStyle = "rgba(237, 242, 244, 0.35)";
  ctx.beginPath();
  ctx.arc(state.bx, state.by, BALL_R + 4, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = "#edf2f4";
  ctx.beginPath();
  ctx.arc(state.bx, state.by, BALL_R, 0, Math.PI * 2);
  ctx.fill();

  drawScoreCard(ctx, state);

  ctx.textAlign = "center";
  ctx.fillStyle = "#8d99ae";
  ctx.font = "13px Trebuchet MS, Segoe UI, sans-serif";
  const controls = state.mode === "1p"
    ? "Up/Down move | P pause | R rematch | Q menu"
    : "Up/Down P1 | W/S P2 | P pause | R rematch | Q menu";
  ctx.fillText(controls, WIDTH / 2, HEIGHT - 24);

  if (state.paused || state.winner) {
    ctx.fillStyle = "rgba(0, 0, 0, 0.6)";
    ctx.fillRect(0, 0, WIDTH, HEIGHT);

    ctx.fillStyle = "#edf2f4";
    ctx.font = "bold 46px Trebuchet MS, Segoe UI, sans-serif";
    const text = state.paused ? "Paused" : `${state.winner} WINS!`;
    ctx.fillText(text, WIDTH / 2, HEIGHT / 2 - 12);

    ctx.font = "22px Trebuchet MS, Segoe UI, sans-serif";
    ctx.fillText(`${state.p1s}  -  ${state.p2s}`, WIDTH / 2, HEIGHT / 2 + 28);

    ctx.fillStyle = "#8d99ae";
    ctx.font = "14px Trebuchet MS, Segoe UI, sans-serif";
    ctx.fillText("R rematch | Q menu", WIDTH / 2, HEIGHT / 2 + 64);
  }

  ctx.textAlign = "left";
}

function drawPaddle(ctx: CanvasRenderingContext2D, x: number, y: number, color: string): void {
  const gradient = ctx.createLinearGradient(x, y, x, y + PAD_H);
  gradient.addColorStop(0, lighten(color, 0.22));
  gradient.addColorStop(1, color);

  ctx.fillStyle = gradient;
  roundedRect(ctx, x, y, PAD_W, PAD_H, 6);
  ctx.fill();

  ctx.strokeStyle = "rgba(255,255,255,0.45)";
  ctx.lineWidth = 1;
  roundedRect(ctx, x, y, PAD_W, PAD_H, 6);
  ctx.stroke();
}

function drawScoreCard(ctx: CanvasRenderingContext2D, state: PongState): void {
  const x = WIDTH / 2 - 120;
  const y = 16;

  ctx.fillStyle = "rgba(20, 33, 55, 0.9)";
  roundedRect(ctx, x, y, 240, 68, 10);
  ctx.fill();

  ctx.strokeStyle = "#2b436a";
  ctx.lineWidth = 1;
  roundedRect(ctx, x, y, 240, 68, 10);
  ctx.stroke();

  ctx.fillStyle = "#8d99ae";
  ctx.font = "bold 11px Trebuchet MS, Segoe UI, sans-serif";
  ctx.fillText("P1", WIDTH / 2 - 55, 36);
  ctx.fillText(state.mode === "1p" ? "AI" : "P2", WIDTH / 2 + 55, 36);

  ctx.font = "bold 36px Trebuchet MS, Segoe UI, sans-serif";
  ctx.fillStyle = "#4cc9f0";
  ctx.fillText(String(state.p1s), WIDTH / 2 - 55, 66);
  ctx.fillStyle = "#f72585";
  ctx.fillText(String(state.p2s), WIDTH / 2 + 55, 66);
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
  const cleaned = hex.replace("#", "");
  const value = Number.parseInt(cleaned, 16);
  if (Number.isNaN(value)) {
    return hex;
  }

  const r = (value >> 16) & 255;
  const g = (value >> 8) & 255;
  const b = value & 255;

  const nr = Math.min(255, Math.round(r + (255 - r) * amount));
  const ng = Math.min(255, Math.round(g + (255 - g) * amount));
  const nb = Math.min(255, Math.round(b + (255 - b) * amount));

  return `rgb(${nr}, ${ng}, ${nb})`;
}

export default PongGame;
