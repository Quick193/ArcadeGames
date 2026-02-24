export type GameId =
  | "tetris"
  | "snake"
  | "pong"
  | "flappy"
  | "chess"
  | "breakout"
  | "memory_match"
  | "neon_blob_dash"
  | "endless_metro_run"
  | "space_invaders"
  | "game_2048"
  | "minesweeper"
  | "connect4"
  | "sudoku"
  | "asteroids";

export interface GameMeta {
  id: GameId;
  name: string;
  desc: string;
  color: string;
  status: "implemented" | "planned";
}
