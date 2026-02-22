"""
systems/profile.py
------------------
PlayerProfile: The player's identity and aggregated stats view.

PlayerProfile wraps StatsTracker and adds:
  | Display name
  | Total playtime formatted as "3h 42m"
  | Favourite game (most played)
  | Overall win rate across all games
  | Per-game best score access

The profile is the source of truth for the profile screen UI.
It does NOT duplicate stats storage - it reads from StatsTracker.

Usage
-----
    from systems.profile import PlayerProfile
    from systems.stats   import StatsTracker

    stats   = StatsTracker()
    profile = PlayerProfile(stats)

    print(profile.display_name)           # "Player 1"
    print(profile.playtime_formatted)     # "3h 42m"
    print(profile.favourite_game)         # "tetris"
    print(profile.overall_win_rate)       # 0.62
    print(profile.best_score("tetris"))   # 18400

    profile.set_name("Arcade Pro")

Profile file: data/profile.json
"""

import json
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from systems.stats import StatsTracker

DATA_DIR  = os.path.join(os.path.dirname(__file__), "..", "data")
SAVE_PATH = os.path.join(DATA_DIR, "profile.json")

KNOWN_GAMES = [
    "tetris", "snake", "pong", "flappy", "chess",
    "breakout", "memory_match", "neon_blob_dash",
    "endless_metro_run", "space_invaders", "game_2048",
    "minesweeper", "connect4", "sudoku", "asteroids",
]

# Human-readable game names for the profile screen
GAME_DISPLAY_NAMES = {
    "tetris":           "Tetris",
    "snake":            "Snake",
    "pong":             "Pong",
    "flappy":           "Flappy Bird",
    "chess":            "Chess",
    "breakout":         "Breakout",
    "memory_match":     "Memory Match",
    "neon_blob_dash":   "Neon Blob Dash",
    "endless_metro_run":"Endless Metro Run",
    "space_invaders":   "Space Invaders",
    "game_2048":        "2048",
    "minesweeper":      "Minesweeper",
    "connect4":         "Connect 4",
    "sudoku":           "Sudoku",
    "asteroids":        "Asteroids",
}


class PlayerProfile:
    """
    Player identity and derived stats.  Reads live data from StatsTracker.
    Persists only: display_name, avatar_index.
    """

    def __init__(self, stats: "StatsTracker", path: str = SAVE_PATH) -> None:
        self._stats = stats
        self._path = path
        self._display_name: str = "Player 1"
        self._avatar_index: int = 0
        self._load()

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    @property
    def display_name(self) -> str:
        return self._display_name

    def set_name(self, name: str) -> None:
        name = name.strip()[:24]  # max 24 chars
        if name:
            self._display_name = name
            self._save()

    @property
    def avatar_index(self) -> int:
        return self._avatar_index

    def set_avatar(self, index: int) -> None:
        self._avatar_index = max(0, index)
        self._save()

    # ------------------------------------------------------------------
    # Derived stats (live - reads from StatsTracker each time)
    # ------------------------------------------------------------------

    @property
    def playtime_formatted(self) -> str:
        """Return total playtime as a human-readable string: '3h 42m' or '45m'."""
        total_seconds = int(self._stats.total_playtime())
        hours   = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        if hours > 0:
            return f"{hours}h {minutes:02d}m"
        return f"{minutes}m"

    @property
    def playtime_seconds(self) -> float:
        return self._stats.total_playtime()

    @property
    def total_games_played(self) -> int:
        return self._stats.global_summary()["total_games"]

    @property
    def total_wins(self) -> int:
        return self._stats.global_summary()["total_wins"]

    @property
    def overall_win_rate(self) -> float:
        """Overall win rate across all games.  0.0 if no games played."""
        summary = self._stats.global_summary()
        played = summary["total_games"]
        if played == 0:
            return 0.0
        return summary["total_wins"] / played

    @property
    def overall_win_rate_pct(self) -> str:
        """Win rate as a percentage string: '62%'."""
        return f"{int(self.overall_win_rate * 100)}%"

    @property
    def favourite_game(self) -> str | None:
        """
        Game ID of the most-played game.
        Returns None if no games have been played yet.
        """
        best_id, best_count = None, 0
        for gid in KNOWN_GAMES:
            count = self._stats.games_played(gid)
            if count > best_count:
                best_count = count
                best_id = gid
        return best_id

    @property
    def favourite_game_name(self) -> str:
        gid = self.favourite_game
        if gid is None:
            return "-"
        return GAME_DISPLAY_NAMES.get(gid, gid.replace("_", " ").title())

    def best_score(self, game_id: str) -> int:
        return self._stats.best_score(game_id)

    def games_played(self, game_id: str) -> int:
        return self._stats.games_played(game_id)

    def win_rate(self, game_id: str) -> str:
        """Win rate for one game as a percentage string."""
        return f"{int(self._stats.win_rate(game_id) * 100)}%"

    def best_streak(self, game_id: str) -> int:
        return self._stats.best_streak(game_id)

    # ------------------------------------------------------------------
    # Full profile snapshot (for the profile screen UI)
    # ------------------------------------------------------------------

    def full_snapshot(self) -> dict:
        """
        Return a complete dict with all profile + per-game stats,
        ready to be displayed in the profile screen.
        """
        games = {}
        for gid in KNOWN_GAMES:
            played = self._stats.games_played(gid)
            games[gid] = {
                "name":          GAME_DISPLAY_NAMES.get(gid, gid),
                "played":        played,
                "won":           self._stats.games_won(gid),
                "best_score":    self._stats.best_score(gid),
                "best_streak":   self._stats.best_streak(gid),
                "win_rate_pct":  self.win_rate(gid),
                "playtime_secs": self._stats.game_playtime(gid),
            }

        return {
            "display_name":       self.display_name,
            "avatar_index":       self.avatar_index,
            "total_games":        self.total_games_played,
            "total_wins":         self.total_wins,
            "overall_win_rate":   self.overall_win_rate_pct,
            "playtime_formatted": self.playtime_formatted,
            "favourite_game":     self.favourite_game_name,
            "games":              games,
        }

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            self._display_name = str(raw.get("display_name", "Player 1"))[:24]
            self._avatar_index = int(raw.get("avatar_index", 0))
        except (FileNotFoundError, json.JSONDecodeError, IOError):
            pass

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        tmp = self._path + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump({
                    "display_name": self._display_name,
                    "avatar_index": self._avatar_index,
                }, f, indent=2)
            os.replace(tmp, self._path)
        except IOError:
            pass

    def __repr__(self) -> str:
        return (
            f"PlayerProfile(name='{self._display_name}', "
            f"played={self.total_games_played}, "
            f"playtime='{self.playtime_formatted}')"
        )
