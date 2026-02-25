import { useEffect, useMemo, useState } from "react";
import MobileControls from "../../components/ui/MobileControls";
import { useGameSession } from "../../services/progression/useGameSession";
import type { ControlScheme } from "../../types/settings";
import "./sudoku.css";

interface SudokuGameProps {
  onExit: () => void;
  controlScheme: ControlScheme;
}

const PUZZLE = [
  [5, 3, 0, 0, 7, 0, 0, 0, 0],
  [6, 0, 0, 1, 9, 5, 0, 0, 0],
  [0, 9, 8, 0, 0, 0, 0, 6, 0],
  [8, 0, 0, 0, 6, 0, 0, 0, 3],
  [4, 0, 0, 8, 0, 3, 0, 0, 1],
  [7, 0, 0, 0, 2, 0, 0, 0, 6],
  [0, 6, 0, 0, 0, 0, 2, 8, 0],
  [0, 0, 0, 4, 1, 9, 0, 0, 5],
  [0, 0, 0, 0, 8, 0, 0, 7, 9]
];

const SOLUTION = [
  [5, 3, 4, 6, 7, 8, 9, 1, 2],
  [6, 7, 2, 1, 9, 5, 3, 4, 8],
  [1, 9, 8, 3, 4, 2, 5, 6, 7],
  [8, 5, 9, 7, 6, 1, 4, 2, 3],
  [4, 2, 6, 8, 5, 3, 7, 9, 1],
  [7, 1, 3, 9, 2, 4, 8, 5, 6],
  [9, 6, 1, 5, 3, 7, 2, 8, 4],
  [2, 8, 7, 4, 1, 9, 6, 3, 5],
  [3, 4, 5, 2, 8, 6, 1, 7, 9]
];

function SudokuGame({ onExit, controlScheme }: SudokuGameProps) {
  const [board, setBoard] = useState(() => PUZZLE.map((r) => [...r]));
  const [sel, setSel] = useState<[number, number]>([4, 4]);
  const [mistakes, setMistakes] = useState(0);
  const session = useGameSession("sudoku");
  const exitToMenu = () => {
    session.recordPlaytimeOnly();
    onExit();
  };

  const won = useMemo(() => board.every((r, ri) => r.every((v, ci) => v === SOLUTION[ri][ci])), [board]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "q" || e.key === "Escape") exitToMenu();
      if (e.key === "r") {
        session.restartSession();
        setBoard(PUZZLE.map((r) => [...r]));
        setMistakes(0);
      }
      if (e.key === "ArrowUp") setSel(([r, c]) => [Math.max(0, r - 1), c]);
      if (e.key === "ArrowDown") setSel(([r, c]) => [Math.min(8, r + 1), c]);
      if (e.key === "ArrowLeft") setSel(([r, c]) => [r, Math.max(0, c - 1)]);
      if (e.key === "ArrowRight") setSel(([r, c]) => [r, Math.min(8, c + 1)]);
      const n = Number(e.key);
      if (n >= 1 && n <= 9) place(n);
      if (e.key === "Backspace" || e.key === "Delete") place(0);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [exitToMenu, session, won]);

  useEffect(() => {
    if (!won) {
      return;
    }
    session.recordResult({
      score: Math.max(0, 1500 - mistakes * 50),
      won: true,
      extra: {
        mistakes,
        hints_used: 0,
        difficulty: "medium"
      }
    });
  }, [mistakes, session, won]);

  const place = (n: number) => {
    const [r, c] = sel;
    if (PUZZLE[r][c] !== 0 || won) return;
    setBoard((prev) => {
      const next = prev.map((row) => [...row]);
      next[r][c] = n;
      return next;
    });
    if (n !== 0 && n !== SOLUTION[r][c]) setMistakes((m) => m + 1);
  };

  return (
    <section className="sudoku-screen">
      <header className="sudoku-header">
        <div>
          <h1>Sudoku</h1>
          <p>Arrow keys move, 1-9 place, R reset.</p>
        </div>
        <button type="button" onClick={exitToMenu}>Back to Menu</button>
      </header>

      <div className="sudoku-stats">
        <span>Mistakes: {mistakes}</span>
        {won && <span>Solved</span>}
      </div>

      <div className="sudoku-grid">
        {board.flatMap((row, r) =>
          row.map((v, c) => {
            const fixed = PUZZLE[r][c] !== 0;
            const selected = sel[0] === r && sel[1] === c;
            const wrong = v !== 0 && v !== SOLUTION[r][c] && !fixed;
            return (
              <button
                key={`${r}-${c}`}
                type="button"
                className={`sq ${fixed ? "fixed" : ""} ${selected ? "sel" : ""} ${wrong ? "wrong" : ""}`}
                onClick={() => setSel([r, c])}
              >
                {v || ""}
              </button>
            );
          })
        )}
      </div>

      <div className="sudoku-numpad">
        {[1,2,3,4,5,6,7,8,9].map((n) => (
          <button key={n} type="button" onClick={() => place(n)}>{n}</button>
        ))}
      </div>

      {controlScheme === "buttons" && (
        <MobileControls
          dpad={{ up: () => setSel(([r,c]) => [Math.max(0, r-1), c]), down: () => setSel(([r,c]) => [Math.min(8, r+1), c]), left: () => setSel(([r,c]) => [r, Math.max(0, c-1)]), right: () => setSel(([r,c]) => [r, Math.min(8, c+1)]) }}
          actions={[{ label: "Clear", onPress: () => place(0) }, { label: "Reset", onPress: () => { session.restartSession(); setBoard(PUZZLE.map((r) => [...r])); setMistakes(0);} }, { label: "Menu", onPress: exitToMenu }]}
        />
      )}
    </section>
  );
}

export default SudokuGame;
