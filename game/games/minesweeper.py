"""games/minesweeper.py - MinesweeperScene"""
import random, pygame
from engine import BaseScene, Theme, RenderManager, FontCache, draw_text, draw_card, draw_overlay, draw_footer_hint
from engine.engine import SCREEN_WIDTH as W, SCREEN_HEIGHT as H

DIFFICULTIES = [
    {"name":"Beginner",     "rows": 9, "cols": 9,  "mines": 10, "cell":52},
    {"name":"Intermediate", "rows":16, "cols":16,  "mines": 40, "cell":36},
    {"name":"Expert",       "rows":16, "cols":30,  "mines": 99, "cell":26},
]
NUM_COLORS = [(0,0,0),(25,100,255),(60,160,60),(220,50,50),(0,0,128),(128,0,0),(0,128,128),(0,0,0),(80,80,80)]

class MinesweeperScene(BaseScene):
    GAME_ID = "minesweeper"

    def on_enter(self):
        self._phase = "select"; self._sel = 0; self._time = 0.0

    def _start(self, diff_idx):
        d = DIFFICULTIES[diff_idx]
        self._diff = d; self._rows = d["rows"]; self._cols = d["cols"]
        self._mines = d["mines"]; self._cell = d["cell"]
        bw = self._cols*self._cell; bh = self._rows*self._cell
        self._ox = (W-bw)//2; self._oy = (H-bh)//2 + 20
        self._board  = [[0]*self._cols for _ in range(self._rows)]
        self._revealed = [[False]*self._cols for _ in range(self._rows)]
        self._flagged  = [[False]*self._cols for _ in range(self._rows)]
        self._first_click = True
        self._dead = self._won = False
        self._session_t = self._timer = 0.0
        self._phase = "game"

    def _place_mines(self, safe_r, safe_c):
        cells = [(r,c) for r in range(self._rows) for c in range(self._cols) if not (abs(r-safe_r)<=1 and abs(c-safe_c)<=1)]
        random.shuffle(cells)
        for r,c in cells[:self._mines]:
            self._board[r][c] = -1
        for r in range(self._rows):
            for c in range(self._cols):
                if self._board[r][c]==-1: continue
                cnt=0
                for dr in [-1,0,1]:
                    for dc in [-1,0,1]:
                        nr,nc=r+dr,c+dc
                        if 0<=nr<self._rows and 0<=nc<self._cols and self._board[nr][nc]==-1: cnt+=1
                self._board[r][c]=cnt

    def _reveal(self, r, c):
        if not (0<=r<self._rows and 0<=c<self._cols): return
        if self._revealed[r][c] or self._flagged[r][c]: return
        self._revealed[r][c]=True
        if self._board[r][c]==0:
            for dr in [-1,0,1]:
                for dc in [-1,0,1]:
                    if dr or dc: self._reveal(r+dr,c+dc)

    def _check_win(self):
        for r in range(self._rows):
            for c in range(self._cols):
                if self._board[r][c]!=-1 and not self._revealed[r][c]: return False
        return True

    def update(self, dt):
        self._time += dt
        if self._phase=="game" and not self._dead and not self._won:
            self._session_t += dt
            if not self._first_click: self._timer += dt

    def draw(self, screen):
        screen.blit(RenderManager.get_background(W, H), (0,0))
        if self._phase=="select":
            self._draw_select(screen)
        else:
            self._draw_game(screen)

    def _draw_select(self, screen):
        draw_text(screen,"MINESWEEPER",FontCache.get("Segoe UI",46,bold=True),Theme.TEXT_PRIMARY,W//2,120,align="center")
        bf=FontCache.get("Segoe UI",20)
        for i,d in enumerate(DIFFICULTIES):
            bx,by,bw,bh=(W-320)//2,260+i*88,320,62
            sel=i==self._sel
            bg=Theme.ACCENT_RED if sel else Theme.CARD_BG
            pygame.draw.rect(screen,bg,(bx,by,bw,bh),border_radius=10)
            pygame.draw.rect(screen,Theme.CARD_BORDER,(bx,by,bw,bh),1,border_radius=10)
            draw_text(screen,d["name"],bf,Theme.TEXT_PRIMARY if sel else Theme.TEXT_SECONDARY,bx+bw//2,by+bh//2-10,align="center")
            sf=FontCache.get("Segoe UI",11)
            draw_text(screen,f"{d['cols']}x{d['rows']}  |  {d['mines']} mines",sf,Theme.TEXT_MUTED,bx+bw//2,by+bh//2+12,align="center")
        draw_footer_hint(screen,"^v Select  |  Enter Start  |  Q Back",y_offset=26)

    def _draw_game(self, screen):
        cs=self._cell
        # Header
        draw_card(screen,((W-460)//2,14,460,46))
        hf=FontCache.get("Segoe UI",16,bold=True)
        flags=sum(self._flagged[r][c] for r in range(self._rows) for c in range(self._cols))
        draw_text(screen,f"* {self._mines-flags}",hf,Theme.ACCENT_RED,(W-460)//2+24,30)
        draw_text(screen,f"T {int(self._timer)}s",hf,Theme.ACCENT_CYAN,(W+460)//2-100,30)
        draw_text(screen,self._diff["name"],hf,Theme.TEXT_MUTED,W//2,30,align="center")
        # Grid
        for r in range(self._rows):
            for c in range(self._cols):
                x=self._ox+c*cs; y=self._oy+r*cs
                rev=self._revealed[r][c]; flag=self._flagged[r][c]
                if rev:
                    pygame.draw.rect(screen,(44,52,68),(x+1,y+1,cs-2,cs-2),border_radius=3)
                    val=self._board[r][c]
                    if val==-1:
                        pygame.draw.circle(screen,Theme.ACCENT_RED,(x+cs//2,y+cs//2),cs//3)
                    elif val>0:
                        nc=NUM_COLORS[min(val,8)]
                        draw_text(screen,str(val),FontCache.get("Segoe UI",max(10,cs-14),bold=True),nc,x+cs//2,y+cs//2,align="center")
                elif flag:
                    pygame.draw.rect(screen,Theme.BG_TERTIARY,(x+1,y+1,cs-2,cs-2),border_radius=3)
                    pygame.draw.rect(screen,Theme.CARD_BORDER,(x+1,y+1,cs-2,cs-2),1,border_radius=3)
                    # Draw a simple flag shape
                    fx, fy = x + cs//2, y + cs//2
                    pygame.draw.line(screen, Theme.ACCENT_RED, (fx-1, fy-cs//3), (fx-1, fy+cs//3), 2)
                    pygame.draw.polygon(screen, Theme.ACCENT_RED, [(fx-1, fy-cs//3), (fx+cs//4, fy-cs//6), (fx-1, fy)])
                else:
                    pygame.draw.rect(screen,Theme.CARD_BG,(x+1,y+1,cs-2,cs-2),border_radius=3)
                    pygame.draw.rect(screen,Theme.CARD_BORDER,(x+1,y+1,cs-2,cs-2),1,border_radius=3)
        draw_footer_hint(screen,"Left Click Reveal  |  Right Click Flag  |  R Restart  |  Q Menu",y_offset=26)
        if self._dead: self._draw_end(screen,False)
        elif self._won: self._draw_end(screen,True)

    def _draw_end(self,screen,won):
        draw_overlay(screen,180)
        cw,ch=400,200; cx,cy=(W-cw)//2,(H-ch)//2
        draw_card(screen,(cx,cy,cw,ch))
        title="CLEARED!" if won else "BOOM!"
        color=Theme.ACCENT_GREEN if won else Theme.ACCENT_RED
        draw_text(screen,title,FontCache.get("Segoe UI",40,bold=True),color,W//2,cy+52,align="center")
        draw_text(screen,f"Time: {int(self._timer)}s",FontCache.get("Segoe UI",20),Theme.TEXT_PRIMARY,W//2,cy+108,align="center")
        draw_text(screen,"R Restart  |  Q Menu",FontCache.get("Segoe UI",13),Theme.TEXT_MUTED,W//2,cy+158,align="center")

    def handle_event(self, event):
        if event.type==pygame.KEYDOWN:
            k=event.key
            if k in(pygame.K_q,pygame.K_ESCAPE):
                if self._phase=="game": self.engine.pop_scene()
                else: self.engine.pop_scene()
                return
            if k==pygame.K_r:
                if self._phase=="game": self._start(DIFFICULTIES.index(self._diff))
                return
            if self._phase=="select":
                if k==pygame.K_UP:    self._sel=(self._sel-1)%3
                if k==pygame.K_DOWN:  self._sel=(self._sel+1)%3
                if k==pygame.K_RETURN: self._start(self._sel)
        elif event.type==pygame.MOUSEBUTTONDOWN and self._phase=="game":
            if self._dead or self._won: return
            mx,my=event.pos
            c=(mx-self._ox)//self._cell; r=(my-self._oy)//self._cell
            if not(0<=r<self._rows and 0<=c<self._cols): return
            if event.button==1:
                if self._flagged[r][c]: return
                if self._first_click:
                    self._first_click=False
                    self._place_mines(r,c)
                self._reveal(r,c)
                if self._board[r][c]==-1:
                    # Reveal all mines
                    for rr in range(self._rows):
                        for cc in range(self._cols):
                            if self._board[rr][cc]==-1: self._revealed[rr][cc]=True
                    self._dead=True
                    if self.stats: self.stats.record_game(self.GAME_ID,score=0,won=False,duration=self._session_t)
                elif self._check_win():
                    self._won=True
                    if self.stats:
                        self.stats.record_game(self.GAME_ID,score=max(0,1000-int(self._timer)),won=True,duration=self._session_t)
                    if self.achievements:
                        self.achievements.check_and_unlock({"game_id":self.GAME_ID,"won":True,
                            "total_games_played":self.stats.global_summary()["total_games"] if self.stats else 1,
                            "total_wins":self.stats.global_summary()["total_wins"] if self.stats else 1})
            elif event.button==3:
                if not self._revealed[r][c]: self._flagged[r][c]=not self._flagged[r][c]

GAME_META={"id":"minesweeper","name":"Minesweeper","desc":"Clear the minefield","color":lambda:Theme.ACCENT_RED,"scene_class":MinesweeperScene}
