"""games/memory_match.py — MemoryMatchScene"""
import random, pygame
from engine import BaseScene, Theme, RenderManager, FontCache, draw_text, draw_card, draw_overlay, draw_footer_hint
from engine.engine import SCREEN_WIDTH as W, SCREEN_HEIGHT as H

ROWS, COLS = 4, 4
CARD_W, CARD_H, GAP = 110, 120, 16
GRID_W  = COLS*CARD_W + (COLS-1)*GAP
START_X = (W - GRID_W) // 2
START_Y = 145
REVEAL_T = 0.65   # seconds a failed pair stays visible

COLORS = [
    lambda: Theme.ACCENT_CYAN,   lambda: Theme.ACCENT_GREEN,
    lambda: Theme.ACCENT_ORANGE, lambda: Theme.ACCENT_PURPLE,
    lambda: Theme.ACCENT_PINK,   lambda: Theme.ACCENT_BLUE,
    lambda: Theme.ACCENT_YELLOW, lambda: Theme.ACCENT_RED,
]

class MemoryMatchScene(BaseScene):
    GAME_ID = "memory_match"

    def on_enter(self): self._reset()

    def _reset(self):
        values = list(range(ROWS*COLS//2)) * 2
        random.shuffle(values)
        self._cards = []
        for idx, v in enumerate(values):
            r, c = idx//COLS, idx%COLS
            self._cards.append({
                "value": v,
                "rect": pygame.Rect(START_X+c*(CARD_W+GAP), START_Y+r*(CARD_H+GAP), CARD_W, CARD_H),
                "flipped": False, "matched": False,
            })
        self._first = self._second = None
        self._hide_timer = 0.0
        self._moves = self._pairs = self._mismatches = 0
        self._won   = False
        self._session_t = 0.0

    def update(self, dt):
        if not self._won: self._session_t += dt
        if self._hide_timer > 0:
            self._hide_timer -= dt
            if self._hide_timer <= 0:
                a, b = self._cards[self._first], self._cards[self._second]
                if a["value"] == b["value"]:
                    a["matched"] = b["matched"] = True
                    self._pairs += 1
                    if self._pairs == ROWS*COLS//2:
                        self._won = True
                        self._finish()
                else:
                    a["flipped"] = b["flipped"] = False
                    self._mismatches += 1
                self._first = self._second = None

    def _finish(self):
        if self.stats:
            self.stats.record_game(self.GAME_ID, score=max(0,1000-self._moves*10),
                won=True, duration=self._session_t, extra={"mismatches":self._mismatches})
        if self.achievements:
            self.achievements.check_and_unlock({
                "game_id": self.GAME_ID, "won": True,
                "mismatches": self._mismatches,
                "total_games_played": self.stats.global_summary()["total_games"] if self.stats else 1,
                "total_wins": self.stats.global_summary()["total_wins"] if self.stats else 1,
            })

    def draw(self, screen):
        screen.blit(RenderManager.get_background(W, H), (0, 0))
        draw_text(screen, "MEMORY MATCH", FontCache.get("Segoe UI",46,bold=True), Theme.TEXT_PRIMARY, W//2, 38, align="center")
        hw = 720; hx = (W-hw)//2
        draw_card(screen, (hx, 58, hw, 52))
        hf = FontCache.get("Segoe UI",17,bold=True)
        draw_text(screen, f"Moves: {self._moves}", hf, Theme.ACCENT_CYAN, hx+24, 76)
        draw_text(screen, f"Pairs: {self._pairs}/{ROWS*COLS//2}", hf, Theme.ACCENT_GREEN, W//2, 76, align="center")
        draw_text(screen, f"Errors: {self._mismatches}", hf, Theme.ACCENT_ORANGE, hx+hw-130, 76)
        for card in self._cards:
            if card["matched"] or card["flipped"]:
                color = COLORS[card["value"] % len(COLORS)]()
                pygame.draw.rect(screen, color, card["rect"], border_radius=10)
                pygame.draw.rect(screen, Theme.TEXT_PRIMARY, card["rect"], 1, border_radius=10)
                draw_text(screen, str(card["value"]+1), FontCache.get("Segoe UI",38,bold=True),
                          Theme.BG_PRIMARY, card["rect"].centerx, card["rect"].centery, align="center")
                if card["matched"]:
                    pygame.draw.rect(screen, (255,255,255,60), card["rect"], 2, border_radius=10)
            else:
                pygame.draw.rect(screen, Theme.CARD_BG, card["rect"], border_radius=10)
                pygame.draw.rect(screen, Theme.CARD_BORDER, card["rect"], 1, border_radius=10)
                pygame.draw.circle(screen, Theme.TEXT_MUTED, card["rect"].center, 8)
        draw_footer_hint(screen, "Click to flip  •  R Restart  •  Q Menu", y_offset=26)
        if self._won: self._draw_win(screen)

    def _draw_win(self, screen):
        draw_overlay(screen, 160)
        cw,ch=440,220; cx,cy=(W-cw)//2,(H-ch)//2
        draw_card(screen,(cx,cy,cw,ch))
        draw_text(screen,"MATCH COMPLETE!",FontCache.get("Segoe UI",42,bold=True),Theme.ACCENT_GREEN,W//2,cy+52,align="center")
        draw_text(screen,f"Finished in {self._moves} moves",FontCache.get("Segoe UI",22,bold=True),Theme.TEXT_PRIMARY,W//2,cy+108,align="center")
        draw_text(screen,f"Errors: {self._mismatches}",FontCache.get("Segoe UI",15),Theme.TEXT_MUTED,W//2,cy+148,align="center")
        draw_text(screen,"R Play Again  •  Q Menu",FontCache.get("Segoe UI",13),Theme.TEXT_MUTED,W//2,cy+186,align="center")

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            k = event.key
            if k in (pygame.K_q, pygame.K_ESCAPE): self.engine.pop_scene(); return
            if k == pygame.K_r: self._reset()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._hide_timer > 0 or self._won: return
            mx, my = event.pos
            for i, card in enumerate(self._cards):
                if card["rect"].collidepoint(mx,my) and not card["flipped"] and not card["matched"]:
                    card["flipped"] = True
                    if self._first is None:
                        self._first = i
                    elif self._second is None and i != self._first:
                        self._second = i
                        self._moves += 1
                        self._hide_timer = REVEAL_T
                    break

GAME_META = {"id":"memory_match","name":"Memory Match","desc":"Find all pairs","color":lambda:Theme.ACCENT_GREEN,"scene_class":MemoryMatchScene}
