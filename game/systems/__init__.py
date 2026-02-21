"""
systems/__init__.py
-------------------
Public API for the systems package.

Usage
-----
    # Option A — import individually
    from systems import SettingsManager, StatsTracker, PlayerProfile, AchievementSystem

    # Option B — boot all four in one call (used by main.py)
    from systems import boot_systems

    engine.systems = boot_systems()
    # → {
    #     "settings":     SettingsManager instance,
    #     "stats":        StatsTracker instance,
    #     "profile":      PlayerProfile instance,
    #     "achievements": AchievementSystem instance,
    #   }
"""

from systems.settings     import SettingsManager
from systems.stats        import StatsTracker
from systems.profile      import PlayerProfile
from systems.achievements import AchievementSystem, AchievementDef, AchievementPopup


def boot_systems() -> dict:
    """
    Instantiate all four systems in dependency order and return them
    as a dict keyed by the names used in engine.systems.

    Call this once from main.py before pushing the first scene.
    """
    settings     = SettingsManager()
    stats        = StatsTracker()
    profile      = PlayerProfile(stats)
    achievements = AchievementSystem()

    # Apply saved theme immediately
    try:
        from engine.theme import Theme
        Theme.set_theme(settings.theme)
    except (ImportError, ValueError):
        pass

    return {
        "settings":     settings,
        "stats":        stats,
        "profile":      profile,
        "achievements": achievements,
    }


__all__ = [
    "SettingsManager", "StatsTracker", "PlayerProfile",
    "AchievementSystem", "AchievementDef", "AchievementPopup",
    "boot_systems",
]
