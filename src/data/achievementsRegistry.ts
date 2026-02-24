export interface AchievementMeta {
  id: string;
  name: string;
  description: string;
  icon: string;
  color: string;
  game_id: string | null;
  secret?: boolean;
  points: number;
}

export const ACHIEVEMENT_REGISTRY: AchievementMeta[] = [
  { id: "first_game", name: "Welcome to the Arcade", description: "Play your first game of anything", icon: "CTR", color: "#63b3ed", game_id: null, points: 5 },
  { id: "ten_games", name: "Getting Warmed Up", description: "Play 10 games total across all titles", icon: "HOT", color: "#ff9f43", game_id: null, points: 10 },
  { id: "hundred_games", name: "Arcade Regular", description: "Play 100 games total", icon: "100", color: "#ab63fa", game_id: null, points: 25 },
  { id: "first_win", name: "Winner Winner", description: "Win your first game", icon: "WIN", color: "#ffd666", game_id: null, points: 5 },
  { id: "win_streak_5", name: "On a Roll", description: "Win 5 games in a row (same game)", icon: "ZAP", color: "#4feaff", game_id: null, points: 20 },
  { id: "one_hour", name: "Time Flies", description: "Accumulate 1 hour of total playtime", icon: "CLK", color: "#5cdb95", game_id: null, points: 10 },
  { id: "night_owl", name: "Night Owl", description: "Play every game at least once", icon: "OWL", color: "#ab63fa", game_id: null, points: 30, secret: true },

  { id: "tetris_first", name: "Stacker", description: "Complete your first Tetris game", icon: "BLK", color: "#4feaff", game_id: "tetris", points: 10 },
  { id: "tetris_1000", name: "Getting Started", description: "Score 1,000 points in Tetris", icon: "UP+", color: "#63b3ed", game_id: "tetris", points: 10 },
  { id: "tetris_10000", name: "Line Clearer", description: "Score 10,000 points in Tetris", icon: "GEM", color: "#ab63fa", game_id: "tetris", points: 20 },
  { id: "tetris_tetris", name: "TETRIS!", description: "Clear 4 lines at once", icon: "***", color: "#ffd666", game_id: "tetris", points: 15 },
  { id: "tetris_100_lines", name: "Century", description: "Clear 100 total lines in Tetris", icon: "100", color: "#5cdb95", game_id: "tetris", points: 25 },

  { id: "snake_first", name: "Slithering Start", description: "Play your first game of Snake", icon: "SNK", color: "#5cdb95", game_id: "snake", points: 10 },
  { id: "snake_10", name: "Growing Up", description: "Reach a length of 10 in Snake", icon: "LEN", color: "#5cdb95", game_id: "snake", points: 10 },
  { id: "snake_50", name: "Sssserious", description: "Reach a length of 50 in Snake", icon: "DRG", color: "#ffd666", game_id: "snake", points: 20 },

  { id: "pong_first_win", name: "Paddle Up", description: "Win your first Pong match", icon: "PNG", color: "#fa63b4", game_id: "pong", points: 10 },
  { id: "pong_shutout", name: "Shutout", description: "Win a Pong match without conceding a point", icon: "SHD", color: "#4feaff", game_id: "pong", points: 25 },
  { id: "pong_5_wins", name: "Pong Master", description: "Win 5 Pong matches", icon: "1ST", color: "#ffd666", game_id: "pong", points: 15 },

  { id: "flappy_first", name: "First Flap", description: "Pass your first pipe in Flappy Bird", icon: "FLY", color: "#ffd666", game_id: "flappy", points: 10 },
  { id: "flappy_10", name: "Sky Pilot", description: "Pass 10 pipes in one run", icon: "JET", color: "#4feaff", game_id: "flappy", points: 15 },
  { id: "flappy_25", name: "Bird God", description: "Pass 25 pipes in one run", icon: "ACE", color: "#ff9f43", game_id: "flappy", points: 30 },

  { id: "chess_first", name: "Opening Move", description: "Play your first game of Chess", icon: "CHK", color: "#ab63fa", game_id: "chess", points: 10 },
  { id: "chess_win", name: "Checkmate!", description: "Win a game of Chess", icon: "KNG", color: "#ffd666", game_id: "chess", points: 15 },
  { id: "chess_beat_hard", name: "Grandmaster", description: "Beat the AI on Hard difficulty", icon: "PRO", color: "#4feaff", game_id: "chess", points: 50, secret: true },

  { id: "breakout_first", name: "Brick By Brick", description: "Play your first Breakout game", icon: "BLK", color: "#ff9f43", game_id: "breakout", points: 10 },
  { id: "breakout_clear", name: "Clean Sweep", description: "Clear all bricks in a Breakout level", icon: "CLR", color: "#5cdb95", game_id: "breakout", points: 20 },

  { id: "memory_first", name: "Total Recall", description: "Complete your first Memory Match game", icon: "CRD", color: "#5cdb95", game_id: "memory_match", points: 10 },
  { id: "memory_no_mistake", name: "Perfect Memory", description: "Complete Memory Match without a single mismatch", icon: "PZL", color: "#ffd666", game_id: "memory_match", points: 30, secret: true },

  { id: "space_first", name: "Defender", description: "Survive your first wave in Space Invaders", icon: "RKT", color: "#4feaff", game_id: "space_invaders", points: 10 },
  { id: "space_wave5", name: "Space Ace", description: "Reach wave 5 in Space Invaders", icon: "STR", color: "#ffd666", game_id: "space_invaders", points: 20 },

  { id: "2048_first", name: "Starter Tile", description: "Play your first game of 2048", icon: "NUM", color: "#ff9f43", game_id: "game_2048", points: 10 },
  { id: "2048_tile", name: "Two Thousand!", description: "Reach the 2048 tile", icon: "MDL", color: "#ffd666", game_id: "game_2048", points: 30 },

  { id: "mine_first", name: "Lucky", description: "Clear your first Minesweeper board", icon: "BMB", color: "#ff6b6b", game_id: "minesweeper", points: 10 },
  { id: "c4_first", name: "Four in a Row", description: "Win your first Connect 4 game", icon: "C-4", color: "#ff6b6b", game_id: "connect4", points: 10 },

  { id: "neon_first", name: "Dasher", description: "Complete a level in Neon Blob Dash", icon: "DSH", color: "#4feaff", game_id: "neon_blob_dash", points: 10 },

  { id: "metro_100", name: "Hundred Meter", description: "Run 100 metres in Endless Metro Run", icon: "RUN", color: "#63b3ed", game_id: "endless_metro_run", points: 10 },
  { id: "metro_1000", name: "Marathon", description: "Run 1,000 metres in Endless Metro Run", icon: "MDL", color: "#ffd666", game_id: "endless_metro_run", points: 25 },

  { id: "sudoku_first", name: "First Fill", description: "Solve your first Sudoku puzzle", icon: "SUD", color: "#ab63fa", game_id: "sudoku", points: 10 },
  { id: "sudoku_no_mistakes", name: "Perfectionist", description: "Solve a Sudoku with zero mistakes", icon: "ZRO", color: "#5cdb95", game_id: "sudoku", points: 20 },
  { id: "sudoku_no_hints", name: "No Peeking", description: "Solve a Sudoku without using any hints", icon: "EYE", color: "#ffd666", game_id: "sudoku", points: 15 },
  { id: "sudoku_hard", name: "Logic Master", description: "Solve a Hard difficulty Sudoku", icon: "PRO", color: "#4feaff", game_id: "sudoku", points: 30 },
  { id: "sudoku_speed", name: "Speed Solver", description: "Solve an Easy Sudoku in under 3 minutes", icon: "ZAP", color: "#ff9f43", game_id: "sudoku", points: 25, secret: true },
  { id: "sudoku_flawless", name: "Flawless", description: "Solve a Hard Sudoku with no mistakes and no hints", icon: "GEM", color: "#ffd666", game_id: "sudoku", points: 60, secret: true },

  { id: "asteroids_first", name: "Into the Void", description: "Play your first game of Asteroids", icon: "AST", color: "#63b3ed", game_id: "asteroids", points: 10 },
  { id: "asteroids_wave3", name: "Rock Crusher", description: "Reach wave 3 in Asteroids", icon: "RCK", color: "#5cdb95", game_id: "asteroids", points: 10 },
  { id: "asteroids_wave5", name: "Ace Pilot", description: "Reach wave 5 in Asteroids", icon: "ACE", color: "#ffd666", game_id: "asteroids", points: 25 },
  { id: "asteroids_wave10", name: "Star Destroyer", description: "Reach wave 10 in Asteroids", icon: "STR", color: "#4feaff", game_id: "asteroids", points: 50, secret: true },
  { id: "asteroids_score5k", name: "Five Thousand", description: "Score 5,000 points in a single Asteroids run", icon: "5KP", color: "#ff9f43", game_id: "asteroids", points: 20 },
  { id: "asteroids_score20k", name: "Void Walker", description: "Score 20,000 points in a single Asteroids run", icon: "20K", color: "#ab63fa", game_id: "asteroids", points: 40, secret: true },

  { id: "all_rounder", name: "All-Rounder", description: "Play at least one game in 10 different titles", icon: "10X", color: "#ffd666", game_id: null, points: 35, secret: true }
];
