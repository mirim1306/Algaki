from __future__ import annotations
import pygame
from core.constants import C_BTN, C_BTN_HOV, C_BTN_ACT, C_WHITE, C_GRAY, C_HIGHLIGHT

class Button:
    def __init__(self, x: int, y: int, w: int, h: int, label: str,
                 color=C_BTN, hover_color=C_BTN_HOV, active_color=C_BTN_ACT,
                 font_size: int = 17):
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
        col = (self.active_color if self.active
               else (self.hover_color if self.hovered else self.color))
        pygame.draw.rect(screen, col, self.rect, border_radius=7)
        pygame.draw.rect(screen, C_HIGHLIGHT if self.active else C_GRAY,
                         self.rect, 2, border_radius=7)
        txt_col = C_HIGHLIGHT if self.active else C_WHITE
        txt = self.font.render(self.label, True, txt_col)
        screen.blit(txt, txt.get_rect(center=self.rect.center))

    def is_clicked(self, event: pygame.event.Event) -> bool:
        return (event.type == pygame.MOUSEBUTTONDOWN
                and event.button == 1
                and self.rect.collidepoint(event.pos))


def make_action_buttons() -> dict[str, Button]:
    """
      (Renderer.BTN_ZONE_H=56 ):
      / : BOARD_BOTTOM+4 ~ +30  (26px )
      / : BOARD_BOTTOM+32 ~ +54 (22px )
    """
    import core.constants as _c
    bb   = _c.BOARD_BOTTOM
    cx   = (_c.BOARD_LEFT + _c.BOARD_RIGHT) // 2
    bw1, bh1 = 130, 26
    bw2, bh2 = 120, 22
    gap  = 8

    return {
        "shoot":   Button(cx - bw1 - gap, bb + 4,  bw1, bh1, "발사 모드"),
        "ability": Button(cx + gap,        bb + 4,  bw1, bh1, "능력 사용"),
        "confirm": Button(cx - bw2 - gap,  bb + 32, bw2, bh2, "/"),
        "cancel":  Button(cx + gap,        bb + 32, bw2, bh2, "취  소"),
    }