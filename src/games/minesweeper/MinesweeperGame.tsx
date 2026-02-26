import { useEffect, useMemo, useRef, useState } from "react";
import MobileControls from "../../components/ui/MobileControls";
import { useGameSession } from "../../services/progression/useGameSession";
import type { ControlScheme } from "../../types/settings";
import { DIFFICULTIES, countFlags, createState, placeMines, reveal, toggleFlag, type Diff, type MineState } from "./minesweeper.logic";
import "./minesweeper.css";

interface MinesweeperGameProps {
  onExit: () => void;
  controlScheme: ControlScheme;
}

function MinesweeperGame({ onExit, controlScheme }: MinesweeperGameProps) {
  const [phase, setPhase] = useState<"select" | "game">("select");
  const [sel, setSel] = useState(0);
  const [diff, setDiff] = useState<Diff | null>(null);
  const [state, setState] = useState<MineState | null>(null);
  const [seconds, setSeconds] = useState(0);
  const [mode, setMode] = useState<"reveal" | "flag">("reveal");
  const pressRef = useRef<number | null>(null);
  const session = useGameSession("minesweeper");
  const exitToMenu = () => {
    session.recordPlaytimeOnly();
    onExit();
  };

  const start = (idx: number) => {
    session.restartSession();
    const d = DIFFICULTIES[idx] ?? DIFFICULTIES[1];
    setDiff(d);
    setState(createState(d));
    setSeconds(0);
    setPhase("game");
  };

  useEffect(() => {
    if (!state || state.dead || state.won || state.firstClick) return;
    const id = window.setInterval(() => setSeconds((s) => s + 1), 1000);
    return () => window.clearInterval(id);
  }, [state]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      const k = event.key;
      if (k === "q" || k === "Escape") {
        exitToMenu();
        return;
      }
      if (phase === "select") {
        if (k === "ArrowUp") setSel((s) => (s + 2) % 3);
        if (k === "ArrowDown") setSel((s) => (s + 1) % 3);
        if (k === "Enter") start(sel);
        return;
      }
      if (phase === "game" && diff) {
        if (k === "r") start(DIFFICULTIES.findIndex((d) => d.name === diff.name));
        if (k === "f") setMode((m) => (m === "reveal" ? "flag" : "reveal"));
      }
    };

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [diff, exitToMenu, phase, sel, session]);

  useEffect(() => {
    if (!state || (!state.dead && !state.won)) {
      return;
    }
    session.recordResult({
      score: state.won ? Math.max(0, 1000 - seconds * 5) : 0,
      won: state.won,
      extra: {
        difficulty: diff?.name?.toLowerCase() ?? "medium"
      }
    });
  }, [diff?.name, seconds, session, state]);

  const flags = useMemo(() => (state ? countFlags(state.flagged) : 0), [state]);

  return (
    <section className="ms-screen">
      <header className="ms-header">
        <div>
          <h1>Minesweeper</h1>
          <p>Reveal all non-mine cells.</p>
        </div>
        <button type="button" onClick={exitToMenu}>Back to Menu</button>
      </header>

      {phase === "select" && (
        <section className="ms-select">
          {DIFFICULTIES.map((d, i) => (
            <div key={d.name} className={`opt ${i === sel ? "active" : ""}`}>
              <strong>{d.name}</strong>
              <span>{d.cols}x{d.rows} | {d.mines} mines</span>
            </div>
          ))}
        </section>
      )}

      {phase === "game" && state && diff && (
        <section className="ms-game">
          <div className="ms-stats">
            <span>Mines Left: {Math.max(0, diff.mines - flags)}</span>
            <span>Time: {seconds}s</span>
            <span>Mode: {mode}</span>
          </div>

          <div className="ms-board" style={{ gridTemplateColumns: `repeat(${diff.cols}, 1fr)` }}>
            {state.board.flatMap((row, r) =>
              row.map((cell, c) => {
                const rev = state.revealed[r][c];
                const flag = state.flagged[r][c];
                const deadMine = rev && cell === -1;

                return (
                  <button
                    key={`${r}-${c}`}
                    type="button"
                    className={`ms-cell ${rev ? "rev" : "hid"} ${deadMine ? "mine" : ""}`}
                    onClick={(e) => {
                      e.preventDefault();
                      if (state.dead || state.won) return;
                      setState((prev) => {
                        if (!prev) return prev;
                        let next = prev;
                        if (mode === "flag") {
                          next = toggleFlag(next, r, c);
                        } else {
                          if (next.firstClick) {
                            const b = next.board.map((rr) => [...rr]);
                            placeMines(b, r, c, diff.mines);
                            next = { ...next, firstClick: false, board: b };
                          }
                          next = reveal(next, r, c);
                        }
                        return next;
                      });
                    }}
                    onContextMenu={(e) => {
                      e.preventDefault();
                      if (state.dead || state.won) return;
                      setState((prev) => (prev ? toggleFlag(prev, r, c) : prev));
                    }}
                    onTouchStart={(event) => {
                      if (controlScheme !== "gestures") return;
                      event.preventDefault();
                      pressRef.current = window.setTimeout(() => {
                        setState((prev) => (prev ? toggleFlag(prev, r, c) : prev));
                      }, 350);
                    }}
                    onTouchEnd={(event) => {
                      if (controlScheme !== "gestures") return;
                      event.preventDefault();
                      if (pressRef.current != null) {
                        window.clearTimeout(pressRef.current);
                        pressRef.current = null;
                        setState((prev) => {
                          if (!prev || prev.dead || prev.won) return prev;
                          let next = prev;
                          if (next.firstClick) {
                            const b = next.board.map((rr) => [...rr]);
                            placeMines(b, r, c, diff.mines);
                            next = { ...next, firstClick: false, board: b };
                          }
                          return reveal(next, r, c);
                        });
                      }
                    }}
                  >
                    {rev ? (cell === -1 ? "*" : cell === 0 ? "" : cell) : flag ? "F" : ""}
                  </button>
                );
              })
            )}
          </div>

          {(state.dead || state.won) && (
            <div className="ms-end">{state.won ? "CLEARED!" : "BOOM!"}</div>
          )}
        </section>
      )}

      {controlScheme === "buttons" && phase === "select" && (
        <MobileControls
          dpad={{ up: () => setSel((s) => (s + 2) % 3), down: () => setSel((s) => (s + 1) % 3) }}
          actions={[{ label: "Start", onPress: () => start(sel) }, { label: "Menu", onPress: exitToMenu }]}
        />
      )}

      {controlScheme === "buttons" && phase === "game" && diff && (
        <MobileControls
          actions={[
            { label: mode === "reveal" ? "Switch Flag" : "Switch Reveal", onPress: () => setMode((m) => (m === "reveal" ? "flag" : "reveal")) },
            { label: "Restart", onPress: () => start(DIFFICULTIES.findIndex((d) => d.name === diff.name)) },
            { label: "Menu", onPress: exitToMenu }
          ]}
        />
      )}
    </section>
  );
}

export default MinesweeperGame;
