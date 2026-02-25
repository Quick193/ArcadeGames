import { useEffect, useState } from "react";
import { useGameSession } from "../../services/progression/useGameSession";
import type { ControlScheme } from "../../types/settings";
import "./chess.css";

interface ChessGameProps {
  onExit: () => void;
  controlScheme: ControlScheme;
}

type Board = (string | null)[][];

function ChessGame({ onExit }: ChessGameProps) {
  const [board, setBoard] = useState<Board>(() => initialBoard());
  const [whiteTurn, setWhiteTurn] = useState(true);
  const [selected, setSelected] = useState<[number, number] | null>(null);
  const session = useGameSession("chess");
  const exitToMenu = () => {
    session.recordPlaytimeOnly();
    onExit();
  };

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "q" || e.key === "Escape") exitToMenu();
      if (e.key === "r") {
        session.restartSession();
        setBoard(initialBoard());
        setWhiteTurn(true);
        setSelected(null);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [exitToMenu, session]);

  useEffect(() => {
    const flat = board.flat().filter(Boolean) as string[];
    const blackKingAlive = flat.includes("k");
    const whiteKingAlive = flat.includes("K");
    if (!blackKingAlive || !whiteKingAlive) {
      session.recordResult({
        score: flat.length,
        won: blackKingAlive ? false : true
      });
    }
  }, [board, session]);

  return (
    <section className="chess-screen">
      <header className="chess-header">
        <div>
          <h1>Chess</h1>
          <p>React migration version (core piece movement). R reset, Q menu.</p>
        </div>
        <button type="button" onClick={exitToMenu}>Back to Menu</button>
      </header>

      <div className="chess-info">Turn: {whiteTurn ? "White" : "Black"}</div>

      <div className="chess-board">
        {board.flatMap((row, r) =>
          row.map((piece, c) => {
            const dark = (r + c) % 2 === 1;
            const sel = selected?.[0] === r && selected?.[1] === c;
            return (
              <button
                key={`${r}-${c}`}
                type="button"
                className={`chess-cell ${dark ? "dark" : "light"} ${sel ? "sel" : ""}`}
                onClick={() => {
                  if (selected) {
                    const [sr, sc] = selected;
                    if (sr === r && sc === c) {
                      setSelected(null);
                      return;
                    }
                    const from = board[sr][sc];
                    if (!from) {
                      setSelected(null);
                      return;
                    }
                    const legal = pseudoLegal(board, sr, sc);
                    if (legal.some(([rr, cc]) => rr === r && cc === c)) {
                      setBoard((prev) => {
                        const next = prev.map((rr) => [...rr]);
                        next[r][c] = from;
                        next[sr][sc] = null;
                        return next;
                      });
                      setWhiteTurn((t) => !t);
                      setSelected(null);
                    } else {
                      if (piece && isWhite(piece) === whiteTurn) setSelected([r, c]);
                      else setSelected(null);
                    }
                  } else if (piece && isWhite(piece) === whiteTurn) {
                    setSelected([r, c]);
                  }
                }}
              >
                {pieceToGlyph(piece)}
              </button>
            );
          })
        )}
      </div>
    </section>
  );
}

function initialBoard(): Board {
  return [
    ["r", "n", "b", "q", "k", "b", "n", "r"],
    ["p", "p", "p", "p", "p", "p", "p", "p"],
    [null, null, null, null, null, null, null, null],
    [null, null, null, null, null, null, null, null],
    [null, null, null, null, null, null, null, null],
    [null, null, null, null, null, null, null, null],
    ["P", "P", "P", "P", "P", "P", "P", "P"],
    ["R", "N", "B", "Q", "K", "B", "N", "R"]
  ];
}

function isWhite(p: string) { return p === p.toUpperCase(); }

function pseudoLegal(board: Board, r: number, c: number): Array<[number, number]> {
  const p = board[r][c];
  if (!p) return [];
  const pt = p.toUpperCase();
  const white = isWhite(p);
  const out: Array<[number, number]> = [];

  const add = (rr: number, cc: number) => {
    if (rr < 0 || rr > 7 || cc < 0 || cc > 7) return false;
    const t = board[rr][cc];
    if (!t) {
      out.push([rr, cc]);
      return true;
    }
    if (isWhite(t) !== white) out.push([rr, cc]);
    return false;
  };

  if (pt === "P") {
    const d = white ? -1 : 1;
    const sr = white ? 6 : 1;
    if (r + d >= 0 && r + d <= 7 && !board[r + d][c]) {
      out.push([r + d, c]);
      if (r === sr && !board[r + d * 2][c]) out.push([r + d * 2, c]);
    }
    for (const dc of [-1, 1]) {
      const rr = r + d;
      const cc = c + dc;
      if (rr >= 0 && rr <= 7 && cc >= 0 && cc <= 7 && board[rr][cc] && isWhite(board[rr][cc] as string) !== white) out.push([rr, cc]);
    }
  }

  if (pt === "N") {
    for (const [dr, dc] of [[-2,-1],[-2,1],[-1,-2],[-1,2],[1,-2],[1,2],[2,-1],[2,1]]) add(r + dr, c + dc);
  }

  if (["B", "R", "Q"].includes(pt)) {
    const dirs: Array<[number, number]> = [];
    if (["B", "Q"].includes(pt)) dirs.push([-1,-1],[-1,1],[1,-1],[1,1]);
    if (["R", "Q"].includes(pt)) dirs.push([-1,0],[1,0],[0,-1],[0,1]);
    for (const [dr, dc] of dirs) {
      for (let i = 1; i <= 7; i += 1) {
        if (!add(r + dr * i, c + dc * i)) break;
      }
    }
  }

  if (pt === "K") {
    for (let dr = -1; dr <= 1; dr += 1) {
      for (let dc = -1; dc <= 1; dc += 1) {
        if (dr || dc) add(r + dr, c + dc);
      }
    }
  }

  return out;
}

function pieceToGlyph(piece: string | null): string {
  const map: Record<string, string> = {
    K: "♔", Q: "♕", R: "♖", B: "♗", N: "♘", P: "♙",
    k: "♚", q: "♛", r: "♜", b: "♝", n: "♞", p: "♟"
  };
  return piece ? map[piece] ?? piece : "";
}

export default ChessGame;
