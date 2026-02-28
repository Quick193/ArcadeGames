import { useEffect, useMemo, useState } from "react";
import MobileControls from "../../components/ui/MobileControls";
import { useGameSession } from "../../services/progression/useGameSession";
import type { ControlScheme } from "../../types/settings";
import "./chess.css";

interface ChessGameProps {
  onExit: () => void;
  controlScheme: ControlScheme;
}

type Board = Array<Array<string | null>>;
type Square = [number, number];
type Castling = { K: boolean; Q: boolean; k: boolean; q: boolean };
type GameMode = "1p" | "2p";
type Difficulty = "easy" | "medium" | "hard";
type Phase = "select" | "game";
type PromotionPiece = "Q" | "R" | "B" | "N";
type MoveSpecial = "ck" | "cq" | "ep" | "promo" | null;

interface ChessState {
  board: Board;
  whiteTurn: boolean;
  castling: Castling;
  ep: Square | null;
  selected: Square | null;
  legal: Square[];
  lastMove: { from: Square; to: Square } | null;
  winner: "white" | "black" | null;
  stalemate: boolean;
  moveHistory: string[];
  capturedByWhite: string[];
  capturedByBlack: string[];
  pendingPromotion: { from: Square; to: Square; white: boolean } | null;
}

const SAVE_KEY = "arcade.chess.autosave.v2";
const DIFF_DEPTH: Record<Difficulty, number> = { easy: 1, medium: 2, hard: 3 };
const PIECE_VALUE: Record<string, number> = { P: 100, N: 320, B: 330, R: 500, Q: 900, K: 0 };
const PROMOTION_OPTIONS: PromotionPiece[] = ["Q", "R", "B", "N"];

function ChessGame({ onExit, controlScheme }: ChessGameProps) {
  const session = useGameSession("chess");
  const [phase, setPhase] = useState<Phase>("select");
  const [mode, setMode] = useState<GameMode>("1p");
  const [difficulty, setDifficulty] = useState<Difficulty>("medium");
  const [state, setState] = useState<ChessState>(() => loadState());
  const promoteWith = (piece: PromotionPiece) => {
    setState((prev) => {
      if (!prev.pendingPromotion) return prev;
      const { from, to } = prev.pendingPromotion;
      return applyFullMove({ ...prev, pendingPromotion: null, selected: null, legal: [] }, from, to, piece);
    });
  };

  const statusText = useMemo(() => {
    if (state.winner) return `${state.winner === "white" ? "White" : "Black"} wins`;
    if (state.stalemate) return "Stalemate";
    if (state.pendingPromotion) return `${state.pendingPromotion.white ? "White" : "Black"} promoting`;
    if (inCheck(state.board, state.whiteTurn)) return `${state.whiteTurn ? "White" : "Black"} to move (check)`;
    return `${state.whiteTurn ? "White" : "Black"} to move`;
  }, [state.board, state.pendingPromotion, state.stalemate, state.whiteTurn, state.winner]);

  const exitToMenu = () => {
    session.recordPlaytimeOnly();
    onExit();
  };

  const resetGame = () => {
    session.restartSession();
    const next = freshState();
    setState(next);
    saveState(next);
  };

  useEffect(() => {
    if (phase !== "game") return;
    saveState(state);
  }, [phase, state]);

  useEffect(() => {
    const done = state.winner || state.stalemate;
    if (phase !== "game" || !done) return;
    session.recordResult({
      score: materialScore(state.board),
      won: state.winner === "white",
      extra: {
        difficulty
      }
    });
  }, [difficulty, phase, session, state.board, state.stalemate, state.winner]);

  useEffect(() => {
    if (phase !== "game") return;
    if (mode !== "1p" || state.winner || state.stalemate || state.whiteTurn) return;
    if (state.pendingPromotion) return;
    const id = window.setTimeout(() => {
      const move = pickAiMove(state, DIFF_DEPTH[difficulty]);
      if (!move) return;
      setState((prev) => applyFullMove(prev, move.from, move.to));
    }, 120);
    return () => window.clearTimeout(id);
  }, [difficulty, mode, phase, state, state.pendingPromotion]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const key = e.key.toLowerCase();
      if (phase === "select") {
        if (key === "q" || key === "escape") {
          exitToMenu();
          return;
        }
        if (key === "1") {
          setMode("1p");
          setPhase("game");
          resetGame();
        }
        if (key === "2") {
          setMode("2p");
          setPhase("game");
          resetGame();
        }
        return;
      }

      if (state.pendingPromotion) {
        if (key === "q" || key === "r" || key === "b" || key === "n") promoteWith(key.toUpperCase() as PromotionPiece);
        if (key === "enter") promoteWith("Q");
        return;
      }
      if (key === "q" || key === "escape") {
        setPhase("select");
        return;
      }
      if (key === "r") resetGame();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [phase, state.pendingPromotion]);

  if (phase === "select") {
    return (
      <section className="chess-screen">
        <header className="chess-header">
          <div>
            <h1>Chess</h1>
            <p>Full legal moves, castling, en passant, check/checkmate.</p>
          </div>
          <button type="button" onClick={exitToMenu}>Back to Menu</button>
        </header>
        <section className="chess-select">
          <button type="button" onClick={() => { setMode("1p"); setPhase("game"); resetGame(); }}>1 Player vs AI</button>
          <button type="button" onClick={() => { setMode("2p"); setPhase("game"); resetGame(); }}>2 Players Local</button>
          {mode === "1p" && (
            <label className="setting-row">
              <span>AI Difficulty</span>
              <select value={difficulty} onChange={(e) => setDifficulty(e.target.value as Difficulty)}>
                <option value="easy">Easy</option>
                <option value="medium">Medium</option>
                <option value="hard">Hard</option>
              </select>
            </label>
          )}
        </section>
      </section>
    );
  }

  return (
    <section className="chess-screen">
      <header className="chess-header">
        <div>
          <h1>Chess</h1>
          <p>R reset, Q back.</p>
        </div>
        <button type="button" onClick={() => setPhase("select")}>Back</button>
      </header>

      <div className="chess-info">
        <span>{statusText}</span>
        {mode === "1p" && <span>AI: {difficulty}</span>}
      </div>

      <div className="chess-layout">
        <div className="chess-board-wrap">
          <div className="chess-board">
            {state.board.flatMap((row, r) =>
              row.map((piece, c) => {
                const dark = (r + c) % 2 === 1;
                const selected = state.selected?.[0] === r && state.selected?.[1] === c;
                const legal = state.legal.some(([rr, cc]) => rr === r && cc === c);
                const last = state.lastMove && ((state.lastMove.from[0] === r && state.lastMove.from[1] === c) || (state.lastMove.to[0] === r && state.lastMove.to[1] === c));
                return (
                  <button
                    key={`${r}-${c}`}
                    type="button"
                    className={`chess-cell ${dark ? "dark" : "light"} ${selected ? "sel" : ""} ${legal ? "legal" : ""} ${last ? "last" : ""}`}
                    onClick={() => {
                      setState((prev) => clickSquare(prev, [r, c], mode));
                    }}
                  >
                    {pieceGlyph(piece)}
                  </button>
                );
              })
            )}
          </div>
          {state.pendingPromotion && (
            <div className="chess-promo">
              <span>Choose promotion piece</span>
              <div className="chess-promo-options">
                {PROMOTION_OPTIONS.map((piece) => (
                  <button key={piece} type="button" onClick={() => promoteWith(piece)}>
                    {pieceGlyph(state.pendingPromotion?.white ? piece : piece.toLowerCase())} {piece}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        <aside className="chess-side-panels">
          <section className="chess-panel">
            <h2>Captured by White</h2>
            <div className="chess-captured">
              {state.capturedByWhite.length === 0 ? (
                <span className="empty">None</span>
              ) : state.capturedByWhite.map((piece, i) => (
                <span key={`${piece}-${i}`} aria-label={piece}>{pieceGlyph(piece)}</span>
              ))}
            </div>
          </section>

          <section className="chess-panel">
            <h2>Captured by Black</h2>
            <div className="chess-captured">
              {state.capturedByBlack.length === 0 ? (
                <span className="empty">None</span>
              ) : state.capturedByBlack.map((piece, i) => (
                <span key={`${piece}-${i}`} aria-label={piece}>{pieceGlyph(piece)}</span>
              ))}
            </div>
          </section>

          <section className="chess-panel chess-history">
            <h2>Move History</h2>
            <ul className="chess-history-list">
              {state.moveHistory.length === 0 ? (
                <li className="empty">No moves yet</li>
              ) : state.moveHistory.map((mv, i) => (
                <li key={`${mv}-${i}`}>
                  <span className="ply">{Math.floor(i / 2) + 1}{i % 2 === 0 ? "." : "..."}</span>
                  <span>{mv}</span>
                </li>
              ))}
            </ul>
          </section>
        </aside>
      </div>

      {controlScheme === "buttons" && (
        <MobileControls
          actions={[
            { label: "Reset", onPress: resetGame },
            { label: "Menu", onPress: () => setPhase("select") }
          ]}
        />
      )}
    </section>
  );
}

function clickSquare(state: ChessState, sq: Square, mode: GameMode): ChessState {
  if (state.winner || state.stalemate) return state;
  if (state.pendingPromotion) return state;
  const [r, c] = sq;
  const piece = state.board[r][c];
  const whiteSide = state.whiteTurn;
  if (mode === "1p" && !whiteSide) return state;

  if (state.selected) {
    const [sr, sc] = state.selected;
    const legal = state.legal.some(([rr, cc]) => rr === r && cc === c);
    if (legal) return applyFullMove(state, [sr, sc], [r, c]);
    if (piece && isWhite(piece) === whiteSide) {
      const nextLegal = legalMovesFor(state.board, [r, c], state.castling, state.ep);
      return { ...state, selected: [r, c], legal: nextLegal };
    }
    return { ...state, selected: null, legal: [] };
  }

  if (piece && isWhite(piece) === whiteSide) {
    const legal = legalMovesFor(state.board, [r, c], state.castling, state.ep);
    return { ...state, selected: [r, c], legal };
  }
  return state;
}

function applyFullMove(state: ChessState, from: Square, to: Square, promotionPiece?: PromotionPiece): ChessState {
  const moving = state.board[from[0]][from[1]];
  if (!moving) return state;
  if (moving.toUpperCase() === "P" && (to[0] === 0 || to[0] === 7) && !promotionPiece) {
    return {
      ...state,
      selected: null,
      legal: [],
      pendingPromotion: { from, to, white: isWhite(moving) }
    };
  }
  const { board, ep, castling, captured, special } = applyMove(state.board, from, to, moving, state.castling, state.ep, promotionPiece);
  const whiteTurn = !state.whiteTurn;
  const legalForNext = allLegalMoves(board, whiteTurn, castling, ep);
  const inChk = inCheck(board, whiteTurn);
  const isMate = legalForNext.length === 0 && inChk;
  const isStalemate = legalForNext.length === 0 && !inChk;
  const suffix = isMate ? "#" : inChk ? "+" : "";
  const notation = moveNotation(state.board, from, to, moving, captured, special, promotionPiece, suffix);
  const capturedByWhite = [...state.capturedByWhite];
  const capturedByBlack = [...state.capturedByBlack];
  if (captured) {
    if (state.whiteTurn) capturedByWhite.push(captured);
    else capturedByBlack.push(captured);
  }
  return {
    board,
    ep,
    castling,
    whiteTurn,
    selected: null,
    legal: [],
    lastMove: { from, to },
    winner: isMate ? (whiteTurn ? "black" : "white") : null,
    stalemate: isStalemate,
    moveHistory: [...state.moveHistory, notation],
    capturedByWhite,
    capturedByBlack,
    pendingPromotion: null
  };
}

function freshState(): ChessState {
  return {
    board: initBoard(),
    whiteTurn: true,
    castling: { K: true, Q: true, k: true, q: true },
    ep: null,
    selected: null,
    legal: [],
    lastMove: null,
    winner: null,
    stalemate: false,
    moveHistory: [],
    capturedByWhite: [],
    capturedByBlack: [],
    pendingPromotion: null
  };
}

function loadState(): ChessState {
  const raw = window.localStorage.getItem(SAVE_KEY);
  if (!raw) return freshState();
  try {
    const parsed = JSON.parse(raw) as Partial<ChessState>;
    if (!isValidBoard(parsed.board)) return freshState();
    const moveHistory = Array.isArray(parsed.moveHistory) ? parsed.moveHistory.filter((m): m is string => typeof m === "string") : [];
    const capturedByWhite = Array.isArray(parsed.capturedByWhite) ? parsed.capturedByWhite.filter((p): p is string => typeof p === "string") : [];
    const capturedByBlack = Array.isArray(parsed.capturedByBlack) ? parsed.capturedByBlack.filter((p): p is string => typeof p === "string") : [];
    return {
      board: parsed.board,
      whiteTurn: Boolean(parsed.whiteTurn),
      castling: parsed.castling ?? { K: true, Q: true, k: true, q: true },
      ep: parsed.ep ?? null,
      selected: null,
      legal: [],
      lastMove: parsed.lastMove ?? null,
      winner: parsed.winner ?? null,
      stalemate: Boolean(parsed.stalemate),
      moveHistory,
      capturedByWhite,
      capturedByBlack,
      pendingPromotion: null
    };
  } catch {
    return freshState();
  }
}

function saveState(state: ChessState): void {
  window.localStorage.setItem(SAVE_KEY, JSON.stringify({
    board: state.board,
    whiteTurn: state.whiteTurn,
    castling: state.castling,
    ep: state.ep,
    lastMove: state.lastMove,
    winner: state.winner,
    stalemate: state.stalemate,
    moveHistory: state.moveHistory,
    capturedByWhite: state.capturedByWhite,
    capturedByBlack: state.capturedByBlack
  }));
}

function initBoard(): Board {
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

function isWhite(p: string): boolean { return p === p.toUpperCase(); }

function pieceGlyph(piece: string | null): string {
  const map: Record<string, string> = {
    K: "♔", Q: "♕", R: "♖", B: "♗", N: "♘", P: "♙",
    k: "♚", q: "♛", r: "♜", b: "♝", n: "♞", p: "♟"
  };
  return piece ? (map[piece] ?? piece) : "";
}

function pseudoMoves(board: Board, [r, c]: Square, castling: Castling, ep: Square | null): Square[] {
  const p = board[r][c];
  if (!p) return [];
  const white = isWhite(p);
  const pt = p.toUpperCase();
  const out: Square[] = [];
  const push = (rr: number, cc: number): boolean => {
    if (rr < 0 || rr > 7 || cc < 0 || cc > 7) return false;
    const t = board[rr][cc];
    if (!t) { out.push([rr, cc]); return true; }
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
      if (rr < 0 || rr > 7 || cc < 0 || cc > 7) continue;
      const t = board[rr][cc];
      if (t && isWhite(t) !== white) out.push([rr, cc]);
      if (ep && ep[0] === rr && ep[1] === cc) out.push([rr, cc]);
    }
  } else if (pt === "N") {
    for (const [dr, dc] of [[-2, -1], [-2, 1], [-1, -2], [-1, 2], [1, -2], [1, 2], [2, -1], [2, 1]]) push(r + dr, c + dc);
  } else if (pt === "B" || pt === "R" || pt === "Q") {
    const dirs: Square[] = [];
    if (pt === "B" || pt === "Q") dirs.push([-1, -1], [-1, 1], [1, -1], [1, 1]);
    if (pt === "R" || pt === "Q") dirs.push([-1, 0], [1, 0], [0, -1], [0, 1]);
    for (const [dr, dc] of dirs) {
      for (let i = 1; i <= 7; i += 1) if (!push(r + dr * i, c + dc * i)) break;
    }
  } else if (pt === "K") {
    for (let dr = -1; dr <= 1; dr += 1) for (let dc = -1; dc <= 1; dc += 1) if (dr || dc) push(r + dr, c + dc);
    if (white && r === 7 && c === 4) {
      if (castling.K && !board[7][5] && !board[7][6]) out.push([7, 6]);
      if (castling.Q && !board[7][1] && !board[7][2] && !board[7][3]) out.push([7, 2]);
    }
    if (!white && r === 0 && c === 4) {
      if (castling.k && !board[0][5] && !board[0][6]) out.push([0, 6]);
      if (castling.q && !board[0][1] && !board[0][2] && !board[0][3]) out.push([0, 2]);
    }
  }
  return out;
}

function attacked(board: Board, rr: number, cc: number, byWhite: boolean): boolean {
  for (let r = 0; r < 8; r += 1) {
    for (let c = 0; c < 8; c += 1) {
      const p = board[r][c];
      if (!p || isWhite(p) !== byWhite) continue;
      if (p.toUpperCase() === "P") {
        const d = byWhite ? -1 : 1;
        if (r + d === rr && Math.abs(c - cc) === 1) return true;
      } else {
        const pm = pseudoMoves(board, [r, c], { K: false, Q: false, k: false, q: false }, null);
        if (pm.some(([r2, c2]) => r2 === rr && c2 === cc)) return true;
      }
    }
  }
  return false;
}

function findKing(board: Board, white: boolean): Square | null {
  const target = white ? "K" : "k";
  for (let r = 0; r < 8; r += 1) for (let c = 0; c < 8; c += 1) if (board[r][c] === target) return [r, c];
  return null;
}

function inCheck(board: Board, white: boolean): boolean {
  const k = findKing(board, white);
  return Boolean(k && attacked(board, k[0], k[1], !white));
}

function legalMovesFor(board: Board, sq: Square, castling: Castling, ep: Square | null): Square[] {
  const p = board[sq[0]][sq[1]];
  if (!p) return [];
  const white = isWhite(p);
  const out: Square[] = [];
  for (const to of pseudoMoves(board, sq, castling, ep)) {
    // Castling cannot pass through attacked squares
    if (p.toUpperCase() === "K" && Math.abs(sq[1] - to[1]) === 2) {
      if (inCheck(board, white)) continue;
      const mid = to[1] === 6 ? 5 : 3;
      if (attacked(board, sq[0], mid, !white) || attacked(board, sq[0], to[1], !white)) continue;
    }
    const moved = applyMove(board, sq, to, p, castling, ep);
    if (!inCheck(moved.board, white)) out.push(to);
  }
  return out;
}

function allLegalMoves(board: Board, white: boolean, castling: Castling, ep: Square | null): Array<{ from: Square; to: Square }> {
  const all: Array<{ from: Square; to: Square }> = [];
  for (let r = 0; r < 8; r += 1) {
    for (let c = 0; c < 8; c += 1) {
      const p = board[r][c];
      if (!p || isWhite(p) !== white) continue;
      for (const to of legalMovesFor(board, [r, c], castling, ep)) all.push({ from: [r, c], to });
    }
  }
  return all;
}

function applyMove(
  board: Board,
  from: Square,
  to: Square,
  moving: string,
  castling: Castling,
  ep: Square | null,
  promotionPiece: PromotionPiece = "Q"
): { board: Board; castling: Castling; ep: Square | null; captured: string | null; special: MoveSpecial } {
  const next = board.map((row) => [...row]);
  const outCastling = { ...castling };
  const [fr, fc] = from;
  const [tr, tc] = to;
  const white = isWhite(moving);
  let captured = next[tr][tc];
  let special: MoveSpecial = null;

  // en passant capture
  if (moving.toUpperCase() === "P" && ep && tr === ep[0] && tc === ep[1] && !captured) {
    captured = next[fr][tc];
    next[fr][tc] = null;
    special = "ep";
  }

  next[fr][fc] = null;
  next[tr][tc] = moving;

  // castling rook move
  if (moving.toUpperCase() === "K" && Math.abs(fc - tc) === 2) {
    if (tc === 6) {
      next[tr][5] = next[tr][7];
      next[tr][7] = null;
      special = "ck";
    } else {
      next[tr][3] = next[tr][0];
      next[tr][0] = null;
      special = "cq";
    }
  }

  // promotion
  if (moving.toUpperCase() === "P" && (tr === 0 || tr === 7)) {
    next[tr][tc] = white ? promotionPiece : promotionPiece.toLowerCase();
    special = "promo";
  }

  // castling rights update
  if (moving === "K") { outCastling.K = false; outCastling.Q = false; }
  if (moving === "k") { outCastling.k = false; outCastling.q = false; }
  if (moving === "R" && fr === 7 && fc === 0) outCastling.Q = false;
  if (moving === "R" && fr === 7 && fc === 7) outCastling.K = false;
  if (moving === "r" && fr === 0 && fc === 0) outCastling.q = false;
  if (moving === "r" && fr === 0 && fc === 7) outCastling.k = false;
  if (captured === "R" && tr === 7 && tc === 0) outCastling.Q = false;
  if (captured === "R" && tr === 7 && tc === 7) outCastling.K = false;
  if (captured === "r" && tr === 0 && tc === 0) outCastling.q = false;
  if (captured === "r" && tr === 0 && tc === 7) outCastling.k = false;

  let nextEp: Square | null = null;
  if (moving.toUpperCase() === "P" && Math.abs(tr - fr) === 2) {
    nextEp = [Math.floor((fr + tr) / 2), fc];
  }

  return { board: next, castling: outCastling, ep: nextEp, captured, special };
}

function squareName([r, c]: Square): string {
  return `${"abcdefgh"[c]}${"87654321"[r]}`;
}

function moveNotation(
  board: Board,
  from: Square,
  to: Square,
  moving: string,
  captured: string | null,
  special: MoveSpecial,
  promotionPiece: PromotionPiece | undefined,
  suffix: string
): string {
  const [, fc] = from;
  const [, tc] = to;
  const target = squareName(to);
  if (special === "ck") return `O-O${suffix}`;
  if (special === "cq") return `O-O-O${suffix}`;
  if (moving.toUpperCase() === "P") {
    const capture = Boolean(captured) || fc !== tc;
    let san = capture ? `${"abcdefgh"[fc]}x${target}` : target;
    if (special === "promo") san += `=${(promotionPiece ?? "Q").toUpperCase()}`;
    return `${san}${suffix}`;
  }
  const capture = Boolean(captured) || board[to[0]][to[1]] !== null;
  return `${moving.toUpperCase()}${capture ? "x" : ""}${target}${suffix}`;
}

function isValidBoard(board: unknown): board is Board {
  if (!Array.isArray(board) || board.length !== 8) return false;
  return board.every((row) => Array.isArray(row) && row.length === 8 && row.every((cell) => cell === null || typeof cell === "string"));
}

function materialScore(board: Board): number {
  let score = 0;
  for (const row of board) {
    for (const p of row) {
      if (!p) continue;
      const v = PIECE_VALUE[p.toUpperCase()] ?? 0;
      score += isWhite(p) ? v : -v;
    }
  }
  return score;
}

function pickAiMove(state: ChessState, depth: number): { from: Square; to: Square } | null {
  const moves = allLegalMoves(state.board, false, state.castling, state.ep);
  if (moves.length === 0) return null;
  let best = Number.POSITIVE_INFINITY;
  let bestMove: { from: Square; to: Square } | null = null;
  for (const mv of moves) {
    const next = applyMove(state.board, mv.from, mv.to, state.board[mv.from[0]][mv.from[1]] as string, state.castling, state.ep);
    const val = minimax(next.board, depth - 1, true, next.castling, next.ep, -999999, 999999);
    if (val < best) {
      best = val;
      bestMove = mv;
    }
  }
  return bestMove;
}

function minimax(board: Board, depth: number, whiteTurn: boolean, castling: Castling, ep: Square | null, alpha: number, beta: number): number {
  const moves = allLegalMoves(board, whiteTurn, castling, ep);
  if (depth <= 0 || moves.length === 0) return materialScore(board);

  if (whiteTurn) {
    let best = -999999;
    for (const mv of moves) {
      const moving = board[mv.from[0]][mv.from[1]] as string;
      const next = applyMove(board, mv.from, mv.to, moving, castling, ep);
      best = Math.max(best, minimax(next.board, depth - 1, false, next.castling, next.ep, alpha, beta));
      alpha = Math.max(alpha, best);
      if (beta <= alpha) break;
    }
    return best;
  }

  let best = 999999;
  for (const mv of moves) {
    const moving = board[mv.from[0]][mv.from[1]] as string;
    const next = applyMove(board, mv.from, mv.to, moving, castling, ep);
    best = Math.min(best, minimax(next.board, depth - 1, true, next.castling, next.ep, alpha, beta));
    beta = Math.min(beta, best);
    if (beta <= alpha) break;
  }
  return best;
}

export default ChessGame;
