import type { GameId, GameMeta } from "../types/game";
import type { ProfileData } from "../types/profile";
import type { StatsData } from "../types/stats";
import type { AchievementsData } from "../services/storage/achievementsStorage";
import { ACHIEVEMENT_REGISTRY } from "../data/achievementsRegistry";

interface MainMenuProps {
  games: GameMeta[];
  profile: ProfileData;
  stats: StatsData;
  achievements: AchievementsData;
  onSelectGame: (gameId: GameId) => void;
  onOpenSettings: () => void;
  onOpenProfile: () => void;
  onOpenAchievements: () => void;
}

function MainMenu({
  games,
  profile,
  stats,
  achievements,
  onSelectGame,
  onOpenSettings,
  onOpenProfile,
  onOpenAchievements
}: MainMenuProps) {
  const totalWins = Object.values(stats.games).reduce((sum, g) => sum + g.games_won, 0);
  const unlocked = Object.keys(achievements.unlocked).length;
  const totalAchievements = ACHIEVEMENT_REGISTRY.length;
  return (
    <main className="main-menu">
      <header className="hero">
        <h1>Modern Arcade</h1>
        <p>Mobile-first React port. All original titles are now available with touch controls and settings.</p>
      </header>

      <section className="settings-panel quick-nav">
        <button type="button" onClick={onOpenSettings}>Settings</button>
        <button type="button" onClick={onOpenProfile}>Profile</button>
        <button type="button" onClick={onOpenAchievements}>Achievements</button>
      </section>

      <section className="settings-panel">
        <h2>{profile.display_name}</h2>
        <p>
          Games {stats.total_games} • Wins {totalWins} • Playtime {Math.round(stats.global_playtime / 60)}m
        </p>
        <p>
          Achievements {unlocked}/{totalAchievements}
        </p>
      </section>

      <section className="grid">
        {games.map((game) => {
          const isImplemented = game.status === "implemented";
          const bestScore = stats.games[game.id]?.best_score ?? 0;
          return (
            <article key={game.id} className="game-card" style={{ borderColor: game.color }}>
              <h3>{game.name}</h3>
              <p>{game.desc}</p>
              <p className="game-meta">Best Score: {bestScore > 0 ? bestScore.toLocaleString() : "—"}</p>
              <button
                type="button"
                onClick={() => {
                  onSelectGame(game.id);
                }}
              >
                {isImplemented ? "Play" : "Open Placeholder"}
              </button>
            </article>
          );
        })}
      </section>
    </main>
  );
}

export default MainMenu;
