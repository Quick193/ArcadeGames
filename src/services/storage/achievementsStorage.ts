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

export function writeAchievements(achievements: AchievementsData): void {
  window.localStorage.setItem(KEY, JSON.stringify(achievements));
}

export function resetAchievements(): AchievementsData {
  const next: AchievementsData = { unlocked: {} };
  writeAchievements(next);
  return next;
}
