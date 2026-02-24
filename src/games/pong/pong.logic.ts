export const WIDTH = 960;
export const HEIGHT = 600;

export const PAD_W = 12;
export const PAD_H = 90;
export const BALL_R = 8;
export const WIN_SCORE = 7;

const PLAYER_SPEED = 8;

export type Phase = "mode" | "difficulty" | "game";
export type Mode = "1p" | "2p";
export type Difficulty = "easy" | "medium" | "hard";

export interface AiParams {
  speed: number;
  error: number;
  react: number;
}

export const AI_PARAMS: Record<Difficulty, AiParams> = {
  easy: { speed: 3.2, error: 60, react: 0.25 },
  medium: { speed: 5.8, error: 22, react: 0.55 },
  hard: { speed: 10.5, error: 2, react: 0.95 }
};

export interface PongState {
  phase: Phase;
  mode: Mode | null;
  diff: Difficulty | null;
  selection: number;

  p1y: number;
  p2y: number;
  p1x: number;
  p2x: number;

  bx: number;
  by: number;
  bdx: number;
  bdy: number;

  p1s: number;
  p2s: number;

  paused: boolean;
  winner: "P1" | "P2" | "AI" | null;
}

export interface InputState {
  p1Up: boolean;
  p1Down: boolean;
  p2Up: boolean;
  p2Down: boolean;
}

export function createInitialState(): PongState {
  return {
    phase: "mode",
    mode: null,
    diff: null,
    selection: 0,
    ...createMatchCore()
  };
}

export function enterModeSelection(state: PongState): PongState {
  return { ...state, phase: "mode", selection: 0 };
}

export function enterDifficultySelection(state: PongState): PongState {
  return { ...state, phase: "difficulty", mode: "1p", selection: 1 };
}

export function startGame(state: PongState, mode: Mode, diff: Difficulty | null): PongState {
  return {
    ...state,
    phase: "game",
    mode,
    diff,
    selection: 0,
    ...createMatchCore()
  };
}

export function restartMatch(state: PongState): PongState {
  return {
    ...state,
    ...createMatchCore()
  };
}

export function stepGame(state: PongState, input: InputState): PongState {
  if (state.phase !== "game" || state.paused || state.winner) {
    return state;
  }

  let p1y = state.p1y;
  let p2y = state.p2y;

  if (input.p1Up) {
    p1y = Math.max(0, p1y - PLAYER_SPEED);
  }
  if (input.p1Down) {
    p1y = Math.min(HEIGHT - PAD_H, p1y + PLAYER_SPEED);
  }

  if (state.mode === "2p") {
    if (input.p2Up) {
      p2y = Math.max(0, p2y - PLAYER_SPEED);
    }
    if (input.p2Down) {
      p2y = Math.min(HEIGHT - PAD_H, p2y + PLAYER_SPEED);
    }
  } else if (state.diff) {
    const p = AI_PARAMS[state.diff];
    if (state.bx > WIDTH * (1 - p.react)) {
      const target = state.by - PAD_H / 2 + randomBetween(-p.error, p.error);
      if (p2y < target) {
        p2y = Math.min(HEIGHT - PAD_H, p2y + p.speed);
      } else if (p2y > target) {
        p2y = Math.max(0, p2y - p.speed);
      }
    }
  }

  let nx = state.bx + state.bdx;
  let ny = state.by + state.bdy;
  let bdx = state.bdx;
  let bdy = state.bdy;
  let p1s = state.p1s;
  let p2s = state.p2s;
  let winner: PongState["winner"] = state.winner;

  if (ny - BALL_R < 0) {
    ny = BALL_R;
    bdy = Math.abs(bdy);
  }
  if (ny + BALL_R > HEIGHT) {
    ny = HEIGHT - BALL_R;
    bdy = -Math.abs(bdy);
  }

  if (nx - BALL_R <= state.p1x + PAD_W && state.bx - BALL_R > state.p1x) {
    if (p1y <= ny && ny <= p1y + PAD_H) {
      bdx = Math.abs(bdx) + 0.4;
      nx = state.p1x + PAD_W + BALL_R;
      bdy = ((ny - (p1y + PAD_H / 2)) / (PAD_H / 2)) * 8;
    }
  }

  if (nx + BALL_R >= state.p2x && state.bx + BALL_R < state.p2x + PAD_W) {
    if (p2y <= ny && ny <= p2y + PAD_H) {
      bdx = -Math.abs(bdx) - 0.4;
      nx = state.p2x - BALL_R;
      bdy = ((ny - (p2y + PAD_H / 2)) / (PAD_H / 2)) * 8;
    }
  }

  if (nx < -20) {
    p2s += 1;
    ({ x: nx, y: ny, dx: bdx, dy: bdy } = resetBall(1));
    if (p2s >= WIN_SCORE) {
      winner = state.mode === "1p" ? "AI" : "P2";
    }
  } else if (nx > WIDTH + 20) {
    p1s += 1;
    ({ x: nx, y: ny, dx: bdx, dy: bdy } = resetBall(-1));
    if (p1s >= WIN_SCORE) {
      winner = "P1";
    }
  }

  return {
    ...state,
    p1y,
    p2y,
    bx: nx,
    by: ny,
    bdx,
    bdy,
    p1s,
    p2s,
    winner
  };
}

function createMatchCore() {
  return {
    p1y: HEIGHT / 2 - PAD_H / 2,
    p2y: HEIGHT / 2 - PAD_H / 2,
    p1x: 40,
    p2x: WIDTH - 52,
    bx: WIDTH / 2,
    by: HEIGHT / 2,
    bdx: 6,
    bdy: 5 * randomSign(),
    p1s: 0,
    p2s: 0,
    paused: false,
    winner: null
  };
}

function resetBall(dxSign: 1 | -1) {
  return {
    x: WIDTH / 2,
    y: HEIGHT / 2,
    dx: 6 * dxSign,
    dy: 5 * randomSign()
  };
}

function randomSign(): 1 | -1 {
  return Math.random() < 0.5 ? -1 : 1;
}

function randomBetween(min: number, max: number): number {
  return min + Math.random() * (max - min);
}
