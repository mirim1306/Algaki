"""모드 선택 화면 – 싱글플레이 / 멀티플레이."""
from __future__ import annotations
import math, pygame
from core.constants import *


def _mk_font(name, size, bold=False):
    try:
        return pygame.font.SysFont(name, size, bold=bold)
    except Exception:
        return pygame.font.Font(None, size + 4)


class ModeSelectScreen:
    C_BG     = (8,  12, 28)
    C_TITLE  = (210, 230, 255)
    C_SUB    = (120, 150, 200)
    C_BACK_N = (30,  45, 100)
    C_BACK_H = (55,  80, 170)

    MODE_CARDS = [
        ("single", "싱글플레이",  "AI 대전",
         "컴퓨터와 대결합니다.\n알 선택은 AI가 자동으로 결정합니다.",
         (30, 60, 140), (55, 100, 220), (160, 200, 255)),
        ("multi",  "멀티플레이", "2인 대전",
         "같은 PC에서 두 플레이어가 대결합니다.\n각자 원하는 알을 골라보세요!",
         (80, 28,  28), (150, 50,  50), (255, 170, 170)),
    ]

    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.w = screen.get_width()
        self.h = screen.get_height()
        self.tick = 0
        self.hovered: str | None = None

        self.font_title = _mk_font("malgungothic", 36, bold=True)
        self.font_sub   = _mk_font("malgungothic", 20)
        self.font_card  = _mk_font("malgungothic", 26, bold=True)
        self.font_icon  = _mk_font("malgungothic", 20)
        self.font_body  = _mk_font("malgungothic", 16)
        self.font_btn   = _mk_font("malgungothic", 20, bold=True)

        self._build_layout()

    def _build_layout(self):
        cx = self.w // 2
        card_w = int(self.w * 0.28)
        card_h = int(self.h * 0.42)
        gap = int(self.w * 0.05)
        cy = int(self.h * 0.52)

        self.card_rects: dict[str, pygame.Rect] = {}
        total_w = card_w * 2 + gap
        start_x = cx - total_w // 2
        for i, (key, *_) in enumerate(self.MODE_CARDS):
            x = start_x + i * (card_w + gap)
            rect = pygame.Rect(x, cy - card_h // 2, card_w, card_h)
            self.card_rects[key] = rect

        bw, bh = 160, 46
        self.back_rect = pygame.Rect(cx - bw // 2, self.h - bh - 16, bw, bh)
        self.hov_back = False

    def handle_event(self, event: pygame.event.Event) -> str | None:
        """반환: 'single' | 'multi' | 'back' | None"""
        if event.type == pygame.MOUSEMOTION:
            mx, my = event.pos
            self.hovered = None
            for key, rect in self.card_rects.items():
                if rect.collidepoint(mx, my):
                    self.hovered = key
            self.hov_back = self.back_rect.collidepoint(mx, my)
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            return "back"
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.back_rect.collidepoint(event.pos):
                return "back"
            for key, rect in self.card_rects.items():
                if rect.collidepoint(event.pos):
                    return key
        return None

    def draw(self):
        self.tick += 1
        s = self.screen
        s.fill(self.C_BG)

        cx = self.w // 2

        # 타이틀
        title = self.font_title.render("모드 선택", True, self.C_TITLE)
        s.blit(title, title.get_rect(center=(cx, 55)))
        sub = self.font_sub.render("원하는 게임 모드를 선택하세요", True, self.C_SUB)
        s.blit(sub, sub.get_rect(center=(cx, 100)))

        # 모드 카드
        for key, name, icon_label, desc, cn, ch, ct in self.MODE_CARDS:
            rect = self.card_rects[key]
            hov = (self.hovered == key)
            bg = ch if hov else cn

            # 글로우
            if hov:
                for r_off in range(18, 0, -4):
                    gs = pygame.Surface((rect.w + r_off * 2, rect.h + r_off * 2), pygame.SRCALPHA)
                    pygame.draw.rect(gs, (*ct, 12),
                                     (0, 0, rect.w + r_off * 2, rect.h + r_off * 2),
                                     border_radius=18)
                    s.blit(gs, (rect.x - r_off, rect.y - r_off))

            # 카드 본체
            pygame.draw.rect(s, bg, rect, border_radius=16)
            pygame.draw.rect(s, ct, rect, 2, border_radius=16)

            # 아이콘 레이블
            icon_t = self.font_icon.render(icon_label, True, ct)
            s.blit(icon_t, icon_t.get_rect(center=(rect.centerx, rect.y + 55)))

            # 카드 이름
            nm = self.font_card.render(name, True, ct)
            s.blit(nm, nm.get_rect(center=(rect.centerx, rect.y + 100)))

            # 구분선
            pygame.draw.line(s, (*ct, 100), (rect.x + 24, rect.y + 120),
                             (rect.right - 24, rect.y + 120), 1)

            # 설명
            for i, line in enumerate(desc.split("\n")):
                bt = self.font_body.render(line, True, (180, 195, 225))
                s.blit(bt, bt.get_rect(center=(rect.centerx, rect.y + 148 + i * 24)))

            # 선택 안내
            if hov:
                sel = self.font_btn.render("▶ 선택", True, ct)
                s.blit(sel, sel.get_rect(center=(rect.centerx, rect.bottom - 36)))

        # 뒤로 가기
        bc = self.C_BACK_H if self.hov_back else self.C_BACK_N
        pygame.draw.rect(s, bc, self.back_rect, border_radius=10)
        pygame.draw.rect(s, (100, 140, 230), self.back_rect, 2, border_radius=10)
        bt = self.font_btn.render("← 뒤로", True, (200, 215, 255))
        s.blit(bt, bt.get_rect(center=self.back_rect.center))