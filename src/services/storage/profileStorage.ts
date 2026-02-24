import type { ProfileData } from "../../types/profile";

const KEY = "arcade.profile.v1";

const DEFAULT_PROFILE: ProfileData = {
  display_name: "Player 1",
  avatar_index: 0
};

export function readProfile(): ProfileData {
  const raw = window.localStorage.getItem(KEY);
  if (!raw) {
    return DEFAULT_PROFILE;
  }

  try {
    const parsed = JSON.parse(raw) as Partial<ProfileData>;
    return {
      display_name: typeof parsed.display_name === "string" && parsed.display_name.trim() ? parsed.display_name.slice(0, 24) : "Player 1",
      avatar_index: Number.isFinite(parsed.avatar_index) ? Math.max(0, Number(parsed.avatar_index)) : 0
    };
  } catch {
    return DEFAULT_PROFILE;
  }
}

export function writeProfile(profile: ProfileData): void {
  window.localStorage.setItem(KEY, JSON.stringify(profile));
}
