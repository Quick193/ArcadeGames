import { useEffect, useMemo, useRef, useState } from "react";
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
  const [selectedIndex, setSelectedIndex] = useState(0);
  const cardRefs = useRef<Array<HTMLElement | null>>([]);
  const totalWins = Object.values(stats.games).reduce((sum, g) => sum + g.games_won, 0);
  const unlocked = Object.keys(achievements.unlocked).length;
  const totalAchievements = ACHIEVEMENT_REGISTRY.length;
  const achievementPoints = ACHIEVEMENT_REGISTRY.filter((a) => achievements.unlocked[a.id]).reduce((sum, a) => sum + a.points, 0);
  const overallWinRate = stats.total_games > 0 ? `${Math.floor((totalWins / stats.total_games) * 100)}%` : "0%";
  const playtimeMinutes = Math.max(0, Math.round(stats.global_playtime / 60));

  const favourite = useMemo(() => {
    let bestName = "-";
    let bestPlayed = 0;
    for (const game of games) {
      const played = stats.games[game.id]?.games_played ?? 0;
      if (played > bestPlayed) {
        bestPlayed = played;
        bestName = game.name;
      }
    }
    return bestName;
  }, [games, stats.games]);

  useEffect(() => {
    setSelectedIndex((prev) => {
      if (games.length === 0) {
        return 0;
      }
      return Math.max(0, Math.min(prev, games.length - 1));
    });
  }, [games.length]);

  useEffect(() => {
    const target = cardRefs.current[selectedIndex];
    if (!target) {
      return;
    }
    target.scrollIntoView({ block: "nearest", inline: "nearest" });
  }, [selectedIndex]);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const active = document.activeElement as HTMLElement | null;
      const tag = active?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") {
        return;
      }
      if (games.length === 0) {
        return;
      }

      const key = event.key.toLowerCase();
      const cols = 3;
      if (key === "arrowright") {
        event.preventDefault();
        setSelectedIndex((i) => (i + 1) % games.length);
        return;
      }
      if (key === "arrowleft") {
        event.preventDefault();
        setSelectedIndex((i) => (i + games.length - 1) % games.length);
        return;
      }
      if (key === "arrowdown") {
        event.preventDefault();
        setSelectedIndex((i) => (i + cols) % games.length);
        return;
      }
      if (key === "arrowup") {
        event.preventDefault();
        setSelectedIndex((i) => (i + games.length - cols) % games.length);
        return;
      }
      if (key === "enter" || key === " ") {
        event.preventDefault();
        onSelectGame(games[selectedIndex]!.id);
        return;
      }
      if (key === "s") {
        onOpenSettings();
        return;
      }
      if (key === "a") {
        onOpenAchievements();
        return;
      }
      if (key === "p") {
        onOpenProfile();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [games, onOpenAchievements, onOpenProfile, onOpenSettings, onSelectGame, selectedIndex]);

  return (
    <main className="main-menu">
      <header className="hero">
        <h1>Arcade</h1>
        <p>Select a game to play.</p>
      </header>

      <div className="menu-layout">
        <section className="menu-games">
          <div className="menu-grid">
            {games.map((game, index) => {
              const isImplemented = game.status === "implemented";
              const bestScore = stats.games[game.id]?.best_score ?? 0;
              const played = stats.games[game.id]?.games_played ?? 0;
              const isSelected = index === selectedIndex;

              return (
                <article
                  key={game.id}
                  ref={(node) => {
                    cardRefs.current[index] = node;
                  }}
                  className={`menu-game-card ${isSelected ? "selected" : ""}`}
                  style={{ borderColor: isSelected ? game.color : undefined }}
                  onMouseEnter={() => setSelectedIndex(index)}
                >
                  <div className="menu-game-top">
                    <div className="menu-game-icon" style={{ background: game.color }}>
                      {iconTag(game.id)}
                    </div>
                    <div>
                      <h3>{game.name}</h3>
                      <p>{game.desc}</p>
                    </div>
                  </div>
                  <div className="menu-game-meta">
                    <span>Best: {bestScore > 0 ? bestScore.toLocaleString() : "—"}</span>
                    {played > 0 && <span>x{played}</span>}
                  </div>
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
          </div>
        </section>

        <aside className="settings-block menu-sidebar">
          <h2>{profile.display_name}</h2>

          <div className="menu-stat-list">
            <div>
              <small>Playtime</small>
              <strong>{playtimeMinutes}m</strong>
            </div>
            <div>
              <small>Games</small>
              <strong>{stats.total_games}</strong>
            </div>
            <div>
              <small>Win Rate</small>
              <strong>{overallWinRate}</strong>
            </div>
            <div>
              <small>Favourite</small>
              <strong>{favourite}</strong>
            </div>
          </div>

          <div className="menu-ach-summary">
            <h4>Achievements</h4>
            <p>{unlocked}/{totalAchievements} • {achievementPoints} pts</p>
            <div className="ach-progress">
              <div className="ach-progress-fill" style={{ width: `${totalAchievements > 0 ? Math.round((unlocked / totalAchievements) * 100) : 0}%` }} />
            </div>
          </div>

          <div className="settings-actions">
            <button type="button" onClick={onOpenSettings}>Settings</button>
            <button type="button" onClick={onOpenAchievements}>Achievements</button>
            <button type="button" onClick={onOpenProfile}>Profile</button>
          </div>
        </aside>
      </div>
    </main>
  );
}

function iconTag(gameId: GameId): string {
  const map: Record<GameId, string> = {
    tetris: "TET",
    snake: "SNK",
    pong: "PNG",
    flappy: "FLY",
    chess: "CHS",
    breakout: "BRK",
    memory_match: "MEM",
    neon_blob_dash: "NBD",
    endless_metro_run: "EMR",
    space_invaders: "INV",
    game_2048: "204",
    minesweeper: "MNS",
    connect4: "C4",
    sudoku: "SDK",
    asteroids: "AST"
  };
  return map[gameId];
}

export default MainMenu;
