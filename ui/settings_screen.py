"""설정 화면."""
from __future__ import annotations
import math, pygame
from core.constants import *


def _mk_font(name, size, bold=False):
    try:
        return pygame.font.SysFont(name, size, bold=bold)
    except Exception:
        return pygame.font.Font(None, size + 4)


class Settings:
    """전역 설정값 컨테이너."""
    bgm_volume:   int = 50    # 0~100
    sfx_volume:   int = 70
    show_fps:     bool = True
    show_grid:    bool = False
    fullscreen:   bool = True
    friction_lvl: int = 1     # 0=, 1=, 2=


_SETTINGS = Settings()


def get_settings() -> Settings:
    return _SETTINGS


class SettingsScreen:
    C_BG    = (8,  12, 28)
    C_TITLE = (210, 230, 255)
    C_LABEL = (160, 185, 235)
    C_VAL   = (100, 220, 180)
    C_BORD  = (40,  60, 120)
    C_CARD  = (16,  22, 52)
    C_BTN_N = (30,  45, 100)
    C_BTN_H = (55,  80, 170)

    FRICTION_LABELS = [" ()", "", " ()"]

    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.w = screen.get_width()
        self.h = screen.get_height()
        self.s = _SETTINGS
        self.tick = 0
        self.hovered: str | None = None

        self.font_title = _mk_font("malgungothic", 36, bold=True)
        self.font_label = _mk_font("malgungothic", 22)
        self.font_val   = _mk_font("malgungothic", 20, bold=True)
        self.font_btn   = _mk_font("malgungothic", 20, bold=True)

        self._build_rows()

    def _build_rows(self):
        cx = self.w // 2
        row_h   = 72
        start_y = 120

        self.rows = [
            ("bgm_volume",   "BGM 볼륨",    "slider"),
            ("sfx_volume",   "효과음 볼륨", "slider"),
            ("show_fps",     "FPS 표시",    "toggle"),
            ("show_grid",    "그리드 표시", "toggle"),
            ("friction_lvl", "마찰력",      "cycle"),
        ]

        card_w   = int(self.w * 0.60)   #
        pad      = 16                   #
        lbl_w    = 180                  #
        btn_w    = 36                   # - / +
        val_w    = 56                   #
        gap      = 8                    #
        card_x0  = cx - card_w // 2

        self.rects: dict[str, dict] = {}
        for i, (key, label, typ) in enumerate(self.rows):
            y    = start_y + i * row_h
            card = pygame.Rect(card_x0, y, card_w, row_h - 6)

            if typ == "slider":
                # [card_x0+pad+lbl_w] [gap] [minus] [gap] [bar] [gap] [plus] [gap] [val]
                cx0      = card_x0 + pad + lbl_w + gap
                minus_x  = cx0
                bar_x    = minus_x + btn_w + gap
                plus_x   = card_x0 + card_w - pad - val_w - gap - btn_w
                bar_w    = plus_x - gap - bar_x
                bar_w    = max(40, bar_w)

                minus_r = pygame.Rect(minus_x, y + 17, btn_w, 32)
                plus_r  = pygame.Rect(plus_x,  y + 17, btn_w, 32)

                self.rects[key] = {
                    "card":  card,
                    "bar_x": bar_x,
                    "bar_w": bar_w,
                    "bar_y": y + 28,
                    "val_x": card_x0 + card_w - pad - val_w + 4,
                    "val_y": y + 22,
                    "minus": minus_r,
                    "plus":  plus_r,
                }

            elif typ == "toggle":
                toggle_w = 72
                toggle_r = pygame.Rect(card_x0 + card_w - pad - toggle_w,
                                       y + 16, toggle_w, 36)
                self.rects[key] = {"card": card, "toggle": toggle_r}

            elif typ == "cycle":
                # [] [ ] [>]
                left_r  = pygame.Rect(card_x0 + pad + lbl_w + gap,
                                      y + 17, btn_w, 32)
                right_r = pygame.Rect(card_x0 + card_w - pad - btn_w,
                                      y + 17, btn_w, 32)
                self.rects[key] = {"card": card, "left": left_r, "right": right_r}

        bw, bh = 160, 46
        self.back_rect = pygame.Rect(cx - bw // 2, self.h - bh - 16, bw, bh)
        self.hov_back  = False

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEMOTION:
            mx, my = event.pos
            self.hov_back = self.back_rect.collidepoint(mx, my)
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.back_rect.collidepoint(event.pos):
                return True
            self._handle_click(event.pos)
        return False

    def _handle_click(self, pos):
        mx, my = pos
        for key, label, typ in self.rows:
            info = self.rects[key]
            if typ == "slider":
                if info["minus"].collidepoint(pos):
                    val = getattr(self.s, key)
                    setattr(self.s, key, max(0, val - 10))
                elif info["plus"].collidepoint(pos):
                    val = getattr(self.s, key)
                    setattr(self.s, key, min(100, val + 10))
            elif typ == "toggle":
                if info["toggle"].collidepoint(pos):
                    setattr(self.s, key, not getattr(self.s, key))
            elif typ == "cycle":
                if info["left"].collidepoint(pos):
                    val = getattr(self.s, key)
                    setattr(self.s, key, (val - 1) % 3)
                elif info["right"].collidepoint(pos):
                    val = getattr(self.s, key)
                    setattr(self.s, key, (val + 1) % 3)

    def draw(self):
        self.tick += 1
        s = self.screen
        s.fill(self.C_BG)

        title = self.font_title.render("설  정", True, self.C_TITLE)
        s.blit(title, title.get_rect(center=(self.w // 2, 60)))

        for key, label, typ in self.rows:
            info = self.rects[key]
            #
            pygame.draw.rect(s, self.C_CARD, info["card"], border_radius=8)
            pygame.draw.rect(s, self.C_BORD, info["card"], 1, border_radius=8)

            lbl = self.font_label.render(label, True, self.C_LABEL)
            s.blit(lbl, (info["card"].x + 16, info["card"].y + 16))

            if typ == "slider":
                val = getattr(self.s, key)
                bx  = info["bar_x"]
                bw  = info["bar_w"]
                by  = info["bar_y"]
                #
                pygame.draw.rect(s, (30, 40, 80), (bx, by, bw, 10), border_radius=5)
                fill_w = max(0, int(bw * val / 100))
                pygame.draw.rect(s, (60, 140, 240), (bx, by, fill_w, 10), border_radius=5)
                #
                handle_x = bx + fill_w
                pygame.draw.circle(s, (120, 180, 255), (handle_x, by + 5), 7)
                # - +
                for r, sym in [(info["minus"], "−"), (info["plus"], "+")]:
                    pygame.draw.rect(s, self.C_BTN_N, r, border_radius=6)
                    pygame.draw.rect(s, (80, 120, 200), r, 1, border_radius=6)
                    t = self.font_val.render(sym, True, (200, 220, 255))
                    s.blit(t, t.get_rect(center=r.center))
                #  (  )
                vt = self.font_val.render(f"{val}%", True, self.C_VAL)
                s.blit(vt, (info["val_x"], info["val_y"]))

            elif typ == "toggle":
                val = getattr(self.s, key)
                tr = info["toggle"]
                bg = (30, 130, 70) if val else (80, 30, 30)
                pygame.draw.rect(s, bg, tr, border_radius=18)
                pygame.draw.rect(s, (100, 180, 140) if val else (160, 80, 80), tr, 2, border_radius=18)
                tt = self.font_val.render("ON" if val else "OFF", True,
                                          (150, 255, 180) if val else (255, 140, 140))
                s.blit(tt, tt.get_rect(center=tr.center))

            elif typ == "cycle":
                val = getattr(self.s, key)
                for r, sym in [(info["left"], ""), (info["right"], ">")]:
                    pygame.draw.rect(s, self.C_BTN_N, r, border_radius=6)
                    pygame.draw.rect(s, (80, 120, 200), r, 1, border_radius=6)
                    t = self.font_val.render(sym, True, (200, 220, 255))
                    s.blit(t, t.get_rect(center=r.center))
                vt = self.font_val.render(self.FRICTION_LABELS[val], True, self.C_VAL)
                mid_x = (info["left"].right + info["right"].left) // 2
                mid_y = info["left"].centery
                s.blit(vt, vt.get_rect(center=(mid_x, mid_y)))

        #
        bc = self.C_BTN_H if self.hov_back else self.C_BTN_N
        pygame.draw.rect(s, bc, self.back_rect, border_radius=10)
        pygame.draw.rect(s, (100, 140, 230), self.back_rect, 2, border_radius=10)
        bt = self.font_btn.render("<- ", True, (200, 215, 255))
        s.blit(bt, bt.get_rect(center=self.back_rect.center))