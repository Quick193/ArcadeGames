import type { ProfileData } from "../types/profile";
import type { StatsData } from "../types/stats";
import { GAME_DISPLAY_NAMES, KNOWN_GAMES } from "../data/gameDisplayNames";
import type { AchievementsData } from "../services/storage/achievementsStorage";
import { ACHIEVEMENT_REGISTRY } from "../data/achievementsRegistry";

interface ProfileScreenProps {
  profile: ProfileData;
  stats: StatsData;
  achievements: AchievementsData;
  onChangeProfile: (next: ProfileData) => void;
  onBack: () => void;
}

function ProfileScreen({ profile, stats, achievements, onChangeProfile, onBack }: ProfileScreenProps) {
  const games = KNOWN_GAMES.map((id) => {
    const g = stats.games[id];
    const played = g?.games_played ?? 0;
    const won = g?.games_won ?? 0;
    const best = g?.best_score ?? 0;
    const streak = g?.best_streak ?? 0;
    const playtime = g?.total_playtime ?? 0;
    const winRate = played > 0 ? `${Math.floor((won / played) * 100)}%` : "0%";
    return { id, name: GAME_DISPLAY_NAMES[id] ?? id, played, won, best, streak, winRate, playtime };
  }).sort((a, b) => b.played - a.played || a.name.localeCompare(b.name));

  const totalWins = games.reduce((sum, g) => sum + g.won, 0);
  const overallWinRate = stats.total_games > 0 ? `${Math.floor((totalWins / stats.total_games) * 100)}%` : "0%";
  const favourite = games.find((g) => g.played > 0)?.name ?? "-";
  const totalSeconds = Math.max(0, Math.floor(stats.global_playtime));
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const playtimeFormatted = hours > 0 ? `${hours}h ${String(minutes).padStart(2, "0")}m` : `${minutes}m`;
  const unlockedCount = Object.keys(achievements.unlocked).length;
  const totalAchievements = ACHIEVEMENT_REGISTRY.length;
  const achievementPoints = ACHIEVEMENT_REGISTRY.filter((a) => achievements.unlocked[a.id]).reduce((sum, a) => sum + a.points, 0);
  const achievementProgress = totalAchievements > 0 ? Math.round((unlockedCount / totalAchievements) * 100) : 0;

  return (
    <section className="profile-screen">
      <header className="hero">
        <h1>Profile</h1>
        <p>{profile.display_name}</p>
      </header>

      <section className="settings-block">
        <h3>Identity</h3>
        <label className="setting-row">
          <span>Name</span>
          <input
            type="text"
            maxLength={24}
            value={profile.display_name}
            onChange={(e) => {
              const value = e.target.value.slice(0, 24);
              onChangeProfile({ ...profile, display_name: value || "Player 1" });
            }}
          />
        </label>
        <label className="setting-row">
          <span>Avatar Index</span>
          <input
            type="range"
            min={0}
            max={7}
            step={1}
            value={profile.avatar_index}
            onChange={(e) => onChangeProfile({ ...profile, avatar_index: Number(e.target.value) })}
          />
        </label>
      </section>

      <section className="settings-block">
        <h3>Global Stats</h3>
        <p>Total Games: {stats.total_games}</p>
        <p>Total Wins: {totalWins}</p>
        <p>Win Rate: {overallWinRate}</p>
        <p>Total Playtime: {playtimeFormatted}</p>
        <p>Favourite Game: {favourite}</p>
      </section>

      <section className="settings-block">
        <h3>Achievements</h3>
        <p>Unlocked: {unlockedCount}/{totalAchievements}</p>
        <p>Points: {achievementPoints}</p>
        <p>Progress: {achievementProgress}%</p>
        <div className="ach-progress">
          <div className="ach-progress-fill" style={{ width: `${achievementProgress}%` }} />
        </div>
      </section>

      <section className="settings-block">
        <h3>Per Game</h3>
        <div className="table-wrap">
          <table className="stats-table">
            <thead>
              <tr>
                <th>Game</th>
                <th>Played</th>
                <th>Won</th>
                <th>Best</th>
                <th>Streak</th>
                <th>Win Rate</th>
                <th>Playtime</th>
              </tr>
            </thead>
            <tbody>
              {games.map((g) => (
                <tr key={g.id}>
                  <td>{g.name}</td>
                  <td>{g.played}</td>
                  <td>{g.won}</td>
                  <td>{g.best > 0 ? g.best : "—"}</td>
                  <td>{g.streak > 0 ? g.streak : "—"}</td>
                  <td>{g.winRate}</td>
                  <td>{Math.round(g.playtime / 60)}m</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <button type="button" onClick={onBack}>Back to Menu</button>
    </section>
  );
}

export default ProfileScreen;
