export interface GameStats {
  games_played: number;
  games_won: number;
  games_lost: number;
  best_score: number;
  total_playtime: number;
  current_streak: number;
  best_streak: number;
}

export interface StatsData {
  games: Record<string, GameStats>;
  global_playtime: number;
  total_games: number;
  first_play: string | null;
  last_play: string | null;
}
