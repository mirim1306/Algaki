# ui/buttons.py
from __future__ import annotations
import pygame
from core.constants import C_BTN, C_BTN_HOV, C_BTN_ACT, C_WHITE, C_GRAY, C_HIGHLIGHT

class Button:
    def __init__(self, x: int, y: int, w: int, h: int, label: str,
                 color=C_BTN, hover_color=C_BTN_HOV, active_color=C_BTN_ACT,
                 font_size: int = 18):
        self.rect = pygame.Rect(x, y, w, h)
        self.label = label
        self.color = color
        self.hover_color = hover_color
        self.active_color = active_color
        self.hovered = False
        self.active  = False
        try:
            self.font = pygame.font.SysFont("malgungothic", font_size)
        except Exception:
            self.font = pygame.font.Font(None, font_size + 4)

    def update(self, mx: int, my: int):
        self.hovered = self.rect.collidepoint(mx, my)

    def draw(self, screen: pygame.Surface):
        col = self.active_color if self.active else (self.hover_color if self.hovered else self.color)
        pygame.draw.rect(screen, col, self.rect, border_radius=8)
        pygame.draw.rect(screen, C_HIGHLIGHT if self.active else C_GRAY,
                         self.rect, 2, border_radius=8)
        txt_col = C_HIGHLIGHT if self.active else C_WHITE
        txt = self.font.render(self.label, True, txt_col)
        screen.blit(txt, txt.get_rect(center=self.rect.center))

    def is_clicked(self, event: pygame.event.Event) -> bool:
        return (event.type == pygame.MOUSEBUTTONDOWN and
                event.button == 1 and
                self.rect.collidepoint(event.pos))


def make_action_buttons() -> dict[str, Button]:
    """게임 중 사용할 행동 버튼. 레이아웃은 render 시 재조정."""
    from core.constants import BOARD_RIGHT, BOARD_BOTTOM, BOARD_LEFT
    bw, bh = 140, 40
    margin = 10
    cx = (BOARD_LEFT + BOARD_RIGHT) // 2
    by = BOARD_BOTTOM + 6
    return {
        "shoot":   Button(cx - bw - margin, by, bw, bh, "발사 모드"),
        "ability": Button(cx + margin,       by, bw, bh, "능력 사용"),
        "confirm": Button(cx - bw // 2,      by + bh + 6, bw, bh, "확인 / 발동"),
        "cancel":  Button(cx + bw // 2 + 6,  by + bh + 6, bw - 10, bh - 4, "취소"),
    }