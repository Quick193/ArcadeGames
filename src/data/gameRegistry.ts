import type { GameMeta } from "../types/game";

export const gameRegistry: GameMeta[] = [
  { id: "tetris", name: "Tetris", desc: "Stack and clear lines", color: "#4cc9f0", status: "implemented" },
  { id: "snake", name: "Snake", desc: "Grow and survive", color: "#70e000", status: "implemented" },
  { id: "pong", name: "Pong", desc: "Classic paddle duel", color: "#f72585", status: "implemented" },
  { id: "flappy", name: "Flappy Bird", desc: "Thread the pipes", color: "#ffbe0b", status: "implemented" },
  { id: "chess", name: "Chess", desc: "Tactical battles", color: "#9d4edd", status: "planned" },
  { id: "breakout", name: "Breakout", desc: "Break every brick", color: "#fb8500", status: "planned" },
  { id: "memory_match", name: "Memory Match", desc: "Find all pairs", color: "#70e000", status: "planned" },
  { id: "neon_blob_dash", name: "Neon Blob Dash", desc: "Dash and survive", color: "#4cc9f0", status: "planned" },
  { id: "endless_metro_run", name: "Endless Metro Run", desc: "Endless platform run", color: "#4895ef", status: "planned" },
  { id: "space_invaders", name: "Space Invaders", desc: "Defend against waves", color: "#fb8500", status: "planned" },
  { id: "game_2048", name: "2048", desc: "Merge to the top", color: "#ffbe0b", status: "implemented" },
  { id: "minesweeper", name: "Minesweeper", desc: "Clear the minefield", color: "#e63946", status: "planned" },
  { id: "connect4", name: "Connect 4", desc: "Four in a row wins", color: "#f72585", status: "planned" },
  { id: "sudoku", name: "Sudoku", desc: "Fill the 9x9 grid", color: "#9d4edd", status: "planned" },
  { id: "asteroids", name: "Asteroids", desc: "Destroy all rocks", color: "#4cc9f0", status: "planned" }
];
