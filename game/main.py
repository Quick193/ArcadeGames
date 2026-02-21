"""
main.py
-------
Entry point for the Modern Arcade platform.
Run with:   python main.py
"""

import pygame
from engine import ArcadeEngine
from systems import boot_systems


def main():
    engine = ArcadeEngine()

    # Phase 3: Boot all systems
    engine.systems = boot_systems()

    # Phase 4: Launch the main menu
    from scenes.main_menu import MainMenuScene
    engine.push_scene(MainMenuScene(engine))

    engine.run()


if __name__ == "__main__":
    main()
