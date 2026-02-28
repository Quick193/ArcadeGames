import { useEffect, useMemo, useState } from "react";
import MobileControls from "../../components/ui/MobileControls";
import { useGameSession } from "../../services/progression/useGameSession";
import type { ControlScheme } from "../../types/settings";
import "./sudoku.css";

interface SudokuGameProps {
  onExit: () => void;
  controlScheme: ControlScheme;
}

type Difficulty = "easy" | "medium" | "hard";
type Board = number[][];
type Pencil = Set<number>[][]; // [r][c] => candidate digits
type Phase = "select" | "loading" | "game";

const DIFFICULTIES: Array<{ id: Difficulty; name: string; givens: number }> = [
  { id: "easy", name: "Easy", givens: 45 },
  { id: "medium", name: "Medium", givens: 34 },
  { id: "hard", name: "Hard", givens: 25 }
];

const MAX_MISTAKES = 3;

function SudokuGame({ onExit, controlScheme }: SudokuGameProps) {
  const session = useGameSession("sudoku");
  const [phase, setPhase] = useState<Phase>("select");
  const [selDiff, setSelDiff] = useState(1);
  const [difficulty, setDifficulty] = useState<Difficulty>("medium");

  const [puzzle, setPuzzle] = useState<Board>(() => emptyBoard());
  const [solution, setSolution] = useState<Board>(() => emptyBoard());
  const [board, setBoard] = useState<Board>(() => emptyBoard());
  const [pencil, setPencil] = useState<Pencil>(() => emptyPencil());
  const [sel, setSel] = useState<[number, number]>([4, 4]);
  const [mistakes, setMistakes] = useState(0);
  const [hintsUsed, setHintsUsed] = useState(0);
  const [pencilMode, setPencilMode] = useState(false);
  const [paused, setPaused] = useState(false);
  const [seconds, setSeconds] = useState(0);
  const [wrongCellKey, setWrongCellKey] = useState<string | null>(null);

  const solved = useMemo(
    () => board.every((r, ri) => r.every((v, ci) => v !== 0 && v === solution[ri][ci])),
    [board, solution]
  );
  const lost = mistakes >= MAX_MISTAKES;
  const done = solved || lost;

  const selectedValue = board[sel[0]][sel[1]];

  const exitToMenu = () => {
    session.recordPlaytimeOnly();
    onExit();
  };

  const startDifficulty = (index: number) => {
    const d = DIFFICULTIES[index] ?? DIFFICULTIES[1];
    session.restartSession();
    setSelDiff(index);
    setDifficulty(d.id);
    setPhase("loading");
  };

  const resetCurrent = () => {
    session.restartSession();
    setBoard(puzzle.map((r) => [...r]));
    setPencil(emptyPencil());
    setMistakes(0);
    setHintsUsed(0);
    setPencilMode(false);
    setPaused(false);
    setSeconds(0);
    setSel([4, 4]);
    setWrongCellKey(null);
    setPhase("game");
  };

  useEffect(() => {
    if (phase !== "loading") {
      return;
    }
    const id = window.setTimeout(() => {
      const d = DIFFICULTIES[selDiff] ?? DIFFICULTIES[1];
      const generated = generatePuzzle(d.givens);
      setPuzzle(generated.puzzle);
      setSolution(generated.solution);
      setBoard(generated.puzzle.map((r) => [...r]));
      setPencil(emptyPencil());
      setMistakes(0);
      setHintsUsed(0);
      setPencilMode(false);
      setPaused(false);
      setSeconds(0);
      setSel([4, 4]);
      setWrongCellKey(null);
      setPhase("game");
    }, 10);
    return () => window.clearTimeout(id);
  }, [phase, selDiff]);

  useEffect(() => {
    if (phase !== "game" || done || paused) {
      return;
    }
    const id = window.setInterval(() => setSeconds((s) => s + 1), 1000);
    return () => window.clearInterval(id);
  }, [done, paused, phase]);

  useEffect(() => {
    if (phase !== "game" || !done) {
      return;
    }
    const winScore = Math.max(0, 2000 - seconds * 4 - mistakes * 70 - hintsUsed * 80);
    session.recordResult({
      score: solved ? winScore : 0,
      won: solved,
      extra: {
        mistakes,
        hints_used: hintsUsed,
        difficulty
      }
    });
  }, [difficulty, done, hintsUsed, mistakes, phase, seconds, session, solved]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "q" || e.key === "Escape") {
        exitToMenu();
        return;
      }

      if (phase === "select") {
        if (e.key === "ArrowUp") setSelDiff((s) => (s + DIFFICULTIES.length - 1) % DIFFICULTIES.length);
        if (e.key === "ArrowDown") setSelDiff((s) => (s + 1) % DIFFICULTIES.length);
        if (e.key === "Enter") startDifficulty(selDiff);
        return;
      }

      if (phase !== "game") {
        return;
      }

      if (e.key === "n") {
        startDifficulty(selDiff);
        return;
      }
      if (e.key === "r") {
        resetCurrent();
        return;
      }
      if (e.key === "h") {
        revealHint();
        return;
      }
      if (e.key === "p") {
        setPaused((v) => !v);
        return;
      }
      if (e.key === "m" || e.key === "`") {
        setPencilMode((v) => !v);
        return;
      }
      if (paused) return;
      if (e.key === "ArrowUp") setSel(([r, c]) => [Math.max(0, r - 1), c]);
      if (e.key === "ArrowDown") setSel(([r, c]) => [Math.min(8, r + 1), c]);
      if (e.key === "ArrowLeft") setSel(([r, c]) => [r, Math.max(0, c - 1)]);
      if (e.key === "ArrowRight") setSel(([r, c]) => [r, Math.min(8, c + 1)]);

      const n = Number(e.key);
      if (n >= 1 && n <= 9) place(n);
      if (e.key === "Backspace" || e.key === "Delete" || e.key === "0") place(0);
    };

    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [done, exitToMenu, paused, phase, selDiff]);

  const revealHint = () => {
    if (done || phase !== "game" || paused || hintsUsed >= 3) {
      return;
    }
    const empty: Array<[number, number]> = [];
    for (let r = 0; r < 9; r += 1) {
      for (let c = 0; c < 9; c += 1) {
        if (board[r][c] === 0) {
          empty.push([r, c]);
        }
      }
    }
    if (empty.length === 0) {
      return;
    }
    const [r, c] = empty[Math.floor(Math.random() * empty.length)] as [number, number];
    setBoard((prev) => {
      const next = prev.map((row) => [...row]);
      next[r][c] = solution[r][c];
      return next;
    });
    setPencil((prev) => clearPencilAt(prev, r, c));
    setHintsUsed((h) => h + 1);
  };

  const place = (n: number) => {
    if (phase !== "game" || done || paused) {
      return;
    }
    const [r, c] = sel;
    if (puzzle[r][c] !== 0) {
      return;
    }

    if (pencilMode && n > 0) {
      setPencil((prev) => {
        const next = clonePencil(prev);
        if (next[r][c].has(n)) next[r][c].delete(n);
        else next[r][c].add(n);
        return next;
      });
      return;
    }

    setBoard((prev) => {
      const next = prev.map((row) => [...row]);
      next[r][c] = n;
      return next;
    });

    setPencil((prev) => {
      const next = clonePencil(prev);
      next[r][c].clear();
      if (n > 0) {
        removePencilPeers(next, r, c, n);
      }
      return next;
    });

    if (n > 0 && n !== solution[r][c]) {
      setMistakes((m) => m + 1);
      const key = `${r}-${c}`;
      setWrongCellKey(key);
      window.setTimeout(() => {
        setWrongCellKey((curr) => (curr === key ? null : curr));
      }, 550);
    }
  };

  return (
    <section className="sudoku-screen">
      <header className="sudoku-header">
        <div>
          <h1>Sudoku</h1>
          <p>N new puzzle, H hint, P pause, M pencil mode, R reset, Q menu.</p>
        </div>
        <button type="button" onClick={exitToMenu}>Back to Menu</button>
      </header>

      {phase === "select" && (
        <section className="sudoku-select">
          <h2>Select Difficulty</h2>
          {DIFFICULTIES.map((d, i) => (
            <button key={d.id} type="button" className={`opt ${i === selDiff ? "active" : ""}`} onClick={() => startDifficulty(i)}>
              {d.name} • {d.givens} givens
            </button>
          ))}
        </section>
      )}

      {phase === "loading" && (
        <section className="sudoku-loading">
          <p>Generating unique puzzle...</p>
        </section>
      )}

      {phase === "game" && (
        <>
          <div className="sudoku-stats">
            <span>Difficulty: {difficulty}</span>
            <span>Time: {formatTime(seconds)}</span>
            <span>Mistakes: {mistakes}/{MAX_MISTAKES}</span>
            <span>Hints: {hintsUsed}/3</span>
            <span>Mode: {pencilMode ? "Pencil" : "Normal"}</span>
            {paused && <span>Paused</span>}
            {solved && <span>Solved</span>}
            {lost && <span>Failed</span>}
          </div>

          <div className="sudoku-grid">
            {board.flatMap((row, r) =>
              row.map((v, c) => {
                const fixed = puzzle[r][c] !== 0;
                const selected = sel[0] === r && sel[1] === c;
                const peer = sel[0] === r || sel[1] === c || Math.floor(sel[0] / 3) === Math.floor(r / 3) && Math.floor(sel[1] / 3) === Math.floor(c / 3);
                const sameNum = selectedValue !== 0 && v === selectedValue;
                const wrong = wrongCellKey === `${r}-${c}` || (v !== 0 && v !== solution[r][c] && !fixed);
                const notes = pencil[r][c];

                return (
                  <button
                    key={`${r}-${c}`}
                    type="button"
                    className={[
                      "sq",
                      fixed ? "fixed" : "",
                      selected ? "sel" : "",
                      peer ? "peer" : "",
                      sameNum ? "same" : "",
                      wrong ? "wrong" : ""
                    ].join(" ")}
                    onClick={() => {
                      if (paused) return;
                      setSel([r, c]);
                    }}
                  >
                    {v > 0 ? (
                      <span>{v}</span>
                    ) : (
                      <small>
                        {[1, 2, 3, 4, 5, 6, 7, 8, 9].filter((n) => notes.has(n)).join("")}
                      </small>
                    )}
                  </button>
                );
              })
            )}
          </div>

          <div className="sudoku-numpad">
            {[1, 2, 3, 4, 5, 6, 7, 8, 9].map((n) => (
              <button key={n} type="button" onClick={() => place(n)}>{n}</button>
            ))}
            <button type="button" onClick={() => place(0)}>Clear</button>
            <button type="button" onClick={() => setPencilMode((v) => !v)}>{pencilMode ? "Normal" : "Pencil"}</button>
            <button type="button" onClick={revealHint} disabled={paused || hintsUsed >= 3}>Hint</button>
            <button type="button" onClick={() => setPaused((v) => !v)}>{paused ? "Resume" : "Pause"}</button>
          </div>

          {paused && (
            <div className="sudoku-overlay">
              <strong>Paused</strong>
              <span>Press P to resume</span>
            </div>
          )}

          {solved && (
            <div className="sudoku-overlay solved">
              <strong>Puzzle Solved!</strong>
              <span>N new game or Q menu</span>
            </div>
          )}

          {lost && (
            <div className="sudoku-overlay failed">
              <strong>Too Many Mistakes</strong>
              <span>N new game or Q menu</span>
            </div>
          )}
        </>
      )}

      {controlScheme === "buttons" && phase === "game" && (
        <MobileControls
          dpad={{
            up: () => setSel(([r, c]) => [Math.max(0, r - 1), c]),
            down: () => setSel(([r, c]) => [Math.min(8, r + 1), c]),
            left: () => setSel(([r, c]) => [r, Math.max(0, c - 1)]),
            right: () => setSel(([r, c]) => [r, Math.min(8, c + 1)])
          }}
          actions={[
            { label: pencilMode ? "Normal" : "Pencil", onPress: () => setPencilMode((v) => !v) },
            { label: "Hint", onPress: revealHint },
            { label: paused ? "Resume" : "Pause", onPress: () => setPaused((v) => !v) },
            { label: "Reset", onPress: resetCurrent },
            { label: "New", onPress: () => startDifficulty(selDiff) },
            { label: "Menu", onPress: exitToMenu }
          ]}
        />
      )}
    </section>
  );
}

function emptyBoard(): Board {
  return Array.from({ length: 9 }, () => Array(9).fill(0));
}

function emptyPencil(): Pencil {
  return Array.from({ length: 9 }, () => Array.from({ length: 9 }, () => new Set<number>()));
}

function clonePencil(p: Pencil): Pencil {
  return p.map((row) => row.map((cell) => new Set(cell)));
}

function clearPencilAt(p: Pencil, r: number, c: number): Pencil {
  const next = clonePencil(p);
  next[r][c].clear();
  return next;
}

function removePencilPeers(p: Pencil, r: number, c: number, n: number): void {
  for (let i = 0; i < 9; i += 1) {
    p[r][i].delete(n);
    p[i][c].delete(n);
  }
  const br = Math.floor(r / 3) * 3;
  const bc = Math.floor(c / 3) * 3;
  for (let rr = br; rr < br + 3; rr += 1) {
    for (let cc = bc; cc < bc + 3; cc += 1) {
      p[rr][cc].delete(n);
    }
  }
}

function isValid(board: Board, r: number, c: number, n: number): boolean {
  if (board[r].includes(n)) return false;
  for (let rr = 0; rr < 9; rr += 1) {
    if (board[rr][c] === n) return false;
  }
  const br = Math.floor(r / 3) * 3;
  const bc = Math.floor(c / 3) * 3;
  for (let rr = br; rr < br + 3; rr += 1) {
    for (let cc = bc; cc < bc + 3; cc += 1) {
      if (board[rr][cc] === n) return false;
    }
  }
  return true;
}

function solve(board: Board, shuffle: boolean): boolean {
  for (let r = 0; r < 9; r += 1) {
    for (let c = 0; c < 9; c += 1) {
      if (board[r][c] !== 0) continue;
      const nums = [1, 2, 3, 4, 5, 6, 7, 8, 9];
      if (shuffle) shuffleInPlace(nums);
      for (const n of nums) {
        if (!isValid(board, r, c, n)) continue;
        board[r][c] = n;
        if (solve(board, shuffle)) return true;
        board[r][c] = 0;
      }
      return false;
    }
  }
  return true;
}

function countSolutions(board: Board, limit = 2): number {
  let count = 0;
  const work = board.map((r) => [...r]);
  const backtrack = (): void => {
    if (count >= limit) return;
    for (let r = 0; r < 9; r += 1) {
      for (let c = 0; c < 9; c += 1) {
        if (work[r][c] !== 0) continue;
        for (let n = 1; n <= 9; n += 1) {
          if (!isValid(work, r, c, n)) continue;
          work[r][c] = n;
          backtrack();
          work[r][c] = 0;
        }
        return;
      }
    }
    count += 1;
  };
  backtrack();
  return count;
}

function generatePuzzle(givens: number): { puzzle: Board; solution: Board } {
  const solution = emptyBoard();
  solve(solution, true);
  const puzzle = solution.map((r) => [...r]);
  const cells: Array<[number, number]> = [];
  for (let r = 0; r < 9; r += 1) {
    for (let c = 0; c < 9; c += 1) {
      cells.push([r, c]);
    }
  }
  shuffleInPlace(cells);
  const targetRemovals = 81 - givens;
  let removed = 0;
  for (const [r, c] of cells) {
    if (removed >= targetRemovals) break;
    const old = puzzle[r][c];
    puzzle[r][c] = 0;
    if (countSolutions(puzzle, 2) === 1) {
      removed += 1;
    } else {
      puzzle[r][c] = old;
    }
  }
  return { puzzle, solution };
}

function shuffleInPlace<T>(arr: T[]): void {
  for (let i = arr.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [arr[i], arr[j]] = [arr[j] as T, arr[i] as T];
  }
}

function formatTime(total: number): string {
  const m = Math.floor(total / 60);
  const s = total % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}

export default SudokuGame;
