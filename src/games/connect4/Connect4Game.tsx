import { useEffect, useMemo, useRef, useState } from "react";
import MobileControls from "../../components/ui/MobileControls";
import type { ControlScheme } from "../../types/settings";
import { COLS, aiMove, checkWin, drop, emptyGrid, validCols, winningCells, type Grid } from "./connect4.logic";
import "./connect4.css";

type Phase = "mode" | "difficulty" | "game";
type Mode = "1p" | "2p";
type Diff = "easy" | "medium" | "hard";

const DEPTH: Record<Diff, number> = { easy: 1, medium: 4, hard: 6 };
const RAND: Record<Diff, number> = { easy: 0.45, medium: 0, hard: 0 };

interface Connect4GameProps {
  onExit: () => void;
  controlScheme: ControlScheme;
}

function Connect4Game({ onExit, controlScheme }: Connect4GameProps) {
  const [phase, setPhase] = useState<Phase>("mode");
  const [mode, setMode] = useState<Mode | null>(null);
  const [diff, setDiff] = useState<Diff>("medium");
  const [sel, setSel] = useState(0);

  const [grid, setGrid] = useState<Grid>(() => emptyGrid());
  const [turn, setTurn] = useState<1 | 2>(1);
  const [winner, setWinner] = useState<0 | 1 | 2>(0);
  const [isDraw, setIsDraw] = useState(false);
  const [hover, setHover] = useState(Math.floor(COLS / 2));
  const [flashTick, setFlashTick] = useState(0);
  const [aiPending, setAiPending] = useState(false);
  const touchStartRef = useRef<{ x: number; y: number } | null>(null);

  const winCells = useMemo(() => (winner ? winningCells(grid, winner as 1 | 2) : []), [grid, winner]);

  const resetGame = () => {
    setGrid(emptyGrid());
    setTurn(1);
    setWinner(0);
    setIsDraw(false);
    setAiPending(false);
    setHover(Math.floor(COLS / 2));
  };

  const place = (col: number) => {
    if (phase !== "game" || winner || isDraw) return;
    if (mode === "1p" && turn === 2) return;

    const placed = drop(grid, col, turn);
    if (!placed) return;

    setGrid(placed.grid);

    if (checkWin(placed.grid, turn)) {
      setWinner(turn);
      return;
    }

    const valid = validCols(placed.grid);
    if (valid.length === 0) {
      setIsDraw(true);
      return;
    }

    const nextTurn = turn === 1 ? 2 : 1;
    setTurn(nextTurn);
    if (mode === "1p" && nextTurn === 2) {
      setAiPending(true);
    }
  };

  useEffect(() => {
    if (!winner) return;
    const id = window.setInterval(() => setFlashTick((v) => v + 1), 160);
    return () => window.clearInterval(id);
  }, [winner]);

  useEffect(() => {
    if (!aiPending || mode !== "1p" || phase !== "game" || winner || isDraw) {
      return;
    }
    const valid = validCols(grid);
    if (valid.length === 0) {
      setAiPending(false);
      return;
    }
    const timer = window.setTimeout(() => {
      let col: number | null = null;
      if (Math.random() < RAND[diff]) {
        col = valid[Math.floor(Math.random() * valid.length)] ?? null;
      } else {
        col = aiMove(grid, DEPTH[diff], 2);
      }
      setAiPending(false);
      if (col != null) {
        const placed = drop(grid, col, 2);
        if (!placed) return;
        setGrid(placed.grid);
        if (checkWin(placed.grid, 2)) {
          setWinner(2);
          return;
        }
        if (validCols(placed.grid).length === 0) {
          setIsDraw(true);
          return;
        }
        setTurn(1);
      }
    }, 200);
    return () => window.clearTimeout(timer);
  }, [aiPending, diff, grid, isDraw, mode, phase, winner]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      const k = event.key;
      if (k === "q" || k === "Escape") {
        if (phase === "difficulty") {
          setPhase("mode");
          setSel(0);
        } else {
          onExit();
        }
        return;
      }

      if (phase === "mode") {
        if (k === "ArrowUp") setSel((s) => (s + 1) % 2);
        if (k === "ArrowDown") setSel((s) => (s + 1) % 2);
        if (k === "Enter") {
          if (sel === 0) {
            setMode("1p");
            setPhase("difficulty");
            setSel(1);
          } else {
            setMode("2p");
            setPhase("game");
            resetGame();
          }
        }
        return;
      }

      if (phase === "difficulty") {
        if (k === "ArrowUp") setSel((s) => (s + 2) % 3);
        if (k === "ArrowDown") setSel((s) => (s + 1) % 3);
        if (k === "Enter") {
          const d = (["easy", "medium", "hard"] as Diff[])[sel] ?? "medium";
          setDiff(d);
          setPhase("game");
          resetGame();
        }
        return;
      }

      if (phase === "game") {
        if (k === "r") {
          resetGame();
          return;
        }
        if (winner || isDraw || (mode === "1p" && turn === 2)) {
          return;
        }
        if (k === "ArrowLeft") setHover((h) => Math.max(0, h - 1));
        if (k === "ArrowRight") setHover((h) => Math.min(COLS - 1, h + 1));
        if (["Enter", " ", "ArrowDown"].includes(k)) {
          place(hover);
        }
      }
    };

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [hover, isDraw, mode, onExit, phase, sel, turn, winner]);

  return (
    <section className="c4-screen">
      <header className="c4-header">
        <div>
          <h1>Connect 4</h1>
          <p>Line up four discs before your opponent.</p>
        </div>
        <button type="button" onClick={onExit}>Back to Menu</button>
      </header>

      {phase === "mode" && <SelectCard title="CONNECT 4" options={["1 Player vs AI", "2 Players Local"]} sel={sel} />}
      {phase === "difficulty" && <SelectCard title="Difficulty" options={["Easy", "Medium", "Hard"]} sel={sel} />}

      {phase === "game" && (
        <section className="c4-game">
          <div className="c4-status">
            <span>P1 vs {mode === "1p" ? "AI" : "P2"}</span>
            {!winner && !isDraw && <span>{turn === 1 ? "P1" : mode === "1p" ? "AI" : "P2"} turn</span>}
            {winner !== 0 && <span>{winner === 1 ? "P1" : mode === "1p" ? "AI" : "P2"} wins</span>}
            {isDraw && <span>Draw</span>}
          </div>

          <div
            className="c4-board"
            onMouseMove={(e) => {
              const rect = (e.currentTarget as HTMLDivElement).getBoundingClientRect();
              const x = e.clientX - rect.left;
              const c = Math.floor(x / (rect.width / COLS));
              if (c >= 0 && c < COLS) setHover(c);
            }}
            onClick={(e) => {
              const rect = (e.currentTarget as HTMLDivElement).getBoundingClientRect();
              const x = e.clientX - rect.left;
              const c = Math.floor(x / (rect.width / COLS));
              if (c >= 0 && c < COLS) place(c);
            }}
            onTouchStart={(event) => {
              if (controlScheme !== "gestures") return;
              const touch = event.touches[0];
              touchStartRef.current = { x: touch.clientX, y: touch.clientY };
            }}
            onTouchEnd={(event) => {
              if (controlScheme !== "gestures" || !touchStartRef.current) return;
              const touch = event.changedTouches[0];
              const dx = touch.clientX - touchStartRef.current.x;
              const dy = touch.clientY - touchStartRef.current.y;
              touchStartRef.current = null;
              if (Math.abs(dx) > Math.abs(dy) && Math.abs(dx) > 16) {
                setHover((h) => Math.max(0, Math.min(COLS - 1, h + (dx > 0 ? 1 : -1))));
              } else {
                place(hover);
              }
            }}
          >
            <div className="c4-hover" style={{ left: `calc(${(hover / COLS) * 100}% + (100% / ${COLS} / 2))` }} />
            {grid.flatMap((row, r) =>
              row.map((cell, c) => {
                const highlight = winCells.some(([wr, wc]) => wr === r && wc === c) && flashTick % 2 === 0;
                return (
                  <div key={`${r}-${c}`} className="c4-cell">
                    <span className={`disc ${cell === 1 ? "p1" : cell === 2 ? "p2" : "empty"} ${highlight ? "hl" : ""}`} />
                  </div>
                );
              })
            )}
          </div>
        </section>
      )}

      {controlScheme === "buttons" && phase === "game" && (
        <MobileControls
          dpad={{ left: () => setHover((h) => Math.max(0, h - 1)), right: () => setHover((h) => Math.min(COLS - 1, h + 1)) }}
          actions={[{ label: "Drop", onPress: () => place(hover) }, { label: "Restart", onPress: resetGame }, { label: "Menu", onPress: onExit }]}
        />
      )}

      {controlScheme === "buttons" && phase !== "game" && (
        <MobileControls
          dpad={{ up: () => setSel((s) => (phase === "mode" ? (s + 1) % 2 : (s + 2) % 3)), down: () => setSel((s) => (phase === "mode" ? (s + 1) % 2 : (s + 1) % 3)) }}
          actions={[
            {
              label: "Select",
              onPress: () => {
                if (phase === "mode") {
                  if (sel === 0) {
                    setMode("1p");
                    setPhase("difficulty");
                    setSel(1);
                  } else {
                    setMode("2p");
                    setPhase("game");
                    resetGame();
                  }
                } else if (phase === "difficulty") {
                  const d = (["easy", "medium", "hard"] as Diff[])[sel] ?? "medium";
                  setDiff(d);
                  setPhase("game");
                  resetGame();
                }
              }
            },
            { label: "Back", onPress: onExit }
          ]}
        />
      )}
    </section>
  );
}

function SelectCard({ title, options, sel }: { title: string; options: string[]; sel: number }) {
  return (
    <section className="c4-select">
      <h2>{title}</h2>
      {options.map((opt, i) => (
        <div key={opt} className={`opt ${i === sel ? "active" : ""}`}>{opt}</div>
      ))}
    </section>
  );
}

export default Connect4Game;
