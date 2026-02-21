"""
scenes/settings_screen.py
--------------------------
SettingsScene: Live settings panel.

Sections
--------
  Audio      - Music volume slider, SFX volume slider, enable toggles
  Display    - Theme selector, Particles toggle, BG animation toggle,
               FPS cap selector, Show FPS toggle
  Gameplay   - Ghost piece toggle, Chess hints toggle,
               Auto-clear chess annotations toggle
  Data       - Reset stats, Reset achievements (with confirmation)

Controls
--------
  ^ v          - navigate rows
  < >          - adjust selected setting (sliders, selectors)
  Enter / Space - toggle booleans, confirm reset
  Q / Esc      - back (all changes already saved live)
"""

import pygame

from engine import (
    BaseScene, Theme, RenderManager, FontCache,
    draw_text, draw_card, draw_overlay, draw_footer_hint,
)
from engine.engine import SCREEN_WIDTH, SCREEN_HEIGHT


# ---------------------------------------------------------------------------
# Row descriptors - tell the renderer what to draw and the handler what to do
# ---------------------------------------------------------------------------

class _Row:
    """Base class for a settings row."""
    def __init__(self, label: str, section: bool = False):
        self.label   = label
        self.section = section   # True = section header, not interactive


class _SectionRow(_Row):
    def __init__(self, label: str):
        super().__init__(label, section=True)


class _SliderRow(_Row):
    def __init__(self, label: str, key: str, step: float = 0.05):
        super().__init__(label)
        self.key  = key
        self.step = step


class _ToggleRow(_Row):
    def __init__(self, label: str, key: str):
        super().__init__(label)
        self.key = key


class _SelectorRow(_Row):
    """Cycles through a list of string values."""
    def __init__(self, label: str, key: str, options: list):
        super().__init__(label)
        self.key     = key
        self.options = options


class _ActionRow(_Row):
    """Button that triggers a callback."""
    def __init__(self, label: str, action_id: str, color=None):
        super().__init__(label)
        self.action_id = action_id
        self.color     = color


# ---------------------------------------------------------------------------
# SettingsScene
# ---------------------------------------------------------------------------

class SettingsScene(BaseScene):

    ROW_H    = 52
    LEFT_X   = 80
    RIGHT_X  = SCREEN_WIDTH - 80
    CONTENT_Y = 130
    SCROLL_SPD = 200

    def on_enter(self) -> None:
        self._scroll     = 0.0
        self._max_scroll = 0.0
        self._selected   = 0
        self._confirm_action: str | None = None   # pending destructive action
        self._confirm_timer = 0.0
        self._status_msg  = ""
        self._status_timer = 0.0
        self._build_rows()

    def _build_rows(self) -> None:
        from engine.theme import Theme as T
        fps_opts    = ["30", "60", "120", "Unlimited"]
        theme_opts  = T.AVAILABLE

        self._rows: list[_Row] = [
            # ---- Audio ----
            _SectionRow("AUDIO"),
            _SliderRow("Music Volume",   "music_volume"),
            _SliderRow("SFX Volume",     "sfx_volume"),
            _ToggleRow("Music Enabled",  "music_enabled"),
            _ToggleRow("SFX Enabled",    "sfx_enabled"),

            # ---- Display ----
            _SectionRow("DISPLAY"),
            _SelectorRow("Theme",        "theme",    theme_opts),
            _ToggleRow("Particles",      "show_particles"),
            _ToggleRow("BG Animation",   "show_bg_anim"),
            _SelectorRow("FPS Cap",      "fps_cap",  fps_opts),
            _ToggleRow("Show FPS",       "show_fps"),

            # ---- Gameplay ----
            _SectionRow("GAMEPLAY"),
            _ToggleRow("Ghost Piece",         "show_ghost_piece"),
            _ToggleRow("Chess Move Hints",    "chess_show_hints"),
            _ToggleRow("Auto-Clear Arrows",   "auto_clear_annotations"),

            # ---- Data ----
            _SectionRow("DATA"),
            _ActionRow("Reset All Stats",         "reset_stats",    color=(255, 107, 107)),
            _ActionRow("Reset Achievements",       "reset_ach",      color=(255, 107, 107)),
            _ActionRow("Reset All (Full Wipe)",    "reset_all",      color=(255, 60,  60)),
        ]

        # Only interactive rows are selectable
        self._interactive = [i for i, r in enumerate(self._rows)
                             if not r.section]
        self._selected = 0

        total_h  = len(self._rows) * self.ROW_H
        visible_h = SCREEN_HEIGHT - self.CONTENT_Y - 50
        self._max_scroll = max(0.0, total_h - visible_h)

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def update(self, dt: float) -> None:
        if self._status_timer > 0:
            self._status_timer = max(0, self._status_timer - dt)
        if self._confirm_timer > 0:
            self._confirm_timer -= dt
            if self._confirm_timer <= 0:
                self._confirm_action = None

        # Scroll to keep selected row visible
        sel_idx = self._interactive[self._selected] if self._interactive else 0
        row_y   = sel_idx * self.ROW_H - int(self._scroll)
        visible_h = SCREEN_HEIGHT - self.CONTENT_Y - 50
        if row_y < 0:
            self._scroll = max(0, self._scroll + row_y)
        elif row_y + self.ROW_H > visible_h:
            self._scroll = min(self._max_scroll,
                               self._scroll + (row_y + self.ROW_H - visible_h))

    # ------------------------------------------------------------------
    # Draw
    # ------------------------------------------------------------------

    def draw(self, screen: pygame.Surface) -> None:
        w, h = screen.get_size()
        screen.blit(RenderManager.get_background(w, h), (0, 0))

        self._draw_header(screen, w)
        self._draw_rows(screen, w, h)
        draw_footer_hint(screen,
            "^v Navigate  |  <> Adjust  |  Enter Toggle  |  Q Back",
            y_offset=26)

        if self._confirm_action:
            self._draw_confirm(screen, w, h)

    def _draw_header(self, screen: pygame.Surface, w: int) -> None:
        title_font = FontCache.get("Segoe UI", 46, bold=True)
        draw_text(screen, "SETTINGS", title_font, Theme.TEXT_PRIMARY,
                  w // 2, 46, align="center")

        sub_font = FontCache.get("Segoe UI", 13)
        draw_text(screen, "Changes are saved automatically",
                  sub_font, Theme.TEXT_MUTED, w // 2, 96, align="center")

        # Status message
        if self._status_msg and self._status_timer > 0:
            a = min(1.0, self._status_timer) * 255
            sf = FontCache.get("Segoe UI", 13, bold=True)
            draw_text(screen, self._status_msg, sf,
                      (*Theme.ACCENT_GREEN[:3],),
                      w // 2, 116, align="center")

        pygame.draw.line(screen, Theme.CARD_BORDER,
                         (self.LEFT_X, 120),
                         (self.RIGHT_X, 120))

    def _draw_rows(self, screen: pygame.Surface, w: int, h: int) -> None:
        clip = pygame.Rect(0, self.CONTENT_Y, w, h - self.CONTENT_Y - 40)
        screen.set_clip(clip)

        s   = self.settings
        col_w = self.RIGHT_X - self.LEFT_X

        for i, row in enumerate(self._rows):
            ry = self.CONTENT_Y + i * self.ROW_H - int(self._scroll)
            if ry + self.ROW_H < self.CONTENT_Y or ry > h:
                continue

            if row.section:
                self._draw_section_header(screen, row.label, ry, col_w)
                continue

            # Is this row selected?
            try:
                is_sel = (self._interactive[self._selected] == i)
            except IndexError:
                is_sel = False

            self._draw_row_bg(screen, ry, col_w, is_sel)
            self._draw_row_label(screen, row, ry, is_sel)

            if s:
                self._draw_row_control(screen, row, ry, s, is_sel, w)

        screen.set_clip(None)

        # Bottom fade
        if self._scroll < self._max_scroll:
            fade_h = 30
            fade = pygame.Surface((w, fade_h), pygame.SRCALPHA)
            for fi in range(fade_h):
                a = int(150 * fi / fade_h)
                pygame.draw.line(fade, (*Theme.BG_PRIMARY, a),
                                 (0, fi), (w, fi))
            screen.blit(fade, (0, h - fade_h - 40))

    def _draw_section_header(self, screen, label, ry, col_w) -> None:
        sf = FontCache.get("Segoe UI", 11, bold=True)
        draw_text(screen, label, sf, Theme.ACCENT_BLUE,
                  self.LEFT_X, ry + self.ROW_H // 2 - 6)
        pygame.draw.line(screen, Theme.CARD_BORDER,
                         (self.LEFT_X + sf.size(label)[0] + 12, ry + self.ROW_H // 2),
                         (self.RIGHT_X, ry + self.ROW_H // 2))

    def _draw_row_bg(self, screen, ry, col_w, is_sel) -> None:
        if is_sel:
            bg = pygame.Surface((col_w, self.ROW_H - 4), pygame.SRCALPHA)
            pygame.draw.rect(bg, (*Theme.ACCENT_BLUE[:3], 28),
                             (0, 0, col_w, self.ROW_H - 4), border_radius=8)
            pygame.draw.rect(bg, (*Theme.ACCENT_BLUE[:3], 80),
                             (0, 0, col_w, self.ROW_H - 4), 1, border_radius=8)
            screen.blit(bg, (self.LEFT_X, ry + 2))

    def _draw_row_label(self, screen, row, ry, is_sel) -> None:
        lf   = FontCache.get("Segoe UI", 14, bold=is_sel)
        color = Theme.TEXT_PRIMARY if is_sel else Theme.TEXT_SECONDARY
        if isinstance(row, _ActionRow) and row.color:
            color = row.color if is_sel else (*row.color[:3],)
        draw_text(screen, row.label, lf, color,
                  self.LEFT_X + 14, ry + self.ROW_H // 2 - 7)

    def _draw_row_control(self, screen, row, ry, s, is_sel, w) -> None:
        cy = ry + self.ROW_H // 2 - 8
        rx = self.RIGHT_X

        if isinstance(row, _SliderRow):
            val     = s.get(row.key, 0.0)
            bar_w   = 180
            bar_x   = rx - bar_w - 60
            fill_w  = int(bar_w * val)
            # Track
            pygame.draw.rect(screen, Theme.BG_TERTIARY,
                             (bar_x, cy + 6, bar_w, 6), border_radius=3)
            # Fill
            fc = Theme.ACCENT_CYAN if is_sel else Theme.ACCENT_BLUE
            if fill_w > 0:
                pygame.draw.rect(screen, fc,
                                 (bar_x, cy + 6, fill_w, 6), border_radius=3)
            # Thumb
            pygame.draw.circle(screen, fc,
                               (bar_x + fill_w, cy + 9), 8 if is_sel else 6)
            # Value label
            vf = FontCache.get("Segoe UI", 12, bold=True)
            draw_text(screen, f"{int(val * 100)}%", vf, Theme.TEXT_SECONDARY,
                      rx - 8, cy + 2, align="right")

        elif isinstance(row, _ToggleRow):
            val = s.get(row.key, False)
            self._draw_toggle(screen, val, rx - 60, cy + 4, is_sel)

        elif isinstance(row, _SelectorRow):
            val     = str(s.get(row.key, row.options[0]))
            opts    = row.options
            # Map fps_cap int > string
            if row.key == "fps_cap":
                val = "Unlimited" if val == "0" else val
            idx     = opts.index(val) if val in opts else 0
            vf      = FontCache.get("Segoe UI", 13, bold=True)
            vc      = Theme.ACCENT_CYAN if is_sel else Theme.TEXT_SECONDARY
            arrows  = FontCache.get("Segoe UI", 14)
            # Prev arrow
            can_prev = idx > 0
            draw_text(screen, "<", arrows,
                      (*Theme.ACCENT_BLUE[:3],) if can_prev else Theme.TEXT_MUTED,
                      rx - 220, cy + 2)
            draw_text(screen, val, vf, vc, rx - 60, cy + 2, align="right")
            can_next = idx < len(opts) - 1
            draw_text(screen, ">", arrows,
                      (*Theme.ACCENT_BLUE[:3],) if can_next else Theme.TEXT_MUTED,
                      rx - 8, cy + 2, align="right")

        elif isinstance(row, _ActionRow):
            if is_sel:
                af = FontCache.get("Segoe UI", 11, bold=True)
                draw_text(screen, "< / > or Enter to confirm",
                          af, Theme.TEXT_MUTED, rx - 8, cy + 4, align="right")

    def _draw_toggle(self, screen, value: bool, x: int, y: int,
                     highlight: bool) -> None:
        tw, th = 46, 24
        bg_color = Theme.ACCENT_GREEN if value else Theme.BG_TERTIARY
        pygame.draw.rect(screen, bg_color, (x, y, tw, th), border_radius=th // 2)
        pygame.draw.rect(screen, Theme.CARD_BORDER, (x, y, tw, th),
                         1, border_radius=th // 2)
        thumb_x = x + tw - th + 2 if value else x + 2
        tc = (255, 255, 255) if value else Theme.TEXT_MUTED
        pygame.draw.circle(screen, tc, (thumb_x + th // 2 - 2, y + th // 2), th // 2 - 3)

    def _draw_confirm(self, screen, w, h) -> None:
        draw_overlay(screen, 200)
        card_w, card_h = 480, 180
        cx = (w - card_w) // 2
        cy = (h - card_h) // 2
        draw_card(screen, (cx, cy, card_w, card_h))
        pygame.draw.rect(screen, Theme.ACCENT_RED,
                         (cx, cy, card_w, 4), border_radius=4)

        tf = FontCache.get("Segoe UI", 20, bold=True)
        draw_text(screen, "Are you sure?", tf, Theme.TEXT_PRIMARY,
                  w // 2, cy + 40, align="center")

        mf = FontCache.get("Segoe UI", 13)
        draw_text(screen, "This cannot be undone.", mf, Theme.TEXT_MUTED,
                  w // 2, cy + 75, align="center")

        hf = FontCache.get("Segoe UI", 13, bold=True)
        draw_text(screen, "Enter = Confirm   |   Esc = Cancel",
                  hf, Theme.TEXT_SECONDARY, w // 2, cy + 118, align="center")

        timer_f = FontCache.get("Segoe UI", 11)
        secs    = max(0, self._confirm_timer)
        draw_text(screen, f"Auto-cancel in {secs:.0f}s...",
                  timer_f, Theme.TEXT_MUTED, w // 2, cy + 148, align="center")

    # ------------------------------------------------------------------
    # Input
    # ------------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type != pygame.KEYDOWN:
            if event.type == pygame.MOUSEWHEEL:
                self._scroll = max(0, min(self._max_scroll,
                                          self._scroll - event.y * 40))
            return

        key = event.key

        # Confirmation dialog
        if self._confirm_action:
            if key == pygame.K_RETURN:
                self._execute_action(self._confirm_action)
                self._confirm_action = None
            elif key in (pygame.K_ESCAPE, pygame.K_q):
                self._confirm_action = None
            return

        if key in (pygame.K_q, pygame.K_ESCAPE, pygame.K_BACKSPACE):
            self.engine.pop_scene()
            return

        if not self._interactive:
            return

        if key == pygame.K_DOWN:
            self._selected = min(len(self._interactive) - 1, self._selected + 1)
        elif key == pygame.K_UP:
            self._selected = max(0, self._selected - 1)
        elif key in (pygame.K_LEFT, pygame.K_RIGHT):
            self._adjust(key == pygame.K_RIGHT)
        elif key in (pygame.K_RETURN, pygame.K_SPACE):
            self._activate()

    def _current_row(self) -> _Row | None:
        if not self._interactive:
            return None
        idx = self._interactive[self._selected]
        return self._rows[idx]

    def _adjust(self, right: bool) -> None:
        row = self._current_row()
        s   = self.settings
        if not s or not row:
            return

        if isinstance(row, _SliderRow):
            val = s.get(row.key, 0.0)
            val = round(val + (row.step if right else -row.step), 2)
            val = max(0.0, min(1.0, val))
            s.set(row.key, val)

        elif isinstance(row, _ToggleRow):
            s.set(row.key, not s.get(row.key, False))

        elif isinstance(row, _SelectorRow):
            val  = str(s.get(row.key, row.options[0]))
            if row.key == "fps_cap":
                val = "Unlimited" if val == "0" else val
            opts = row.options
            idx  = opts.index(val) if val in opts else 0
            if right:
                idx = min(len(opts) - 1, idx + 1)
            else:
                idx = max(0, idx - 1)
            new_val = opts[idx]
            if row.key == "fps_cap":
                new_val = "0" if new_val == "Unlimited" else new_val
            s.set(row.key, int(new_val) if row.key == "fps_cap" else new_val)

        elif isinstance(row, _ActionRow):
            self._request_confirm(row.action_id)

    def _activate(self) -> None:
        row = self._current_row()
        s   = self.settings
        if not s or not row:
            return

        if isinstance(row, _ToggleRow):
            s.set(row.key, not s.get(row.key, False))

        elif isinstance(row, _ActionRow):
            self._request_confirm(row.action_id)

    def _request_confirm(self, action_id: str) -> None:
        self._confirm_action = action_id
        self._confirm_timer  = 6.0

    def _execute_action(self, action_id: str) -> None:
        if action_id == "reset_stats" and self.stats:
            self.stats.reset_all()
            self._show_status("Stats reset!")
        elif action_id == "reset_ach" and self.achievements:
            self.achievements.reset_all()
            self._show_status("Achievements reset!")
        elif action_id == "reset_all":
            if self.stats:        self.stats.reset_all()
            if self.achievements: self.achievements.reset_all()
            if self.settings:     self.settings.reset_to_defaults()
            self._show_status("Full reset complete!")

    def _show_status(self, msg: str) -> None:
        self._status_msg   = msg
        self._status_timer = 2.5
