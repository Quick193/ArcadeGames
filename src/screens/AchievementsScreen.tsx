import type { AchievementsData } from "../services/storage/achievementsStorage";

interface AchievementsScreenProps {
  achievements: AchievementsData;
  onBack: () => void;
}

function AchievementsScreen({ achievements, onBack }: AchievementsScreenProps) {
  const unlocked = Object.entries(achievements.unlocked).sort((a, b) => b[1].localeCompare(a[1]));

  return (
    <section className="ach-screen">
      <header className="hero">
        <h1>Achievements</h1>
        <p>{unlocked.length} unlocked</p>
      </header>

      <section className="settings-block">
        {unlocked.length === 0 ? (
          <p>No achievements unlocked yet.</p>
        ) : (
          <ul className="ach-list">
            {unlocked.map(([id, date]) => (
              <li key={id}>
                <strong>{id}</strong>
                <span>{date.slice(0, 10)}</span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <button type="button" onClick={onBack}>Back to Menu</button>
    </section>
  );
}

export default AchievementsScreen;
