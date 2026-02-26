import type { AppSettings } from "../types/settings";

type ThemeColors = {
  bg: string;
  panel: string;
  panel2: string;
  text: string;
  muted: string;
  line: string;
};

const THEMES: Record<string, ThemeColors> = {
  modern_dark: {
    bg: "#02050d",
    panel: "#0d1727",
    panel2: "#142137",
    text: "#edf2f4",
    muted: "#8d99ae",
    line: "#23324d"
  },
  neon_cyber: {
    bg: "#05050f",
    panel: "#0b1224",
    panel2: "#1a0f2e",
    text: "#e6ffff",
    muted: "#66cfd8",
    line: "#1ab6c9"
  },
  retro_crt: {
    bg: "#061607",
    panel: "#0a2010",
    panel2: "#113019",
    text: "#c9ffc9",
    muted: "#76b776",
    line: "#2e6d37"
  },
  minimal_light: {
    bg: "#f2f5fb",
    panel: "#ffffff",
    panel2: "#edf1f7",
    text: "#1d2433",
    muted: "#5f6b80",
    line: "#c7d1e1"
  },
  glass_ui: {
    bg: "#102036",
    panel: "#1a2f4f",
    panel2: "#243f66",
    text: "#f0f7ff",
    muted: "#9fb8d8",
    line: "#4f77ad"
  }
};

export const THEME_OPTIONS = Object.keys(THEMES);

export function applyTheme(themeName: AppSettings["theme"]): void {
  const theme = THEMES[themeName] ?? THEMES.modern_dark;
  const root = document.documentElement;
  root.style.setProperty("--bg", theme.bg);
  root.style.setProperty("--panel", theme.panel);
  root.style.setProperty("--panel-2", theme.panel2);
  root.style.setProperty("--text", theme.text);
  root.style.setProperty("--muted", theme.muted);
  root.style.setProperty("--line", theme.line);
}
