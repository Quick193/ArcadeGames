export interface Diff {
  name: string;
  rows: number;
  cols: number;
  mines: number;
}

export const DIFFICULTIES: Diff[] = [
  { name: "Beginner", rows: 9, cols: 9, mines: 10 },
  { name: "Intermediate", rows: 16, cols: 16, mines: 40 },
  { name: "Expert", rows: 16, cols: 30, mines: 99 }
];

export interface MineState {
  board: number[][];
  revealed: boolean[][];
  flagged: boolean[][];
  firstClick: boolean;
  dead: boolean;
  won: boolean;
}

export function createState(diff: Diff): MineState {
  return {
    board: Array.from({ length: diff.rows }, () => Array.from({ length: diff.cols }, () => 0)),
    revealed: Array.from({ length: diff.rows }, () => Array.from({ length: diff.cols }, () => false)),
    flagged: Array.from({ length: diff.rows }, () => Array.from({ length: diff.cols }, () => false)),
    firstClick: true,
    dead: false,
    won: false
  };
}

export function placeMines(board: number[][], safeR: number, safeC: number, mines: number): void {
  const rows = board.length;
  const cols = board[0]?.length ?? 0;
  const cells: Array<[number, number]> = [];

  for (let r = 0; r < rows; r += 1) {
    for (let c = 0; c < cols; c += 1) {
      if (Math.abs(r - safeR) <= 1 && Math.abs(c - safeC) <= 1) continue;
      cells.push([r, c]);
    }
  }

  shuffle(cells);
  for (const [r, c] of cells.slice(0, mines)) {
    board[r][c] = -1;
  }

  for (let r = 0; r < rows; r += 1) {
    for (let c = 0; c < cols; c += 1) {
      if (board[r][c] === -1) continue;
      let cnt = 0;
      for (let dr = -1; dr <= 1; dr += 1) {
        for (let dc = -1; dc <= 1; dc += 1) {
          const nr = r + dr;
          const nc = c + dc;
          if (nr >= 0 && nr < rows && nc >= 0 && nc < cols && board[nr][nc] === -1) cnt += 1;
        }
      }
      board[r][c] = cnt;
    }
  }
}

export function reveal(state: MineState, r: number, c: number): MineState {
  const rows = state.board.length;
  const cols = state.board[0].length;
  if (r < 0 || r >= rows || c < 0 || c >= cols) return state;
  if (state.revealed[r][c] || state.flagged[r][c]) return state;

  const next: MineState = {
    ...state,
    revealed: state.revealed.map((row) => [...row]),
    flagged: state.flagged.map((row) => [...row]),
    board: state.board.map((row) => [...row])
  };

  const flood = (rr: number, cc: number) => {
    if (rr < 0 || rr >= rows || cc < 0 || cc >= cols) return;
    if (next.revealed[rr][cc] || next.flagged[rr][cc]) return;
    next.revealed[rr][cc] = true;
    if (next.board[rr][cc] === 0) {
      for (let dr = -1; dr <= 1; dr += 1) {
        for (let dc = -1; dc <= 1; dc += 1) {
          if (dr || dc) flood(rr + dr, cc + dc);
        }
      }
    }
  };

  flood(r, c);

  if (next.board[r][c] === -1) {
    next.dead = true;
    for (let rr = 0; rr < rows; rr += 1) {
      for (let cc = 0; cc < cols; cc += 1) {
        if (next.board[rr][cc] === -1) next.revealed[rr][cc] = true;
      }
    }
  } else {
    next.won = checkWin(next);
  }

  return next;
}

export function toggleFlag(state: MineState, r: number, c: number): MineState {
  if (state.revealed[r][c]) return state;
  const flagged = state.flagged.map((row) => [...row]);
  flagged[r][c] = !flagged[r][c];
  return { ...state, flagged };
}

export function checkWin(state: MineState): boolean {
  for (let r = 0; r < state.board.length; r += 1) {
    for (let c = 0; c < state.board[0].length; c += 1) {
      if (state.board[r][c] !== -1 && !state.revealed[r][c]) return false;
    }
  }
  return true;
}

export function countFlags(flagged: boolean[][]): number {
  return flagged.flat().filter(Boolean).length;
}

function shuffle<T>(arr: T[]): void {
  for (let i = arr.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [arr[i], arr[j]] = [arr[j], arr[i]];
  }
}
