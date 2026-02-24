import { useMemo, useState } from "react";
import { gameRegistry } from "./data/gameRegistry";
import FlappyGame from "./games/flappy/FlappyGame";
import Game2048 from "./games/game_2048/Game2048";
import PongGame from "./games/pong/PongGame";
import SnakeGame from "./games/snake/SnakeGame";
import TetrisGame from "./games/tetris/TetrisGame";
import MainMenu from "./screens/MainMenu";
import type { GameId, GameMeta } from "./types/game";
import type { ControlScheme } from "./types/settings";

function App() {
  const [activeGame, setActiveGame] = useState<GameId | null>(null);
  const [controlScheme, setControlScheme] = useState<ControlScheme>(() => readControlScheme());

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
          controlScheme={controlScheme}
          onControlSchemeChange={(scheme) => {
            setControlScheme(scheme);
            writeControlScheme(scheme);
          }}
          onSelectGame={(gameId) => {
            setActiveGame(gameId);
          }}
        />
      )}

      {activeGame === "snake" && (
        <SnakeGame
          controlScheme={controlScheme}
          onExit={() => {
            setActiveGame(null);
          }}
        />
      )}

      {activeGame === "tetris" && (
        <TetrisGame
          controlScheme={controlScheme}
          onExit={() => {
            setActiveGame(null);
          }}
        />
      )}

      {activeGame === "pong" && (
        <PongGame
          controlScheme={controlScheme}
          onExit={() => {
            setActiveGame(null);
          }}
        />
      )}

      {activeGame === "flappy" && (
        <FlappyGame
          controlScheme={controlScheme}
          onExit={() => {
            setActiveGame(null);
          }}
        />
      )}

      {activeGame === "game_2048" && (
        <Game2048
          controlScheme={controlScheme}
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

function readControlScheme(): ControlScheme {
  const raw = window.localStorage.getItem("arcade.controls.scheme");
  return raw === "gestures" ? "gestures" : "buttons";
}

function writeControlScheme(scheme: ControlScheme): void {
  window.localStorage.setItem("arcade.controls.scheme", scheme);
}

export default App;
