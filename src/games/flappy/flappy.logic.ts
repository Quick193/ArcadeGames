export const WIDTH = 540;
export const HEIGHT = 900;
export const PIPE_W = 70;
export const BIRD_R = 14;

export type Difficulty = "easy" | "medium" | "hard";
export type Phase = "select" | "game";

export interface DiffParams {
  gap: number;
  dist: number;
  grav: number;
  flap: number;
  spd: number;
}

export const DIFF: Record<Difficulty, DiffParams> = {
  easy: { gap: 250, dist: 2.8, grav: 0.45, flap: -11, spd: 220 },
  medium: { gap: 210, dist: 2.2, grav: 0.55, flap: -13, spd: 260 },
  hard: { gap: 180, dist: 1.8, grav: 0.65, flap: -15, spd: 300 }
};

export interface Pipe {
  x: number;
  y: number;
  scored: boolean;
}

export interface FlappyState {
  phase: Phase;
  selection: number;
  diff: Difficulty | null;
  params: DiffParams | null;

  birdX: number;
  birdY: number;
  vel: number;

  pipes: Pipe[];
  pipeTimer: number;

  score: number;
  dead: boolean;
  paused: boolean;
}

export function createInitialState(): FlappyState {
  return {
    phase: "select",
    selection: 1,
    diff: null,
    params: null,
    birdX: 150,
    birdY: HEIGHT / 2,
    vel: 0,
    pipes: [],
    pipeTimer: 0,
    score: 0,
    dead: false,
    paused: false
  };
}

export function startGame(state: FlappyState, diff: Difficulty): FlappyState {
  return {
    ...state,
    phase: "game",
    diff,
    params: DIFF[diff],
    birdX: 150,
    birdY: HEIGHT / 2,
    vel: 0,
    pipes: [],
    pipeTimer: 0,
    score: 0,
    dead: false,
    paused: false
  };
}

export function stepGame(state: FlappyState, dt: number): FlappyState {
  if (state.phase !== "game" || state.paused || state.dead || !state.params) {
    return state;
  }

  const p = state.params;
  const vel = Math.min(state.vel + p.grav, 20);
  const birdY = state.birdY + vel;

  let pipeTimer = state.pipeTimer + dt;
  const pipes = state.pipes.map((pipe) => ({ ...pipe }));

  if (pipeTimer >= p.dist) {
    pipeTimer = 0;
    pipes.push({ x: WIDTH, y: randomInt(90, HEIGHT - 90 - p.gap), scored: false });
  }

  let score = state.score;
  let dead = false;

  for (const pipe of pipes) {
    pipe.x -= p.spd * dt;

    if (state.birdX + BIRD_R - 6 > pipe.x && state.birdX - BIRD_R + 6 < pipe.x + PIPE_W) {
      if (birdY - BIRD_R + 6 < pipe.y || birdY + BIRD_R - 6 > pipe.y + p.gap) {
        dead = true;
      }
    }

    if (pipe.x + PIPE_W < state.birdX && !pipe.scored) {
      pipe.scored = true;
      score += 1;
    }
  }

  const visible = pipes.filter((pipe) => pipe.x > -PIPE_W);

  if (birdY + BIRD_R > HEIGHT || birdY - BIRD_R < 0) {
    dead = true;
  }

  return {
    ...state,
    birdY,
    vel,
    pipes: visible,
    pipeTimer,
    score,
    dead
  };
}

export function flap(state: FlappyState): FlappyState {
  if (state.phase !== "game" || state.paused || state.dead || !state.params) {
    return state;
  }

  return { ...state, vel: state.params.flap };
}

function randomInt(min: number, max: number): number {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}
