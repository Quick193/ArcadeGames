import type { AppSettings } from "../types/settings";
import { THEME_OPTIONS } from "../data/themePalettes";

interface SettingsScreenProps {
  settings: AppSettings;
  onChange: (next: AppSettings) => void;
  onResetStats: () => void;
  onResetAchievements: () => void;
  onResetAll: () => void;
  onBack: () => void;
}

const FPS_OPTIONS = [30, 60, 120, 0];

function SettingsScreen({
  settings,
  onChange,
  onResetStats,
  onResetAchievements,
  onResetAll,
  onBack
}: SettingsScreenProps) {
  const set = <K extends keyof AppSettings>(key: K, value: AppSettings[K]) => {
    onChange({ ...settings, [key]: value });
  };

  return (
    <section className="settings-screen">
      <header className="hero">
        <h1>Settings</h1>
        <p>Changes save immediately.</p>
      </header>

      <section className="settings-block">
        <h3>Audio</h3>
        <label className="setting-row">
          <span>Music Enabled</span>
          <input type="checkbox" checked={settings.music_enabled} onChange={(e) => set("music_enabled", e.target.checked)} />
        </label>
        <label className="setting-row">
          <span>Music Volume</span>
          <input
            type="range"
            min={0}
            max={100}
            step={5}
            value={Math.round(settings.music_volume * 100)}
            onChange={(e) => set("music_volume", Number(e.target.value) / 100)}
          />
        </label>
        <label className="setting-row">
          <span>SFX Enabled</span>
          <input type="checkbox" checked={settings.sfx_enabled} onChange={(e) => set("sfx_enabled", e.target.checked)} />
        </label>
        <label className="setting-row">
          <span>SFX Volume</span>
          <input
            type="range"
            min={0}
            max={100}
            step={5}
            value={Math.round(settings.sfx_volume * 100)}
            onChange={(e) => set("sfx_volume", Number(e.target.value) / 100)}
          />
        </label>
      </section>

      <section className="settings-block">
        <h3>Display</h3>
        <label className="setting-row">
          <span>Theme</span>
          <select value={settings.theme} onChange={(e) => set("theme", e.target.value)}>
            {THEME_OPTIONS.map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
        </label>
        <label className="setting-row">
          <span>Particles</span>
          <input type="checkbox" checked={settings.show_particles} onChange={(e) => set("show_particles", e.target.checked)} />
        </label>
        <label className="setting-row">
          <span>Background Animation</span>
          <input type="checkbox" checked={settings.show_bg_anim} onChange={(e) => set("show_bg_anim", e.target.checked)} />
        </label>
        <label className="setting-row">
          <span>Show FPS</span>
          <input type="checkbox" checked={settings.show_fps} onChange={(e) => set("show_fps", e.target.checked)} />
        </label>
        <label className="setting-row">
          <span>FPS Cap</span>
          <select value={settings.fps_cap} onChange={(e) => set("fps_cap", Number(e.target.value))}>
            {FPS_OPTIONS.map((fps) => (
              <option key={fps} value={fps}>{fps === 0 ? "Unlimited" : fps}</option>
            ))}
          </select>
        </label>
      </section>

      <section className="settings-block">
        <h3>Gameplay</h3>
        <label className="setting-row">
          <span>Ghost Piece</span>
          <input type="checkbox" checked={settings.show_ghost_piece} onChange={(e) => set("show_ghost_piece", e.target.checked)} />
        </label>
        <label className="setting-row">
          <span>Chess Move Hints</span>
          <input type="checkbox" checked={settings.chess_show_hints} onChange={(e) => set("chess_show_hints", e.target.checked)} />
        </label>
        <label className="setting-row">
          <span>Auto-Clear Arrows</span>
          <input type="checkbox" checked={settings.auto_clear_annotations} onChange={(e) => set("auto_clear_annotations", e.target.checked)} />
        </label>
      </section>

      <section className="settings-block">
        <h3>Mobile Controls</h3>
        <p className="settings-muted">Buttons-only controls are enabled across all games.</p>
      </section>

      <section className="settings-block">
        <h3>Data</h3>
        <label className="setting-row">
          <span>Reset on Start</span>
          <input type="checkbox" checked={settings.reset_on_start} onChange={(e) => set("reset_on_start", e.target.checked)} />
        </label>
        <div className="settings-actions">
          <button type="button" onClick={onResetStats}>Reset Stats</button>
          <button type="button" onClick={onResetAchievements}>Reset Achievements</button>
          <button type="button" onClick={onResetAll}>Full Wipe</button>
        </div>
      </section>

      <button type="button" onClick={onBack}>Back to Menu</button>
    </section>
  );
}

export default SettingsScreen;
