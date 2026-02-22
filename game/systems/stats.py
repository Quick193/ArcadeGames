"""
systems/stats.py
----------------
StatsTracker: Records and persists per-game and global gameplay statistics.

Every game calls into this system to record outcomes.  The tracker stores:
  | Best score per game
  | Games played / won / lost per game
  | Total playtime (seconds) per game and globally
  | Current and longest win streaks per game
  | Game-specific extra stats (e.g. Tetris lines cleared, Chess captures)

All data is persisted to data/stats.json.

Usage
-----
    from systems.stats import StatsTracker

    t = StatsTracker()

    # After a game ends
    t.record_game("tetris", score=4200, won=True, duration=180.0,
                  extra={"lines": 32, "level": 8})

    # Read stats
    best = t.best_score("tetris")       # > 4200
    played = t.games_played("tetris")   # > 1
    playtime = t.total_playtime()       # > 180.0 (seconds, all games)

    # Leaderboard-style top scores
    top = t.top_scores("tetris", n=5)   # > [{"score":4200, "date":"..."}]

Stats file: data/stats.json
"""

import json
import os
import time
from copy import deepcopy
from datetime import datetime
from typing import Any

DATA_DIR  = os.path.join(os.path.dirname(__file__), "..", "data")
SAVE_PATH = os.path.join(DATA_DIR, "stats.json")

# Maximum number of top-score entries to keep per game
MAX_TOP_SCORES = 10

# Known game IDs - new ones are accepted dynamically (plugin support)
KNOWN_GAMES = [
    "tetris", "snake", "pong", "flappy", "chess",
    "breakout", "memory_match", "neon_blob_dash",
    "endless_metro_run", "space_invaders", "game_2048",
    "minesweeper", "connect4",
]


def _empty_game_stats() -> dict:
    return {
        "games_played":   0,
        "games_won":      0,
        "games_lost":     0,
        "best_score":     0,
        "total_playtime": 0.0,   # seconds
        "current_streak": 0,
        "best_streak":    0,
        "top_scores":     [],    # list of {"score": int, "date": str, "extra": dict}
        "extra":          {},    # game-specific cumulative stats
    }


class StatsTracker:
    """
    Tracks gameplay statistics for all games.
    Thread-safe writes via atomic file replace.
    """

    def __init__(self, path: str = SAVE_PATH) -> None:
        self._path = path
        self._data: dict[str, Any] = {
            "games":          {},   # game_id > _empty_game_stats()
            "global_playtime": 0.0,
            "total_games":    0,
            "first_play":     None,
            "last_play":      None,
        }
        self._load()

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def record_game(
        self,
        game_id: str,
        score: int = 0,
        won: bool = False,
        duration: float = 0.0,
        extra: dict | None = None,
    ) -> dict:
        """
        Record the outcome of a completed game session.

        Parameters
        ----------
        game_id  : str   - e.g. "tetris"
        score    : int   - final score (0 if not applicable)
        won      : bool  - whether the player won
        duration : float - session duration in seconds
        extra    : dict  - game-specific stats (lines cleared, captures, etc.)

        Returns
        -------
        dict with keys: new_best (bool), streak_broken (bool), streak (int)
        """
        extra = extra or {}
        gs = self._ensure_game(game_id)

        # Counts
        gs["games_played"]      += 1
        self._data["total_games"] += 1

        if won:
            gs["games_won"]      += 1
            gs["current_streak"] += 1
            gs["best_streak"] = max(gs["best_streak"], gs["current_streak"])
            streak_broken = False
        else:
            gs["games_lost"]     += 1
            streak_broken        = gs["current_streak"] > 0
            gs["current_streak"] = 0

        # Playtime
        gs["total_playtime"]             += duration
        self._data["global_playtime"]    += duration

        # Timestamps
        now = datetime.now().isoformat(timespec="seconds")
        if self._data["first_play"] is None:
            self._data["first_play"] = now
        self._data["last_play"] = now

        # Best score
        new_best = score > gs["best_score"]
        if new_best:
            gs["best_score"] = score

        # Top scores list (keep top MAX_TOP_SCORES)
        entry = {"score": score, "date": now, "extra": extra}
        gs["top_scores"].append(entry)
        gs["top_scores"].sort(key=lambda e: e["score"], reverse=True)
        gs["top_scores"] = gs["top_scores"][:MAX_TOP_SCORES]

        # Cumulative extra stats (integer fields only)
        for k, v in extra.items():
            if isinstance(v, (int, float)):
                gs["extra"][k] = gs["extra"].get(k, 0) + v

        self._save()

        return {
            "new_best":     new_best,
            "streak_broken": streak_broken,
            "streak":       gs["current_streak"],
        }

    def add_playtime(self, game_id: str, seconds: float) -> None:
        """
        Add incremental playtime without recording a full game result.
        Useful for tracking time even on mid-game exits.
        """
        gs = self._ensure_game(game_id)
        gs["total_playtime"]          += seconds
        self._data["global_playtime"] += seconds
        self._save()

    # ------------------------------------------------------------------
    # Reading
    # ------------------------------------------------------------------

    def best_score(self, game_id: str) -> int:
        return self._ensure_game(game_id)["best_score"]

    def games_played(self, game_id: str) -> int:
        return self._ensure_game(game_id)["games_played"]

    def games_won(self, game_id: str) -> int:
        return self._ensure_game(game_id)["games_won"]

    def win_rate(self, game_id: str) -> float:
        """Return win rate as a float 0.0–1.0.  Returns 0.0 if no games played."""
        gs = self._ensure_game(game_id)
        if gs["games_played"] == 0:
            return 0.0
        return gs["games_won"] / gs["games_played"]

    def best_streak(self, game_id: str) -> int:
        return self._ensure_game(game_id)["best_streak"]

    def current_streak(self, game_id: str) -> int:
        return self._ensure_game(game_id)["current_streak"]

    def game_playtime(self, game_id: str) -> float:
        """Return total playtime for one game in seconds."""
        return self._ensure_game(game_id)["total_playtime"]

    def total_playtime(self) -> float:
        """Return total playtime across all games in seconds."""
        return self._data["global_playtime"]

    def top_scores(self, game_id: str, n: int = MAX_TOP_SCORES) -> list[dict]:
        """Return up to *n* top score entries, sorted high>low."""
        return self._ensure_game(game_id)["top_scores"][:n]

    def extra_stat(self, game_id: str, key: str, default: Any = 0) -> Any:
        """Return a cumulative extra stat (e.g. total lines cleared in Tetris)."""
        return self._ensure_game(game_id)["extra"].get(key, default)

    def summary(self, game_id: str) -> dict:
        """Return a full stats snapshot for one game."""
        return deepcopy(self._ensure_game(game_id))

    def global_summary(self) -> dict:
        """Return high-level stats across all games."""
        total_played = sum(
            gs["games_played"] for gs in self._data["games"].values()
        )
        total_won = sum(
            gs["games_won"] for gs in self._data["games"].values()
        )
        distinct = sum(
            1 for gs in self._data["games"].values()
            if gs["games_played"] > 0
        )
        return {
            "total_games":          total_played,
            "total_wins":           total_won,
            "distinct_games_played": distinct,
            "global_playtime":      self._data["global_playtime"],
            "first_play":           self._data["first_play"],
            "last_play":            self._data["last_play"],
        }

    def reset_game(self, game_id: str) -> None:
        """Reset all stats for one game."""
        self._data["games"][game_id] = _empty_game_stats()
        self._save()

    def reset_all(self) -> None:
        """Wipe all stats."""
        self._data = {
            "games":          {},
            "global_playtime": 0.0,
            "total_games":    0,
            "first_play":     None,
            "last_play":      None,
        }
        self._save()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _ensure_game(self, game_id: str) -> dict:
        """Return stats dict for *game_id*, creating it if absent."""
        if game_id not in self._data["games"]:
            self._data["games"][game_id] = _empty_game_stats()
        return self._data["games"][game_id]

    def _load(self) -> None:
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            # Deep-merge: preserve all keys from DEFAULTS
            self._data["global_playtime"] = raw.get("global_playtime", 0.0)
            self._data["total_games"]     = raw.get("total_games", 0)
            self._data["first_play"]      = raw.get("first_play")
            self._data["last_play"]       = raw.get("last_play")
            for gid, gdata in raw.get("games", {}).items():
                base = _empty_game_stats()
                base.update(gdata)
                self._data["games"][gid] = base
        except (FileNotFoundError, json.JSONDecodeError, IOError):
            pass

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        tmp = self._path + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2)
            os.replace(tmp, self._path)
        except IOError:
            pass

    def __repr__(self) -> str:
        n = len(self._data["games"])
        return f"StatsTracker(games={n}, total_playtime={self._data['global_playtime']:.0f}s)"
