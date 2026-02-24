# ArcadeGames

This repository now contains two app paths:

- Python arcade (current implementation): `game/`
- React conversion (in progress): project root with `src/`

## React app (new)

The React conversion currently includes:

- Main menu with game registry
- Snake fully playable in browser (canvas)
- Tetris playable in browser (canvas, with hold/hard drop/line clear/leveling)
- Pong playable in browser (1P vs AI and 2P local)
- Flappy Bird playable in browser (difficulty select + pipe gameplay)
- 2048 playable in browser (arrow-key merge logic)
- Placeholders for remaining games
- Mobile touch controls for converted games

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

### Initial React structure

- `src/App.tsx`: scene-style app shell
- `src/data/gameRegistry.ts`: ported game registry metadata
- `src/screens/MainMenu.tsx`: main menu screen
- `src/games/snake/*`: first converted game
- `src/styles/globals.css`: global styles/theme

## Migration approach

1. Keep Python source as behavioral reference.
2. Convert one game at a time from `game/games/*.py` to `src/games/*`.
3. Move profile/settings/stats systems into React state + storage services.
