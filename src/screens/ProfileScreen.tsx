import type { ProfileData } from "../types/profile";
import type { StatsData } from "../types/stats";

interface ProfileScreenProps {
  profile: ProfileData;
  stats: StatsData;
  onBack: () => void;
}

function ProfileScreen({ profile, stats, onBack }: ProfileScreenProps) {
  const games = Object.entries(stats.games).sort((a, b) => b[1].games_played - a[1].games_played);

  return (
    <section className="profile-screen">
      <header className="hero">
        <h1>Profile</h1>
        <p>{profile.display_name}</p>
      </header>

      <section className="settings-block">
        <h3>Global Stats</h3>
        <p>Total Games: {stats.total_games}</p>
        <p>Total Playtime: {Math.round(stats.global_playtime / 60)}m</p>
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
              </tr>
            </thead>
            <tbody>
              {games.map(([id, g]) => (
                <tr key={id}>
                  <td>{id}</td>
                  <td>{g.games_played}</td>
                  <td>{g.games_won}</td>
                  <td>{g.best_score}</td>
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
