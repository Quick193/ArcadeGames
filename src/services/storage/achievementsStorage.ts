export interface AchievementsData {
  unlocked: Record<string, string>;
}

const KEY = "arcade.achievements.v1";

const EMPTY: AchievementsData = { unlocked: {} };

export function readAchievements(): AchievementsData {
  const raw = window.localStorage.getItem(KEY);
  if (!raw) {
    return EMPTY;
  }

  try {
    const parsed = JSON.parse(raw) as AchievementsData;
    return {
      unlocked: parsed.unlocked ?? {}
    };
  } catch {
    return EMPTY;
  }
}
