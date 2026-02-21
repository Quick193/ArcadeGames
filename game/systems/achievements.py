"""
systems/achievements.py
-----------------------
AchievementSystem: Defines, tracks, unlocks, and persists achievements.

Architecture
------------
  • Achievements are defined in the ACHIEVEMENT_REGISTRY dict at the bottom
    of this file.  Each entry is an AchievementDef dataclass.
  • Unlock state (which IDs are unlocked + when) lives in data/achievements.json.
  • Games call check_and_unlock(game_id, stats_snapshot) after each session.
    The system evaluates all relevant conditions and unlocks automatically.
  • Newly unlocked achievements are added to a popup queue that the
    MainMenuScene / game scenes drain each frame to show animated toasts.

Defining a new achievement
--------------------------
    Add an entry to ACHIEVEMENT_REGISTRY:

    "first_blood": AchievementDef(
        id          = "first_blood",
        name        = "First Blood",
        description = "Win your first game of any kind",
        icon        = "🏆",
        color       = (255, 214, 102),
        game_id     = None,          # None = global (any game)
        condition   = lambda snap: snap.get("total_wins", 0) >= 1,
    )

Achievement conditions receive a 'stats snapshot' dict — a flat dict of
combined global + per-game stats passed in by the calling scene.

Usage
-----
    ach = AchievementSystem()

    # After a Tetris game
    snap = {
        "game_id":       "tetris",
        "score":         12000,
        "lines":         48,
        "level":         6,
        "games_played":  3,   # total for tetris
        "total_wins":    5,   # global
        ...
    }
    newly_unlocked = ach.check_and_unlock(snap)
    # → [AchievementDef, ...]  (list of newly unlocked this call)

    # Check if already unlocked
    ach.is_unlocked("tetris_first_clear")   # → True / False

    # Get all for display
    ach.all_achievements()   # → list of (AchievementDef, unlocked_bool, date_or_None)

Achievements file: data/achievements.json
"""

import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Optional


DATA_DIR  = os.path.join(os.path.dirname(__file__), "..", "data")
SAVE_PATH = os.path.join(DATA_DIR, "achievements.json")


# ---------------------------------------------------------------------------
# AchievementDef
# ---------------------------------------------------------------------------

@dataclass
class AchievementDef:
    id:          str
    name:        str
    description: str
    icon:        str                        # emoji or short symbol
    color:       tuple                      # accent color for the popup
    condition:   Callable[[dict], bool]     # receives stats snapshot dict
    game_id:     Optional[str] = None       # None = global achievement
    secret:      bool          = False      # hidden until unlocked
    points:      int           = 10         # gamification weight

    def __hash__(self):
        return hash(self.id)


# ---------------------------------------------------------------------------
# Achievement popup item (put in queue, drained by scenes)
# ---------------------------------------------------------------------------

@dataclass
class AchievementPopup:
    achievement: AchievementDef
    created_at:  float = field(default_factory=lambda: __import__("time").perf_counter())
    duration:    float = 4.0     # seconds to display

    def is_expired(self, now: float) -> bool:
        return now - self.created_at > self.duration


# ---------------------------------------------------------------------------
# Achievement registry
# ---------------------------------------------------------------------------

def _def(id, name, desc, icon, color, condition, game_id=None, secret=False, pts=10):
    return AchievementDef(id=id, name=name, description=desc, icon=icon,
                          color=color, condition=condition, game_id=game_id,
                          secret=secret, points=pts)

_C = lambda r, g, b: (r, g, b)

ACHIEVEMENT_REGISTRY: dict[str, AchievementDef] = {

    # ---- Global --------------------------------------------------------
    "first_game": _def(
        "first_game", "Welcome to the Arcade",
        "Play your first game of anything",
        "🎮", _C(99, 179, 237),
        lambda s: s.get("total_games_played", 0) >= 1,
        pts=5,
    ),
    "ten_games": _def(
        "ten_games", "Getting Warmed Up",
        "Play 10 games total across all titles",
        "🔥", _C(255, 159, 67),
        lambda s: s.get("total_games_played", 0) >= 10,
    ),
    "hundred_games": _def(
        "hundred_games", "Arcade Regular",
        "Play 100 games total",
        "🕹️", _C(171, 99, 250),
        lambda s: s.get("total_games_played", 0) >= 100,
        pts=25,
    ),
    "first_win": _def(
        "first_win", "Winner Winner",
        "Win your first game",
        "🏆", _C(255, 214, 102),
        lambda s: s.get("total_wins", 0) >= 1,
        pts=5,
    ),
    "win_streak_5": _def(
        "win_streak_5", "On a Roll",
        "Win 5 games in a row (same game)",
        "⚡", _C(79, 236, 255),
        lambda s: s.get("current_streak", 0) >= 5,
        pts=20,
    ),
    "one_hour": _def(
        "one_hour", "Time Flies",
        "Accumulate 1 hour of total playtime",
        "⏱️", _C(92, 219, 149),
        lambda s: s.get("total_playtime", 0) >= 3600,
    ),
    "night_owl": _def(
        "night_owl", "Night Owl",
        "Play every game at least once",
        "🦉", _C(171, 99, 250),
        lambda s: s.get("games_tried", 0) >= 13,
        secret=True, pts=30,
    ),

    # ---- Tetris --------------------------------------------------------
    "tetris_first": _def(
        "tetris_first", "Stacker",
        "Complete your first Tetris game",
        "🧱", _C(79, 236, 255),
        lambda s: s.get("games_played", 0) >= 1,
        game_id="tetris",
    ),
    "tetris_1000": _def(
        "tetris_1000", "Getting Started",
        "Score 1,000 points in Tetris",
        "📈", _C(99, 179, 237),
        lambda s: s.get("score", 0) >= 1000,
        game_id="tetris",
    ),
    "tetris_10000": _def(
        "tetris_10000", "Line Clearer",
        "Score 10,000 points in Tetris",
        "💎", _C(171, 99, 250),
        lambda s: s.get("score", 0) >= 10000,
        game_id="tetris", pts=20,
    ),
    "tetris_tetris": _def(
        "tetris_tetris", "TETRIS!",
        "Clear 4 lines at once",
        "✨", _C(255, 214, 102),
        lambda s: s.get("tetris_clears", 0) >= 1,
        game_id="tetris", pts=15,
    ),
    "tetris_100_lines": _def(
        "tetris_100_lines", "Century",
        "Clear 100 total lines in Tetris",
        "💯", _C(92, 219, 149),
        lambda s: s.get("total_lines", 0) >= 100,
        game_id="tetris", pts=25,
    ),

    # ---- Snake ---------------------------------------------------------
    "snake_first": _def(
        "snake_first", "Slithering Start",
        "Play your first game of Snake",
        "🐍", _C(92, 219, 149),
        lambda s: s.get("games_played", 0) >= 1,
        game_id="snake",
    ),
    "snake_10": _def(
        "snake_10", "Growing Up",
        "Reach a length of 10 in Snake",
        "📏", _C(92, 219, 149),
        lambda s: s.get("score", 0) >= 10,
        game_id="snake",
    ),
    "snake_50": _def(
        "snake_50", "Sssserious",
        "Reach a length of 50 in Snake",
        "🐉", _C(255, 214, 102),
        lambda s: s.get("score", 0) >= 50,
        game_id="snake", pts=20,
    ),

    # ---- Pong ----------------------------------------------------------
    "pong_first_win": _def(
        "pong_first_win", "Paddle Up",
        "Win your first Pong match",
        "🏓", _C(250, 99, 180),
        lambda s: s.get("won", False),
        game_id="pong",
    ),
    "pong_shutout": _def(
        "pong_shutout", "Shutout",
        "Win a Pong match without conceding a point",
        "🛡️", _C(79, 236, 255),
        lambda s: s.get("won", False) and s.get("opponent_score", 1) == 0,
        game_id="pong", pts=25,
    ),
    "pong_5_wins": _def(
        "pong_5_wins", "Pong Master",
        "Win 5 Pong matches",
        "🥇", _C(255, 214, 102),
        lambda s: s.get("games_won", 0) >= 5,
        game_id="pong", pts=15,
    ),

    # ---- Flappy Bird ---------------------------------------------------
    "flappy_first": _def(
        "flappy_first", "First Flap",
        "Pass your first pipe in Flappy Bird",
        "🐦", _C(255, 214, 102),
        lambda s: s.get("score", 0) >= 1,
        game_id="flappy",
    ),
    "flappy_10": _def(
        "flappy_10", "Sky Pilot",
        "Pass 10 pipes in one run",
        "✈️", _C(79, 236, 255),
        lambda s: s.get("score", 0) >= 10,
        game_id="flappy", pts=15,
    ),
    "flappy_25": _def(
        "flappy_25", "Bird God",
        "Pass 25 pipes in one run",
        "🦅", _C(255, 159, 67),
        lambda s: s.get("score", 0) >= 25,
        game_id="flappy", pts=30,
    ),

    # ---- Chess ---------------------------------------------------------
    "chess_first": _def(
        "chess_first", "Opening Move",
        "Play your first game of Chess",
        "♟️", _C(171, 99, 250),
        lambda s: s.get("games_played", 0) >= 1,
        game_id="chess",
    ),
    "chess_win": _def(
        "chess_win", "Checkmate!",
        "Win a game of Chess",
        "♔", _C(255, 214, 102),
        lambda s: s.get("won", False),
        game_id="chess", pts=15,
    ),
    "chess_beat_hard": _def(
        "chess_beat_hard", "Grandmaster",
        "Beat the AI on Hard difficulty",
        "🧠", _C(79, 236, 255),
        lambda s: s.get("won", False) and s.get("difficulty") == "hard",
        game_id="chess", pts=50, secret=True,
    ),

    # ---- Breakout ------------------------------------------------------
    "breakout_first": _def(
        "breakout_first", "Brick By Brick",
        "Play your first Breakout game",
        "🧱", _C(255, 159, 67),
        lambda s: s.get("games_played", 0) >= 1,
        game_id="breakout",
    ),
    "breakout_clear": _def(
        "breakout_clear", "Clean Sweep",
        "Clear all bricks in a Breakout level",
        "🧹", _C(92, 219, 149),
        lambda s: s.get("won", False),
        game_id="breakout", pts=20,
    ),

    # ---- Memory Match --------------------------------------------------
    "memory_first": _def(
        "memory_first", "Total Recall",
        "Complete your first Memory Match game",
        "🃏", _C(92, 219, 149),
        lambda s: s.get("won", False),
        game_id="memory_match",
    ),
    "memory_no_mistake": _def(
        "memory_no_mistake", "Perfect Memory",
        "Complete Memory Match without a single mismatch",
        "🧩", _C(255, 214, 102),
        lambda s: s.get("mismatches", 1) == 0 and s.get("won", False),
        game_id="memory_match", pts=30, secret=True,
    ),

    # ---- Space Invaders ------------------------------------------------
    "space_first": _def(
        "space_first", "Defender",
        "Survive your first wave in Space Invaders",
        "🚀", _C(79, 236, 255),
        lambda s: s.get("wave", 0) >= 1,
        game_id="space_invaders",
    ),
    "space_wave5": _def(
        "space_wave5", "Space Ace",
        "Reach wave 5 in Space Invaders",
        "🌟", _C(255, 214, 102),
        lambda s: s.get("wave", 0) >= 5,
        game_id="space_invaders", pts=20,
    ),

    # ---- 2048 ----------------------------------------------------------
    "2048_first": _def(
        "2048_first", "Starter Tile",
        "Play your first game of 2048",
        "🔢", _C(255, 159, 67),
        lambda s: s.get("games_played", 0) >= 1,
        game_id="game_2048",
    ),
    "2048_tile": _def(
        "2048_tile", "Two Thousand!",
        "Reach the 2048 tile",
        "🏅", _C(255, 214, 102),
        lambda s: s.get("best_tile", 0) >= 2048,
        game_id="game_2048", pts=30,
    ),

    # ---- Minesweeper ---------------------------------------------------
    "mine_first": _def(
        "mine_first", "Lucky",
        "Clear your first Minesweeper board",
        "💣", _C(255, 107, 107),
        lambda s: s.get("won", False),
        game_id="minesweeper",
    ),

    # ---- Connect 4 -----------------------------------------------------
    "c4_first": _def(
        "c4_first", "Four in a Row",
        "Win your first Connect 4 game",
        "🔴", _C(255, 107, 107),
        lambda s: s.get("won", False),
        game_id="connect4",
    ),

    # ---- Neon Blob Dash ------------------------------------------------
    "neon_first": _def(
        "neon_first", "Dasher",
        "Complete a level in Neon Blob Dash",
        "💫", _C(79, 236, 255),
        lambda s: s.get("won", False),
        game_id="neon_blob_dash",
    ),

    # ---- Endless Metro Run ---------------------------------------------
    "metro_100": _def(
        "metro_100", "Hundred Meter",
        "Run 100 metres in Endless Metro Run",
        "🏃", _C(99, 179, 237),
        lambda s: s.get("distance", 0) >= 100,
        game_id="endless_metro_run",
    ),
    "metro_1000": _def(
        "metro_1000", "Marathon",
        "Run 1,000 metres in Endless Metro Run",
        "🏅", _C(255, 214, 102),
        lambda s: s.get("distance", 0) >= 1000,
        game_id="endless_metro_run", pts=25,
    ),
}


# ---------------------------------------------------------------------------
# AchievementSystem
# ---------------------------------------------------------------------------

class AchievementSystem:
    """
    Manages achievement state: evaluation, unlocking, persistence, popups.
    """

    def __init__(self, path: str = SAVE_PATH) -> None:
        self._path = path
        # unlocked[id] = ISO datetime string of unlock time
        self._unlocked: dict[str, str] = {}
        self._popup_queue: list[AchievementPopup] = []
        self._load()

    # ------------------------------------------------------------------
    # Checking & unlocking
    # ------------------------------------------------------------------

    def check_and_unlock(self, stats_snapshot: dict) -> list[AchievementDef]:
        """
        Evaluate all achievements against *stats_snapshot*.
        Unlock any that pass their condition and haven't been unlocked yet.

        Returns list of newly unlocked AchievementDef objects (may be empty).
        """
        newly = []
        game_id = stats_snapshot.get("game_id")

        for ach in ACHIEVEMENT_REGISTRY.values():
            if self.is_unlocked(ach.id):
                continue
            # Only evaluate global achievements or matching game achievements
            if ach.game_id is not None and ach.game_id != game_id:
                continue
            try:
                if ach.condition(stats_snapshot):
                    self._unlock(ach)
                    newly.append(ach)
            except Exception:
                pass  # Bad condition — never crash

        if newly:
            self._save()

        return newly

    def unlock(self, achievement_id: str) -> bool:
        """
        Manually unlock an achievement by ID.
        Returns True if it was newly unlocked, False if already unlocked.
        """
        if achievement_id not in ACHIEVEMENT_REGISTRY:
            return False
        if self.is_unlocked(achievement_id):
            return False
        ach = ACHIEVEMENT_REGISTRY[achievement_id]
        self._unlock(ach)
        self._save()
        return True

    def is_unlocked(self, achievement_id: str) -> bool:
        return achievement_id in self._unlocked

    def unlock_date(self, achievement_id: str) -> str | None:
        return self._unlocked.get(achievement_id)

    # ------------------------------------------------------------------
    # Popup queue
    # ------------------------------------------------------------------

    def get_pending_popups(self) -> list[AchievementPopup]:
        """
        Return and clear all pending popup items.
        Call once per frame from the active scene to drain the queue.
        """
        pending = list(self._popup_queue)
        self._popup_queue.clear()
        return pending

    # ------------------------------------------------------------------
    # Querying for the achievements screen
    # ------------------------------------------------------------------

    def all_achievements(self) -> list[tuple[AchievementDef, bool, str | None]]:
        """
        Return list of (AchievementDef, is_unlocked, unlock_date_or_None),
        sorted: unlocked first (by date desc), then locked alphabetically.
        """
        unlocked = []
        locked   = []
        for ach in ACHIEVEMENT_REGISTRY.values():
            date = self._unlocked.get(ach.id)
            if date is not None:
                unlocked.append((ach, True, date))
            else:
                locked.append((ach, False, None))

        unlocked.sort(key=lambda x: x[2], reverse=True)
        locked.sort(key=lambda x: x[0].name)
        return unlocked + locked

    def unlocked_count(self) -> int:
        return len(self._unlocked)

    def total_count(self) -> int:
        return len(ACHIEVEMENT_REGISTRY)

    def total_points(self) -> int:
        """Total achievement points earned."""
        return sum(
            ACHIEVEMENT_REGISTRY[aid].points
            for aid in self._unlocked
            if aid in ACHIEVEMENT_REGISTRY
        )

    def for_game(self, game_id: str) -> list[tuple[AchievementDef, bool, str | None]]:
        """Return achievements filtered to a specific game + global ones."""
        return [
            (ach, self.is_unlocked(ach.id), self.unlock_date(ach.id))
            for ach in ACHIEVEMENT_REGISTRY.values()
            if ach.game_id == game_id or ach.game_id is None
        ]

    def reset_all(self) -> None:
        self._unlocked.clear()
        self._popup_queue.clear()
        self._save()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _unlock(self, ach: AchievementDef) -> None:
        self._unlocked[ach.id] = datetime.now().isoformat(timespec="seconds")
        self._popup_queue.append(AchievementPopup(achievement=ach))

    def _load(self) -> None:
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            self._unlocked = {
                k: v for k, v in raw.get("unlocked", {}).items()
                if k in ACHIEVEMENT_REGISTRY
            }
        except (FileNotFoundError, json.JSONDecodeError, IOError):
            pass

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        tmp = self._path + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump({"unlocked": self._unlocked}, f, indent=2)
            os.replace(tmp, self._path)
        except IOError:
            pass

    def __repr__(self) -> str:
        return (
            f"AchievementSystem("
            f"unlocked={self.unlocked_count()}/{self.total_count()}, "
            f"points={self.total_points()})"
        )
