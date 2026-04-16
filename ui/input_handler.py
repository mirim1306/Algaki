"""마우스·키보드 입력 처리."""
from __future__ import annotations
import math
import pygame
from core.constants import *
from core.game_state import GameState
from core.egg import Egg
from ui.buttons import Button


def _egg_at(gs: GameState, mx: float, my: float,
            owner_filter: int | None = None) -> Egg | None:
    for egg in reversed(gs.eggs):
        if not egg.active:
            continue
        if owner_filter is not None and egg.owner != owner_filter:
            continue
        if math.hypot(egg.x - mx, egg.y - my) <= egg.r + 4:
            return egg
    return None


class InputHandler:
    def __init__(self, buttons: dict[str, Button]):
        self.buttons = buttons

    def _msg(self, gs: GameState, msg: str):
        if msg:
            gs.log(msg)

    def handle_event(self, event: pygame.event.Event, gs: GameState,
                     renderer=None):
        if gs.simulating:
            return

        mx, my = pygame.mouse.get_pos()

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_r:
                gs.reset()
                return
            # ESC는 main.py에서 홈으로 전환 처리

        if gs.phase == STATE_GAMEOVER:
            return

        # ── 버튼 클릭 ─────────────────────────────────────────
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.buttons["shoot"].is_clicked(event):
                gs.action_mode = ACTION_SHOOT
                gs.cancel_ability()
                self._msg(gs, "발사 모드로 전환")
                return

            if self.buttons["ability"].is_clicked(event):
                if gs.selected_egg is None:
                    self._msg(gs, "먼저 자신의 알을 선택하세요.")
                else:
                    ok, msg = gs.start_ability(gs.selected_egg)
                    self._msg(gs, msg)
                return

            # confirm 버튼: 현재 능력이 필요 없으므로 비워둠
            if self.buttons["confirm"].is_clicked(event):
                if gs.phase == STATE_ABILITY:
                    ok, msg = gs.handle_ability_confirm()
                    self._msg(gs, msg)
                return

            if self.buttons["cancel"].is_clicked(event):
                gs.cancel_ability()
                self._msg(gs, "능력 취소")
                return

        # ── 보드 입력 ─────────────────────────────────────────
        in_board = (BOARD_LEFT <= mx <= BOARD_RIGHT and
                    BOARD_TOP  <= my <= BOARD_BOTTOM)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if in_board:
                self._handle_board_click_down(mx, my, gs, renderer)

        elif event.type == pygame.MOUSEMOTION and gs.dragging:
            gs.drag_ex, gs.drag_ey = mx, my

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1 and gs.dragging:
            self._handle_board_drag_release(mx, my, gs, renderer)

    def _handle_board_click_down(self, mx: float, my: float,
                                 gs: GameState, renderer=None):
        if gs.phase == STATE_ABILITY:
            clicked_egg = _egg_at(gs, mx, my)
            if clicked_egg:
                ok, msg = gs.handle_ability_click_egg(clicked_egg)
                self._msg(gs, msg)
                if ok and renderer and clicked_egg.active:
                    renderer.spawn_particles(int(clicked_egg.x),
                                             int(clicked_egg.y),
                                             clicked_egg.base_color, 10)
            else:
                ok, msg = gs.handle_ability_click_pos(mx, my)
                self._msg(gs, msg)
            return

        # 발사 모드: 자신의 알 선택
        my_egg = _egg_at(gs, mx, my, owner_filter=gs.turn)
        if my_egg:
            if my_egg.sealed:
                gs.log("봉인된 알은 선택할 수 없습니다.")
                return
            gs.selected_egg = my_egg
            gs.dragging  = True
            gs.drag_sx   = mx
            gs.drag_sy   = my
            gs.drag_ex   = mx
            gs.drag_ey   = my
        else:
            if gs.phase == STATE_PLAY:
                gs.selected_egg = None

    def _handle_board_drag_release(self, mx: float, my: float,
                                   gs: GameState, renderer=None):
        gs.dragging = False
        egg = gs.selected_egg
        if egg is None:
            return

        dx   = gs.drag_sx - mx
        dy   = gs.drag_sy - my
        dist = math.hypot(dx, dy)
        if dist < 5:
            return   # 클릭만 → 선택 유지

        dist_c = min(dist, MAX_LAUNCH_DIST)
        nx, ny = dx / dist, dy / dist
        speed  = dist_c * LAUNCH_POWER
        vx, vy = nx * speed, ny * speed

        ok = gs.try_shoot(egg, vx, vy)
        if ok and renderer:
            renderer.spawn_particles(int(egg.x), int(egg.y), egg.base_color, 8)

    def update_hover(self, gs: GameState):
        mx, my = pygame.mouse.get_pos()
        for btn in self.buttons.values():
            btn.update(mx, my)

        self.buttons["shoot"].active   = (gs.action_mode == ACTION_SHOOT
                                          and gs.phase != STATE_ABILITY)
        self.buttons["ability"].active = (gs.phase == STATE_ABILITY)
        can_confirm = (gs.phase == STATE_ABILITY
                       and gs.ability_egg is not None)
        self.buttons["confirm"].active = False   # 현재 미사용
        self.buttons["cancel"].active  = (gs.phase == STATE_ABILITY)

    def draw_buttons(self, screen, gs: GameState):
        for key, btn in self.buttons.items():
            if key in ("confirm",) and gs.phase != STATE_ABILITY:
                continue
            if key == "confirm":
                continue   # confirm 버튼 숨김 (필요 없는 능력 제거됨)
            if key == "cancel" and gs.phase != STATE_ABILITY:
                continue
            btn.draw(screen)