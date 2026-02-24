import type { GameId, GameMeta } from "../types/game";

interface MainMenuProps {
  games: GameMeta[];
  onSelectGame: (gameId: GameId) => void;
  onOpenSettings: () => void;
  onOpenProfile: () => void;
  onOpenAchievements: () => void;
}

function MainMenu({ games, onSelectGame, onOpenSettings, onOpenProfile, onOpenAchievements }: MainMenuProps) {
  return (
    <main className="main-menu">
      <header className="hero">
        <h1>Modern Arcade</h1>
        <p>React conversion in progress. Snake, Tetris, Pong, Flappy, 2048, Connect 4, and Minesweeper are playable now.</p>
      </header>

      <section className="settings-panel quick-nav">
        <button type="button" onClick={onOpenSettings}>Settings</button>
        <button type="button" onClick={onOpenProfile}>Profile</button>
        <button type="button" onClick={onOpenAchievements}>Achievements</button>
      </section>

      <section className="grid">
        {games.map((game) => {
          const isImplemented = game.status === "implemented";
          return (
            <article key={game.id} className="game-card" style={{ borderColor: game.color }}>
              <h3>{game.name}</h3>
              <p>{game.desc}</p>
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
