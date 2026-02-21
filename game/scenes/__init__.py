"""
scenes/__init__.py
"""
from scenes.main_menu          import MainMenuScene, GAME_REGISTRY
from scenes.achievements_screen import AchievementsScene
from scenes.profile_screen     import ProfileScene
from scenes.settings_screen    import SettingsScene

__all__ = [
    "MainMenuScene", "GAME_REGISTRY",
    "AchievementsScene", "ProfileScene", "SettingsScene",
]
