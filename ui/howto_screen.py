"""게임 설명 화면 – 재정의된 알 능력 설명."""
from __future__ import annotations
import math, pygame
from core.constants import EGG_INFO, EGG_COLORS


def _mk_font(name, size, bold=False):
    try:
        return pygame.font.SysFont(name, size, bold=bold)
    except Exception:
        return pygame.font.Font(None, size + 4)


EGG_DETAIL = {
    "normal":    ("일반알",
                  "특별한 능력 없이 발사만 가능합니다.\n기본기가 탄탄한 만능 알!",
                  "⚪"),
    "barrier":   ("방벽알",
                  "원하는 빈 위치에 방벽을 생성합니다.\n알이 있는 곳에는 설치 불가.",
                  "🟩"),
    "seal":      ("봉인알",
                  "지정한 알 1개를 1턴 동안 행동 불가 상태로 만듭니다.\n봉인된 알은 발사·능력 사용 불가.",
                  "🔒"),
    "copy":      ("복사알",
                  "① 적 알 클릭 → 그 알의 능력을 저장.\n   재사용 시 저장한 능력을 발동!\n"
                  "② 아군 알 클릭 → 그 알의 위력(속도)을 저장.\n   다음 발사 시 저장 위력이 합산되어 발사!",
                  "📋"),
    "clone":     ("분신알",
                  "주위에 분신 1개를 소환합니다.\n원본과 분신의 위치를 무작위로 섞어\n어느 것이 진짜인지 모르게 합니다.",
                  "👥"),
    "bomb":      ("폭탄알",
                  "원하는 빈 위치에 지뢰를 설치합니다.\n적 알이 접근하면 폭발해 강하게 밀어냅니다!",
                  "💣"),
    "invisible": ("투명알",
                  "알을 투명 상태로 전환합니다.\n투명 상태에서는 상대가 능력을 사용할 수 없습니다.\n발사는 투명 상태에서도 가능.",
                  "👻"),
    "psycho":    ("염력알",
                  "지정한 적 알을 즉시 파괴합니다.\n단, 반동으로 아군 알 1개도 랜덤 파괴되고\n염력알 자신도 소멸합니다!",
                  "🔮"),
    "ice":       ("얼음알",
                  "지정한 알을 슬립 상태로 만듭니다.\n슬립 상태 알은 충돌 시 훨씬 멀리 밀려납니다\n(반발계수 2배).",
                  "❄"),
    "magnet":    ("자석알",
                  "두 알을 선택해 자석으로 연결합니다.\n연결 즉시 서로를 끌어당기기 시작!",
                  "🧲"),
}

COLS = 2


class HowToPlayScreen:
    C_BG     = (8,  12, 28)
    C_CARD   = (16, 22, 52)
    C_BORD   = (40, 60, 120)
    C_TITLE  = (210, 230, 255)
    C_HEAD   = (160, 200, 255)
    C_BODY   = (150, 165, 195)
    C_BACK_N = (30,  45, 100)
    C_BACK_H = (55,  80, 170)

    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.w = screen.get_width()
        self.h = screen.get_height()
        self.tick = 0
        self.hovered_back = False
        self.scroll     = 0
        self.max_scroll = 0

        self.font_title = _mk_font("malgungothic", 34, bold=True)
        self.font_head  = _mk_font("malgungothic", 19, bold=True)
        self.font_body  = _mk_font("malgungothic", 14)
        self.font_btn   = _mk_font("malgungothic", 19, bold=True)
        self.font_em    = _mk_font("malgungothic", 26, bold=True)

        self._build_layout()

    def _build_layout(self):
        margin  = 36
        top     = 92
        card_w  = (self.w - margin * 2 - 16) // COLS
        # 카드 높이를 설명 줄 수에 맞게 자동
        self.cards: list[tuple[str, pygame.Rect]] = []
        gap = 10
        egg_keys = list(EGG_DETAIL.keys())
        y_cursor = top
        col_y = [top, top]   # 각 컬럼 현재 y

        for i, key in enumerate(egg_keys):
            col = i % COLS
            _, desc, _ = EGG_DETAIL[key]
            n_lines  = len(desc.split("\n"))
            card_h   = 56 + n_lines * 20
            x = margin + col * (card_w + 16)
            y = col_y[col]
            self.cards.append((key, pygame.Rect(x, y, card_w, card_h)))
            col_y[col] += card_h + gap

        total_h     = max(col_y) + 60
        self.max_scroll = max(0, total_h - self.h + 80)

        bw, bh = 160, 44
        self.back_rect = pygame.Rect(self.w // 2 - bw // 2, self.h - bh - 10, bw, bh)

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEMOTION:
            self.hovered_back = self.back_rect.collidepoint(event.pos)
        if event.type == pygame.MOUSEWHEEL:
            self.scroll = max(0, min(self.max_scroll, self.scroll - event.y * 28))
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

        title = self.font_title.render("◈  알 능력 도감  ◈", True, self.C_TITLE)
        s.blit(title, title.get_rect(center=(self.w // 2, 48)))

        clip = pygame.Rect(0, 76, self.w, self.h - 130)
        s.set_clip(clip)
        for key, rect in self.cards:
            shifted = rect.move(0, -self.scroll)
            if shifted.bottom < 76 or shifted.top > self.h - 130:
                continue
            self._draw_card(key, shifted)
        s.set_clip(None)

        bc = self.C_BACK_H if self.hovered_back else self.C_BACK_N
        pygame.draw.rect(s, bc, self.back_rect, border_radius=10)
        pygame.draw.rect(s, (100, 140, 230), self.back_rect, 2, border_radius=10)
        bt = self.font_btn.render("← 뒤로", True, (200, 215, 255))
        s.blit(bt, bt.get_rect(center=self.back_rect.center))

        # 스크롤 힌트
        if self.max_scroll > 0:
            hint = self.font_body.render("▼ 스크롤로 더 보기", True, (80, 100, 160))
            s.blit(hint, hint.get_rect(center=(self.w // 2, self.h - 58)))

    def _draw_card(self, key: str, rect: pygame.Rect):
        s   = self.screen
        name, desc, icon = EGG_DETAIL[key]
        ec  = EGG_COLORS.get(key, (180, 180, 180))

        pygame.draw.rect(s, self.C_CARD, rect, border_radius=9)
        bar = pygame.Rect(rect.x, rect.y, 5, rect.h)
        pygame.draw.rect(s, ec, bar, border_radius=9)
        pygame.draw.rect(s, self.C_BORD, rect, 1, border_radius=9)

        # 아이콘 원
        icx, icy = rect.x + 40, rect.y + rect.h // 2
        pygame.draw.circle(s, tuple(max(0, c - 55) for c in ec), (icx, icy), 26)
        pygame.draw.circle(s, ec, (icx, icy), 22)
        ico = self.font_em.render(icon, True, (255, 255, 255))
        s.blit(ico, ico.get_rect(center=(icx, icy)))

        # 이름
        head = self.font_head.render(name, True, self.C_HEAD)
        s.blit(head, (rect.x + 74, rect.y + 10))

        # 설명 (줄바꿈)
        for i, line in enumerate(desc.split("\n")):
            bt = self.font_body.render(line, True, self.C_BODY)
            s.blit(bt, (rect.x + 74, rect.y + 34 + i * 19))