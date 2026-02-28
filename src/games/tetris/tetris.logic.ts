export const ROWS = 20;
export const COLS = 10;
export const CELL_SIZE = 24;

export const BASE_FALL_MS = 500;
export const SPEED_DELTA_MS = 45;
export const MIN_FALL_MS = 50;
export const FLASH_MS = 220;

const SCORE_TABLE: Record<number, number> = { 1: 100, 2: 300, 3: 500, 4: 800 };
const WALL_KICKS = [0, -1, 1, -2, 2];

const PIECE_SHAPES: number[][][] = [
  [[1, 1, 1, 1]],
  [
    [1, 0, 0],
    [1, 1, 1]
  ],
  [
    [0, 0, 1],
    [1, 1, 1]
  ],
  [
    [1, 1],
    [1, 1]
  ],
  [
    [0, 1, 1],
    [1, 1, 0]
  ],
  [
    [0, 1, 0],
    [1, 1, 1]
  ],
  [
    [1, 1, 0],
    [0, 1, 1]
  ]
];

const PIECE_COLORS = ["#4cc9f0", "#4361ee", "#f77f00", "#ffd166", "#70e000", "#b5179e", "#ef476f"];

export type Cell = string | null;
export type Grid = Cell[][];

export interface Piece {
  shape: number[][];
  x: number;
  y: number;
  index: number;
  color: string;
}

export interface TetrisState {
  grid: Grid;
  current: Piece;
  next: Piece;
  held: Piece | null;
  canHold: boolean;
  score: number;
  lines: number;
  level: number;
  fallMs: number;
  tetrisClears: number;
  gameOver: boolean;
  flashRows: number[];
  flashMs: number;
}

export function createInitialState(): TetrisState {
  return {
    grid: createGrid(),
    current: spawnPiece(),
    next: spawnPiece(),
    held: null,
    canHold: true,
    score: 0,
    lines: 0,
    level: 1,
    fallMs: BASE_FALL_MS,
    tetrisClears: 0,
    gameOver: false,
    flashRows: [],
    flashMs: 0
  };
}

export function moveHorizontal(state: TetrisState, delta: number): TetrisState {
  if (state.gameOver || state.flashMs > 0) {
    return state;
  }

  const candidate = { ...state.current, x: state.current.x + delta };
  if (!isValid(candidate, state.grid)) {
    return state;
  }

  return { ...state, current: candidate };
}

export function softDrop(state: TetrisState): TetrisState {
  if (state.gameOver || state.flashMs > 0) {
    return state;
  }

  const candidate = { ...state.current, y: state.current.y + 1 };
  if (!isValid(candidate, state.grid)) {
    return placePiece(state);
  }

  return { ...state, current: candidate };
}

export function rotate(state: TetrisState, clockwise: boolean): TetrisState {
  if (state.gameOver || state.flashMs > 0) {
    return state;
  }

  const rotatedShape = clockwise ? rotateCw(state.current.shape) : rotateCcw(state.current.shape);
  for (const dx of WALL_KICKS) {
    const candidate: Piece = { ...state.current, shape: rotatedShape, x: state.current.x + dx };
    if (isValid(candidate, state.grid)) {
      return { ...state, current: candidate };
    }
  }

  return state;
}

export function hardDrop(state: TetrisState): TetrisState {
  if (state.gameOver || state.flashMs > 0) {
    return state;
  }

  const distance = ghostDistance(state.current, state.grid);
  const dropped = { ...state.current, y: state.current.y + distance };
  const withBonus = { ...state, current: dropped, score: state.score + distance * 2 };
  return placePiece(withBonus);
}

export function hold(state: TetrisState): TetrisState {
  if (state.gameOver || state.flashMs > 0 || !state.canHold) {
    return state;
  }

  if (state.held == null) {
    return {
      ...state,
      held: spawnPieceByIndex(state.current.index),
      current: resetSpawn(state.next),
      next: spawnPiece(),
      canHold: false
    };
  }

  return {
    ...state,
    held: spawnPieceByIndex(state.current.index),
    current: resetSpawn(state.held),
    canHold: false
  };
}

export function advance(state: TetrisState, deltaMs: number, doFallStep: boolean): TetrisState {
  if (state.gameOver) {
    return state;
  }

  if (state.flashMs > 0) {
    const nextFlashMs = Math.max(0, state.flashMs - deltaMs);
    if (nextFlashMs > 0) {
      return { ...state, flashMs: nextFlashMs };
    }

    const cleared = clearRows(state.grid, state.flashRows);
    const nextCurrent = resetSpawn(state.next);
    const valid = isValid(nextCurrent, cleared);

    return {
      ...state,
      grid: cleared,
      current: nextCurrent,
      next: spawnPiece(),
      canHold: true,
      flashRows: [],
      flashMs: 0,
      gameOver: !valid
    };
  }

  if (!doFallStep) {
    return state;
  }

  const candidate = { ...state.current, y: state.current.y + 1 };
  if (isValid(candidate, state.grid)) {
    return { ...state, current: candidate };
  }

  return placePiece(state);
}

function placePiece(state: TetrisState): TetrisState {
  const gridAfterLock = lockPiece(state.grid, state.current);
  const fullRows = findFullRows(gridAfterLock);

  if (fullRows.length > 0) {
    const gained = (SCORE_TABLE[fullRows.length] ?? fullRows.length * 100) * state.level;
    const nextLines = state.lines + fullRows.length;
    const nextLevel = Math.floor(nextLines / 10) + 1;
    const nextFall = Math.max(MIN_FALL_MS, BASE_FALL_MS - (nextLevel - 1) * SPEED_DELTA_MS);

    return {
      ...state,
      grid: gridAfterLock,
      score: state.score + gained,
      lines: nextLines,
      level: nextLevel,
      fallMs: nextFall,
      tetrisClears: state.tetrisClears + (fullRows.length === 4 ? 1 : 0),
      flashRows: fullRows,
      flashMs: FLASH_MS
    };
  }

  const nextCurrent = resetSpawn(state.next);
  const valid = isValid(nextCurrent, gridAfterLock);

  return {
    ...state,
    grid: gridAfterLock,
    current: nextCurrent,
    next: spawnPiece(),
    canHold: true,
    gameOver: !valid
  };
}

export function getGhostY(piece: Piece, grid: Grid): number {
  return piece.y + ghostDistance(piece, grid);
}

function ghostDistance(piece: Piece, grid: Grid): number {
  let d = 0;
  while (isValid({ ...piece, y: piece.y + d + 1 }, grid)) {
    d += 1;
  }
  return d;
}

function createGrid(): Grid {
  return Array.from({ length: ROWS }, () => Array.from({ length: COLS }, () => null));
}

function spawnPiece(): Piece {
  const index = Math.floor(Math.random() * PIECE_SHAPES.length);
  return spawnPieceByIndex(index);
}

function spawnPieceByIndex(index: number): Piece {
  const shape = PIECE_SHAPES[index].map((row) => [...row]);
  const x = Math.floor(COLS / 2) - Math.floor(shape[0].length / 2);

  return {
    shape,
    x,
    y: 0,
    index,
    color: PIECE_COLORS[index]
  };
}

function resetSpawn(piece: Piece): Piece {
  const shape = piece.shape.map((row) => [...row]);
  return {
    ...piece,
    shape,
    x: Math.floor(COLS / 2) - Math.floor(shape[0].length / 2),
    y: 0
  };
}

function rotateCw(shape: number[][]): number[][] {
  return shape[0].map((_, i) => shape.map((row) => row[i]).reverse());
}

function rotateCcw(shape: number[][]): number[][] {
  return rotateCw(rotateCw(rotateCw(shape)));
}

function isValid(piece: Piece, grid: Grid): boolean {
  for (let r = 0; r < piece.shape.length; r += 1) {
    for (let c = 0; c < piece.shape[r].length; c += 1) {
      if (piece.shape[r][c] === 0) {
        continue;
      }

      const x = piece.x + c;
      const y = piece.y + r;

      if (x < 0 || x >= COLS || y >= ROWS) {
        return false;
      }

      if (y >= 0 && grid[y][x] != null) {
        return false;
      }
    }
  }

  return true;
}

function lockPiece(grid: Grid, piece: Piece): Grid {
  const next = grid.map((row) => [...row]);

  for (let r = 0; r < piece.shape.length; r += 1) {
    for (let c = 0; c < piece.shape[r].length; c += 1) {
      if (piece.shape[r][c] === 0) {
        continue;
      }

      const x = piece.x + c;
      const y = piece.y + r;
      if (y >= 0) {
        next[y][x] = piece.color;
      }
    }
  }

  return next;
}

function findFullRows(grid: Grid): number[] {
  const rows: number[] = [];

  for (let y = 0; y < ROWS; y += 1) {
    if (grid[y].every((cell) => cell != null)) {
      rows.push(y);
    }
  }

  return rows;
}

function clearRows(grid: Grid, rows: number[]): Grid {
  const removed = new Set(rows);
  const keep = grid.filter((_, idx) => !removed.has(idx));
  const cleared = Array.from({ length: rows.length }, () => Array.from({ length: COLS }, () => null));
  return [...cleared, ...keep];
}
