import type { GameId, GameMeta } from "../types/game";
import type { ControlScheme } from "../types/settings";

interface MainMenuProps {
  games: GameMeta[];
  onSelectGame: (gameId: GameId) => void;
  controlScheme: ControlScheme;
  onControlSchemeChange: (scheme: ControlScheme) => void;
}

function MainMenu({ games, onSelectGame, controlScheme, onControlSchemeChange }: MainMenuProps) {
  return (
    <main className="main-menu">
      <header className="hero">
        <h1>Modern Arcade</h1>
        <p>React conversion in progress. Snake, Tetris, Pong, Flappy, and 2048 are playable now.</p>
      </header>

      <section className="settings-panel">
        <h2>Controls</h2>
        <p>Choose mobile input style for all games.</p>
        <div className="segmented">
          <button
            type="button"
            className={controlScheme === "buttons" ? "active" : ""}
            onClick={() => onControlSchemeChange("buttons")}
          >
            Buttons
          </button>
          <button
            type="button"
            className={controlScheme === "gestures" ? "active" : ""}
            onClick={() => onControlSchemeChange("gestures")}
          >
            Gestures
          </button>
        </div>
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
