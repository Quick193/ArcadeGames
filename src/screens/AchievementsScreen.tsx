import { ACHIEVEMENT_REGISTRY } from "../data/achievementsRegistry";
import type { AchievementsData } from "../services/storage/achievementsStorage";

interface AchievementsScreenProps {
  achievements: AchievementsData;
  onBack: () => void;
}

function AchievementsScreen({ achievements, onBack }: AchievementsScreenProps) {
  const all = ACHIEVEMENT_REGISTRY.map((a) => {
    const date = achievements.unlocked[a.id];
    return {
      ...a,
      unlocked: Boolean(date),
      date: date ?? null
    };
  }).sort((a, b) => {
    if (a.unlocked && !b.unlocked) return -1;
    if (!a.unlocked && b.unlocked) return 1;
    if (a.unlocked && b.unlocked) return (b.date ?? "").localeCompare(a.date ?? "");
    return a.name.localeCompare(b.name);
  });

  const unlockedCount = all.filter((a) => a.unlocked).length;
  const totalPoints = all.filter((a) => a.unlocked).reduce((sum, a) => sum + a.points, 0);
  const progress = all.length > 0 ? Math.round((unlockedCount / all.length) * 100) : 0;

  return (
    <section className="ach-screen">
      <header className="hero">
        <h1>Achievements</h1>
        <p>{unlockedCount} / {all.length} unlocked • {totalPoints} pts earned</p>
      </header>

      <section className="settings-block ach-header-stats">
        <p className="settings-muted">{progress}% complete</p>
        <div className="ach-progress">
          <div className="ach-progress-fill" style={{ width: `${progress}%` }} />
        </div>
      </section>

      <section className="settings-block ach-grid-wrap">
        <ul className="ach-grid">
          {all.map((a) => (
            <li
              key={a.id}
              className={`ach-card ${a.unlocked ? "ach-unlocked" : "ach-locked"}`}
              style={{
                borderColor: a.unlocked ? a.color : "#2d3e5d"
              }}
            >
              <div className="ach-icon-pill" style={{ background: a.unlocked ? a.color : "#4a5770" }}>
                {a.icon.slice(0, 3)}
              </div>
              <div className="ach-card-content">
                <div className="ach-card-head">
                  <strong>{a.name}</strong>
                  <span>{a.points} pts</span>
                </div>
                <p>{a.unlocked || !a.secret ? a.description : "Secret achievement - keep playing to unlock"}</p>
                <div className="ach-card-foot">
                  <small>{a.game_id ? a.game_id.replace(/_/g, " ").toUpperCase() : "GLOBAL"}</small>
                  <small>{a.unlocked && a.date ? `OK ${a.date.slice(0, 10)}` : "LOCKED"}</small>
                </div>
              </div>
            </li>
          ))}
        </ul>
      </section>

      <div className="settings-actions">
        <button type="button" onClick={onBack}>Back to Menu</button>
      </div>
    </section>
  );
}

export default AchievementsScreen;
