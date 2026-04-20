"""알 선택 화면 — 맵 선택 / 포진 선택 / 알 개수 / 알 종류(중복 허용) 선택."""
from __future__ import annotations
import math, random, pygame
from core.constants import *
from core.egg import calc_uses, BASE_ABILITY_USES, NO_SCALE_TYPES


def _mk_font(name, size, bold=False):
    try:
        return pygame.font.SysFont(name, size, bold=bold)
    except Exception:
        return pygame.font.Font(None, size + 4)


def _lt(color, f=1.5):
    return tuple(min(255, int(c * f)) for c in color[:3])


SELECTABLE_EGGS = list(EGG_INFO.keys())


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

        self.selected_map  = 0
        self.selected_form = 0          # 포진 인덱스
        self.egg_count     = EGGS_PER_PLAYER

        # 선택 리스트 (중복 허용 → list, 같은 타입 여러 개 OK)
        self.p1_selected: list[str] = []
        self.p2_selected: list[str] = []
        self.tab = 0   # 0=P1, 1=P2 (멀티)

        self.hov_egg:    str | None = None
        self.hov_back    = False
        self.hov_start   = False
        self.hov_minus   = False
        self.hov_plus    = False
        self.hov_map:    int | None = None
        self.hov_form:   int | None = None

        self.font_title = _mk_font("malgungothic", 26, bold=True)
        self.font_sec   = _mk_font("malgungothic", 16, bold=True)
        self.font_body  = _mk_font("malgungothic", 13)
        self.font_sm    = _mk_font("malgungothic", 11)
        self.font_btn   = _mk_font("malgungothic", 15, bold=True)
        self.font_num   = _mk_font("malgungothic", 20, bold=True)

        self._build_layout()

        if mode == "single":
            self._ai_pick()

    # ── AI 자동 선택 ─────────────────────────────────────────────
    def _ai_pick(self):
        pool = SELECTABLE_EGGS[:]
        random.shuffle(pool)
        self.p2_selected = (pool * 2)[:self.egg_count]

    # ── 레이아웃 계산 ─────────────────────────────────────────────
    def _build_layout(self):
        cx = self.w // 2
        from core.map_system import MAP_DEFS, FORMATION_DEFS

        # ── 전체 섹션 높이 예산 ──
        # 제목: 50px
        # 섹션 레이블 + 카드:  맵(74) + 포진(60) + 개수(42) + 알팔레트(160) + AI(30)
        # 여백 사이사이: 넉넉하게 배분
        y = 58   # 첫 섹션 시작

        GAP_LABEL = 8    # 레이블 → 카드 간격
        GAP_SEC   = 22   # 섹션 → 다음 섹션 간격

        # ── 맵 카드 행 ──
        n_maps  = len(MAP_DEFS)
        map_cw  = min(200, (self.w - 80) // n_maps - 10)
        map_ch  = 68
        map_gap = 10
        total_mw = n_maps * map_cw + (n_maps - 1) * map_gap
        map_x0   = cx - total_mw // 2
        self._map_label_y = y
        map_y = y + 22
        self.map_rects = [
            pygame.Rect(map_x0 + i * (map_cw + map_gap), map_y, map_cw, map_ch)
            for i in range(n_maps)
        ]
        y = map_y + map_ch + GAP_SEC

        # ── 포진 카드 행 ──
        n_forms  = len(FORMATION_DEFS)
        form_cw  = min(180, (self.w - 80) // n_forms - 10)
        form_ch  = 52
        form_gap = 10
        total_fw = n_forms * form_cw + (n_forms - 1) * form_gap
        form_x0  = cx - total_fw // 2
        self._form_label_y = y
        form_y = y + 22
        self.form_rects = [
            pygame.Rect(form_x0 + i * (form_cw + form_gap), form_y, form_cw, form_ch)
            for i in range(n_forms)
        ]
        y = form_y + form_ch + GAP_SEC

        # ── 알 개수 행 ──
        self._cnt_label_y = y
        cnt_y = y + 22
        self.minus_rect = pygame.Rect(cx - 72, cnt_y, 34, 34)
        self.plus_rect  = pygame.Rect(cx + 38, cnt_y, 34, 34)
        self.count_rect = pygame.Rect(cx - 30, cnt_y, 68, 34)
        y = cnt_y + 34 + GAP_SEC

        # ── 탭 / 알 선택 안내 ──
        self._tab_label_y = y
        tab_y = y + 22
        self.tab_rects = [
            pygame.Rect(cx - 130, tab_y, 118, 28),
            pygame.Rect(cx + 12,  tab_y, 118, 28),
        ]
        y = tab_y + 28 + GAP_LABEL

        # ── 알 팔레트 ──
        egg_cols = 5
        egg_cw   = min(140, (self.w - 60) // egg_cols - 8)
        egg_ch   = 52
        eg       = 8
        total_ew = egg_cols * (egg_cw + eg) - eg
        palette_x = cx - total_ew // 2
        self.egg_rects: dict[str, pygame.Rect] = {}
        for i, key in enumerate(SELECTABLE_EGGS):
            col = i % egg_cols
            row = i // egg_cols
            rx  = palette_x + col * (egg_cw + eg)
            ry  = y + row * (egg_ch + eg)
            self.egg_rects[key] = pygame.Rect(rx, ry, egg_cw, egg_ch)

        last_row = (len(SELECTABLE_EGGS) - 1) // egg_cols
        self.ai_label_y = y + (last_row + 1) * (egg_ch + eg) + 6

        # ── 뒤로 / 시작 버튼 ──
        bw, bh = 150, 44
        self.back_rect  = pygame.Rect(36, self.h - bh - 14, bw, bh)
        self.start_rect = pygame.Rect(self.w - 36 - bw, self.h - bh - 14, bw, bh)

    # ── 이벤트 처리 ───────────────────────────────────────────────
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
            self.hov_form  = next((i for i, r in enumerate(self.form_rects)
                                   if r.collidepoint(p)), None)

        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            return "back"

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            p = event.pos
            if self.back_rect.collidepoint(p):  return "back"
            if self.start_rect.collidepoint(p): return self._build_config()

            # 맵 선택
            for i, r in enumerate(self.map_rects):
                if r.collidepoint(p):
                    self.selected_map = i

            # 포진 선택
            for i, r in enumerate(self.form_rects):
                if r.collidepoint(p):
                    self.selected_form = i

            # 알 개수
            if self.minus_rect.collidepoint(p):
                self.egg_count = max(MIN_EGGS, self.egg_count - 1)
                self._on_count_change()
            if self.plus_rect.collidepoint(p):
                self.egg_count = min(MAX_EGGS, self.egg_count + 1)
                self._on_count_change()

            # 탭 (멀티)
            if self.mode == "multi":
                for i, r in enumerate(self.tab_rects):
                    if r.collidepoint(p):
                        self.tab = i

            # 알 클릭 — 중복 허용: 클릭마다 1개 추가, 우클릭으로 1개 제거

        if event.type == pygame.MOUSEBUTTONDOWN:
            p = event.pos
            for key, r in self.egg_rects.items():
                if r.collidepoint(p):
                    if event.button == 1:   # 좌클릭 = 추가
                        self._add_egg(key)
                    elif event.button == 3: # 우클릭 = 제거
                        self._remove_egg(key)
                    break

        return None

    def _on_count_change(self):
        if self.mode == "single":
            self._ai_pick()
            while len(self.p1_selected) > self.egg_count:
                self.p1_selected.pop()
        else:
            while len(self.p1_selected) > self.egg_count:
                self.p1_selected.pop()
            while len(self.p2_selected) > self.egg_count:
                self.p2_selected.pop()

    def _cur_list(self) -> list[str]:
        if self.mode == "single":
            return self.p1_selected
        return self.p1_selected if self.tab == 0 else self.p2_selected

    def _add_egg(self, key: str):
        lst = self._cur_list()
        if len(lst) < self.egg_count:
            lst.append(key)

    def _remove_egg(self, key: str):
        lst = self._cur_list()
        for i in range(len(lst) - 1, -1, -1):
            if lst[i] == key:
                lst.pop(i)
                return

    def _fill(self, lst: list[str]) -> list[str]:
        result = lst[:]
        pool = SELECTABLE_EGGS * 3
        random.shuffle(pool)
        for t in pool:
            if len(result) >= self.egg_count:
                break
            result.append(t)
        return result[:self.egg_count]

    def _build_config(self) -> dict:
        p1 = self._fill(self.p1_selected)
        p2 = (self.p2_selected[:] if self.mode == "single"
               else self._fill(self.p2_selected))
        return {
            "mode":      self.mode,
            "map_index": self.selected_map,
            "formation": self.selected_form,
            "egg_count": self.egg_count,
            "p1_eggs":   p1,
            "p2_eggs":   p2,
        }

    # ── 그리기 ───────────────────────────────────────────────────
    def draw(self):
        self.tick += 1
        s  = self.screen
        cx = self.w // 2
        s.fill(self.C_BG)

        mode_label = "싱글플레이" if self.mode == "single" else "멀티플레이"
        t = self.font_title.render(f"게임 설정  ({mode_label})", True, self.C_TITLE)
        s.blit(t, t.get_rect(center=(cx, 32)))

        self._draw_map_row(s, cx)
        self._draw_form_row(s, cx)
        self._draw_count_row(s, cx)
        self._draw_egg_palette(s, cx)
        if self.mode == "single":
            self._draw_ai_preview(s)
        self._draw_bottom_buttons(s)

    def _draw_map_row(self, s, cx):
        from core.map_system import MAP_DEFS
        sec = self.font_sec.render("◆ 맵 선택", True, (160, 200, 255))
        s.blit(sec, (self.map_rects[0].x, self._map_label_y))
        for i, (r, md) in enumerate(zip(self.map_rects, MAP_DEFS)):
            sel = (i == self.selected_map)
            hov = (self.hov_map == i)
            bg  = tuple(min(255, int(c*1.35)) for c in md["color"]) if (sel or hov) else md["color"]
            pygame.draw.rect(s, bg, r, border_radius=7)
            bc  = self.C_SEL if sel else ((90,130,190) if hov else self.C_BORD)
            pygame.draw.rect(s, bc, r, 2 if not sel else 3, border_radius=7)
            nm = self.font_body.render(md["name"], True, (230,245,255) if sel else (170,195,230))
            ds = self.font_sm.render(md["desc"][:16], True, (100,125,165))
            s.blit(nm, nm.get_rect(center=(r.centerx, r.y+20)))
            s.blit(ds, ds.get_rect(center=(r.centerx, r.y+44)))
            if sel:
                s.blit(self.font_sm.render("✔", True, self.C_SEL), (r.x+4, r.y+3))

    def _draw_form_row(self, s, cx):
        from core.map_system import FORMATION_DEFS
        sec = self.font_sec.render("◆ 포진 선택", True, (160, 200, 255))
        s.blit(sec, (self.form_rects[0].x, self._form_label_y))
        patterns = ["─────", "↑↓↑↓↑", "↓↑↓↑↓", "↑↓─↓↑"]
        for i, (r, fd) in enumerate(zip(self.form_rects, FORMATION_DEFS)):
            sel = (i == self.selected_form)
            hov = (self.hov_form == i)
            bg  = (45, 55, 110) if (sel or hov) else (22, 28, 58)
            bc  = self.C_SEL if sel else ((80,110,180) if hov else self.C_BORD)
            pygame.draw.rect(s, bg, r, border_radius=6)
            pygame.draw.rect(s, bc, r, 2 if sel else 1, border_radius=6)
            nm  = self.font_body.render(fd["name"], True, (220,240,255) if sel else (160,185,220))
            pat = self.font_sm.render(patterns[i], True, (120,160,220))
            s.blit(nm, nm.get_rect(center=(r.centerx, r.y+16)))
            s.blit(pat, pat.get_rect(center=(r.centerx, r.y+34)))
            if sel:
                s.blit(self.font_sm.render("✔", True, self.C_SEL), (r.x+3, r.y+2))

    def _draw_count_row(self, s, cx):
        sec = self.font_sec.render("◆ 알 개수", True, (160, 200, 255))
        s.blit(sec, (self.minus_rect.x - 4, self._cnt_label_y))
        for r, sym, hov in [(self.minus_rect,"－",self.hov_minus),
                             (self.plus_rect, "＋",self.hov_plus)]:
            pygame.draw.rect(s, (50,70,140) if hov else (30,45,100), r, border_radius=5)
            pygame.draw.rect(s, (80,120,200), r, 1, border_radius=5)
            t = self.font_num.render(sym, True, (200,220,255))
            s.blit(t, t.get_rect(center=r.center))
        pygame.draw.rect(s, self.C_CARD, self.count_rect, border_radius=5)
        pygame.draw.rect(s, self.C_BORD, self.count_rect, 1, border_radius=5)
        ct = self.font_num.render(str(self.egg_count), True, (100,220,180))
        s.blit(ct, ct.get_rect(center=self.count_rect.center))

    def _draw_egg_palette(self, s, cx):
        if self.mode == "multi":
            for i, (r, (lbl, col)) in enumerate(zip(
                    self.tab_rects, [("P1 (파랑)", C_P1), ("P2 (빨강)", C_P2)])):
                act = (i == self.tab)
                pygame.draw.rect(s, col if act else (22,32,62), r, border_radius=5)
                pygame.draw.rect(s, col, r, 2, border_radius=5)
                t = self.font_body.render(lbl, True, (255,255,255) if act else (130,150,195))
                s.blit(t, t.get_rect(center=r.center))
            cur_lst = self.p1_selected if self.tab == 0 else self.p2_selected
            hl_col  = C_P1 if self.tab == 0 else C_P2
            cnt_t = self.font_body.render(
                f"선택: {len(cur_lst)}/{self.egg_count}  (좌클릭=추가 우클릭=제거)",
                True, hl_col)
            s.blit(cnt_t, (self.tab_rects[1].right + 8, self.tab_rects[0].centery - 7))
        else:
            cur_lst = self.p1_selected
            hl_col  = C_P1
            sec = self.font_sec.render(
                f"◆ 내 알 선택 (P1)  {len(cur_lst)}/{self.egg_count}  "
                f"좌클릭=추가  우클릭=제거",
                True, (160,200,255))
            s.blit(sec, (self.tab_rects[0].x, self._tab_label_y))

        # 팔레트 카드
        for key, r in self.egg_rects.items():
            ec      = EGG_COLORS.get(key, (180,180,180))
            count_in_cur = self._cur_list().count(key)
            hov     = (key == self.hov_egg)

            bg = tuple(min(255, int(c*0.6)) for c in ec) if count_in_cur else \
                 ((32,44,88) if hov else (18,26,54))
            pygame.draw.rect(s, bg, r, border_radius=6)
            bc = hl_col if count_in_cur else ((80,110,180) if hov else self.C_BORD)
            pygame.draw.rect(s, bc, r, 2 if count_in_cur else 1, border_radius=6)

            # 알 원
            pygame.draw.circle(s, ec, (r.x+16, r.centery), 12)
            pygame.draw.circle(s, _lt(ec), (r.x+12, r.centery-4), 4)

            # 이름 + 능력 횟수
            nm = self.font_sm.render(EGG_INFO[key]["name"], True,
                                     (230,245,255) if count_in_cur else (145,165,195))
            s.blit(nm, (r.x+32, r.y+5))

            uses = calc_uses(key, self.egg_count)
            if uses > 0:
                us_col = (255,210,80) if uses >= 3 else (180,220,255)
                us_t = self.font_sm.render(f"×{uses}", True, us_col)
                s.blit(us_t, (r.x+32, r.y+22))
            else:
                ds = self.font_sm.render(EGG_INFO[key]["desc"][:6], True, (80,105,145))
                s.blit(ds, (r.x+32, r.y+22))

            # 선택 수 뱃지
            if count_in_cur > 0:
                badge = self.font_sm.render(f"×{count_in_cur}", True, hl_col)
                s.blit(badge, (r.right - badge.get_width() - 3, r.y+3))

    def _draw_ai_preview(self, s):
        y   = self.ai_label_y
        px0 = min(r.x for r in self.egg_rects.values())
        lbl = self.font_sec.render("AI (P2) 선택:", True, (220, 100, 100))
        s.blit(lbl, (px0, y))
        px = px0 + 92
        for et in self.p2_selected:
            if px + 28 > self.w - 30:
                break
            ec = EGG_COLORS.get(et, (180, 180, 180))
            pygame.draw.circle(s, ec, (px + 12, y + 10), 11)
            t = self.font_sm.render(EGG_INFO[et]["name"][:2], True, (255, 255, 255))
            s.blit(t, t.get_rect(center=(px + 12, y + 10)))
            px += 28

    def _draw_bottom_buttons(self, s):
        bc = self.C_BACK_H if self.hov_back else self.C_BACK_N
        pygame.draw.rect(s, bc, self.back_rect, border_radius=8)
        pygame.draw.rect(s, (100,140,230), self.back_rect, 2, border_radius=8)
        t = self.font_btn.render("← 뒤로", True, (200,215,255))
        s.blit(t, t.get_rect(center=self.back_rect.center))

        gc = self.C_GO_H if self.hov_start else self.C_GO_N
        pygame.draw.rect(s, gc, self.start_rect, border_radius=8)
        pygame.draw.rect(s, (100,220,130), self.start_rect, 2, border_radius=8)
        t = self.font_btn.render("게임 시작 ▶", True, (180,255,200))
        s.blit(t, t.get_rect(center=self.start_rect.center))