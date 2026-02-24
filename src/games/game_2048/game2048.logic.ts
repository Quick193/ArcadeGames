export const GRID = 4;

export type Direction = "left" | "right" | "up" | "down";
export type Board = number[][];

export interface MoveResult {
  board: Board;
  gained: number;
  moved: boolean;
}

export interface Game2048State {
  board: Board;
  score: number;
  won: boolean;
  dead: boolean;
}

export function createInitialState(): Game2048State {
  const board = emptyBoard();
  addTile(board);
  addTile(board);
  return { board, score: 0, won: false, dead: false };
}

export function applyMove(state: Game2048State, direction: Direction): Game2048State {
  if (state.dead) {
    return state;
  }

  const moved = move(state.board, direction);
  if (!moved.moved) {
    return state;
  }

  addTile(moved.board);
  const won = state.won || bestTile(moved.board) >= 2048;
  const dead = !hasMoves(moved.board);

  return {
    board: moved.board,
    score: state.score + moved.gained,
    won,
    dead
  };
}

export function emptyBoard(): Board {
  return Array.from({ length: GRID }, () => Array.from({ length: GRID }, () => 0));
}

export function addTile(board: Board): void {
  const empty: Array<[number, number]> = [];

  for (let r = 0; r < GRID; r += 1) {
    for (let c = 0; c < GRID; c += 1) {
      if (board[r][c] === 0) {
        empty.push([r, c]);
      }
    }
  }

  if (empty.length === 0) {
    return;
  }

  const [r, c] = empty[Math.floor(Math.random() * empty.length)];
  board[r][c] = Math.random() < 0.1 ? 4 : 2;
}

export function move(board: Board, direction: Direction): MoveResult {
  const next = board.map((row) => [...row]);
  let gained = 0;
  let moved = false;

  if (direction === "left") {
    for (let r = 0; r < GRID; r += 1) {
      const slid = slideRow(next[r]);
      if (!equalRows(slid.row, next[r])) {
        moved = true;
      }
      next[r] = slid.row;
      gained += slid.points;
    }
    return { board: next, gained, moved };
  }

  if (direction === "right") {
    for (let r = 0; r < GRID; r += 1) {
      const rev = [...next[r]].reverse();
      const slid = slideRow(rev);
      const row = slid.row.reverse();
      if (!equalRows(row, next[r])) {
        moved = true;
      }
      next[r] = row;
      gained += slid.points;
    }
    return { board: next, gained, moved };
  }

  if (direction === "up") {
    for (let c = 0; c < GRID; c += 1) {
      const col = Array.from({ length: GRID }, (_, r) => next[r][c]);
      const slid = slideRow(col);

      for (let r = 0; r < GRID; r += 1) {
        if (next[r][c] !== slid.row[r]) {
          moved = true;
        }
        next[r][c] = slid.row[r];
      }

      gained += slid.points;
    }
    return { board: next, gained, moved };
  }

  for (let c = 0; c < GRID; c += 1) {
    const col = Array.from({ length: GRID }, (_, r) => next[r][c]).reverse();
    const slid = slideRow(col);
    const merged = slid.row.reverse();

    for (let r = 0; r < GRID; r += 1) {
      if (next[r][c] !== merged[r]) {
        moved = true;
      }
      next[r][c] = merged[r];
    }

    gained += slid.points;
  }

  return { board: next, gained, moved };
}

function slideRow(row: number[]): { row: number[]; points: number } {
  const tiles = row.filter((value) => value !== 0);
  const merged: number[] = [];
  let points = 0;

  for (let i = 0; i < tiles.length; i += 1) {
    if (i + 1 < tiles.length && tiles[i] === tiles[i + 1]) {
      const value = tiles[i] * 2;
      merged.push(value);
      points += value;
      i += 1;
    } else {
      merged.push(tiles[i]);
    }
  }

  while (merged.length < GRID) {
    merged.push(0);
  }

  return { row: merged, points };
}

function equalRows(a: number[], b: number[]): boolean {
  for (let i = 0; i < a.length; i += 1) {
    if (a[i] !== b[i]) {
      return false;
    }
  }
  return true;
}

export function hasMoves(board: Board): boolean {
  for (let r = 0; r < GRID; r += 1) {
    for (let c = 0; c < GRID; c += 1) {
      const value = board[r][c];

      if (value === 0) {
        return true;
      }
      if (c + 1 < GRID && value === board[r][c + 1]) {
        return true;
      }
      if (r + 1 < GRID && value === board[r + 1][c]) {
        return true;
      }
    }
  }

  return false;
}

export function bestTile(board: Board): number {
  let best = 0;
  for (let r = 0; r < GRID; r += 1) {
    for (let c = 0; c < GRID; c += 1) {
      if (board[r][c] > best) {
        best = board[r][c];
      }
    }
  }
  return best;
}
