export const TILE_SIZE = 20;
export const COLS = 48;
export const ROWS = 30;

export const BASE_INTERVAL_MS = 100;
export const MIN_INTERVAL_MS = 48;

export type Point = { x: number; y: number };
export type Direction = { x: number; y: number };

export interface SnakeState {
  snake: Point[];
  dir: Direction;
  nextDir: Direction;
  food: Point;
  score: number;
  stepIntervalMs: number;
  dead: boolean;
}

export function createInitialState(): SnakeState {
  const cx = Math.floor(COLS / 2);
  const cy = Math.floor(ROWS / 2);
  const snake = [{ x: cx, y: cy }];

  return {
    snake,
    dir: { x: 1, y: 0 },
    nextDir: { x: 1, y: 0 },
    food: spawnFood(snake),
    score: 0,
    stepIntervalMs: BASE_INTERVAL_MS,
    dead: false
  };
}

export function getUpdatedDirection(current: Direction, key: string): Direction | null {
  if (key === "ArrowUp" && !(current.x === 0 && current.y === 1)) {
    return { x: 0, y: -1 };
  }
  if (key === "ArrowDown" && !(current.x === 0 && current.y === -1)) {
    return { x: 0, y: 1 };
  }
  if (key === "ArrowLeft" && !(current.x === 1 && current.y === 0)) {
    return { x: -1, y: 0 };
  }
  if (key === "ArrowRight" && !(current.x === -1 && current.y === 0)) {
    return { x: 1, y: 0 };
  }
  return null;
}

export function step(state: SnakeState): SnakeState {
  if (state.dead) {
    return state;
  }

  const dir = state.nextDir;
  const head = state.snake[0];
  const nx = wrap(head.x + dir.x, COLS);
  const ny = wrap(head.y + dir.y, ROWS);

  if (state.snake.some((segment) => segment.x === nx && segment.y === ny)) {
    return { ...state, dead: true, dir };
  }

  const nextSnake = [{ x: nx, y: ny }, ...state.snake];
  const ateFood = nx === state.food.x && ny === state.food.y;

  if (!ateFood) {
    nextSnake.pop();
  }

  const nextScore = ateFood ? state.score + 10 : state.score;
  const nextInterval = Math.max(MIN_INTERVAL_MS, BASE_INTERVAL_MS - nextScore * 1.2);

  return {
    ...state,
    snake: nextSnake,
    dir,
    food: ateFood ? spawnFood(nextSnake) : state.food,
    score: nextScore,
    stepIntervalMs: nextInterval
  };
}

function spawnFood(snake: Point[]): Point {
  while (true) {
    const next = {
      x: Math.floor(Math.random() * COLS),
      y: Math.floor(Math.random() * ROWS)
    };

    if (!snake.some((segment) => segment.x === next.x && segment.y === next.y)) {
      return next;
    }
  }
}

function wrap(value: number, size: number): number {
  return (value + size) % size;
}
