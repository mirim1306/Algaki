# ui/egg_select_screen.py
"""
알 선택 화면
 - 맵 선택 (3종)
 - 알 개수 선택 (4~10)
 - 어떤 알을 가져갈지 선택 (멀티: P1/P2 직접 / 싱글: P1 직접, P2 AI 자동)
"""
from __future__ import annotations
import math, random, pygame
from core.constants import *


def _mk_font(name, size, bold=False):
    try:
        return pygame.font.SysFont(name, size, bold=bold)
    except Exception:
        return pygame.font.Font(None, size + 4)


SELECTABLE_EGGS = list(EGG_INFO.keys())

MAPS = [
    ("기본 맵",  "평범한 직사각형 보드",     (28, 36, 70)),
    ("협곡 맵",  "중앙에 장애물이 있는 보드", (28, 50, 40)),
    ("미러 맵",  "좌우 대칭 특수 구조",       (50, 28, 60)),
]

MIN_EGGS = 4
MAX_EGGS = 10


class EggSelectScreen:
    C_BG      = (8,  12, 28)
    C_TITLE   = (210, 230, 255)
    C_CARD    = (16,  22, 52)
    C_BORD    = (40,  60, 120)
    C_SEL     = (60, 130, 240)
    C_BACK_N  = (30,  45, 100)
    C_BACK_H  = (55,  80, 170)
    C_START_N = (28,  80, 40)
    C_START_H = (50, 150, 70)

    def __init__(self, screen: pygame.Surface, mode: str):
        self.screen = screen
        self.w = screen.get_width()
        self.h = screen.get_height()
        self.mode  = mode
        self.tick  = 0

        self.selected_map: int       = 0
        self.egg_count: int          = EGGS_PER_PLAYER
        self.p1_selected: list[str]  = []
        self.p2_selected: list[str]  = []
        self.current_player_tab: int = 0

        self.hovered_egg: str | None = None
        self.hov_back  = False
        self.hov_start = False
        self.hov_plus  = False
        self.hov_minus = False

        self.font_title = _mk_font("malgungothic", 30, bold=True)
        self.font_sec   = _mk_font("malgungothic", 20, bold=True)
        self.font_body  = _mk_font("malgungothic", 15)
        self.font_sm    = _mk_font("malgungothic", 13)
        self.font_btn   = _mk_font("malgungothic", 18, bold=True)
        self.font_num   = _mk_font("malgungothic", 24, bold=True)

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

    # ── 레이아웃 ──────────────────────────────────────────────────
    def _build_layout(self):
        cx = self.w // 2

        # 맵 선택 (y=85)
        mw, mh, mg = 200, 80, 16
        total_mw = len(MAPS) * mw + (len(MAPS) - 1) * mg
        self.map_rects: list[pygame.Rect] = [
            pygame.Rect(cx - total_mw // 2 + i * (mw + mg), 85, mw, mh)
            for i in range(len(MAPS))
        ]

        # 알 개수 (y=195)
        self.minus_rect = pygame.Rect(cx - 80, 195, 40, 40)
        self.plus_rect  = pygame.Rect(cx + 40, 195, 40, 40)
        self.count_rect = pygame.Rect(cx - 35, 195, 70, 40)

        # 알 선택 섹션
        section_y = 248   # "◆ 알 선택" 헤더 y

        if self.mode == "multi":
            self.tab_rects = [
                pygame.Rect(cx - 130, section_y + 28, 120, 32),
                pygame.Rect(cx + 10,  section_y + 28, 120, 32),
            ]
            palette_y = section_y + 72
        else:
            self.tab_rects = []
            palette_y = section_y + 48   # 헤더 + 카운터 텍스트 아래

        # 팔레트 격자
        egg_cols = 5
        ew, eh, eg = 130, 58, 10
        pw = egg_cols * (ew + eg) - eg
        px = cx - pw // 2
        self.palette_x = px
        self.palette_y = palette_y

        self.egg_rects: dict[str, pygame.Rect] = {}
        for i, key in enumerate(SELECTABLE_EGGS):
            c = i % egg_cols
            r = i // egg_cols
            self.egg_rects[key] = pygame.Rect(
                px + c * (ew + eg),
                palette_y + r * (eh + eg),
                ew, eh
            )

        # 버튼
        bw, bh = 150, 46
        self.back_rect  = pygame.Rect(40, self.h - bh - 14, bw, bh)
        self.start_rect = pygame.Rect(self.w - 40 - bw, self.h - bh - 14, bw, bh)

    # ── 이벤트 처리 ───────────────────────────────────────────────
    def handle_event(self, event: pygame.event.Event):
        """반환: None | 'back' | dict"""
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

            if self.back_rect.collidepoint(pos):
                return "back"
            if self.start_rect.collidepoint(pos):
                return self._build_config()

            for i, r in enumerate(self.map_rects):
                if r.collidepoint(pos):
                    self.selected_map = i

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

            # 알 토글 — 싱글/멀티 모두 클릭 처리
            for key, r in self.egg_rects.items():
                if r.collidepoint(pos):
                    self._toggle_egg(key)
                    break

        return None

    def _on_count_change(self):
        while len(self.p1_selected) > self.egg_count:
            self.p1_selected.pop()
        if self.mode == "single":
            self._ai_pick_eggs()
        else:
            while len(self.p2_selected) > self.egg_count:
                self.p2_selected.pop()

    def _toggle_egg(self, key: str):
        # 멀티: 현재 탭 기준 / 싱글: 항상 P1
        lst = (self.p1_selected if self.current_player_tab == 0
               else self.p2_selected) if self.mode == "multi" else self.p1_selected
        if key in lst:
            lst.remove(key)
        elif len(lst) < self.egg_count:
            lst.append(key)

    def _build_config(self) -> dict:
        pool = SELECTABLE_EGGS[:]
        random.shuffle(pool)

        if self.mode == "multi":
            p1 = self.p1_selected[:]
            p2 = self.p2_selected[:]
            for p in (p1, p2):
                extras = [e for e in pool if e not in p]
                random.shuffle(extras)
                p.extend(extras[:self.egg_count - len(p)])
                if "normal" not in p:
                    p[0] = "normal"
        else:
            # P1: 직접 선택 + 부족분 채움
            p1 = self.p1_selected[:]
            extras = [e for e in pool if e not in p1]
            random.shuffle(extras)
            p1.extend(extras[:self.egg_count - len(p1)])
            if "normal" not in p1:
                p1[0] = "normal"
            # P2: AI 랜덤
            ai = pool[:]
            random.shuffle(ai)
            p2 = ai[:self.egg_count]
            if "normal" not in p2:
                p2[0] = "normal"

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
        s  = self.screen
        cx = self.w // 2
        s.fill(self.C_BG)

        # 타이틀
        mode_label = "싱글플레이" if self.mode == "single" else "멀티플레이"
        title = self.font_title.render(f"게임 설정  ({mode_label})", True, self.C_TITLE)
        s.blit(title, title.get_rect(center=(cx, 48)))

        # ── 맵 선택 ──
        s.blit(self.font_sec.render("◆ 맵 선택", True, (160, 200, 255)),
               (self.map_rects[0].x, 68))
        for i, (name, desc, bg) in enumerate(MAPS):
            r   = self.map_rects[i]
            sel = (i == self.selected_map)
            pygame.draw.rect(s, bg, r, border_radius=8)
            pygame.draw.rect(s, self.C_SEL if sel else self.C_BORD,
                             r, 3 if sel else 2, border_radius=8)
            s.blit(self.font_body.render(name, True,
                   (220, 240, 255) if sel else (160, 185, 220)),
                   self.font_body.render(name, True, (0,0,0)).get_rect(
                       center=(r.centerx, r.y + 24)))
            s.blit(self.font_sm.render(desc, True, (120, 145, 185)),
                   self.font_sm.render(desc, True, (0,0,0)).get_rect(
                       center=(r.centerx, r.y + 52)))
            if sel:
                s.blit(self.font_sm.render("✔", True, self.C_SEL), (r.x + 6, r.y + 4))

        # ── 알 개수 ──
        s.blit(self.font_sec.render("◆ 알 개수", True, (160, 200, 255)),
               (self.minus_rect.x - 10, 175))
        for r, sym, hov in [(self.minus_rect, "－", self.hov_minus),
                             (self.plus_rect,  "＋", self.hov_plus)]:
            pygame.draw.rect(s, (50, 70, 140) if hov else (30, 45, 100), r, border_radius=6)
            pygame.draw.rect(s, (80, 120, 200), r, 1, border_radius=6)
            t = self.font_num.render(sym, True, (200, 220, 255))
            s.blit(t, t.get_rect(center=r.center))
        pygame.draw.rect(s, self.C_CARD,  self.count_rect, border_radius=6)
        pygame.draw.rect(s, self.C_BORD,  self.count_rect, 1, border_radius=6)
        s.blit(self.font_num.render(str(self.egg_count), True, (100, 220, 180)),
               self.font_num.render(str(self.egg_count), True, (0,0,0)).get_rect(
                   center=self.count_rect.center))

        # ── 알 선택 헤더 ──
        section_y = 248
        if self.mode == "multi":
            s.blit(self.font_sec.render("◆ 알 선택 (직접 고르세요)", True, (160, 200, 255)),
                   (self.palette_x, section_y))
            # 탭
            for i, (label, col) in enumerate([("P1 (파랑)", C_P1), ("P2 (빨강)", C_P2)]):
                r = self.tab_rects[i]
                active = (i == self.current_player_tab)
                pygame.draw.rect(s, col if active else (25, 35, 65), r, border_radius=6)
                pygame.draw.rect(s, col, r, 2, border_radius=6)
                t = self.font_body.render(label, True,
                                          (255, 255, 255) if active else (140, 160, 200))
                s.blit(t, t.get_rect(center=r.center))
            cur_list = self.p1_selected if self.current_player_tab == 0 else self.p2_selected
            cnt_col  = C_P1 if self.current_player_tab == 0 else C_P2
            s.blit(self.font_body.render(f"선택됨: {len(cur_list)}/{self.egg_count}개",
                                         True, cnt_col),
                   (self.tab_rects[1].right + 12, self.tab_rects[0].centery - 8))
        else:
            s.blit(self.font_sec.render("◆ 내 알 선택 (P1) — AI(P2) 자동 결정",
                                         True, (160, 200, 255)),
                   (self.palette_x, section_y))
            s.blit(self.font_body.render(
                       f"선택됨: {len(self.p1_selected)}/{self.egg_count}개",
                       True, C_P1),
                   (self.palette_x, section_y + 26))
            cur_list = self.p1_selected

        # ── 팔레트 ──
        if self.mode == "multi":
            cur_list   = self.p1_selected if self.current_player_tab == 0 else self.p2_selected
            other_list = self.p2_selected if self.current_player_tab == 0 else self.p1_selected
            hl_col     = C_P1 if self.current_player_tab == 0 else C_P2
        else:
            cur_list   = self.p1_selected
            other_list = []
            hl_col     = C_P1

        for key, r in self.egg_rects.items():
            ec       = EGG_COLORS.get(key, (180, 180, 180))
            info     = EGG_INFO[key]
            in_cur   = key in cur_list
            in_other = key in other_list
            hov      = (key == self.hovered_egg)

            bg = (tuple(min(255, int(c * 0.7)) for c in ec) if in_cur
                  else ((30, 42, 85) if hov else (20, 28, 58)))
            pygame.draw.rect(s, bg, r, border_radius=8)

            if in_cur:
                pygame.draw.rect(s, hl_col, r, 2, border_radius=8)
            elif in_other:
                oc = C_P2 if self.current_player_tab == 0 else C_P1
                pygame.draw.rect(s, oc, r, 1, border_radius=8)
            else:
                pygame.draw.rect(s, self.C_BORD, r, 1, border_radius=8)

            # 알 원
            pygame.draw.circle(s, ec, (r.x + 22, r.centery), 15)
            pygame.draw.circle(s, tuple(min(255, int(c * 1.4)) for c in ec),
                               (r.x + 17, r.centery - 5), 5)

            # 텍스트
            s.blit(self.font_sm.render(info["name"], True,
                   (230, 245, 255) if in_cur else (150, 165, 195)),
                   (r.x + 42, r.y + 10))
            short = info["desc"][:10] + ("…" if len(info["desc"]) > 10 else "")
            s.blit(self.font_sm.render(short, True, (100, 120, 160)),
                   (r.x + 42, r.y + 30))
            if in_cur:
                s.blit(self.font_sm.render("✔", True, hl_col), (r.right - 16, r.y + 4))

        # AI 선택 표시 (싱글)
        if self.mode == "single" and self.p2_selected:
            last_r = list(self.egg_rects.values())[-1]
            ai_y   = last_r.bottom + 14
            s.blit(self.font_sec.render("AI (P2) 선택 알:", True, (220, 100, 100)),
                   (self.palette_x, ai_y))
            for i, etype in enumerate(self.p2_selected):
                ec  = EGG_COLORS.get(etype, (180, 180, 180))
                bx  = self.palette_x + i * 40
                by  = ai_y + 30
                if bx + 36 > self.w - 40:
                    break
                pygame.draw.circle(s, ec, (bx + 16, by + 16), 14)
                s.blit(self.font_sm.render(EGG_INFO[etype]["name"][:2], True, (255, 255, 255)),
                       self.font_sm.render(EGG_INFO[etype]["name"][:2], True, (0,0,0)).get_rect(
                           center=(bx + 16, by + 16)))

        # ── 버튼 ──
        for rect, hov, cn, ch, bord, label in [
            (self.back_rect,  self.hov_back,  self.C_BACK_N,  self.C_BACK_H,
             (100, 140, 230), "← 뒤로"),
            (self.start_rect, self.hov_start, self.C_START_N, self.C_START_H,
             (100, 220, 130), "게임 시작 ▶"),
        ]:
            pygame.draw.rect(s, ch if hov else cn, rect, border_radius=10)
            pygame.draw.rect(s, bord, rect, 2, border_radius=10)
            t = self.font_btn.render(label, True,
                                     (180, 255, 200) if "시작" in label else (200, 215, 255))
            s.blit(t, t.get_rect(center=rect.center))