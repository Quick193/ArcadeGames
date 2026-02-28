# Python-to-React Full Rewrite Tracker

This file is the source-of-truth checklist for a full migration redo from `game/**/*.py` to React/TS.

## Module Checklist

| Python file | Lines | React target | Status |
|---|---:|---|---|
| `game/engine/__init__.py` | 37 | `src/styles/* + rendering abstractions` | `pending_rewrite` |
| `game/engine/engine.py` | 280 | `src/styles/* + rendering abstractions` | `pending_rewrite` |
| `game/engine/render_manager.py` | 163 | `src/styles/* + rendering abstractions` | `pending_rewrite` |
| `game/engine/scene.py` | 131 | `src/styles/* + rendering abstractions` | `pending_rewrite` |
| `game/engine/theme.py` | 287 | `src/styles/* + rendering abstractions` | `pending_rewrite` |
| `game/engine/ui.py` | 352 | `src/styles/* + rendering abstractions` | `pending_rewrite` |
| `game/games/__init__.py` | 36 | `(pending)` | `pending_rewrite` |
| `game/games/asteroids.py` | 524 | `src/games/asteroids/*` | `in_progress` |
| `game/games/breakout.py` | 168 | `src/games/breakout/*` | `in_progress` |
| `game/games/chess.py` | 1396 | `src/games/chess/*` | `in_progress` |
| `game/games/connect4.py` | 360 | `src/games/connect4/*` | `pending_rewrite` |
| `game/games/endless_metro_run.py` | 870 | `src/games/endless_metro_run/*` | `in_progress` |
| `game/games/flappy.py` | 159 | `src/games/flappy/*` | `pending_rewrite` |
| `game/games/game_2048.py` | 186 | `src/games/game_2048/*` | `pending_rewrite` |
| `game/games/memory_match.py` | 124 | `src/games/memory_match/*` | `pending_rewrite` |
| `game/games/minesweeper.py` | 179 | `src/games/minesweeper/*` | `in_progress` |
| `game/games/neon_blob_dash.py` | 151 | `src/games/neon_blob_dash/*` | `in_progress` |
| `game/games/pong.py` | 189 | `src/games/pong/*` | `pending_rewrite` |
| `game/games/snake.py` | 149 | `src/games/snake/*` | `pending_rewrite` |
| `game/games/space_invaders.py` | 253 | `src/games/space_invaders/*` | `in_progress` |
| `game/games/sudoku.py` | 583 | `src/games/sudoku/*` | `in_progress` |
| `game/games/tetris.py` | 703 | `src/games/tetris/*` | `pending_rewrite` |
| `game/main.py` | 27 | `src/App.tsx + src/main.tsx` | `pending_rewrite` |
| `game/scenes/__init__.py` | 12 | `src/screens/* + in-game select UIs` | `pending_rewrite` |
| `game/scenes/achievements_screen.py` | 288 | `src/screens/* + in-game select UIs` | `in_progress` |
| `game/scenes/main_menu.py` | 928 | `src/screens/* + in-game select UIs` | `in_progress` |
| `game/scenes/profile_screen.py` | 281 | `src/screens/* + in-game select UIs` | `in_progress` |
| `game/scenes/settings_screen.py` | 468 | `src/screens/* + in-game select UIs` | `in_progress` |
| `game/systems/__init__.py` | 60 | `src/services/* + src/screens/*` | `pending_rewrite` |
| `game/systems/achievements.py` | 670 | `src/services/* + src/screens/*` | `in_progress` |
| `game/systems/profile.py` | 245 | `src/services/* + src/screens/*` | `in_progress` |
| `game/systems/settings.py` | 266 | `src/services/* + src/screens/*` | `in_progress` |
| `game/systems/stats.py` | 298 | `src/services/* + src/screens/*` | `pending_rewrite` |

## Rules for completion

- Mark a row complete only after feature-parity verification (UI flow + gameplay + persistence).
- For each game, verify: start flow, pause/resume, restart, exit, scoring, win/loss, stats write, achievements write, mobile controls.
- Keep portrait layout and no-overlap controls as hard requirements.
