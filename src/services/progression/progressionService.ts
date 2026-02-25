import { ACHIEVEMENT_REGISTRY } from "../../data/achievementsRegistry";
import type { AchievementsData } from "../storage/achievementsStorage";
import { readAchievements, writeAchievements } from "../storage/achievementsStorage";
import { readStats, writeStats } from "../storage/statsStorage";
import type { GameStats, StatsData } from "../../types/stats";
import type { GameId } from "../../types/game";

type Primitive = string | number | boolean | null;

export interface RecordGameInput {
  gameId: GameId;
  score?: number;
  won?: boolean;
  durationSec?: number;
  extra?: Record<string, Primitive>;
}

const MAX_TOP_SCORES = 10;
export const ACHIEVEMENT_UNLOCK_EVENT = "arcade:achievement-unlocked";

function nowIso(): string {
  return new Date().toISOString();
}

function emptyGame(): GameStats {
  return {
    games_played: 0,
    games_won: 0,
    games_lost: 0,
    best_score: 0,
    total_playtime: 0,
    current_streak: 0,
    best_streak: 0,
    top_scores: [],
    extra: {}
  };
}

function ensureGame(stats: StatsData, gameId: string): GameStats {
  if (!stats.games[gameId]) {
    stats.games[gameId] = emptyGame();
  } else {
    stats.games[gameId].top_scores ??= [];
    stats.games[gameId].extra ??= {};
  }
  return stats.games[gameId] as GameStats;
}

function numericExtra(input: Record<string, Primitive> | undefined): Record<string, number> {
  const out: Record<string, number> = {};
  if (!input) {
    return out;
  }
  for (const [k, v] of Object.entries(input)) {
    if (typeof v === "number" && Number.isFinite(v)) {
      out[k] = v;
    }
  }
  return out;
}

function asNumber(value: unknown): number {
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}

function unlocked(achievements: AchievementsData, id: string): boolean {
  return Boolean(achievements.unlocked[id]);
}

function unlock(achievements: AchievementsData, id: string): void {
  if (!achievements.unlocked[id]) {
    achievements.unlocked[id] = nowIso();
  }
}

function maybeUnlockAll(
  achievements: AchievementsData,
  stats: StatsData,
  gameId: GameId,
  score: number,
  wonGame: boolean,
  durationSec: number,
  inputExtra: Record<string, Primitive>
): string[] {
  const game = ensureGame(stats, gameId);
  const extra = inputExtra ?? {};
  const gameExtra = game.extra ?? {};
  const unlockedNow: string[] = [];
  const totalWins = Object.values(stats.games).reduce((sum, g) => sum + g.games_won, 0);
  const gamesTried = Object.values(stats.games).filter((g) => g.games_played > 0).length;
  const maxTile = asNumber(extra.max_tile);
  const mistakes = asNumber(extra.mistakes);
  const hints = asNumber(extra.hints_used);
  const difficulty = typeof extra.difficulty === "string" ? extra.difficulty : "";
  const opponentScore = asNumber(extra.opponent_score);
  const waveReached = asNumber(extra.wave_reached);
  const distance = asNumber(extra.distance);
  const snakeLength = asNumber(extra.snake_length);
  const memoryErrors = asNumber(extra.errors);

  const tryUnlock = (id: string, cond: boolean) => {
    if (!cond || unlocked(achievements, id)) {
      return;
    }
    unlock(achievements, id);
    unlockedNow.push(id);
  };

  // Global
  tryUnlock("first_game", stats.total_games >= 1);
  tryUnlock("ten_games", stats.total_games >= 10);
  tryUnlock("hundred_games", stats.total_games >= 100);
  tryUnlock("first_win", totalWins >= 1);
  tryUnlock("win_streak_5", game.current_streak >= 5);
  tryUnlock("one_hour", stats.global_playtime >= 3600);
  tryUnlock("night_owl", gamesTried >= 13);
  tryUnlock("all_rounder", gamesTried >= 10);

  if (gameId === "tetris") {
    tryUnlock("tetris_first", game.games_played >= 1);
    tryUnlock("tetris_1000", score >= 1000);
    tryUnlock("tetris_10000", score >= 10000);
    tryUnlock("tetris_tetris", asNumber(extra.tetris_clears) >= 1);
    tryUnlock("tetris_100_lines", asNumber(gameExtra.lines) >= 100);
  }

  if (gameId === "snake") {
    tryUnlock("snake_first", game.games_played >= 1);
    tryUnlock("snake_10", snakeLength >= 10 || score >= 10);
    tryUnlock("snake_50", snakeLength >= 50 || score >= 50);
  }

  if (gameId === "pong") {
    tryUnlock("pong_first_win", wonGame);
    tryUnlock("pong_shutout", wonGame && opponentScore === 0);
    tryUnlock("pong_5_wins", game.games_won >= 5);
  }

  if (gameId === "flappy") {
    tryUnlock("flappy_first", score >= 1);
    tryUnlock("flappy_10", score >= 10);
    tryUnlock("flappy_25", score >= 25);
  }

  if (gameId === "chess") {
    tryUnlock("chess_first", game.games_played >= 1);
    tryUnlock("chess_win", wonGame);
    tryUnlock("chess_beat_hard", wonGame && difficulty === "hard");
  }

  if (gameId === "breakout") {
    tryUnlock("breakout_first", game.games_played >= 1);
    tryUnlock("breakout_clear", wonGame);
  }

  if (gameId === "memory_match") {
    tryUnlock("memory_first", wonGame);
    tryUnlock("memory_no_mistake", wonGame && memoryErrors === 0);
  }

  if (gameId === "space_invaders") {
    tryUnlock("space_first", waveReached >= 1);
    tryUnlock("space_wave5", waveReached >= 5);
  }

  if (gameId === "game_2048") {
    tryUnlock("2048_first", game.games_played >= 1);
    tryUnlock("2048_tile", maxTile >= 2048);
  }

  if (gameId === "minesweeper") {
    tryUnlock("mine_first", wonGame);
  }

  if (gameId === "connect4") {
    tryUnlock("c4_first", wonGame);
  }

  if (gameId === "neon_blob_dash") {
    tryUnlock("neon_first", wonGame);
  }

  if (gameId === "endless_metro_run") {
    tryUnlock("metro_100", distance >= 100);
    tryUnlock("metro_1000", distance >= 1000);
  }

  if (gameId === "sudoku") {
    tryUnlock("sudoku_first", wonGame);
    tryUnlock("sudoku_no_mistakes", wonGame && mistakes === 0);
    tryUnlock("sudoku_no_hints", wonGame && hints === 0);
    tryUnlock("sudoku_hard", wonGame && difficulty === "hard");
    tryUnlock("sudoku_speed", wonGame && difficulty === "easy" && durationSec > 0 && durationSec < 180);
    tryUnlock("sudoku_flawless", wonGame && difficulty === "hard" && mistakes === 0 && hints === 0);
  }

  if (gameId === "asteroids") {
    tryUnlock("asteroids_first", game.games_played >= 1);
    tryUnlock("asteroids_wave3", waveReached >= 3);
    tryUnlock("asteroids_wave5", waveReached >= 5);
    tryUnlock("asteroids_wave10", waveReached >= 10);
    tryUnlock("asteroids_score5k", score >= 5000);
    tryUnlock("asteroids_score20k", score >= 20000);
  }

  return unlockedNow;
}

export function recordGameResult(input: RecordGameInput): { unlockedIds: string[] } {
  const score = Math.max(0, Math.floor(input.score ?? 0));
  const won = Boolean(input.won);
  const durationSec = Math.max(0, input.durationSec ?? 0);
  const stats = readStats();
  const achievements = readAchievements();
  const game = ensureGame(stats, input.gameId);
  const extra = input.extra ?? {};
  const date = nowIso();

  game.games_played += 1;
  game.total_playtime += durationSec;
  stats.total_games += 1;
  stats.global_playtime += durationSec;
  stats.first_play ??= date;
  stats.last_play = date;

  if (won) {
    game.games_won += 1;
    game.current_streak += 1;
    game.best_streak = Math.max(game.best_streak, game.current_streak);
  } else {
    game.games_lost += 1;
    game.current_streak = 0;
  }

  game.best_score = Math.max(game.best_score, score);
  game.top_scores = [...(game.top_scores ?? []), { score, date, extra }]
    .sort((a, b) => b.score - a.score)
    .slice(0, MAX_TOP_SCORES);

  const numerics = numericExtra(extra);
  for (const [k, v] of Object.entries(numerics)) {
    game.extra![k] = (game.extra![k] ?? 0) + v;
  }

  const unlockedIds = maybeUnlockAll(achievements, stats, input.gameId, score, won, durationSec, extra);
  writeStats(stats);
  writeAchievements(achievements);
  if (unlockedIds.length > 0 && typeof window !== "undefined") {
    window.dispatchEvent(
      new CustomEvent(ACHIEVEMENT_UNLOCK_EVENT, {
        detail: {
          ids: unlockedIds
        }
      })
    );
  }
  return { unlockedIds };
}

export function addSessionPlaytime(gameId: GameId, durationSec: number): void {
  const duration = Math.max(0, durationSec);
  if (!duration) {
    return;
  }
  const stats = readStats();
  const achievements = readAchievements();
  const game = ensureGame(stats, gameId);
  const date = nowIso();
  game.total_playtime += duration;
  stats.global_playtime += duration;
  stats.first_play ??= date;
  stats.last_play = date;
  maybeUnlockAll(achievements, stats, gameId, 0, false, duration, {});
  writeStats(stats);
  writeAchievements(achievements);
}

export function totalAchievementCount(): number {
  return ACHIEVEMENT_REGISTRY.length;
}
