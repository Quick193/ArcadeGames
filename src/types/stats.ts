export interface GameStats {
  games_played: number;
  games_won: number;
  games_lost: number;
  best_score: number;
  total_playtime: number;
  current_streak: number;
  best_streak: number;
  top_scores?: Array<{ score: number; date: string; extra?: Record<string, unknown> }>;
  extra?: Record<string, number>;
}

export interface StatsData {
  games: Record<string, GameStats>;
  global_playtime: number;
  total_games: number;
  first_play: string | null;
  last_play: string | null;
}
