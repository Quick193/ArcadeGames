"""games/connect4.py - Connect4Scene"""
import random, pygame
from engine import BaseScene, Theme, RenderManager, FontCache, draw_text, draw_card, draw_overlay, draw_footer_hint
from engine.engine import SCREEN_WIDTH as W, SCREEN_HEIGHT as H

ROWS, COLS = 6, 7
CELL  = 86
PAD   = 10
BOARD_W = COLS*CELL + (COLS+1)*PAD
BOARD_H = ROWS*CELL + (ROWS+1)*PAD
BOARD_X = (W - BOARD_W)//2
BOARD_Y = (H - BOARD_H)//2 + 30
RADIUS  = (CELL - PAD*2) // 2

P1_COLOR = (255, 80,  80)   # red
P2_COLOR = (255, 214, 60)   # yellow
EMPTY_COLOR = (28, 33, 48)

# ---------------------------------------------------------------------------
# Pure game logic
# ---------------------------------------------------------------------------

def _empty_grid():
    return [[0]*COLS for _ in range(ROWS)]

def _drop(grid, col, player):
    for r in range(ROWS-1, -1, -1):
        if grid[r][col] == 0:
            grid[r][col] = player
            return r
    return -1

def _valid_cols(grid):
    return [c for c in range(COLS) if grid[0][c] == 0]

def _check_win(grid, player):
    # Horizontal
    for r in range(ROWS):
        for c in range(COLS-3):
            if all(grid[r][c+i]==player for i in range(4)): return True
    # Vertical
    for r in range(ROWS-3):
        for c in range(COLS):
            if all(grid[r+i][c]==player for i in range(4)): return True
    # Diagonal /
    for r in range(3, ROWS):
        for c in range(COLS-3):
            if all(grid[r-i][c+i]==player for i in range(4)): return True
    # Diagonal \
    for r in range(ROWS-3):
        for c in range(COLS-3):
            if all(grid[r+i][c+i]==player for i in range(4)): return True
    return False

def _winning_cells(grid, player):
    for r in range(ROWS):
        for c in range(COLS-3):
            if all(grid[r][c+i]==player for i in range(4)): return [(r,c+i) for i in range(4)]
    for r in range(ROWS-3):
        for c in range(COLS):
            if all(grid[r+i][c]==player for i in range(4)): return [(r+i,c) for i in range(4)]
    for r in range(3, ROWS):
        for c in range(COLS-3):
            if all(grid[r-i][c+i]==player for i in range(4)): return [(r-i,c+i) for i in range(4)]
    for r in range(ROWS-3):
        for c in range(COLS-3):
            if all(grid[r+i][c+i]==player for i in range(4)): return [(r+i,c+i) for i in range(4)]
    return []

def _score_window(window, player):
    opp = 2 if player==1 else 1
    p = window.count(player); e = window.count(0); o = window.count(opp)
    if p==4: return 1000
    if p==3 and e==1: return 12
    if p==2 and e==2: return 3
    if o==4: return -1000
    if o==3 and e==1: return -20   # block opponent strongly
    if o==2 and e==2: return -3
    return 0

def _heuristic(grid, player):
    score = 0
    opp   = 2 if player==1 else 1
    # Centre column preference — strongest positional bonus
    for bonus_c, bonus in [(COLS//2, 6), (COLS//2-1, 3), (COLS//2+1, 3)]:
        if 0 <= bonus_c < COLS:
            col_vals = [grid[r][bonus_c] for r in range(ROWS)]
            score += col_vals.count(player) * bonus
            score -= col_vals.count(opp) * bonus

    for r in range(ROWS):
        for c in range(COLS-3):
            w = [grid[r][c+i] for i in range(4)]
            score += _score_window(w, player)
    for r in range(ROWS-3):
        for c in range(COLS):
            w = [grid[r+i][c] for i in range(4)]
            score += _score_window(w, player)
    for r in range(3,ROWS):
        for c in range(COLS-3):
            w = [grid[r-i][c+i] for i in range(4)]
            score += _score_window(w, player)
    for r in range(ROWS-3):
        for c in range(COLS-3):
            w = [grid[r+i][c+i] for i in range(4)]
            score += _score_window(w, player)
    return score

def _minimax(grid, depth, alpha, beta, maximising, ai_player):
    human = 2 if ai_player==1 else 1
    valid = _valid_cols(grid)
    if _check_win(grid, ai_player):  return None,  100000 + depth
    if _check_win(grid, human):      return None, -100000 - depth
    if not valid or depth==0:
        return None, _heuristic(grid, ai_player)

    # Column order: centre-out for better pruning
    order = sorted(valid, key=lambda c: abs(c - COLS//2))
    best_col = order[0]
    if maximising:
        best = -10**9
        for c in order:
            g2 = [row[:] for row in grid]
            _drop(g2, c, ai_player)
            _, score = _minimax(g2, depth-1, alpha, beta, False, ai_player)
            if score > best: best = score; best_col = c
            alpha = max(alpha, best)
            if alpha >= beta: break
        return best_col, best
    else:
        best = 10**9
        for c in order:
            g2 = [row[:] for row in grid]
            _drop(g2, c, human)
            _, score = _minimax(g2, depth-1, alpha, beta, True, ai_player)
            if score < best: best = score; best_col = c
            beta = min(beta, best)
            if alpha >= beta: break
        return best_col, best

AI_DEPTH = {"easy": 1, "medium": 4, "hard": 6}
AI_RAND  = {"easy": 0.45, "medium": 0.0, "hard": 0.0}  # easy sometimes plays random

# ---------------------------------------------------------------------------
# Scene
# ---------------------------------------------------------------------------

class Connect4Scene(BaseScene):
    GAME_ID = "connect4"

    def on_enter(self):
        self._phase    = "mode"
        self._mode     = None   # "1p" or "2p"
        self._diff     = "medium"
        self._sel      = 0
        self._time     = 0.0
        self._session_t = 0.0
        self._init_game()

    def _init_game(self):
        self._grid    = _empty_grid()
        self._turn    = 1            # 1 = P1/human, 2 = P2/AI
        self._hover   = COLS // 2   # keyboard / mouse column cursor
        self._winner  = 0
        self._draw    = False
        self._win_cells = []
        self._flash_t   = 0.0
        self._ai_pending = False     # flag: AI should move next update

    def update(self, dt):
        self._time    += dt
        self._flash_t += dt
        if self._phase != "game" or self._winner or self._draw: return
        self._session_t += dt
        if self._mode=="1p" and self._turn==2 and self._ai_pending:
            self._ai_pending = False
            depth = AI_DEPTH.get(self._diff, 4)
            rand  = AI_RAND.get(self._diff, 0.0)
            valid = _valid_cols(self._grid)
            if valid:
                if rand > 0 and random.random() < rand:
                    col = random.choice(valid)
                else:
                    col, _ = _minimax(self._grid, depth, -10**9, 10**9, True, 2)
                if col is not None and col in valid:
                    self._place(col)

    def _place(self, col):
        if col not in _valid_cols(self._grid): return
        r = _drop(self._grid, col, self._turn)
        if _check_win(self._grid, self._turn):
            self._winner   = self._turn
            self._win_cells = _winning_cells(self._grid, self._turn)
            self._flash_t  = 0.0
            self._end_game()
        elif not _valid_cols(self._grid):
            self._draw = True
            self._end_game()
        else:
            self._turn = 2 if self._turn==1 else 1
            if self._mode=="1p" and self._turn==2:
                self._ai_pending = True

    def _end_game(self):
        p1_won = self._winner == 1
        if self.stats:
            self.stats.record_game(self.GAME_ID, score=1 if p1_won else 0,
                won=p1_won, duration=self._session_t)
        if self.achievements:
            self.achievements.check_and_unlock({
                "game_id": self.GAME_ID, "won": p1_won,
                "games_won": self.stats.games_won(self.GAME_ID) if self.stats else int(p1_won),
                "total_games_played": self.stats.global_summary()["total_games"] if self.stats else 1,
                "total_wins": self.stats.global_summary()["total_wins"] if self.stats else int(p1_won),
            })

    # ------------------------------------------------------------------
    # Draw
    # ------------------------------------------------------------------

    def draw(self, screen):
        screen.blit(RenderManager.get_background(W, H), (0,0))
        if self._phase == "mode":
            self._draw_mode(screen)
        elif self._phase == "difficulty":
            self._draw_diff(screen)
        else:
            self._draw_game(screen)

    def _draw_mode(self, screen):
        draw_text(screen,"CONNECT 4",FontCache.get("Segoe UI",52,bold=True),Theme.TEXT_PRIMARY,W//2,130,align="center")
        opts=["1 Player vs AI","2 Players Local"]
        bf=FontCache.get("Segoe UI",22)
        for i,opt in enumerate(opts):
            sel=i==self._sel
            bx,by,bw,bh=(W-300)//2,280+i*82,300,58
            bg=Theme.ACCENT_BLUE if sel else Theme.CARD_BG
            pygame.draw.rect(screen,bg,(bx,by,bw,bh),border_radius=10)
            pygame.draw.rect(screen,Theme.CARD_BORDER,(bx,by,bw,bh),1,border_radius=10)
            draw_text(screen,opt,bf,Theme.TEXT_PRIMARY if sel else Theme.TEXT_SECONDARY,bx+bw//2,by+bh//2,align="center")
        draw_footer_hint(screen,"^v Select  |  Enter Confirm  |  Q Back",y_offset=26)

    def _draw_diff(self, screen):
        draw_text(screen,"Difficulty",FontCache.get("Segoe UI",46,bold=True),Theme.TEXT_PRIMARY,W//2,130,align="center")
        opts=["Easy","Medium","Hard"]
        bf=FontCache.get("Segoe UI",22)
        for i,opt in enumerate(opts):
            sel=i==self._sel
            bx,by,bw,bh=(W-300)//2,260+i*82,300,58
            bg=Theme.ACCENT_BLUE if sel else Theme.CARD_BG
            pygame.draw.rect(screen,bg,(bx,by,bw,bh),border_radius=10)
            pygame.draw.rect(screen,Theme.CARD_BORDER,(bx,by,bw,bh),1,border_radius=10)
            draw_text(screen,opt,bf,Theme.TEXT_PRIMARY if sel else Theme.TEXT_SECONDARY,bx+bw//2,by+bh//2,align="center")
        draw_footer_hint(screen,"^v Select  |  Enter Confirm  |  Q Back",y_offset=26)

    def _draw_game(self, screen):
        # Hover cursor (column indicator)
        if not self._winner and not self._draw:
            p_col = P1_COLOR if self._turn==1 else P2_COLOR
            cx = BOARD_X + PAD + self._hover*CELL + self._hover*PAD + CELL//2
            pygame.draw.circle(screen, p_col, (cx, BOARD_Y - 28), RADIUS-4)

        # Board background
        pygame.draw.rect(screen,(24,32,56),(BOARD_X,BOARD_Y,BOARD_W,BOARD_H),border_radius=12)
        pygame.draw.rect(screen,Theme.CARD_BORDER,(BOARD_X,BOARD_Y,BOARD_W,BOARD_H),2,border_radius=12)

        win_set = set(map(tuple, self._win_cells))
        flash_on = int(self._flash_t*6) % 2 == 0

        for r in range(ROWS):
            for c in range(COLS):
                cx = BOARD_X + PAD + c*(CELL+PAD) + CELL//2
                cy = BOARD_Y + PAD + r*(CELL+PAD) + CELL//2
                val = self._grid[r][c]
                if (r,c) in win_set and flash_on:
                    color = (255,255,255)
                elif val==1: color=P1_COLOR
                elif val==2: color=P2_COLOR
                else: color=EMPTY_COLOR
                # Shadow
                pygame.draw.circle(screen,(10,14,24),(cx+2,cy+2),RADIUS)
                pygame.draw.circle(screen,color,(cx,cy),RADIUS)
                if val:
                    pygame.draw.circle(screen,(255,255,255,60),(cx,cy),RADIUS,1)

        # Status bar
        draw_card(screen,((W-360)//2,14,360,46))
        sf=FontCache.get("Segoe UI",15,bold=True)
        p2_name = "AI" if self._mode=="1p" else "P2"
        draw_text(screen,"P1",sf,P1_COLOR,(W-360)//2+60,30,align="center")
        draw_text(screen,"vs",sf,Theme.TEXT_MUTED,W//2,30,align="center")
        draw_text(screen,p2_name,sf,P2_COLOR,(W+360)//2-60,30,align="center")

        # Current turn
        if not self._winner and not self._draw:
            tc = P1_COLOR if self._turn==1 else P2_COLOR
            tn = "P1" if self._turn==1 else p2_name
            draw_text(screen,f"{tn}'s turn",FontCache.get("Segoe UI",14),tc,W//2,BOARD_Y+BOARD_H+18,align="center")

        draw_footer_hint(screen,"<> Move  |  Enter / Click Drop  |  R Restart  |  Q Menu",y_offset=26)
        if self._winner or self._draw: self._draw_end(screen)

    def _draw_end(self, screen):
        draw_overlay(screen,180)
        cw,ch=400,200; cx,cy=(W-cw)//2,(H-ch)//2
        draw_card(screen,(cx,cy,cw,ch))
        p2_name="AI" if self._mode=="1p" else "P2"
        if self._draw:
            draw_text(screen,"DRAW!",FontCache.get("Segoe UI",44,bold=True),Theme.ACCENT_YELLOW,W//2,cy+52,align="center")
        else:
            name="P1" if self._winner==1 else p2_name
            color=P1_COLOR if self._winner==1 else P2_COLOR
            draw_text(screen,f"{name} WINS!",FontCache.get("Segoe UI",44,bold=True),color,W//2,cy+52,align="center")
        draw_text(screen,"R Rematch  |  Q Menu",FontCache.get("Segoe UI",13),Theme.TEXT_MUTED,W//2,cy+152,align="center")

    # ------------------------------------------------------------------
    # Input
    # ------------------------------------------------------------------

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            self._handle_key(event.key)
        elif event.type == pygame.MOUSEMOTION and self._phase=="game":
            mx,_ = event.pos
            c = (mx - BOARD_X - PAD) // (CELL+PAD)
            if 0<=c<COLS: self._hover=c
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button==1 and self._phase=="game":
            if self._winner or self._draw: return
            if self._mode=="1p" and self._turn==2: return
            mx,_ = event.pos
            c = (mx - BOARD_X - PAD) // (CELL+PAD)
            if 0<=c<COLS: self._place(c)

    def _handle_key(self, k):
        if k in (pygame.K_q,pygame.K_ESCAPE):
            if self._phase=="game": self.engine.pop_scene()
            elif self._phase=="difficulty": self._phase="mode"; self._sel=0
            else: self.engine.pop_scene()
            return
        if self._phase=="mode":
            if k==pygame.K_UP:    self._sel=(self._sel-1)%2
            if k==pygame.K_DOWN:  self._sel=(self._sel+1)%2
            if k==pygame.K_RETURN:
                if self._sel==0: self._phase="difficulty"; self._mode="1p"; self._sel=1
                else: self._mode="2p"; self._diff=None; self._init_game(); self._phase="game"
        elif self._phase=="difficulty":
            if k==pygame.K_UP:    self._sel=(self._sel-1)%3
            if k==pygame.K_DOWN:  self._sel=(self._sel+1)%3
            if k==pygame.K_RETURN:
                self._diff=["easy","medium","hard"][self._sel]
                self._init_game(); self._phase="game"
        elif self._phase=="game":
            if k==pygame.K_r: self._init_game(); self._session_t=0.0; return
            if self._winner or self._draw: return
            if self._mode=="1p" and self._turn==2: return
            if k==pygame.K_LEFT:  self._hover=max(0,self._hover-1)
            elif k==pygame.K_RIGHT: self._hover=min(COLS-1,self._hover+1)
            elif k in (pygame.K_RETURN,pygame.K_SPACE,pygame.K_DOWN): self._place(self._hover)

GAME_META={"id":"connect4","name":"Connect 4","desc":"Line up four in a row","color":lambda:Theme.ACCENT_BLUE,"scene_class":Connect4Scene}
