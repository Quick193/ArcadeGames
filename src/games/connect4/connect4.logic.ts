export const ROWS = 6;
export const COLS = 7;

export type Grid = number[][];
export type Player = 1 | 2;

export function emptyGrid(): Grid {
  return Array.from({ length: ROWS }, () => Array.from({ length: COLS }, () => 0));
}

export function validCols(grid: Grid): number[] {
  return Array.from({ length: COLS }, (_, c) => c).filter((c) => grid[0][c] === 0);
}

export function drop(grid: Grid, col: number, player: Player): { grid: Grid; row: number } | null {
  const next = grid.map((row) => [...row]);
  for (let r = ROWS - 1; r >= 0; r -= 1) {
    if (next[r][col] === 0) {
      next[r][col] = player;
      return { grid: next, row: r };
    }
  }
  return null;
}

export function checkWin(grid: Grid, player: Player): boolean {
  return winningCells(grid, player).length > 0;
}

export function winningCells(grid: Grid, player: Player): Array<[number, number]> {
  for (let r = 0; r < ROWS; r += 1) {
    for (let c = 0; c < COLS - 3; c += 1) {
      if ([0, 1, 2, 3].every((i) => grid[r][c + i] === player)) {
        return [0, 1, 2, 3].map((i) => [r, c + i]);
      }
    }
  }
  for (let r = 0; r < ROWS - 3; r += 1) {
    for (let c = 0; c < COLS; c += 1) {
      if ([0, 1, 2, 3].every((i) => grid[r + i][c] === player)) {
        return [0, 1, 2, 3].map((i) => [r + i, c]);
      }
    }
  }
  for (let r = 3; r < ROWS; r += 1) {
    for (let c = 0; c < COLS - 3; c += 1) {
      if ([0, 1, 2, 3].every((i) => grid[r - i][c + i] === player)) {
        return [0, 1, 2, 3].map((i) => [r - i, c + i]);
      }
    }
  }
  for (let r = 0; r < ROWS - 3; r += 1) {
    for (let c = 0; c < COLS - 3; c += 1) {
      if ([0, 1, 2, 3].every((i) => grid[r + i][c + i] === player)) {
        return [0, 1, 2, 3].map((i) => [r + i, c + i]);
      }
    }
  }
  return [];
}

function scoreWindow(window: number[], player: Player): number {
  const opp = player === 1 ? 2 : 1;
  const p = window.filter((v) => v === player).length;
  const e = window.filter((v) => v === 0).length;
  const o = window.filter((v) => v === opp).length;

  if (p === 4) return 1000;
  if (p === 3 && e === 1) return 12;
  if (p === 2 && e === 2) return 3;
  if (o === 4) return -1000;
  if (o === 3 && e === 1) return -20;
  if (o === 2 && e === 2) return -3;
  return 0;
}

function heuristic(grid: Grid, player: Player): number {
  const opp = player === 1 ? 2 : 1;
  let score = 0;

  for (const [c, b] of [[Math.floor(COLS / 2), 6], [Math.floor(COLS / 2) - 1, 3], [Math.floor(COLS / 2) + 1, 3]] as const) {
    if (c >= 0 && c < COLS) {
      const values = Array.from({ length: ROWS }, (_, r) => grid[r][c]);
      score += values.filter((v) => v === player).length * b;
      score -= values.filter((v) => v === opp).length * b;
    }
  }

  for (let r = 0; r < ROWS; r += 1) {
    for (let c = 0; c < COLS - 3; c += 1) {
      score += scoreWindow([grid[r][c], grid[r][c + 1], grid[r][c + 2], grid[r][c + 3]], player);
    }
  }
  for (let r = 0; r < ROWS - 3; r += 1) {
    for (let c = 0; c < COLS; c += 1) {
      score += scoreWindow([grid[r][c], grid[r + 1][c], grid[r + 2][c], grid[r + 3][c]], player);
    }
  }
  for (let r = 3; r < ROWS; r += 1) {
    for (let c = 0; c < COLS - 3; c += 1) {
      score += scoreWindow([grid[r][c], grid[r - 1][c + 1], grid[r - 2][c + 2], grid[r - 3][c + 3]], player);
    }
  }
  for (let r = 0; r < ROWS - 3; r += 1) {
    for (let c = 0; c < COLS - 3; c += 1) {
      score += scoreWindow([grid[r][c], grid[r + 1][c + 1], grid[r + 2][c + 2], grid[r + 3][c + 3]], player);
    }
  }

  return score;
}

export function aiMove(grid: Grid, depth: number, aiPlayer: Player): number | null {
  const cols = validCols(grid);
  if (cols.length === 0) {
    return null;
  }

  const ordered = [...cols].sort((a, b) => Math.abs(a - 3) - Math.abs(b - 3));

  function minimax(state: Grid, d: number, alpha: number, beta: number, maximizing: boolean): [number | null, number] {
    const human = aiPlayer === 1 ? 2 : 1;
    const valid = validCols(state);

    if (checkWin(state, aiPlayer)) return [null, 100000 + d];
    if (checkWin(state, human as Player)) return [null, -100000 - d];
    if (valid.length === 0 || d === 0) return [null, heuristic(state, aiPlayer)];

    const order = [...valid].sort((a, b) => Math.abs(a - 3) - Math.abs(b - 3));
    let bestCol = order[0] ?? null;

    if (maximizing) {
      let best = -1_000_000_000;
      for (const c of order) {
        const dropped = drop(state, c, aiPlayer);
        if (!dropped) continue;
        const [, score] = minimax(dropped.grid, d - 1, alpha, beta, false);
        if (score > best) {
          best = score;
          bestCol = c;
        }
        alpha = Math.max(alpha, best);
        if (alpha >= beta) break;
      }
      return [bestCol, best];
    }

    let best = 1_000_000_000;
    for (const c of order) {
      const dropped = drop(state, c, human as Player);
      if (!dropped) continue;
      const [, score] = minimax(dropped.grid, d - 1, alpha, beta, true);
      if (score < best) {
        best = score;
        bestCol = c;
      }
      beta = Math.min(beta, best);
      if (alpha >= beta) break;
    }
    return [bestCol, best];
  }

  const [best] = minimax(grid, depth, -1_000_000_000, 1_000_000_000, true);
  return best ?? ordered[0] ?? null;
}
