import { useEffect, useMemo, useState } from "react";
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
type PendingAction = "stats" | "achievements" | "all" | null;

function SettingsScreen({
  settings,
  onChange,
  onResetStats,
  onResetAchievements,
  onResetAll,
  onBack
}: SettingsScreenProps) {
  const [pendingAction, setPendingAction] = useState<PendingAction>(null);
  const [statusMessage, setStatusMessage] = useState<string>("");
  const set = <K extends keyof AppSettings>(key: K, value: AppSettings[K]) => {
    onChange({ ...settings, [key]: value });
  };
  const actionMessage = useMemo(() => {
    if (pendingAction === "stats") return "Reset all saved stats?";
    if (pendingAction === "achievements") return "Reset all unlocked achievements?";
    if (pendingAction === "all") return "Run full wipe (stats, achievements, profile, settings)?";
    return "";
  }, [pendingAction]);

  useEffect(() => {
    if (!statusMessage) return;
    const id = window.setTimeout(() => setStatusMessage(""), 2500);
    return () => window.clearTimeout(id);
  }, [statusMessage]);

  useEffect(() => {
    if (!pendingAction) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setPendingAction(null);
      }
      if (event.key === "Enter") {
        event.preventDefault();
        if (pendingAction === "stats") {
          onResetStats();
          setStatusMessage("Stats reset.");
        } else if (pendingAction === "achievements") {
          onResetAchievements();
          setStatusMessage("Achievements reset.");
        } else {
          onResetAll();
          setStatusMessage("Full reset complete.");
        }
        setPendingAction(null);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onResetAchievements, onResetAll, onResetStats, pendingAction]);

  const runPendingAction = () => {
    if (pendingAction === "stats") {
      onResetStats();
      setStatusMessage("Stats reset.");
    } else if (pendingAction === "achievements") {
      onResetAchievements();
      setStatusMessage("Achievements reset.");
    } else if (pendingAction === "all") {
      onResetAll();
      setStatusMessage("Full reset complete.");
    }
    setPendingAction(null);
  };

  return (
    <section className="settings-screen">
      <header className="hero">
        <h1>Settings</h1>
        <p>Changes save immediately.</p>
        {statusMessage && <p className="settings-status">{statusMessage}</p>}
      </header>

      <section className="settings-block">
        <h3>Audio</h3>
        <label className="setting-row">
          <span>Music Enabled</span>
          <input type="checkbox" checked={settings.music_enabled} onChange={(e) => set("music_enabled", e.target.checked)} />
        </label>
        <label className="setting-row">
          <span>Music Volume</span>
          <div className="setting-inline">
            <input
              type="range"
              min={0}
              max={100}
              step={5}
              value={Math.round(settings.music_volume * 100)}
              onChange={(e) => set("music_volume", Number(e.target.value) / 100)}
            />
            <small>{Math.round(settings.music_volume * 100)}%</small>
          </div>
        </label>
        <label className="setting-row">
          <span>SFX Enabled</span>
          <input type="checkbox" checked={settings.sfx_enabled} onChange={(e) => set("sfx_enabled", e.target.checked)} />
        </label>
        <label className="setting-row">
          <span>SFX Volume</span>
          <div className="setting-inline">
            <input
              type="range"
              min={0}
              max={100}
              step={5}
              value={Math.round(settings.sfx_volume * 100)}
              onChange={(e) => set("sfx_volume", Number(e.target.value) / 100)}
            />
            <small>{Math.round(settings.sfx_volume * 100)}%</small>
          </div>
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
        <p className="settings-muted">Destructive actions require confirmation.</p>
        <label className="setting-row">
          <span>Reset on Next Launch</span>
          <input type="checkbox" checked={settings.reset_on_start} onChange={(e) => set("reset_on_start", e.target.checked)} />
        </label>
        <div className="settings-actions">
          <button type="button" onClick={() => setPendingAction("stats")}>Reset Stats</button>
          <button type="button" onClick={() => setPendingAction("achievements")}>Reset Achievements</button>
          <button type="button" className="danger" onClick={() => setPendingAction("all")}>Full Wipe</button>
        </div>
      </section>

      <button type="button" onClick={onBack}>Back to Menu</button>

      {pendingAction && (
        <div className="settings-confirm-backdrop" onClick={() => setPendingAction(null)}>
          <div className="settings-confirm-card" onClick={(e) => e.stopPropagation()} role="dialog" aria-modal="true">
            <h3>Confirm Action</h3>
            <p>{actionMessage}</p>
            <p className="settings-muted">This cannot be undone.</p>
            <div className="settings-actions">
              <button type="button" onClick={() => setPendingAction(null)}>Cancel</button>
              <button type="button" className="danger" onClick={runPendingAction}>Confirm</button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}

export default SettingsScreen;
