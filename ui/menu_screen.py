# ui/menu_screen.py
"""
홈 화면: 시작 / 설명 / 설정 / 종료 버튼
"""
from __future__ import annotations
import math, pygame
from core.constants import *


def _mk_font(name: str, size: int, bold=False):
    try:
        return pygame.font.SysFont(name, size, bold=bold)
    except Exception:
        return pygame.font.Font(None, size + 4)


class MenuScreen:
    """메인 홈 화면."""

    BTN_W, BTN_H = 280, 60
    BTN_GAP = 18

    BUTTONS = [
        ("start",    "▶  게임 시작",   (0.36, 0.70, 0.10, 0.10)),
        ("howto",    "📖  게임 설명",   (0.36, 0.70, 0.10, 0.10)),
        ("settings", "⚙  설  정",      (0.36, 0.70, 0.10, 0.10)),
        ("quit",     "✕  종  료",      (0.36, 0.70, 0.10, 0.10)),
    ]

    # 팔레트
    C_BG1   = (8,  12, 28)
    C_BG2   = (14, 20, 50)
    C_GLOW  = (60, 110, 255)
    C_TITLE = (210, 230, 255)
    C_SUB   = (120, 150, 200)
    C_BTN_N = (22,  30,  65)
    C_BTN_H = (38,  55, 120)
    C_BTN_T = (200, 215, 255)

    BTN_COLORS = {
        "start":    ((30, 80, 170),  (50, 120, 240),  (180, 220, 255)),
        "howto":    ((20, 70, 130),  (35, 100, 190),  (170, 210, 255)),
        "settings": ((20, 65, 120),  (32,  95, 175),  (160, 205, 255)),
        "quit":     ((90, 20,  20),  (160, 35,  35),  (255, 170, 170)),
    }

    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.w = screen.get_width()
        self.h = screen.get_height()
        self.tick = 0

        self.font_title = _mk_font("malgungothic", 72, bold=True)
        self.font_sub   = _mk_font("malgungothic", 22)
        self.font_btn   = _mk_font("malgungothic", 24, bold=True)
        self.font_sm    = _mk_font("malgungothic", 16)

        self._build_buttons()
        self.hovered: str | None = None

        # 별 (배경 파티클)
        import random
        self.stars = [
            (random.randint(0, self.w), random.randint(0, self.h),
             random.uniform(0.3, 1.8), random.uniform(0, math.pi * 2))
            for _ in range(160)
        ]

    def _build_buttons(self):
        total_h = len(self.BUTTONS) * self.BTN_H + (len(self.BUTTONS) - 1) * self.BTN_GAP
        start_y = int(self.h * 0.54)
        cx = self.w // 2
        self.rects: dict[str, pygame.Rect] = {}
        for i, (key, _, _) in enumerate(self.BUTTONS):
            y = start_y + i * (self.BTN_H + self.BTN_GAP)
            rect = pygame.Rect(0, 0, self.BTN_W, self.BTN_H)
            rect.centerx = cx
            rect.y = y
            self.rects[key] = rect

    def handle_event(self, event: pygame.event.Event) -> str | None:
        """반환값: 'start' | 'howto' | 'settings' | 'quit' | None"""
        if event.type == pygame.MOUSEMOTION:
            mx, my = event.pos
            self.hovered = None
            for key, rect in self.rects.items():
                if rect.collidepoint(mx, my):
                    self.hovered = key
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            for key, rect in self.rects.items():
                if rect.collidepoint(mx, my):
                    return key
        return None

    def draw(self):
        self.tick += 1
        s = self.screen

        # ── 배경 그라데이션 ──
        for y in range(0, self.h, 3):
            t = y / self.h
            r = int(self.C_BG1[0] * (1 - t) + self.C_BG2[0] * t)
            g = int(self.C_BG1[1] * (1 - t) + self.C_BG2[1] * t)
            b = int(self.C_BG1[2] * (1 - t) + self.C_BG2[2] * t)
            pygame.draw.rect(s, (r, g, b), (0, y, self.w, 3))

        # ── 별 ──
        for (sx, sy, br, ph) in self.stars:
            alpha = int(120 + 100 * math.sin(self.tick * 0.02 + ph))
            c = int(br * alpha)
            c = max(0, min(255, c))
            pygame.draw.circle(s, (c, c, c + 30), (int(sx), int(sy)), 1)

        # ── 중앙 글로우 원 ──
        cx = self.w // 2
        glow_y = int(self.h * 0.28)
        for r_off in range(120, 0, -8):
            alpha_ratio = (120 - r_off) / 120
            gc = (int(20 * alpha_ratio), int(40 * alpha_ratio), int(100 * alpha_ratio))
            glow_surf = pygame.Surface((r_off * 2, r_off * 2), pygame.SRCALPHA)
            pygame.draw.circle(glow_surf, (*gc, int(30 * alpha_ratio)),
                               (r_off, r_off), r_off)
            s.blit(glow_surf, (cx - r_off, glow_y - r_off))

        # ── 타이틀 ──
        wobble = math.sin(self.tick * 0.04) * 3
        title_surf = self.font_title.render("알까기 능력물", True, self.C_TITLE)
        shadow = self.font_title.render("알까기 능력물", True, (20, 30, 80))
        tx = title_surf.get_rect(center=(cx, int(self.h * 0.25))).x
        ty = int(self.h * 0.25) - title_surf.get_height() // 2 + int(wobble)
        s.blit(shadow, (tx + 3, ty + 4))
        s.blit(title_surf, (tx, ty))

        sub = self.font_sub.render("◈  두 플레이어의 알 능력 대결  ◈", True, self.C_SUB)
        s.blit(sub, sub.get_rect(center=(cx, int(self.h * 0.37))))

        # ── 버튼 ──
        for key, label, _ in self.BUTTONS:
            rect = self.rects[key]
            cn, ch, ct = self.BTN_COLORS[key]
            hov = (self.hovered == key)
            bg = ch if hov else cn
            border_col = ct

            # 버튼 배경
            pygame.draw.rect(s, bg, rect, border_radius=12)
            pygame.draw.rect(s, border_col, rect, 2, border_radius=12)

            # 호버 시 내부 글로우
            if hov:
                g_surf = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
                pygame.draw.rect(g_surf, (*ct, 25), (0, 0, rect.w, rect.h),
                                 border_radius=12)
                s.blit(g_surf, rect.topleft)

            txt = self.font_btn.render(label, True, ct if hov else (180, 200, 235))
            s.blit(txt, txt.get_rect(center=rect.center))

        # ── 하단 안내 ──
        tip = self.font_sm.render("ESC: 종료   |   R: 재시작", True, (60, 80, 130))
        s.blit(tip, tip.get_rect(center=(cx, self.h - 22)))