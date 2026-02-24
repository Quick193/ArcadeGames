import { useMemo, useState } from "react";
import { gameRegistry } from "./data/gameRegistry";
import FlappyGame from "./games/flappy/FlappyGame";
import Game2048 from "./games/game_2048/Game2048";
import Connect4Game from "./games/connect4/Connect4Game";
import MinesweeperGame from "./games/minesweeper/MinesweeperGame";
import PongGame from "./games/pong/PongGame";
import SnakeGame from "./games/snake/SnakeGame";
import TetrisGame from "./games/tetris/TetrisGame";
import AchievementsScreen from "./screens/AchievementsScreen";
import MainMenu from "./screens/MainMenu";
import ProfileScreen from "./screens/ProfileScreen";
import SettingsScreen from "./screens/SettingsScreen";
import { readAchievements } from "./services/storage/achievementsStorage";
import { readProfile } from "./services/storage/profileStorage";
import { readSettings, writeSettings } from "./services/storage/settingsStorage";
import { readStats } from "./services/storage/statsStorage";
import type { GameId, GameMeta } from "./types/game";

type View = "menu" | "settings" | "profile" | "achievements";

function App() {
  const [activeGame, setActiveGame] = useState<GameId | null>(null);
  const [view, setView] = useState<View>("menu");
  const [settings, setSettings] = useState(() => readSettings());
  const [profile] = useState(() => readProfile());
  const [stats] = useState(() => readStats());
  const [achievements] = useState(() => readAchievements());

  const selectedGame: GameMeta | null = useMemo(() => {
    if (!activeGame) {
      return null;
    }
    return gameRegistry.find((g) => g.id === activeGame) ?? null;
  }, [activeGame]);

  const controlScheme = settings.mobile_control_scheme;

  return (
    <div className="app-shell">
      {!activeGame && view === "menu" && (
        <MainMenu
          games={gameRegistry}
          onOpenSettings={() => setView("settings")}
          onOpenProfile={() => setView("profile")}
          onOpenAchievements={() => setView("achievements")}
          onSelectGame={(gameId) => {
            setActiveGame(gameId);
          }}
        />
      )}

      {!activeGame && view === "settings" && (
        <SettingsScreen
          settings={settings}
          onChange={(next) => {
            setSettings(next);
            writeSettings(next);
          }}
          onBack={() => setView("menu")}
        />
      )}

      {!activeGame && view === "profile" && (
        <ProfileScreen profile={profile} stats={stats} onBack={() => setView("menu")} />
      )}

      {!activeGame && view === "achievements" && (
        <AchievementsScreen achievements={achievements} onBack={() => setView("menu")} />
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

      {activeGame === "connect4" && (
        <Connect4Game
          controlScheme={controlScheme}
          onExit={() => {
            setActiveGame(null);
          }}
        />
      )}

      {activeGame === "minesweeper" && (
        <MinesweeperGame
          controlScheme={controlScheme}
          onExit={() => {
            setActiveGame(null);
          }}
        />
      )}

      {activeGame && activeGame !== "snake" && activeGame !== "tetris" && activeGame !== "pong" && activeGame !== "flappy" && activeGame !== "game_2048" && activeGame !== "connect4" && activeGame !== "minesweeper" && selectedGame && (
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
