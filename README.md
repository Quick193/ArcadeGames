# ArcadeGames

This repository now contains two app paths:

- Python arcade (current implementation): `game/`
- React conversion (in progress): project root with `src/`

## React app (new)

The React conversion currently includes:

- Main menu with game registry
- All original game IDs now have playable React implementations:
  - `snake`, `tetris`, `pong`, `flappy`, `game_2048`, `connect4`, `minesweeper`
  - `chess`, `breakout`, `memory_match`, `space_invaders`, `asteroids`
  - `sudoku`, `neon_blob_dash`, `endless_metro_run`
- Mobile touch controls with global mode toggle: `Buttons` or `Gestures`
- Profile page with global + per-game table for all games
- Achievements page with full registry (locked/unlocked/secret/points/progress)
- Settings parity improvements from Python:
  - Audio toggles and volume sliders
  - Display toggles, theme selector, FPS cap selector
  - Gameplay toggles (ghost piece, chess hints, auto-clear arrows)
  - Data actions (reset stats, reset achievements, full wipe)

Note: some late-stage ports are lightweight gameplay versions compared to the Python originals.

### Run

```bash
npm install
npm run dev
```

## Mobile + Vercel

This React app is set up for mobile web play and Vercel deployment.

- Touch controls are available on phones/tablets for converted games.
- `vercel.json` is included for Vite + SPA rewrite behavior.

### Deploy to Vercel

1. Push this repository to GitHub.
2. In Vercel, create a new project and import the repo.
3. Framework preset: `Vite`
4. Build command: `npm run build`
5. Output directory: `dist`
6. Deploy.

### React structure

- `src/App.tsx`: scene-style app shell
- `src/data/gameRegistry.ts`: ported game registry metadata
- `src/screens/MainMenu.tsx`: main menu screen
- `src/games/*`: one folder per converted game
- `src/screens/SettingsScreen.tsx`: settings + data management
- `src/screens/ProfileScreen.tsx`: profile + per-game stats view
- `src/screens/AchievementsScreen.tsx`: full achievement browser
- `src/styles/globals.css`: global styles/theme

## Migration approach

1. Keep Python source as behavioral reference.
2. Convert one game at a time from `game/games/*.py` to `src/games/*`.
3. Move profile/settings/stats systems into React state + storage services.
