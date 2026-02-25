import type { StatsData } from "../../types/stats";

const KEY = "arcade.stats.v1";

const EMPTY: StatsData = {
  games: {},
  global_playtime: 0,
  total_games: 0,
  first_play: null,
  last_play: null
};

export function readStats(): StatsData {
  const raw = window.localStorage.getItem(KEY);
  if (!raw) {
    return EMPTY;
  }
  try {
    const parsed = JSON.parse(raw) as StatsData;
    return {
      ...EMPTY,
      ...parsed,
      games: parsed.games ?? {}
    };
  } catch {
    return EMPTY;
  }
}

export function writeStats(stats: StatsData): void {
  window.localStorage.setItem(KEY, JSON.stringify(stats));
}

export function resetStats(): StatsData {
  const next = { ...EMPTY, games: {} };
  writeStats(next);
  return next;
}
