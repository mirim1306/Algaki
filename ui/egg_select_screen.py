# ui/egg_select_screen.py
"""
알 선택 화면
 - 맵 선택 (3종)
 - 알 개수 선택 (4~10)
 - 어떤 알을 가져갈지 선택 (멀티: 직접 / 싱글: AI 자동)
"""
from __future__ import annotations
import math, random, pygame
from core.constants import *


def _mk_font(name, size, bold=False):
    try:
        return pygame.font.SysFont(name, size, bold=bold)
    except Exception:
        return pygame.font.Font(None, size + 4)


# 선택 가능 알 타입 목록 (normal 포함)
SELECTABLE_EGGS = list(EGG_INFO.keys())

# 맵 정의
MAPS = [
    ("기본 맵",   "평범한 직사각형 보드",         (28, 36, 70)),
    ("협곡 맵",   "중앙에 장애물이 있는 보드",      (28, 50, 40)),
    ("미러 맵",   "좌우 대칭 특수 구조",           (50, 28, 60)),
]

MIN_EGGS = 4
MAX_EGGS = 10


class EggSelectScreen:
    C_BG    = (8,  12, 28)
    C_TITLE = (210, 230, 255)
    C_SUB   = (120, 150, 200)
    C_CARD  = (16,  22, 52)
    C_BORD  = (40,  60, 120)
    C_SEL   = (60, 130, 240)
    C_BACK_N = (30, 45, 100)
    C_BACK_H = (55, 80, 170)
    C_START_N = (28, 80, 40)
    C_START_H = (50, 150, 70)

    def __init__(self, screen: pygame.Surface, mode: str):
        """mode: 'single' | 'multi'"""
        self.screen = screen
        self.w = screen.get_width()
        self.h = screen.get_height()
        self.mode = mode
        self.tick = 0

        # 선택 상태
        self.selected_map: int = 0
        self.egg_count: int = EGGS_PER_PLAYER
        # 각 플레이어의 알 선택 (멀티: [p1_types], [p2_types])
        self.p1_selected: list[str] = []
        self.p2_selected: list[str] = []
        self.current_player_tab: int = 0   # 0=P1, 1=P2 (멀티용)

        self.hovered_egg: str | None = None
        self.hov_back  = False
        self.hov_start = False
        self.hov_plus  = False
        self.hov_minus = False

        self.font_title  = _mk_font("malgungothic", 30, bold=True)
        self.font_sec    = _mk_font("malgungothic", 20, bold=True)
        self.font_body   = _mk_font("malgungothic", 15)
        self.font_sm     = _mk_font("malgungothic", 13)
        self.font_btn    = _mk_font("malgungothic", 18, bold=True)
        self.font_num    = _mk_font("malgungothic", 24, bold=True)

        self._build_layout()

        if mode == "single":
            self._ai_pick_eggs()

    # ── AI 자동 선택 ──────────────────────────────────────────────
    def _ai_pick_eggs(self):
        pool = SELECTABLE_EGGS[:]
        random.shuffle(pool)
        chosen = pool[:self.egg_count]
        if "normal" not in chosen:
            chosen[0] = "normal"
        self.p2_selected = chosen[:]

    def _build_layout(self):
        cx = self.w // 2
        # 맵 선택 행
        map_card_w = 200; map_card_h = 80; map_gap = 16
        total_map_w = len(MAPS) * map_card_w + (len(MAPS) - 1) * map_gap
        self.map_rects: list[pygame.Rect] = []
        for i in range(len(MAPS)):
            x = cx - total_map_w // 2 + i * (map_card_w + map_gap)
            self.map_rects.append(pygame.Rect(x, 85, map_card_w, map_card_h))

        # 알 개수 조절
        self.minus_rect = pygame.Rect(cx - 80, 200, 40, 40)
        self.plus_rect  = pygame.Rect(cx + 40, 200, 40, 40)
        self.count_rect = pygame.Rect(cx - 35, 200, 70, 40)

        # 알 팔레트 (선택 가능한 알 격자)
        egg_cols = 5
        egg_w = 120; egg_h = 56; eg = 10
        palette_w = egg_cols * (egg_w + eg) - eg
        palette_x = cx - palette_w // 2
        palette_y = 290
        self.egg_rects: dict[str, pygame.Rect] = {}
        for i, key in enumerate(SELECTABLE_EGGS):
            col = i % egg_cols
            row = i // egg_cols
            x = palette_x + col * (egg_w + eg)
            y = palette_y + row * (egg_h + eg)
            self.egg_rects[key] = pygame.Rect(x, y, egg_w, egg_h)

        # P1/P2 탭 (멀티)
        self.tab_rects = [
            pygame.Rect(cx - 130, 255, 120, 32),
            pygame.Rect(cx + 10,  255, 120, 32),
        ]

        # 뒤로 / 시작 버튼
        bw, bh = 150, 46
        self.back_rect  = pygame.Rect(40, self.h - bh - 14, bw, bh)
        self.start_rect = pygame.Rect(self.w - 40 - bw, self.h - bh - 14, bw, bh)

    # ── 이벤트 처리 ───────────────────────────────────────────────
    def handle_event(self, event: pygame.event.Event):
        """반환: None | 'back' | dict(game config)"""
        if event.type == pygame.MOUSEMOTION:
            mx, my = event.pos
            self.hovered_egg = None
            for key, r in self.egg_rects.items():
                if r.collidepoint(mx, my):
                    self.hovered_egg = key
            self.hov_back  = self.back_rect.collidepoint(mx, my)
            self.hov_start = self.start_rect.collidepoint(mx, my)
            self.hov_minus = self.minus_rect.collidepoint(mx, my)
            self.hov_plus  = self.plus_rect.collidepoint(mx, my)

        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            return "back"

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            # 뒤로
            if self.back_rect.collidepoint(pos):
                return "back"
            # 시작
            if self.start_rect.collidepoint(pos):
                return self._build_config()
            # 맵
            for i, r in enumerate(self.map_rects):
                if r.collidepoint(pos):
                    self.selected_map = i
            # 알 개수
            if self.minus_rect.collidepoint(pos):
                self.egg_count = max(MIN_EGGS, self.egg_count - 1)
                self._on_count_change()
            if self.plus_rect.collidepoint(pos):
                self.egg_count = min(MAX_EGGS, self.egg_count + 1)
                self._on_count_change()
            # 탭 (멀티)
            if self.mode == "multi":
                for i, r in enumerate(self.tab_rects):
                    if r.collidepoint(pos):
                        self.current_player_tab = i
            # 알 토글 (멀티 직접 선택)
            if self.mode == "multi":
                for key, r in self.egg_rects.items():
                    if r.collidepoint(pos):
                        self._toggle_egg(key)
        return None

    def _on_count_change(self):
        if self.mode == "single":
            self._ai_pick_eggs()
        else:
            # 초과분 제거
            while len(self.p1_selected) > self.egg_count:
                self.p1_selected.pop()
            while len(self.p2_selected) > self.egg_count:
                self.p2_selected.pop()

    def _toggle_egg(self, key: str):
        lst = self.p1_selected if self.current_player_tab == 0 else self.p2_selected
        if key in lst:
            lst.remove(key)
        else:
            if len(lst) < self.egg_count:
                lst.append(key)

    def _build_config(self) -> dict:
        # 멀티: 미선택 슬롯은 랜덤 채우기
        if self.mode == "multi":
            p1 = self.p1_selected[:]
            p2 = self.p2_selected[:]
            pool = SELECTABLE_EGGS[:]
            random.shuffle(pool)
            for p in (p1, p2):
                needed = self.egg_count - len(p)
                extras = [e for e in pool if e not in p]
                random.shuffle(extras)
                p.extend(extras[:needed])
                if "normal" not in p:
                    p[0] = "normal"
        else:
            # 싱글: p1 직접 선택 (부족하면 채움), p2 = AI
            p1 = self.p1_selected[:]
            pool = [e for e in SELECTABLE_EGGS if e not in p1]
            random.shuffle(pool)
            p1.extend(pool[:self.egg_count - len(p1)])
            if "normal" not in p1:
                p1[0] = "normal"
            p2 = self.p2_selected[:]
        return {
            "mode": self.mode,
            "map_index": self.selected_map,
            "egg_count": self.egg_count,
            "p1_eggs": p1,
            "p2_eggs": p2,
        }

    # ── 그리기 ───────────────────────────────────────────────────
    def draw(self):
        self.tick += 1
        s = self.screen
        s.fill(self.C_BG)
        cx = self.w // 2

        mode_label = "싱글플레이" if self.mode == "single" else "멀티플레이"
        title = self.font_title.render(f"게임 설정  ({mode_label})", True, self.C_TITLE)
        s.blit(title, title.get_rect(center=(cx, 48)))

        # ── 맵 선택 ──
        sec = self.font_sec.render("◆ 맵 선택", True, (160, 200, 255))
        s.blit(sec, (self.map_rects[0].x, 68))
        for i, (name, desc, bg) in enumerate(MAPS):
            r = self.map_rects[i]
            sel = (i == self.selected_map)
            pygame.draw.rect(s, bg, r, border_radius=8)
            bord = self.C_SEL if sel else self.C_BORD
            pygame.draw.rect(s, bord, r, 2 if not sel else 3, border_radius=8)
            nm = self.font_body.render(name, True,
                                       (220, 240, 255) if sel else (160, 185, 220))
            ds = self.font_sm.render(desc, True, (120, 145, 185))
            s.blit(nm, nm.get_rect(center=(r.centerx, r.y + 24)))
            s.blit(ds, ds.get_rect(center=(r.centerx, r.y + 52)))
            if sel:
                mark = self.font_sm.render("✔", True, self.C_SEL)
                s.blit(mark, (r.x + 6, r.y + 4))

        # ── 알 개수 ──
        sec2 = self.font_sec.render("◆ 알 개수", True, (160, 200, 255))
        s.blit(sec2, (self.minus_rect.x - 10, 178))
        for r, sym, hov in [(self.minus_rect, "－", self.hov_minus),
                             (self.plus_rect,  "＋", self.hov_plus)]:
            pygame.draw.rect(s, (50, 70, 140) if hov else (30, 45, 100), r, border_radius=6)
            pygame.draw.rect(s, (80, 120, 200), r, 1, border_radius=6)
            t = self.font_num.render(sym, True, (200, 220, 255))
            s.blit(t, t.get_rect(center=r.center))
        pygame.draw.rect(s, self.C_CARD, self.count_rect, border_radius=6)
        pygame.draw.rect(s, self.C_BORD, self.count_rect, 1, border_radius=6)
        ct = self.font_num.render(str(self.egg_count), True, (100, 220, 180))
        s.blit(ct, ct.get_rect(center=self.count_rect.center))

        # ── 알 선택 ──
        y_sec3 = 268
        if self.mode == "multi":
            sec3 = self.font_sec.render("◆ 알 선택 (직접 고르세요)", True, (160, 200, 255))
            s.blit(sec3, (self.egg_rects[SELECTABLE_EGGS[0]].x, y_sec3 - 22))
            # 탭
            for i, (label, col) in enumerate([("P1 (파랑)", C_P1), ("P2 (빨강)", C_P2)]):
                r = self.tab_rects[i]
                active = (i == self.current_player_tab)
                bg = col if active else (25, 35, 65)
                pygame.draw.rect(s, bg, r, border_radius=6)
                pygame.draw.rect(s, col, r, 2, border_radius=6)
                t = self.font_body.render(label, True,
                                          (255, 255, 255) if active else (140, 160, 200))
                s.blit(t, t.get_rect(center=r.center))

            current_list = self.p1_selected if self.current_player_tab == 0 else self.p2_selected
            cnt_col = C_P1 if self.current_player_tab == 0 else C_P2
            cnt_txt = self.font_body.render(
                f"선택됨: {len(current_list)}/{self.egg_count}개", True, cnt_col)
            s.blit(cnt_txt, (self.tab_rects[1].right + 12, self.tab_rects[0].centery - 8))
        else:
            sec3 = self.font_sec.render("◆ 내 알 선택 (P1) — AI(P2) 자동 결정", True, (160, 200, 255))
            s.blit(sec3, (self.egg_rects[SELECTABLE_EGGS[0]].x, y_sec3 - 22))
            current_list = self.p1_selected
            cnt_col = C_P1
            cnt_txt = self.font_body.render(
                f"선택됨: {len(current_list)}/{self.egg_count}개", True, cnt_col)
            s.blit(cnt_txt, (self.egg_rects[SELECTABLE_EGGS[0]].x, y_sec3 + 2))

        # 알 팔레트
        if self.mode == "multi":
            current_list = self.p1_selected if self.current_player_tab == 0 else self.p2_selected
            other_list   = self.p2_selected if self.current_player_tab == 0 else self.p1_selected
            hl_col       = C_P1 if self.current_player_tab == 0 else C_P2
        else:
            current_list = self.p1_selected
            other_list   = []
            hl_col       = C_P1

        for key, r in self.egg_rects.items():
            ec = EGG_COLORS.get(key, (180, 180, 180))
            info = EGG_INFO[key]
            in_cur   = key in current_list
            in_other = key in other_list
            hov = (key == self.hovered_egg)

            # 배경
            if in_cur:
                bg = tuple(min(255, int(c * 0.7)) for c in ec)
            else:
                bg = (20, 28, 58) if not hov else (30, 42, 85)
            pygame.draw.rect(s, bg, r, border_radius=8)

            # 테두리
            if in_cur:
                pygame.draw.rect(s, hl_col, r, 2, border_radius=8)
            elif in_other:
                other_col = C_P2 if self.current_player_tab == 0 else C_P1
                pygame.draw.rect(s, other_col, r, 1, border_radius=8)
            else:
                pygame.draw.rect(s, self.C_BORD, r, 1, border_radius=8)

            # 알 원
            pygame.draw.circle(s, ec, (r.x + 20, r.centery), 14)
            pygame.draw.circle(s, tuple(min(255, int(c*1.4)) for c in ec),
                               (r.x + 16, r.centery - 4), 5)

            # 이름
            nt = self.font_sm.render(info["name"], True,
                                     (230, 245, 255) if in_cur else (150, 165, 195))
            s.blit(nt, (r.x + 38, r.y + 8))
            dt = self.font_sm.render(info["desc"][:8] + ("…" if len(info["desc"]) > 8 else ""),
                                     True, (100, 120, 160))
            s.blit(dt, (r.x + 38, r.y + 26))

            if in_cur:
                ck = self.font_sm.render("✔", True, hl_col)
                s.blit(ck, (r.right - 16, r.y + 4))

        # AI 선택 표시 (싱글)
        if self.mode == "single":
            ai_label = self.font_sec.render("AI (P2) 선택 알:", True, (220, 100, 100))
            ai_y = self.egg_rects[SELECTABLE_EGGS[0]].bottom + 16
            s.blit(ai_label, (self.egg_rects[SELECTABLE_EGGS[0]].x, ai_y))
            for i, etype in enumerate(self.p2_selected):
                ec = EGG_COLORS.get(etype, (180, 180, 180))
                bx = self.egg_rects[SELECTABLE_EGGS[0]].x + i * 38
                by = ai_y + 28
                if bx + 34 > self.w - 40:
                    break
                pygame.draw.circle(s, ec, (bx + 16, by + 16), 14)
                nt = self.font_sm.render(EGG_INFO[etype]["name"][:2], True, (255, 255, 255))
                s.blit(nt, nt.get_rect(center=(bx + 16, by + 16)))

        # ── 버튼 ──
        bc = self.C_BACK_H if self.hov_back else self.C_BACK_N
        pygame.draw.rect(s, bc, self.back_rect, border_radius=10)
        pygame.draw.rect(s, (100, 140, 230), self.back_rect, 2, border_radius=10)
        bt = self.font_btn.render("← 뒤로", True, (200, 215, 255))
        s.blit(bt, bt.get_rect(center=self.back_rect.center))

        sc = self.C_START_H if self.hov_start else self.C_START_N
        pygame.draw.rect(s, sc, self.start_rect, border_radius=10)
        pygame.draw.rect(s, (100, 220, 130), self.start_rect, 2, border_radius=10)
        st = self.font_btn.render("게임 시작 ▶", True, (180, 255, 200))
        s.blit(st, st.get_rect(center=self.start_rect.center))