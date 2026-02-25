import { useEffect, useRef, useState } from "react";
import MobileControls from "../../components/ui/MobileControls";
import { useGameSession } from "../../services/progression/useGameSession";
import type { ControlScheme } from "../../types/settings";
import { GRID, applyMove, bestTile, createInitialState, type Direction, type Game2048State } from "./game2048.logic";
import "./game2048.css";

interface Game2048Props {
  onExit: () => void;
  controlScheme: ControlScheme;
}

const COLORS: Record<number, { bg: string; fg: string }> = {
  0: { bg: "#28303f", fg: "#6b7280" },
  2: { bg: "#eee4da", fg: "#776e65" },
  4: { bg: "#ede0c8", fg: "#776e65" },
  8: { bg: "#f2b179", fg: "#f9f6f2" },
  16: { bg: "#f59563", fg: "#f9f6f2" },
  32: { bg: "#f67c5f", fg: "#f9f6f2" },
  64: { bg: "#f65e3b", fg: "#f9f6f2" },
  128: { bg: "#edcf72", fg: "#f9f6f2" },
  256: { bg: "#edcc61", fg: "#f9f6f2" },
  512: { bg: "#edc850", fg: "#f9f6f2" },
  1024: { bg: "#edc53f", fg: "#f9f6f2" },
  2048: { bg: "#edc22e", fg: "#f9f6f2" }
};

function Game2048({ onExit, controlScheme }: Game2048Props) {
  const [state, setState] = useState<Game2048State>(() => createInitialState());
  const [bestScore, setBestScore] = useState<number>(() => readBestScore());
  const touchStartRef = useRef<{ x: number; y: number } | null>(null);
  const session = useGameSession("game_2048");
  const exitToMenu = () => {
    session.recordPlaytimeOnly();
    onExit();
  };

  const move = (dir: Direction) => {
    setState((prev) => applyMove(prev, dir));
  };

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "q" || event.key === "Escape") {
        exitToMenu();
        return;
      }

      if (event.key === "r") {
        session.restartSession();
        setState(createInitialState());
        return;
      }

      const dir = keyToDirection(event.key);
      if (!dir) {
        return;
      }

      event.preventDefault();
      move(dir);
    };

    window.addEventListener("keydown", onKeyDown);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
    };
  }, [exitToMenu, session]);

  useEffect(() => {
    if (state.score <= bestScore) {
      return;
    }

    setBestScore(state.score);
    writeBestScore(state.score);
  }, [bestScore, state.score]);

  const topTile = bestTile(state.board);

  useEffect(() => {
    if (!state.dead && !state.won) {
      return;
    }
    session.recordResult({
      score: state.score,
      won: state.won,
      extra: {
        max_tile: topTile
      }
    });
  }, [session, state.dead, state.score, state.won, topTile]);

  return (
    <section className="g2048-screen">
      <header className="g2048-header">
        <div>
          <h1>2048</h1>
          <p>Arrow keys move tiles. R restart, Q menu.</p>
        </div>
        <button type="button" onClick={exitToMenu}>
          Back to Menu
        </button>
      </header>

      <section className="g2048-stats">
        <span>Score: {state.score}</span>
        <span>Best: {Math.max(bestScore, state.score)}</span>
        <span>Top Tile: {topTile}</span>
      </section>

      <section className="g2048-board-wrap">
        <div
          className="g2048-board"
          style={{ gridTemplateColumns: `repeat(${GRID}, 1fr)` }}
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

            const threshold = 24;
            if (Math.abs(dx) < threshold && Math.abs(dy) < threshold) {
              return;
            }
            if (Math.abs(dx) > Math.abs(dy)) {
              move(dx > 0 ? "right" : "left");
            } else {
              move(dy > 0 ? "down" : "up");
            }
          }}
        >
          {state.board.flatMap((row, r) =>
            row.map((value, c) => {
              const key = `${r}-${c}`;
              const color = COLORS[value] ?? { bg: "#3cc86f", fg: "#ffffff" };
              return (
                <div
                  key={key}
                  className="g2048-tile"
                  style={{ background: color.bg, color: color.fg }}
                  data-big={value >= 1024 ? "true" : "false"}
                >
                  {value > 0 ? value : ""}
                </div>
              );
            })
          )}
        </div>

        {(state.dead || state.won) && (
          <div className="g2048-overlay">
            <h2>{state.won ? "YOU WIN!" : "GAME OVER"}</h2>
            <p>Score: {state.score}</p>
            <p>{state.won ? "Continue playing or press R to restart." : "Press R to restart."}</p>
          </div>
        )}
      </section>

      {controlScheme === "buttons" ? (
        <MobileControls
          dpad={{
            up: () => move("up"),
            down: () => move("down"),
            left: () => move("left"),
            right: () => move("right")
          }}
          actions={[
            { label: "Restart", onPress: () => { session.restartSession(); setState(createInitialState()); } },
            { label: "Menu", onPress: exitToMenu }
          ]}
        />
      ) : (
        <MobileControls
          actions={[
            { label: "Restart", onPress: () => { session.restartSession(); setState(createInitialState()); } },
            { label: "Menu", onPress: exitToMenu }
          ]}
        />
      )}
    </section>
  );
}

function keyToDirection(key: string): Direction | null {
  if (key === "ArrowLeft") {
    return "left";
  }
  if (key === "ArrowRight") {
    return "right";
  }
  if (key === "ArrowUp") {
    return "up";
  }
  if (key === "ArrowDown") {
    return "down";
  }
  return null;
}

function readBestScore(): number {
  const raw = window.localStorage.getItem("arcade.2048.best");
  const parsed = Number(raw);
  return Number.isFinite(parsed) ? parsed : 0;
}

function writeBestScore(score: number): void {
  window.localStorage.setItem("arcade.2048.best", String(score));
}

export default Game2048;
