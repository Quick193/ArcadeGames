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
        <p>{unlockedCount} / {all.length} unlocked • {totalPoints} pts • {progress}%</p>
      </header>

      <section className="settings-block">
        <div className="ach-progress">
          <div className="ach-progress-fill" style={{ width: `${progress}%` }} />
        </div>
        <ul className="ach-list">
          {all.map((a) => (
            <li key={a.id} className={a.unlocked ? "ach-unlocked" : "ach-locked"} style={{ borderColor: a.unlocked ? a.color : "#23324d" }}>
              <div>
                <strong>{a.name}</strong>
                <p>{a.unlocked || !a.secret ? a.description : "Secret achievement - keep playing to unlock"}</p>
                <small>{a.game_id ? a.game_id.replace(/_/g, " ") : "global"}</small>
              </div>
              <div className="ach-meta">
                <span>{a.points} pts</span>
                <span>{a.unlocked && a.date ? a.date.slice(0, 10) : "locked"}</span>
              </div>
            </li>
          ))}
        </ul>
      </section>

      <button type="button" onClick={onBack}>Back to Menu</button>
    </section>
  );
}

export default AchievementsScreen;
