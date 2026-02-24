import type { AppSettings, ControlScheme } from "../../types/settings";

const KEY = "arcade.settings.v1";

export const DEFAULT_SETTINGS: AppSettings = {
  music_volume: 0.8,
  sfx_volume: 0.9,
  music_enabled: true,
  sfx_enabled: true,
  theme: "modern_dark",
  show_particles: true,
  show_bg_anim: true,
  show_fps: false,
  fps_cap: 60,
  show_ghost_piece: true,
  auto_clear_annotations: false,
  chess_show_hints: true,
  mobile_control_scheme: "buttons"
};

export function readSettings(): AppSettings {
  const raw = window.localStorage.getItem(KEY);
  if (!raw) {
    return DEFAULT_SETTINGS;
  }

  try {
    const parsed = JSON.parse(raw) as Partial<AppSettings>;
    const scheme = parsed.mobile_control_scheme === "gestures" ? "gestures" : "buttons";
    return {
      ...DEFAULT_SETTINGS,
      ...parsed,
      mobile_control_scheme: scheme
    };
  } catch {
    return DEFAULT_SETTINGS;
  }
}

export function writeSettings(settings: AppSettings): void {
  window.localStorage.setItem(KEY, JSON.stringify(settings));
}

export function setControlScheme(scheme: ControlScheme): AppSettings {
  const current = readSettings();
  const next = { ...current, mobile_control_scheme: scheme };
  writeSettings(next);
  return next;
}
