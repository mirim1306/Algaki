# ui/egg_select_screen.py
"""알 선택 화면 — 맵 선택 / 알 개수 / 알 종류 선택."""
from __future__ import annotations
import math, random, pygame
from core.constants import *


def _mk_font(name, size, bold=False):
    try:
        return pygame.font.SysFont(name, size, bold=bold)
    except Exception:
        return pygame.font.Font(None, size + 4)


SELECTABLE_EGGS = list(EGG_INFO.keys())   # 10종


class EggSelectScreen:
    C_BG     = (8,  12, 28)
    C_TITLE  = (210, 230, 255)
    C_CARD   = (16,  22, 52)
    C_BORD   = (40,  60, 120)
    C_SEL    = (60, 130, 240)
    C_BACK_N = (30,  45, 100)
    C_BACK_H = (55,  80, 170)
    C_GO_N   = (22,  70, 36)
    C_GO_H   = (44, 140, 65)

    def __init__(self, screen: pygame.Surface, mode: str):
        self.screen = screen
        self.w = screen.get_width()
        self.h = screen.get_height()
        self.mode  = mode
        self.tick  = 0

        self.selected_map   = 0
        self.egg_count      = EGGS_PER_PLAYER
        self.p1_selected: list[str] = []
        self.p2_selected: list[str] = []
        self.tab = 0   # 0=P1, 1=P2 (멀티용)

        # 호버 상태
        self.hov_egg:   str | None = None
        self.hov_back  = False
        self.hov_start = False
        self.hov_minus = False
        self.hov_plus  = False
        self.hov_map:   int | None = None

        self.font_title = _mk_font("malgungothic", 28, bold=True)
        self.font_sec   = _mk_font("malgungothic", 18, bold=True)
        self.font_body  = _mk_font("malgungothic", 14)
        self.font_sm    = _mk_font("malgungothic", 12)
        self.font_btn   = _mk_font("malgungothic", 17, bold=True)
        self.font_num   = _mk_font("malgungothic", 22, bold=True)

        self._build_layout()

        if mode == "single":
            self._ai_pick()

    # ── AI 자동 선택 ─────────────────────────────────────────────
    def _ai_pick(self):
        pool = SELECTABLE_EGGS[:]
        random.shuffle(pool)
        self.p2_selected = pool[:self.egg_count]

    # ── 레이아웃 계산 ─────────────────────────────────────────────
    def _build_layout(self):
        cx = self.w // 2
        from core.map_system import MAP_DEFS

        # ── 맵 카드 ──
        n_maps   = len(MAP_DEFS)
        map_cw   = min(200, (self.w - 80) // n_maps - 12)
        map_ch   = 72
        map_gap  = 12
        total_mw = n_maps * map_cw + (n_maps-1) * map_gap
        map_x0   = cx - total_mw // 2
        map_y    = 74
        self.map_rects = []
        for i in range(n_maps):
            x = map_x0 + i * (map_cw + map_gap)
            self.map_rects.append(pygame.Rect(x, map_y, map_cw, map_ch))

        # ── 알 개수 ──
        cnt_y = map_y + map_ch + 18
        self.minus_rect = pygame.Rect(cx - 72, cnt_y, 36, 36)
        self.plus_rect  = pygame.Rect(cx + 36, cnt_y, 36, 36)
        self.count_rect = pygame.Rect(cx - 30, cnt_y, 66, 36)

        # ── 탭 (멀티) ──
        tab_y = cnt_y + 44
        self.tab_rects = [
            pygame.Rect(cx - 130, tab_y, 118, 28),
            pygame.Rect(cx + 12,  tab_y, 118, 28),
        ]

        # ── 알 팔레트 ──
        palette_y = tab_y + 36
        egg_cols  = 5
        egg_cw    = min(130, (self.w - 60) // egg_cols - 8)
        egg_ch    = 52
        eg        = 8
        total_ew  = egg_cols * (egg_cw + eg) - eg
        palette_x = cx - total_ew // 2
        self.egg_rects: dict[str, pygame.Rect] = {}
        for i, key in enumerate(SELECTABLE_EGGS):
            col = i % egg_cols
            row = i // egg_cols
            x   = palette_x + col * (egg_cw + eg)
            y   = palette_y + row * (egg_ch + eg)
            self.egg_rects[key] = pygame.Rect(x, y, egg_cw, egg_ch)

        # AI 표시줄 y
        last_row = (len(SELECTABLE_EGGS) - 1) // egg_cols
        self.ai_label_y = palette_y + (last_row + 1) * (egg_ch + eg) + 4

        # ── 뒤로/시작 ──
        bw, bh = 140, 42
        self.back_rect  = pygame.Rect(36, self.h - bh - 12, bw, bh)
        self.start_rect = pygame.Rect(self.w - 36 - bw, self.h - bh - 12, bw, bh)

    # ── 이벤트 ───────────────────────────────────────────────────
    def handle_event(self, event: pygame.event.Event):
        if event.type == pygame.MOUSEMOTION:
            p = event.pos
            self.hov_back  = self.back_rect.collidepoint(p)
            self.hov_start = self.start_rect.collidepoint(p)
            self.hov_minus = self.minus_rect.collidepoint(p)
            self.hov_plus  = self.plus_rect.collidepoint(p)
            self.hov_egg   = next((k for k, r in self.egg_rects.items()
                                   if r.collidepoint(p)), None)
            self.hov_map   = next((i for i, r in enumerate(self.map_rects)
                                   if r.collidepoint(p)), None)

        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            return "back"

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            p = event.pos
            if self.back_rect.collidepoint(p):
                return "back"
            if self.start_rect.collidepoint(p):
                return self._build_config()
            # 맵
            for i, r in enumerate(self.map_rects):
                if r.collidepoint(p):
                    self.selected_map = i
            # 개수
            if self.minus_rect.collidepoint(p):
                self.egg_count = max(MIN_EGGS, self.egg_count - 1)
                self._on_count_change()
            if self.plus_rect.collidepoint(p):
                self.egg_count = min(MAX_EGGS, self.egg_count + 1)
                self._on_count_change()
            # 탭
            if self.mode == "multi":
                for i, r in enumerate(self.tab_rects):
                    if r.collidepoint(p):
                        self.tab = i
            # 알 토글
            if self.mode == "multi":
                for key, r in self.egg_rects.items():
                    if r.collidepoint(p):
                        self._toggle(key)
            elif self.mode == "single":
                for key, r in self.egg_rects.items():
                    if r.collidepoint(p):
                        self._toggle_p1(key)
        return None

    def _on_count_change(self):
        if self.mode == "single":
            self._ai_pick()
        else:
            while len(self.p1_selected) > self.egg_count:
                self.p1_selected.pop()
            while len(self.p2_selected) > self.egg_count:
                self.p2_selected.pop()

    def _toggle(self, key: str):
        lst = self.p1_selected if self.tab == 0 else self.p2_selected
        if key in lst:
            lst.remove(key)
        elif len(lst) < self.egg_count:
            lst.append(key)

    def _toggle_p1(self, key: str):
        if key in self.p1_selected:
            self.p1_selected.remove(key)
        elif len(self.p1_selected) < self.egg_count:
            self.p1_selected.append(key)

    def _fill(self, lst: list[str]) -> list[str]:
        """부족한 슬롯을 랜덤으로 채움."""
        pool = [e for e in SELECTABLE_EGGS if e not in lst]
        random.shuffle(pool)
        result = lst[:]
        while len(result) < self.egg_count and pool:
            result.append(pool.pop())
        return result

    def _build_config(self) -> dict:
        p1 = self._fill(self.p1_selected)
        p2 = (self.p2_selected[:] if self.mode == "single"
               else self._fill(self.p2_selected))
        return {
            "mode":      self.mode,
            "map_index": self.selected_map,
            "egg_count": self.egg_count,
            "p1_eggs":   p1,
            "p2_eggs":   p2,
        }

    # ── 그리기 ───────────────────────────────────────────────────
    def draw(self):
        self.tick += 1
        s = self.screen
        s.fill(self.C_BG)
        cx = self.w // 2

        mode_label = "싱글플레이" if self.mode == "single" else "멀티플레이"
        t = self.font_title.render(f"게임 설정  ({mode_label})", True, self.C_TITLE)
        s.blit(t, t.get_rect(center=(cx, 38)))

        self._draw_map_row(s, cx)
        self._draw_count_row(s, cx)
        self._draw_egg_palette(s, cx)
        if self.mode == "single":
            self._draw_ai_preview(s, cx)
        self._draw_bottom_buttons(s)

    def _draw_map_row(self, s, cx):
        from core.map_system import MAP_DEFS
        sec = self.font_sec.render("◆ 맵 선택", True, (160, 200, 255))
        s.blit(sec, (self.map_rects[0].x, self.map_rects[0].y - 20))

        for i, (r, md) in enumerate(zip(self.map_rects, MAP_DEFS)):
            sel = (i == self.selected_map)
            hov = (self.hov_map == i)
            bg  = tuple(min(255, int(c * 1.4)) for c in md["color"]) if (sel or hov) else md["color"]
            pygame.draw.rect(s, bg, r, border_radius=8)
            bc  = self.C_SEL if sel else ((100, 140, 200) if hov else self.C_BORD)
            pygame.draw.rect(s, bc, r, 2 if not sel else 3, border_radius=8)

            nm = self.font_body.render(md["name"], True,
                                       (230, 245, 255) if sel else (170, 195, 230))
            ds = self.font_sm.render(md["desc"][:16], True, (110, 135, 175))
            s.blit(nm, nm.get_rect(center=(r.centerx, r.y + 22)))
            s.blit(ds, ds.get_rect(center=(r.centerx, r.y + 48)))
            if sel:
                ck = self.font_sm.render("✔", True, self.C_SEL)
                s.blit(ck, (r.x + 5, r.y + 3))

    def _draw_count_row(self, s, cx):
        sec = self.font_sec.render("◆ 알 개수", True, (160, 200, 255))
        s.blit(sec, (self.minus_rect.x - 4, self.minus_rect.y - 22))

        for r, sym, hov in [(self.minus_rect, "－", self.hov_minus),
                             (self.plus_rect,  "＋", self.hov_plus)]:
            pygame.draw.rect(s, (50,70,140) if hov else (30,45,100), r, border_radius=6)
            pygame.draw.rect(s, (80,120,200), r, 1, border_radius=6)
            t = self.font_num.render(sym, True, (200, 220, 255))
            s.blit(t, t.get_rect(center=r.center))

        pygame.draw.rect(s, self.C_CARD, self.count_rect, border_radius=6)
        pygame.draw.rect(s, self.C_BORD, self.count_rect, 1, border_radius=6)
        ct = self.font_num.render(str(self.egg_count), True, (100, 220, 180))
        s.blit(ct, ct.get_rect(center=self.count_rect.center))

    def _draw_egg_palette(self, s, cx):
        if self.mode == "multi":
            # 탭
            for i, (r, (lbl, col)) in enumerate(zip(
                    self.tab_rects,
                    [("P1 (파랑)", C_P1), ("P2 (빨강)", C_P2)])):
                act = (i == self.tab)
                bg  = col if act else (22, 32, 62)
                pygame.draw.rect(s, bg, r, border_radius=5)
                pygame.draw.rect(s, col, r, 2, border_radius=5)
                t = self.font_body.render(lbl, True,
                                          (255,255,255) if act else (130,150,195))
                s.blit(t, t.get_rect(center=r.center))
            cur_lst = self.p1_selected if self.tab == 0 else self.p2_selected
            hl_col  = C_P1 if self.tab == 0 else C_P2
            # 선택 수
            cnt_c = C_P1 if self.tab == 0 else C_P2
            cnt_t = self.font_body.render(
                f"선택: {len(cur_lst)}/{self.egg_count}", True, cnt_c)
            s.blit(cnt_t, (self.tab_rects[1].right + 10,
                           self.tab_rects[0].centery - 8))
            other_lst = self.p2_selected if self.tab == 0 else self.p1_selected
            other_col = C_P2 if self.tab == 0 else C_P1
        else:
            cur_lst   = self.p1_selected
            hl_col    = C_P1
            other_lst = []
            other_col = (100, 100, 100)
            # 안내
            sec = self.font_sec.render(
                f"◆ 내 알 선택 (P1) — {len(cur_lst)}/{self.egg_count}개",
                True, (160, 200, 255))
            s.blit(sec, (self.tab_rects[0].x, self.tab_rects[0].y - 2))

        for key, r in self.egg_rects.items():
            ec  = EGG_COLORS.get(key, (180, 180, 180))
            in_cur   = key in cur_lst
            in_other = key in other_lst
            hov = (key == self.hov_egg)

            # 배경
            if in_cur:
                bg = tuple(min(255, int(c * 0.65)) for c in ec)
            elif hov:
                bg = (32, 44, 88)
            else:
                bg = (18, 26, 54)
            pygame.draw.rect(s, bg, r, border_radius=7)

            # 테두리
            if in_cur:
                pygame.draw.rect(s, hl_col, r, 2, border_radius=7)
            elif in_other:
                pygame.draw.rect(s, other_col, r, 1, border_radius=7)
            else:
                pygame.draw.rect(s, self.C_BORD, r, 1, border_radius=7)

            # 알 원형
            pygame.draw.circle(s, ec, (r.x + 18, r.centery), 13)
            pygame.draw.circle(s, _lt(ec), (r.x+14, r.centery-4), 4)

            # 이름/설명
            nm = self.font_sm.render(EGG_INFO[key]["name"], True,
                                     (230,245,255) if in_cur else (145,165,195))
            ds = self.font_sm.render(EGG_INFO[key]["desc"][:7]+"…"
                                     if len(EGG_INFO[key]["desc"])>7
                                     else EGG_INFO[key]["desc"],
                                     True, (90, 110, 150))
            s.blit(nm, (r.x+36, r.y+6))
            s.blit(ds, (r.x+36, r.y+24))

            if in_cur:
                ck = self.font_sm.render("✔", True, hl_col)
                s.blit(ck, (r.right-14, r.y+4))

    def _draw_ai_preview(self, s, cx):
        y = self.ai_label_y
        lbl = self.font_sec.render("AI (P2) 선택:", True, (220, 100, 100))
        s.blit(lbl, (self.egg_rects[SELECTABLE_EGGS[0]].x, y))
        px = self.egg_rects[SELECTABLE_EGGS[0]].x + 90
        for et in self.p2_selected:
            if px + 30 > self.w - 40:
                break
            ec = EGG_COLORS.get(et, (180,180,180))
            pygame.draw.circle(s, ec, (px+13, y+10), 12)
            t = self.font_sm.render(EGG_INFO[et]["name"][:2], True, (255,255,255))
            s.blit(t, t.get_rect(center=(px+13, y+10)))
            px += 30

    def _draw_bottom_buttons(self, s):
        bc = self.C_BACK_H if self.hov_back else self.C_BACK_N
        pygame.draw.rect(s, bc, self.back_rect, border_radius=9)
        pygame.draw.rect(s, (100,140,230), self.back_rect, 2, border_radius=9)
        t = self.font_btn.render("← 뒤로", True, (200,215,255))
        s.blit(t, t.get_rect(center=self.back_rect.center))

        gc = self.C_GO_H if self.hov_start else self.C_GO_N
        pygame.draw.rect(s, gc, self.start_rect, border_radius=9)
        pygame.draw.rect(s, (100,220,130), self.start_rect, 2, border_radius=9)
        t = self.font_btn.render("게임 시작 ▶", True, (180,255,200))
        s.blit(t, t.get_rect(center=self.start_rect.center))


def _lt(color, f=1.5):
    return tuple(min(255, int(c*f)) for c in color[:3])