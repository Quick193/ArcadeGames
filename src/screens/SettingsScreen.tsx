import type { AppSettings } from "../types/settings";

interface SettingsScreenProps {
  settings: AppSettings;
  onChange: (next: AppSettings) => void;
  onBack: () => void;
}

function SettingsScreen({ settings, onChange, onBack }: SettingsScreenProps) {
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
          <span>SFX Enabled</span>
          <input type="checkbox" checked={settings.sfx_enabled} onChange={(e) => set("sfx_enabled", e.target.checked)} />
        </label>
      </section>

      <section className="settings-block">
        <h3>Display</h3>
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
      </section>

      <section className="settings-block">
        <h3>Mobile Controls</h3>
        <p className="settings-muted">Applies to all supported games.</p>
        <div className="segmented">
          <button
            type="button"
            className={settings.mobile_control_scheme === "buttons" ? "active" : ""}
            onClick={() => set("mobile_control_scheme", "buttons")}
          >
            Buttons
          </button>
          <button
            type="button"
            className={settings.mobile_control_scheme === "gestures" ? "active" : ""}
            onClick={() => set("mobile_control_scheme", "gestures")}
          >
            Gestures
          </button>
        </div>
      </section>

      <button type="button" onClick={onBack}>Back to Menu</button>
    </section>
  );
}

export default SettingsScreen;
