import { useEffect, useMemo, useState } from "react";
import AchievementToasts from "./components/ui/AchievementToasts";
import { ACHIEVEMENT_REGISTRY } from "./data/achievementsRegistry";
import { gameRegistry } from "./data/gameRegistry";
import { applyTheme } from "./data/themePalettes";
import FlappyGame from "./games/flappy/FlappyGame";
import Game2048 from "./games/game_2048/Game2048";
import Connect4Game from "./games/connect4/Connect4Game";
import MinesweeperGame from "./games/minesweeper/MinesweeperGame";
import PongGame from "./games/pong/PongGame";
import SnakeGame from "./games/snake/SnakeGame";
import TetrisGame from "./games/tetris/TetrisGame";
import BreakoutGame from "./games/breakout/BreakoutGame";
import MemoryMatchGame from "./games/memory_match/MemoryMatchGame";
import SudokuGame from "./games/sudoku/SudokuGame";
import ChessGame from "./games/chess/ChessGame";
import SpaceInvadersGame from "./games/space_invaders/SpaceInvadersGame";
import AsteroidsGame from "./games/asteroids/AsteroidsGame";
import NeonBlobDashGame from "./games/neon_blob_dash/NeonBlobDashGame";
import EndlessMetroRunGame from "./games/endless_metro_run/EndlessMetroRunGame";
import AchievementsScreen from "./screens/AchievementsScreen";
import MainMenu from "./screens/MainMenu";
import ProfileScreen from "./screens/ProfileScreen";
import SettingsScreen from "./screens/SettingsScreen";
import { readAchievements, resetAchievements } from "./services/storage/achievementsStorage";
import { ACHIEVEMENT_UNLOCK_EVENT } from "./services/progression/progressionService";
import { readProfile, resetProfile, writeProfile } from "./services/storage/profileStorage";
import { readSettings, writeSettings } from "./services/storage/settingsStorage";
import { readStats, resetStats } from "./services/storage/statsStorage";
import type { GameId, GameMeta } from "./types/game";

type View = "menu" | "settings" | "profile" | "achievements";

function App() {
  const [activeGame, setActiveGame] = useState<GameId | null>(null);
  const [view, setView] = useState<View>("menu");
  const [settings, setSettings] = useState(() => readSettings());
  const [profile, setProfile] = useState(() => readProfile());
  const [stats, setStats] = useState(() => readStats());
  const [achievements, setAchievements] = useState(() => readAchievements());
  const [toastItems, setToastItems] = useState<Array<{ key: string; name: string; points: number; color: string }>>([]);

  const refreshData = () => {
    setProfile(readProfile());
    setStats(readStats());
    setAchievements(readAchievements());
  };

  useEffect(() => {
    if (!settings.reset_on_start) {
      return;
    }
    setStats(resetStats());
    setAchievements(resetAchievements());
    setProfile(resetProfile());
  }, [settings.reset_on_start]);

  useEffect(() => {
    applyTheme(settings.theme);
  }, [settings.theme]);

  useEffect(() => {
    const active = Boolean(activeGame);
    document.body.classList.toggle("game-active", active);
    return () => {
      document.body.classList.remove("game-active");
    };
  }, [activeGame]);

  useEffect(() => {
    const onUnlocked = (event: Event) => {
      const custom = event as CustomEvent<{ ids?: string[] }>;
      const ids = custom.detail?.ids ?? [];
      if (ids.length === 0) {
        return;
      }
      const next = ids
        .map((id) => ACHIEVEMENT_REGISTRY.find((a) => a.id === id))
        .filter((a): a is (typeof ACHIEVEMENT_REGISTRY)[number] => Boolean(a))
        .map((a, idx) => ({
          key: `${a.id}-${Date.now()}-${idx}`,
          name: a.name,
          points: a.points,
          color: a.color
        }));
      if (next.length === 0) {
        return;
      }
      setAchievements(readAchievements());
      setToastItems((prev) => [...prev, ...next].slice(-5));
      window.setTimeout(() => {
        setToastItems((prev) => prev.filter((t) => !next.some((n) => n.key === t.key)));
      }, 3600);
    };

    window.addEventListener(ACHIEVEMENT_UNLOCK_EVENT, onUnlocked as EventListener);
    return () => {
      window.removeEventListener(ACHIEVEMENT_UNLOCK_EVENT, onUnlocked as EventListener);
    };
  }, []);

  const selectedGame: GameMeta | null = useMemo(() => {
    if (!activeGame) {
      return null;
    }
    return gameRegistry.find((g) => g.id === activeGame) ?? null;
  }, [activeGame]);

  const controlScheme = settings.mobile_control_scheme;

  return (
    <div className="app-shell">
      <AchievementToasts items={toastItems} />
      {!activeGame && view === "menu" && (
        <MainMenu
          games={gameRegistry}
          profile={profile}
          stats={stats}
          achievements={achievements}
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
          onResetStats={() => {
            setStats(resetStats());
          }}
          onResetAchievements={() => {
            setAchievements(resetAchievements());
          }}
          onResetAll={() => {
            setStats(resetStats());
            setAchievements(resetAchievements());
            setProfile(resetProfile());
          }}
          onBack={() => {
            refreshData();
            setView("menu");
          }}
        />
      )}

      {!activeGame && view === "profile" && (
        <ProfileScreen
          profile={profile}
          stats={stats}
          achievements={achievements}
          onChangeProfile={(next) => {
            setProfile(next);
            writeProfile(next);
          }}
          onBack={() => setView("menu")}
        />
      )}

      {!activeGame && view === "achievements" && (
        <AchievementsScreen achievements={achievements} onBack={() => setView("menu")} />
      )}

      {activeGame === "snake" && (
        <SnakeGame
          controlScheme={controlScheme}
          onExit={() => {
            refreshData();
            setActiveGame(null);
          }}
        />
      )}

      {activeGame === "tetris" && (
        <TetrisGame
          controlScheme={controlScheme}
          onExit={() => {
            refreshData();
            setActiveGame(null);
          }}
        />
      )}

      {activeGame === "pong" && (
        <PongGame
          controlScheme={controlScheme}
          onExit={() => {
            refreshData();
            setActiveGame(null);
          }}
        />
      )}

      {activeGame === "flappy" && (
        <FlappyGame
          controlScheme={controlScheme}
          onExit={() => {
            refreshData();
            setActiveGame(null);
          }}
        />
      )}

      {activeGame === "game_2048" && (
        <Game2048
          controlScheme={controlScheme}
          onExit={() => {
            refreshData();
            setActiveGame(null);
          }}
        />
      )}

      {activeGame === "connect4" && (
        <Connect4Game
          controlScheme={controlScheme}
          onExit={() => {
            refreshData();
            setActiveGame(null);
          }}
        />
      )}

      {activeGame === "minesweeper" && (
        <MinesweeperGame
          controlScheme={controlScheme}
          onExit={() => {
            refreshData();
            setActiveGame(null);
          }}
        />
      )}

      {activeGame === "breakout" && (
        <BreakoutGame
          controlScheme={controlScheme}
          onExit={() => {
            refreshData();
            setActiveGame(null);
          }}
        />
      )}

      {activeGame === "memory_match" && (
        <MemoryMatchGame
          controlScheme={controlScheme}
          onExit={() => {
            refreshData();
            setActiveGame(null);
          }}
        />
      )}

      {activeGame === "sudoku" && (
        <SudokuGame
          controlScheme={controlScheme}
          onExit={() => {
            refreshData();
            setActiveGame(null);
          }}
        />
      )}

      {activeGame === "chess" && (
        <ChessGame
          controlScheme={controlScheme}
          onExit={() => {
            refreshData();
            setActiveGame(null);
          }}
        />
      )}

      {activeGame === "space_invaders" && (
        <SpaceInvadersGame
          controlScheme={controlScheme}
          onExit={() => {
            refreshData();
            setActiveGame(null);
          }}
        />
      )}

      {activeGame === "asteroids" && (
        <AsteroidsGame
          controlScheme={controlScheme}
          onExit={() => {
            refreshData();
            setActiveGame(null);
          }}
        />
      )}

      {activeGame === "neon_blob_dash" && (
        <NeonBlobDashGame
          controlScheme={controlScheme}
          onExit={() => {
            refreshData();
            setActiveGame(null);
          }}
        />
      )}

      {activeGame === "endless_metro_run" && (
        <EndlessMetroRunGame
          controlScheme={controlScheme}
          onExit={() => {
            refreshData();
            setActiveGame(null);
          }}
        />
      )}

      {activeGame &&
        activeGame !== "snake" &&
        activeGame !== "tetris" &&
        activeGame !== "pong" &&
        activeGame !== "flappy" &&
        activeGame !== "game_2048" &&
        activeGame !== "connect4" &&
        activeGame !== "minesweeper" &&
        activeGame !== "breakout" &&
        activeGame !== "memory_match" &&
        activeGame !== "sudoku" &&
        activeGame !== "chess" &&
        activeGame !== "space_invaders" &&
        activeGame !== "asteroids" &&
        activeGame !== "neon_blob_dash" &&
        activeGame !== "endless_metro_run" &&
        selectedGame && (
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
