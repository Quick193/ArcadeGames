import { useMemo, useState } from "react";
import { gameRegistry } from "./data/gameRegistry";
import FlappyGame from "./games/flappy/FlappyGame";
import Game2048 from "./games/game_2048/Game2048";
import PongGame from "./games/pong/PongGame";
import SnakeGame from "./games/snake/SnakeGame";
import TetrisGame from "./games/tetris/TetrisGame";
import MainMenu from "./screens/MainMenu";
import type { GameId, GameMeta } from "./types/game";

function App() {
  const [activeGame, setActiveGame] = useState<GameId | null>(null);

  const selectedGame: GameMeta | null = useMemo(() => {
    if (!activeGame) {
      return null;
    }
    return gameRegistry.find((g) => g.id === activeGame) ?? null;
  }, [activeGame]);

  return (
    <div className="app-shell">
      {!activeGame && (
        <MainMenu
          games={gameRegistry}
          onSelectGame={(gameId) => {
            setActiveGame(gameId);
          }}
        />
      )}

      {activeGame === "snake" && (
        <SnakeGame
          onExit={() => {
            setActiveGame(null);
          }}
        />
      )}

      {activeGame === "tetris" && (
        <TetrisGame
          onExit={() => {
            setActiveGame(null);
          }}
        />
      )}

      {activeGame === "pong" && (
        <PongGame
          onExit={() => {
            setActiveGame(null);
          }}
        />
      )}

      {activeGame === "flappy" && (
        <FlappyGame
          onExit={() => {
            setActiveGame(null);
          }}
        />
      )}

      {activeGame === "game_2048" && (
        <Game2048
          onExit={() => {
            setActiveGame(null);
          }}
        />
      )}

      {activeGame && activeGame !== "snake" && activeGame !== "tetris" && activeGame !== "pong" && activeGame !== "flappy" && activeGame !== "game_2048" && selectedGame && (
        <section className="coming-soon">
          <h2>{selectedGame.name}</h2>
          <p>{selectedGame.desc}</p>
          <p>This game is queued for conversion from the Python version.</p>
          <button
            type="button"
            onClick={() => {
              setActiveGame(null);
            }}
          >
            Back to Menu
          </button>
        </section>
      )}
    </div>
  );
}

export default App;
