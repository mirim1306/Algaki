# ui/renderer.py
"""pygame 화면을 담당하는 렌더러."""
from __future__ import annotations
import math, pygame
from core.constants import *
from core.egg import Egg, Barrier, Mine
from core.game_state import GameState

def _darken(color, factor=0.55):
    return tuple(int(c * factor) for c in color)

def _lighten(color, factor=1.4):
    return tuple(min(255, int(c * factor)) for c in color)

def _blend(c1, c2, t=0.5):
    return tuple(int(c1[i] * (1 - t) + c2[i] * t) for i in range(3))


class Renderer:
    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.w = screen.get_width()
        self.h = screen.get_height()
        self._load_fonts()
        self.particles: list[dict] = []   # 시각 파티클

    def _load_fonts(self):
        pygame.font.init()
        try:
            self.font_lg = pygame.font.SysFont("malgungothic", 26, bold=True)
            self.font_md = pygame.font.SysFont("malgungothic", 18)
            self.font_sm = pygame.font.SysFont("malgungothic", 13)
            self.font_xl = pygame.font.SysFont("malgungothic", 46, bold=True)
        except Exception:
            self.font_lg = pygame.font.Font(None, 28)
            self.font_md = pygame.font.Font(None, 20)
            self.font_sm = pygame.font.Font(None, 14)
            self.font_xl = pygame.font.Font(None, 50)

    # ── 파티클 ──────────────────────────────────────────────────
    def spawn_particles(self, x, y, color, count=10):
        import random
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(1, 5)
            self.particles.append({
                "x": x, "y": y,
                "vx": math.cos(angle) * speed,
                "vy": math.sin(angle) * speed,
                "life": 30, "max": 30,
                "color": color, "r": random.randint(2, 5)
            })

    def update_particles(self):
        alive = []
        for p in self.particles:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["vy"] += 0.15
            p["life"] -= 1
            if p["life"] > 0:
                alive.append(p)
        self.particles = alive

    def draw_particles(self):
        surf = self.screen
        for p in self.particles:
            alpha = int(255 * p["life"] / p["max"])
            r, g, b = p["color"]
            color = (r, g, b)
            pygame.draw.circle(surf, color, (int(p["x"]), int(p["y"])), p["r"])

    # ── 메인 렌더 ────────────────────────────────────────────────
    def render(self, gs: GameState):
        self.update_particles()
        self.screen.fill(C_BG)
        self._draw_board(gs)
        self._draw_mines(gs)
        self._draw_barriers(gs)
        self._draw_magnet_lines(gs)
        self._draw_eggs(gs)
        self.draw_particles()
        self._draw_aim(gs)
        self._draw_hud(gs)
        if gs.phase == STATE_GAMEOVER:
            self._draw_gameover(gs)

    # ── 보드 ────────────────────────────────────────────────────
    def _draw_board(self, gs: GameState):
        board_rect = pygame.Rect(BOARD_LEFT, BOARD_TOP,
                                 BOARD_RIGHT - BOARD_LEFT,
                                 BOARD_BOTTOM - BOARD_TOP)
        pygame.draw.rect(self.screen, C_BOARD, board_rect, border_radius=8)
        pygame.draw.rect(self.screen, C_LINE, board_rect, 2, border_radius=8)
        # 중앙선
        pygame.draw.line(self.screen, C_LINE,
                         (MID_X, BOARD_TOP), (MID_X, BOARD_BOTTOM), 1)

    # ── 지뢰 ────────────────────────────────────────────────────
    def _draw_mines(self, gs: GameState):
        for mine in gs.mines:
            if not mine.active:
                continue
            col = C_P1 if mine.owner == 0 else C_P2
            cx, cy = int(mine.x), int(mine.y)
            pygame.draw.circle(self.screen, _darken(col, 0.4), (cx, cy), mine.r + 4)
            pygame.draw.circle(self.screen, col, (cx, cy), mine.r)
            # 지뢰 심볼
            pygame.draw.circle(self.screen, (20, 20, 20), (cx, cy), mine.r - 3)
            for angle in range(0, 360, 45):
                rad = math.radians(angle)
                x2 = cx + int(math.cos(rad) * (mine.r + 5))
                y2 = cy + int(math.sin(rad) * (mine.r + 5))
                pygame.draw.line(self.screen, col, (cx, cy), (x2, y2), 2)
            txt = self.font_sm.render("💣", True, C_WHITE)
            self.screen.blit(txt, txt.get_rect(center=(cx, cy)))

    # ── 방벽 ────────────────────────────────────────────────────
    def _draw_barriers(self, gs: GameState):
        for b in gs.barriers:
            if not b.active:
                continue
            cx, cy = int(b.x), int(b.y)
            # 육각형 방벽
            pts = [(cx + int(b.r * math.cos(math.radians(60 * i - 30))),
                    cy + int(b.r * math.sin(math.radians(60 * i - 30))))
                   for i in range(6)]
            pygame.draw.polygon(self.screen, (40, 90, 60), pts)
            pygame.draw.polygon(self.screen, (80, 200, 120), pts, 2)
            txt = self.font_sm.render("壁", True, (80, 200, 120))
            self.screen.blit(txt, txt.get_rect(center=(cx, cy)))

    # ── 자석 선 ─────────────────────────────────────────────────
    def _draw_magnet_lines(self, gs: GameState):
        drawn = set()
        for egg in gs.eggs:
            if egg.active and egg.magnet_pair and egg.magnet_pair.active:
                pair = egg.magnet_pair
                key = tuple(sorted([egg.id, pair.id]))
                if key in drawn:
                    continue
                drawn.add(key)
                pygame.draw.line(self.screen, (180, 120, 240),
                                 (int(egg.x), int(egg.y)),
                                 (int(pair.x), int(pair.y)), 2)

    # ── 알 ──────────────────────────────────────────────────────
    def _draw_eggs(self, gs: GameState):
        for egg in gs.eggs:
            if not egg.active:
                continue
            self._draw_single_egg(egg, gs)

    def _draw_single_egg(self, egg: Egg, gs: GameState):
        cx, cy = int(egg.x), int(egg.y)
        selected = (egg is gs.selected_egg or egg is gs.ability_egg)
        col = egg.base_color
        owner_col = C_P1 if egg.owner == 0 else C_P2

        # 투명알 반투명 처리
        if egg.invisible:
            surf = pygame.Surface((egg.r * 2 + 4, egg.r * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(surf, (*col, 70), (egg.r + 2, egg.r + 2), egg.r)
            self.screen.blit(surf, (cx - egg.r - 2, cy - egg.r - 2))
            return

        # 외곽 글로우 (선택됨)
        if selected:
            pygame.draw.circle(self.screen, _lighten(col, 1.8), (cx, cy), egg.r + 6)

        # 주인 테두리
        pygame.draw.circle(self.screen, owner_col, (cx, cy), egg.r + 3)

        # 봉인: 회색 덮기
        draw_col = (100, 100, 120) if egg.sealed else col
        pygame.draw.circle(self.screen, _darken(draw_col, 0.5), (cx, cy), egg.r)
        pygame.draw.circle(self.screen, draw_col, (cx, cy), egg.r - 2)

        # 얼음 오버레이
        if egg.icy:
            ice_surf = pygame.Surface((egg.r * 2, egg.r * 2), pygame.SRCALPHA)
            pygame.draw.circle(ice_surf, (100, 220, 255, 80),
                               (egg.r, egg.r), egg.r)
            self.screen.blit(ice_surf, (cx - egg.r, cy - egg.r))

        # 하이라이트 (광택)
        pygame.draw.circle(self.screen, _lighten(col, 1.6),
                           (cx - egg.r // 3, cy - egg.r // 3), egg.r // 3)

        # 능력 타깃 표시
        if gs.phase == STATE_ABILITY and egg in gs.ability_targets:
            pygame.draw.circle(self.screen, C_HIGHLIGHT, (cx, cy), egg.r + 5, 2)

        # 텍스트 (알 이름 2글자)
        name = EGG_INFO[egg.type]["name"][:2]
        txt = self.font_sm.render(name, True, C_WHITE)
        self.screen.blit(txt, txt.get_rect(center=(cx, cy)))

        # 봉인/얼음 아이콘
        if egg.sealed:
            self.font_sm.render("🔒", True, C_WHITE)
        if egg.icy:
            icon = self.font_sm.render("❄", True, (100, 230, 255))
            self.screen.blit(icon, (cx + egg.r - 6, cy - egg.r - 2))
        if egg.invisible:
            icon = self.font_sm.render("👻", True, (200, 200, 255))
            self.screen.blit(icon, (cx - 8, cy - 8))

    # ── 조준선 ──────────────────────────────────────────────────
    def _draw_aim(self, gs: GameState):
        if not gs.dragging or gs.selected_egg is None:
            return
        egg = gs.selected_egg
        ex, ey = int(egg.x), int(egg.y)
        dx = gs.drag_sx - gs.drag_ex
        dy = gs.drag_sy - gs.drag_ey
        dist = math.hypot(dx, dy)
        if dist < 2:
            return

        scale = min(dist / MAX_LAUNCH_DIST, 1.0)
        nx, ny = dx / dist, dy / dist
        end_x = int(ex + nx * 90 * scale)
        end_y = int(ey + ny * 90 * scale)

        # 점선
        for i in range(0, 80, 12):
            t = i / 80
            px = int(ex + nx * i * scale)
            py = int(ey + ny * i * scale)
            radius = max(2, int(5 * (1 - t)))
            alpha_col = _blend(C_AIM_LINE, C_BG, t * 0.7)
            pygame.draw.circle(self.screen, alpha_col, (px, py), radius)

        # 화살표 끝
        pygame.draw.circle(self.screen, C_AIM_LINE, (end_x, end_y), 5)

        # 발사 위력 표시
        pct = int(scale * 100)
        txt = self.font_sm.render(f"발사 위력: {pct}%", True, C_AIM_LINE)
        self.screen.blit(txt, (end_x + 8, end_y - 10))

    # ── HUD ─────────────────────────────────────────────────────
    def _draw_hud(self, gs: GameState):
        self._draw_panel_left(gs)
        self._draw_panel_right(gs)
        self._draw_top_bar(gs)
        self._draw_log(gs)

    def _draw_top_bar(self, gs: GameState):
        # 턴 표시
        turn_name = "P1 (파랑)" if gs.turn == 0 else "P2 (빨강)"
        turn_col  = C_P1 if gs.turn == 0 else C_P2
        txt = self.font_lg.render(f"{turn_name} 차례", True, turn_col)
        self.screen.blit(txt, txt.get_rect(center=(self.w // 2, BOARD_TOP - 60)))

        # 현재 행동
        if gs.phase == STATE_ABILITY and gs.ability_egg:
            from core.abilities import _find_egg_by_id
            prompt = gs.ability_egg.type
            desc = EGG_INFO.get(prompt, {}).get("name", "")
            mode_txt = self.font_md.render(f"능력 사용 중: {desc}", True, C_HIGHLIGHT)
        elif gs.action_mode == ACTION_SHOOT:
            mode_txt = self.font_md.render("모드: 발사", True, C_GRAY)
        else:
            mode_txt = self.font_md.render("모드: 능력", True, (200, 160, 255))
        self.screen.blit(mode_txt, mode_txt.get_rect(center=(self.w // 2, BOARD_TOP - 30)))

    def _draw_panel_left(self, gs: GameState):
        """P1 정보 패널."""
        self._draw_egg_list(gs, 0, 10, BOARD_TOP)

    def _draw_panel_right(self, gs: GameState):
        """P2 정보 패널."""
        self._draw_egg_list(gs, 1, BOARD_RIGHT + 10, BOARD_TOP)

    def _draw_egg_list(self, gs: GameState, owner: int, px: int, py: int):
        panel_w = BOARD_LEFT - 12 if owner == 0 else self.w - BOARD_RIGHT - 12
        label = "P1" if owner == 0 else "P2"
        col   = C_P1 if owner == 0 else C_P2

        # 헤더
        eggs_alive = len(self.my_eggs_for(gs, owner))
        header = self.font_md.render(f"{label}: {eggs_alive}개", True, col)
        self.screen.blit(header, (px, py))

        y = py + 28
        for egg in self.my_eggs_for(gs, owner):
            info = EGG_INFO[egg.type]
            # 선택 강조
            is_sel = (egg is gs.selected_egg or egg is gs.ability_egg)
            bg = C_BTN_ACT if is_sel else C_UI_BG
            pygame.draw.rect(self.screen, bg,
                             (px, y, panel_w - 4, 22), border_radius=4)
            name_col = C_HIGHLIGHT if is_sel else C_WHITE
            name_txt = self.font_sm.render(
                f"{'🔒' if egg.sealed else ''}{'❄' if egg.icy else ''}"
                f"{'👻' if egg.invisible else ''}{info['name']}",
                True, name_col)
            self.screen.blit(name_txt, (px + 4, y + 3))
            y += 26

    def my_eggs_for(self, gs: GameState, owner: int) -> list[Egg]:
        return [e for e in gs.eggs if e.active and e.owner == owner]

    # ── 로그 ────────────────────────────────────────────────────
    def _draw_log(self, gs: GameState):
        log_x = 10
        log_y = BOARD_BOTTOM + 8
        log_w = self.w - 20
        log_h = self.h - BOARD_BOTTOM - 8

        pygame.draw.rect(self.screen, C_UI_BG,
                         (log_x, log_y, log_w, log_h), border_radius=6)
        pygame.draw.rect(self.screen, C_UI_BORDER,
                         (log_x, log_y, log_w, log_h), 1, border_radius=6)

        # 최근 3줄
        recent = gs.logs[-4:]
        for i, msg in enumerate(recent):
            alpha = 180 + i * 25
            col = (min(255, alpha), min(255, alpha), min(255, alpha))
            txt = self.font_sm.render(msg, True, col)
            self.screen.blit(txt, (log_x + 8, log_y + 6 + i * 18))

    # ── 게임오버 오버레이 ──────────────────────────────────────
    def _draw_gameover(self, gs: GameState):
        overlay = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self.screen.blit(overlay, (0, 0))

        winner = "P1 (파랑)" if gs.winner == 0 else "P2 (빨강)"
        col    = C_P1 if gs.winner == 0 else C_P2
        txt1 = self.font_xl.render(f"{winner} 승리!", True, col)
        txt2 = self.font_md.render("R 키를 누르면 재시작", True, C_GRAY)
        self.screen.blit(txt1, txt1.get_rect(center=(self.w // 2, self.h // 2 - 30)))
        self.screen.blit(txt2, txt2.get_rect(center=(self.w // 2, self.h // 2 + 30)))