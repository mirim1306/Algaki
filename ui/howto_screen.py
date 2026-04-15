# ui/howto_screen.py
"""게임 설명 화면 – 각 알의 능력 설명."""
from __future__ import annotations
import math, pygame
from core.constants import EGG_INFO, EGG_COLORS, C_P1, C_P2


def _mk_font(name, size, bold=False):
    try:
        return pygame.font.SysFont(name, size, bold=bold)
    except Exception:
        return pygame.font.Font(None, size + 4)


# 알 별 상세 설명
EGG_DETAIL = {
    "normal":    ("일반알",    "특별한 능력 없이 발사만 가능합니다.\n기본기가 탄탄한 만능 알!",                                 "⚪"),
    "barrier":   ("방벽알",    "보드의 빈 위치에 방벽(육각형 장애물)을\n생성합니다. 적의 진로를 막아보세요!",                   "🟩"),
    "seal":      ("봉인알",    "선택한 아군/적 알을 봉인 상태로 만듭니다.\n봉인된 알은 발사·능력 사용이 불가합니다.",             "🔒"),
    "copy":      ("복사알",    "적 알을 클릭 → 그 알의 능력 타입 복사\n아군 알을 클릭 → 그 알의 발사 위력 복사",               "📋"),
    "clone":     ("분신알",    "주변 4방향에 분신을 소환한 뒤\n원본과 분신의 위치를 무작위로 섞습니다.",                        "👥"),
    "bomb":      ("폭탄알",    "보드의 빈 위치에 지뢰를 설치합니다.\n적 알이 폭발 반경 내로 들어오면 폭발!",                   "💣"),
    "invisible": ("투명알",    "알을 투명 상태로 전환합니다.\n투명 상태에서도 발사·충돌은 정상 적용됩니다.",                    "👻"),
    "psycho":    ("염력알",    "선택한 적 알을 즉시 파괴합니다.\n단, 자신도 소멸하고 아군 알 하나가 랜덤 파괴됩니다!",          "🔮"),
    "ice":       ("얼음알",    "선택한 알에 얼음 상태를 부여합니다.\n충돌 시 훨씬 멀리 밀려납니다(반발계수 2배).",              "❄"),
    "magnet":    ("자석알",    "두 알을 자석으로 연결합니다.\n연결된 두 알은 서로를 강하게 끌어당깁니다.",                     "🧲"),
}

COLS = 2
ROWS = 5


class HowToPlayScreen:
    C_BG    = (8,  12, 28)
    C_CARD  = (16, 22, 52)
    C_BORD  = (40, 60, 120)
    C_TITLE = (210, 230, 255)
    C_HEAD  = (160, 200, 255)
    C_BODY  = (150, 165, 195)
    C_BACK_N = (30, 45, 100)
    C_BACK_H = (55, 80, 170)

    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.w = screen.get_width()
        self.h = screen.get_height()
        self.tick = 0
        self.hovered_back = False
        self.scroll = 0          # 스크롤 오프셋
        self.max_scroll = 0

        self.font_title = _mk_font("malgungothic", 36, bold=True)
        self.font_head  = _mk_font("malgungothic", 20, bold=True)
        self.font_body  = _mk_font("malgungothic", 15)
        self.font_btn   = _mk_font("malgungothic", 20, bold=True)
        self.font_em    = _mk_font("malgungothic", 28, bold=True)

        self._build_layout()

    def _build_layout(self):
        margin = 40
        top = 100
        card_w = (self.w - margin * 2 - 20) // COLS
        card_h = 140
        gap = 14
        self.cards: list[tuple[str, pygame.Rect]] = []

        egg_keys = list(EGG_DETAIL.keys())
        for i, key in enumerate(egg_keys):
            col = i % COLS
            row = i // COLS
            x = margin + col * (card_w + 20)
            y = top + row * (card_h + gap)
            self.cards.append((key, pygame.Rect(x, y, card_w, card_h)))

        total_h = top + (len(egg_keys) // COLS + 1) * (card_h + gap)
        self.max_scroll = max(0, total_h - self.h + 80)

        # 뒤로 가기 버튼
        bw, bh = 160, 46
        self.back_rect = pygame.Rect(self.w // 2 - bw // 2, self.h - bh - 12, bw, bh)

    def handle_event(self, event: pygame.event.Event) -> bool:
        """True 반환 시 홈 화면으로 돌아감."""
        if event.type == pygame.MOUSEMOTION:
            mx, my = event.pos
            self.hovered_back = self.back_rect.collidepoint(mx, my)
        if event.type == pygame.MOUSEWHEEL:
            self.scroll = max(0, min(self.max_scroll, self.scroll - event.y * 30))
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.back_rect.collidepoint(event.pos):
                return True
        return False

    def draw(self):
        self.tick += 1
        s = self.screen
        s.fill(self.C_BG)

        # 타이틀
        title = self.font_title.render("◈  알 능력 도감  ◈", True, self.C_TITLE)
        s.blit(title, title.get_rect(center=(self.w // 2, 52)))

        # 카드들 (스크롤 반영)
        clip_rect = pygame.Rect(0, 80, self.w, self.h - 140)
        s.set_clip(clip_rect)
        for key, rect in self.cards:
            shifted = rect.move(0, -self.scroll)
            if shifted.bottom < 80 or shifted.top > self.h - 140:
                continue
            self._draw_card(key, shifted)
        s.set_clip(None)

        # 뒤로 가기 버튼
        bc = self.C_BACK_H if self.hovered_back else self.C_BACK_N
        pygame.draw.rect(s, bc, self.back_rect, border_radius=10)
        pygame.draw.rect(s, (100, 140, 230), self.back_rect, 2, border_radius=10)
        bt = self.font_btn.render("← 뒤로", True, (200, 215, 255))
        s.blit(bt, bt.get_rect(center=self.back_rect.center))

    def _draw_card(self, key: str, rect: pygame.Rect):
        s = self.screen
        name, desc, icon = EGG_DETAIL[key]
        egg_col = EGG_COLORS.get(key, (180, 180, 180))

        # 카드 배경
        pygame.draw.rect(s, self.C_CARD, rect, border_radius=10)
        # 왼쪽 컬러 바
        bar_rect = pygame.Rect(rect.x, rect.y, 6, rect.h)
        pygame.draw.rect(s, egg_col, bar_rect,
                         border_radius=10)
        pygame.draw.rect(s, self.C_BORD, rect, 1, border_radius=10)

        # 아이콘 + 알 색 원
        cx = rect.x + 46
        cy = rect.centery
        pygame.draw.circle(s, tuple(max(0, c - 60) for c in egg_col), (cx, cy), 28)
        pygame.draw.circle(s, egg_col, (cx, cy), 24)
        ico = self.font_em.render(icon, True, (255, 255, 255))
        s.blit(ico, ico.get_rect(center=(cx, cy)))

        # 이름
        head = self.font_head.render(name, True, self.C_HEAD)
        s.blit(head, (rect.x + 88, rect.y + 18))

        # 설명 (줄바꿈 지원)
        lines = desc.split("\n")
        for i, line in enumerate(lines):
            bt = self.font_body.render(line, True, self.C_BODY)
            s.blit(bt, (rect.x + 88, rect.y + 50 + i * 22))