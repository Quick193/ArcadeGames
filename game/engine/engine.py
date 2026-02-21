"""
engine/engine.py
----------------
ArcadeEngine: The heart of the arcade platform.

Responsibilities:
  | Owns the ONE and ONLY pygame event/update/render loop
  | Manages a scene stack (push/pop/replace)
  | Holds references to all global systems (settings, profile, stats, achievements)
  | Owns the AudioEngine instance
  | Manages the debug overlay
  | Drives scene transitions

Usage (main.py):
    engine = ArcadeEngine()
    engine.systems['settings'] = SettingsManager()
    engine.systems['profile']  = PlayerProfile()
    ...
    engine.push_scene(MainMenuScene(engine))
    engine.run()
"""

import pygame
import sys
import time
from typing import Optional

from engine.scene import BaseScene


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SCREEN_WIDTH  = 1280
SCREEN_HEIGHT = 800
TARGET_FPS    = 60
WINDOW_TITLE  = "Modern Arcade"


# ---------------------------------------------------------------------------
# ArcadeEngine
# ---------------------------------------------------------------------------

class ArcadeEngine:
    """
    Central engine.  One instance lives for the entire program lifetime.

    Scene stack behaviour:
        push_scene(s)    - s becomes active; previous scene is paused (not exited)
        pop_scene()      - current scene exits; previous scene resumes
        replace_scene(s) - current scene exits; s enters (no growing stack)
        clear_and_push(s)- entire stack is cleared; s is the only scene

    All three scene-change methods are deferred: they take effect at the
    START of the next frame, after the current frame finishes rendering.
    This prevents mid-frame state corruption.
    """

    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption(WINDOW_TITLE)

        self.screen: pygame.Surface = pygame.display.set_mode(
            (SCREEN_WIDTH, SCREEN_HEIGHT)
        )
        self.clock = pygame.time.Clock()

        # Scene stack - index -1 is always the active scene
        self._scene_stack: list[BaseScene] = []

        # Deferred scene operations (applied at start of next frame)
        # Each entry: ('push'|'pop'|'replace'|'clear_push', scene_or_None)
        self._pending_ops: list[tuple[str, Optional[BaseScene]]] = []

        # Global systems registry - populated by main.py before run()
        self.systems: dict = {}

        # Audio engine - set by main.py
        self.audio = None

        # Debug overlay toggle
        self.debug: bool = False

        # Frame timing
        self._last_time: float = time.perf_counter()
        self._fps_display: float = 0.0
        self._fps_accum: float = 0.0
        self._fps_frames: int = 0

        # Transition state (for engine/transitions.py - Phase 9)
        self._transition = None

    # ------------------------------------------------------------------
    # Scene management (deferred - safe to call from anywhere in a scene)
    # ------------------------------------------------------------------

    def push_scene(self, scene: BaseScene) -> None:
        """
        Push *scene* on top of the stack.
        Current scene stays in the stack but on_exit() is NOT called
        (it will resume when this new scene is popped).
        """
        self._pending_ops.append(("push", scene))

    def pop_scene(self) -> None:
        """
        Remove the current scene from the stack.
        The scene below it (if any) becomes active again and its
        on_enter() is called to signal resumption.
        If the stack becomes empty the engine exits cleanly.
        """
        self._pending_ops.append(("pop", None))

    def replace_scene(self, scene: BaseScene) -> None:
        """
        Exit and remove the current scene; push *scene* in its place.
        Stack depth stays the same.  Use for normal navigation
        (e.g. menu > game, game > menu).
        """
        self._pending_ops.append(("replace", scene))

    def clear_and_push(self, scene: BaseScene) -> None:
        """
        Clear the entire scene stack, then push *scene*.
        Use when you need a hard reset (e.g. after 'Return to main menu'
        from deep inside a nested pause/settings stack).
        """
        self._pending_ops.append(("clear_push", scene))

    # ------------------------------------------------------------------
    # Active scene accessor
    # ------------------------------------------------------------------

    @property
    def current_scene(self) -> Optional[BaseScene]:
        return self._scene_stack[-1] if self._scene_stack else None

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def run(self) -> None:
        """
        Start the engine.  Blocks until the program exits.
        Call this exactly once from main.py, after all systems are
        registered and the first scene has been pushed.
        """
        if not self._scene_stack and not self._pending_ops:
            raise RuntimeError(
                "ArcadeEngine.run() called with no scene. "
                "Push a scene before calling run()."
            )

        self._last_time = time.perf_counter()

        while True:
            # ---- 1. Apply any deferred scene operations ----------------
            self._apply_pending_ops()

            # If stack is empty after ops, we're done
            if not self._scene_stack:
                self._quit()

            # ---- 2. Compute delta time (capped at 100 ms) --------------
            now = time.perf_counter()
            dt = min(now - self._last_time, 0.1)
            self._last_time = now

            # FPS counter update (rolling average over 30 frames)
            self._fps_accum += self.clock.get_fps()
            self._fps_frames += 1
            if self._fps_frames >= 30:
                self._fps_display = self._fps_accum / self._fps_frames
                self._fps_accum = 0.0
                self._fps_frames = 0

            # ---- 3. Process events ------------------------------------
            scene = self.current_scene
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self._quit()

                # Global debug toggle (F3)
                if event.type == pygame.KEYDOWN and event.key == pygame.K_F3:
                    self.debug = not self.debug

                scene.handle_event(event)

            # ---- 4. Update --------------------------------------------
            scene.update(dt)

            # ---- 5. Draw ----------------------------------------------
            scene.draw(self.screen)

            # ---- 6. Debug overlay (drawn on top of everything) --------
            if self.debug:
                self._draw_debug_overlay()

            # ---- 7. Flip display --------------------------------------
            pygame.display.flip()
            self.clock.tick(TARGET_FPS)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _apply_pending_ops(self) -> None:
        """Process all deferred scene-change operations in order."""
        if not self._pending_ops:
            return

        for op, scene in self._pending_ops:
            if op == "push":
                # Don't call on_exit on the scene below - it's still in the stack
                self._scene_stack.append(scene)
                scene.on_enter()

            elif op == "pop":
                if self._scene_stack:
                    old = self._scene_stack.pop()
                    old.on_exit()
                # The scene below (if any) gets on_enter to signal resume
                if self._scene_stack:
                    self._scene_stack[-1].on_enter()

            elif op == "replace":
                if self._scene_stack:
                    old = self._scene_stack.pop()
                    old.on_exit()
                self._scene_stack.append(scene)
                scene.on_enter()

            elif op == "clear_push":
                # Exit all scenes from top to bottom
                while self._scene_stack:
                    old = self._scene_stack.pop()
                    old.on_exit()
                self._scene_stack.append(scene)
                scene.on_enter()

        self._pending_ops.clear()

    def _draw_debug_overlay(self) -> None:
        """
        Draw a lightweight debug HUD on top of the current scene.
        Toggle with F3.  Expanded in Phase 8 (debug overlay system).
        """
        try:
            font = pygame.font.SysFont("Consolas", 13)
        except Exception:
            font = pygame.font.SysFont(None, 14)

        scene_name = type(self.current_scene).__name__ if self.current_scene else "None"
        stack_depth = len(self._scene_stack)

        lines = [
            f"FPS:   {self._fps_display:.1f}",
            f"Scene: {scene_name}",
            f"Stack: {stack_depth}",
            f"DEBUG: F3 to hide",
        ]

        # Semi-transparent background panel
        panel_w = 180
        panel_h = len(lines) * 18 + 12
        panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 160))
        self.screen.blit(panel, (8, 8))

        for i, line in enumerate(lines):
            color = (100, 220, 100) if i == 0 else (200, 200, 200)
            surf = font.render(line, True, color)
            self.screen.blit(surf, (14, 14 + i * 18))

    @staticmethod
    def _quit() -> None:
        """Clean shutdown."""
        pygame.quit()
        sys.exit(0)
