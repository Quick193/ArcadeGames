"""games/game_2048.py - Game2048Scene"""
import random, pygame
from engine import BaseScene, Theme, RenderManager, FontCache, draw_text, draw_card, draw_overlay, draw_footer_hint
from engine.engine import SCREEN_WIDTH as W, SCREEN_HEIGHT as H

GRID  = 4
TILE  = 110
GAP   = 12
BOARD_SIZE = GRID*TILE + (GRID+1)*GAP
BOARD_X = (W - BOARD_SIZE)//2
BOARD_Y = (H - BOARD_SIZE)//2 + 30

TILE_COLORS = {
    0:    ((40,46,60),    (107,114,128)),
    2:    ((238,228,218), (119,110,101)),
    4:    ((237,224,200), (119,110,101)),
    8:    ((242,177,121), (249,246,242)),
    16:   ((245,149,99),  (249,246,242)),
    32:   ((246,124,95),  (249,246,242)),
    64:   ((246,94,59),   (249,246,242)),
    128:  ((237,207,114), (249,246,242)),
    256:  ((237,204,97),  (249,246,242)),
    512:  ((237,200,80),  (249,246,242)),
    1024: ((237,197,63),  (249,246,242)),
    2048: ((237,194,46),  (249,246,242)),
}

def _empty_board():
    return [[0]*GRID for _ in range(GRID)]

def _add_tile(board):
    empty = [(r,c) for r in range(GRID) for c in range(GRID) if board[r][c]==0]
    if not empty: return
    r, c = random.choice(empty)
    board[r][c] = 4 if random.random()<0.1 else 2

def _slide_row(row):
    # Remove zeros, merge, pad
    tiles = [x for x in row if x]
    merged = []
    pts = 0
    i = 0
    while i < len(tiles):
        if i+1 < len(tiles) and tiles[i]==tiles[i+1]:
            val = tiles[i]*2; merged.append(val); pts+=val; i+=2
        else:
            merged.append(tiles[i]); i+=1
    merged += [0]*(GRID-len(merged))
    return merged, pts

def _move(board, direction):
    """Returns (new_board, score_gained, moved_bool)"""
    new = [row[:] for row in board]
    pts = 0
    moved = False
    if direction == "left":
        for r in range(GRID):
            merged, p = _slide_row(new[r])
            if merged != new[r]: moved=True
            new[r] = merged; pts+=p
    elif direction == "right":
        for r in range(GRID):
            rev, p = _slide_row(new[r][::-1])
            merged = rev[::-1]
            if merged != new[r]: moved=True
            new[r] = merged; pts+=p
    elif direction == "up":
        for c in range(GRID):
            col = [new[r][c] for r in range(GRID)]
            merged, p = _slide_row(col)
            for r in range(GRID):
                if merged[r] != new[r][c]: moved=True
                new[r][c] = merged[r]
            pts+=p
    elif direction == "down":
        for c in range(GRID):
            col = [new[r][c] for r in range(GRID)][::-1]
            merged, p = _slide_row(col)
            merged = merged[::-1]
            for r in range(GRID):
                if merged[r] != new[r][c]: moved=True
                new[r][c] = merged[r]
            pts+=p
    return new, pts, moved

def _has_moves(board):
    for r in range(GRID):
        for c in range(GRID):
            if board[r][c]==0: return True
            if c+1<GRID and board[r][c]==board[r][c+1]: return True
            if r+1<GRID and board[r][c]==board[r+1][c]: return True
    return False

def _best_tile(board):
    return max(board[r][c] for r in range(GRID) for c in range(GRID))

class Game2048Scene(BaseScene):
    GAME_ID = "game_2048"

    def on_enter(self): self._reset()

    def _reset(self):
        self._board = _empty_board()
        _add_tile(self._board); _add_tile(self._board)
        self._score = 0; self._dead = False; self._won = False
        self._new_best = False; self._session_t = 0.0

    def update(self, dt):
        if not self._dead: self._session_t += dt

    def _do_move(self, direction):
        if self._dead: return
        new_board, pts, moved = _move(self._board, direction)
        if not moved: return
        self._board = new_board
        self._score += pts
        _add_tile(self._board)
        if _best_tile(self._board) >= 2048 and not self._won:
            self._won = True
        if not _has_moves(self._board):
            self._finish()

    def _finish(self):
        self._dead = True
        bt = _best_tile(self._board)
        if self.stats:
            self._new_best = self._score > self.stats.best_score(self.GAME_ID)
            self.stats.record_game(self.GAME_ID, score=self._score, won=self._won,
                duration=self._session_t, extra={"best_tile": bt})
        if self.achievements:
            self.achievements.check_and_unlock({
                "game_id": self.GAME_ID, "score": self._score, "best_tile": bt,
                "games_played": self.stats.games_played(self.GAME_ID) if self.stats else 1,
                "total_games_played": self.stats.global_summary()["total_games"] if self.stats else 1,
                "total_wins": self.stats.global_summary()["total_wins"] if self.stats else int(self._won),
            })

    def draw(self, screen):
        screen.blit(RenderManager.get_background(W, H), (0, 0))
        # Title + score
        draw_text(screen,"2048",FontCache.get("Segoe UI",52,bold=True),Theme.TEXT_PRIMARY,W//2,46,align="center")
        best = self.stats.best_score(self.GAME_ID) if self.stats else 0
        draw_card(screen,((W-320)//2,82,320,52))
        hf=FontCache.get("Segoe UI",17,bold=True)
        draw_text(screen,f"Score: {self._score}",hf,Theme.ACCENT_YELLOW,(W-320)//2+24,100)
        draw_text(screen,f"Best: {max(best,self._score)}",hf,Theme.ACCENT_CYAN,(W+320)//2-130,100)
        # Board background
        pygame.draw.rect(screen,(44,52,68),(BOARD_X-GAP,BOARD_Y-GAP,BOARD_SIZE+GAP*2,BOARD_SIZE+GAP*2),border_radius=12)
        for r in range(GRID):
            for c in range(GRID):
                tx=BOARD_X+GAP+c*(TILE+GAP); ty=BOARD_Y+GAP+r*(TILE+GAP)
                val=self._board[r][c]
                bg, fg = TILE_COLORS.get(val, ((60,200,80),(255,255,255)))
                pygame.draw.rect(screen,bg,(tx,ty,TILE,TILE),border_radius=8)
                if val:
                    fs = 36 if val<1000 else (28 if val<10000 else 22)
                    draw_text(screen,str(val),FontCache.get("Segoe UI",fs,bold=True),fg,tx+TILE//2,ty+TILE//2,align="center")
        draw_footer_hint(screen,"Arrow Keys Move  |  R Restart  |  Q Menu",y_offset=26)
        if self._dead or self._won: self._draw_end(screen)

    def _draw_end(self, screen):
        draw_overlay(screen,190)
        cw,ch=420,240; cx,cy=(W-cw)//2,(H-ch)//2
        draw_card(screen,(cx,cy,cw,ch))
        if self._won:
            draw_text(screen,"YOU WIN!",FontCache.get("Segoe UI",44,bold=True),Theme.ACCENT_GREEN,W//2,cy+52,align="center")
        else:
            draw_text(screen,"GAME OVER",FontCache.get("Segoe UI",44,bold=True),Theme.ACCENT_RED,W//2,cy+52,align="center")
        draw_text(screen,f"Score: {self._score}",FontCache.get("Segoe UI",26,bold=True),Theme.TEXT_PRIMARY,W//2,cy+108,align="center")
        if self._new_best:
            draw_text(screen,"** NEW BEST **",FontCache.get("Segoe UI",13,bold=True),Theme.ACCENT_YELLOW,W//2,cy+148,align="center")
        hint = "Continue playing or R Restart  |  Q Menu" if self._won else "R Restart  |  Q Menu"
        draw_text(screen,hint,FontCache.get("Segoe UI",13),Theme.TEXT_MUTED,W//2,cy+196,align="center")

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN: return
        k = event.key
        if k in (pygame.K_q,pygame.K_ESCAPE): self.engine.pop_scene(); return
        if k == pygame.K_r: self._reset(); return
        if self._dead: return
        if k == pygame.K_LEFT:  self._do_move("left")
        elif k == pygame.K_RIGHT: self._do_move("right")
        elif k == pygame.K_UP:   self._do_move("up")
        elif k == pygame.K_DOWN: self._do_move("down")

GAME_META={"id":"game_2048","name":"2048","desc":"Merge to the top","color":lambda:Theme.ACCENT_YELLOW,"scene_class":Game2048Scene}
