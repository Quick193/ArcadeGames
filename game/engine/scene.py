"""
engine/scene.py
---------------
BaseScene: Abstract base class for every screen in the arcade.

All games, menus, overlays, and popups are Scenes.
The engine owns the single event/update/render loop and delegates to the
active scene — no scene ever runs its own while-loop.

Lifecycle:
    on_enter()     — called once when scene becomes active (init state here)
    update(dt)     — called every frame, dt = seconds since last frame
    draw(screen)   — called every frame after update
    handle_event() — called for each pygame event
    on_exit()      — called once when scene is being replaced or popped

Scene Control (called from inside a scene):
    self.engine.push_scene(scene)    — push new scene on top (e.g. pause menu)
    self.engine.pop_scene()          — pop back to previous scene
    self.engine.replace_scene(scene) — replace current scene (e.g. go to menu)
"""

from abc import ABC, abstractmethod
import pygame


class BaseScene(ABC):
    """
    Abstract base for every scene in the arcade engine.

    Subclasses must implement update(), draw(), and handle_event().
    on_enter() and on_exit() are optional lifecycle hooks.
    """

    def __init__(self, engine: "ArcadeEngine"):  # noqa: F821 — forward ref
        self.engine = engine

    # ------------------------------------------------------------------
    # Lifecycle hooks — override as needed
    # ------------------------------------------------------------------

    def on_enter(self) -> None:
        """
        Called once when this scene becomes the active scene.
        Use this to (re)initialise all game state, reset timers, etc.
        DO NOT put one-time resource loading here — do that in __init__.
        """
        pass

    def on_exit(self) -> None:
        """
        Called once just before this scene is removed from the stack
        or replaced.  Use it to pause music, persist state, etc.
        """
        pass

    # ------------------------------------------------------------------
    # Frame callbacks — called every frame by the engine
    # ------------------------------------------------------------------

    @abstractmethod
    def update(self, dt: float) -> None:
        """
        Update game/scene logic.

        Parameters
        ----------
        dt : float
            Seconds elapsed since the previous frame.  Always use dt to
            scale movement and timers so the game runs identically at any
            frame rate.
        """
        ...

    @abstractmethod
    def draw(self, screen: pygame.Surface) -> None:
        """
        Render this scene onto *screen*.

        Do not call pygame.display.flip() or pygame.display.update() here —
        the engine does that after draw() returns.
        """
        ...

    @abstractmethod
    def handle_event(self, event: pygame.event.Event) -> None:
        """
        Handle a single pygame event.

        The engine calls this once per event per frame, before update().
        Common pattern:

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.engine.pop_scene()
        """
        ...

    # ------------------------------------------------------------------
    # Convenience helpers available to every scene
    # ------------------------------------------------------------------

    @property
    def screen_size(self) -> tuple[int, int]:
        """Return (width, height) of the current display surface."""
        return pygame.display.get_surface().get_size()

    @property
    def settings(self):
        """Shortcut to engine.systems['settings']."""
        return self.engine.systems.get("settings")

    @property
    def profile(self):
        """Shortcut to engine.systems['profile']."""
        return self.engine.systems.get("profile")

    @property
    def achievements(self):
        """Shortcut to engine.systems['achievements']."""
        return self.engine.systems.get("achievements")

    @property
    def stats(self):
        """Shortcut to engine.systems['stats']."""
        return self.engine.systems.get("stats")

    @property
    def audio(self):
        """Shortcut to engine.audio."""
        return self.engine.audio
