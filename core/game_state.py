# core/game_state.py
from __future__ import annotations
import math, random
from core.egg      import Egg, Barrier, Mine
from core.physics  import step_physics, all_still
from core.abilities import (
    ability_barrier, ability_seal, tick_seal,
    ability_copy_ability, ability_copy_power, use_copied_ability,
    ability_clone, ability_bomb, explode_mine,
    ability_invisible, ability_psycho,
    ability_ice, ability_magnet,
    pos_occupied,
)
from core.constants import *


def _build_initial_eggs(p1_types=None, p2_types=None) -> list[Egg]:
    import core.constants as _c
    eggs: list[Egg] = []
    types_pool = [
        "barrier", "seal", "copy", "clone",
        "bomb", "invisible", "psycho", "ice", "magnet", "normal",
    ]

    def make_types(custom, count):
        if custom:
            return list(custom[:count])
        pool = types_pool[:]
        random.shuffle(pool)
        return pool[:count]

    def place(owner: int, types_list: list[str]):
        n = len(types_list)
        r = _c.EGG_RADIUS
        zone_left  = _c.BOARD_LEFT  if owner == 0 else _c.MID_X + 10
        zone_right = _c.MID_X - 10  if owner == 0 else _c.BOARD_RIGHT
        zone_w = zone_right - zone_left
        zone_h = _c.BOARD_BOTTOM - _c.BOARD_TOP

        cols = max(1, min(n, int(math.ceil(math.sqrt(n * zone_w / max(zone_h, 1))))))
        rows = math.ceil(n / cols)
        pad    = r * 2 + 12
        cell_w = max(pad, zone_w // (cols + 1))
        cell_h = max(pad, zone_h // (rows + 1))
        cx = (zone_left + zone_right) // 2
        cy = (_c.BOARD_TOP + _c.BOARD_BOTTOM) // 2
        start_x = cx - (cell_w * cols) // 2 + cell_w // 2
        start_y = cy - (cell_h * rows) // 2 + cell_h // 2

        positions = []
        for row in range(rows):
            for col in range(cols):
                px = max(zone_left + r + 4, min(zone_right - r - 4,
                         start_x + col * cell_w))
                py = max(_c.BOARD_TOP + r + 4, min(_c.BOARD_BOTTOM - r - 4,
                         start_y + row * cell_h))
                positions.append((px, py))

        for i, t in enumerate(types_list):
            px, py = positions[i % len(positions)]
            eggs.append(Egg(float(px), float(py), owner, t))

    n1 = len(p1_types) if p1_types else _c.EGGS_PER_PLAYER
    n2 = len(p2_types) if p2_types else _c.EGGS_PER_PLAYER
    place(0, make_types(p1_types, n1))
    place(1, make_types(p2_types, n2))
    return eggs


class GameState:
    def __init__(self):
        self.eggs:         list[Egg]     = []
        self.barriers:     list[Barrier] = []
        self.mines:        list[Mine]    = []
        self.map_barriers: list[Barrier] = []
        self.map_index:    int           = 0

        self.turn:  int  = 0
        self.phase: str  = STATE_PLAY

        self.action_mode:     str  = ACTION_SHOOT
        self.ability_step:    int  = 0
        self.ability_targets: list = []
        self.ability_egg:  Egg | None = None

        # 복사알이 "ability" 모드로 재사용할 때 위임할 능력 타입
        self._copy_delegate: str | None = None

        self.selected_egg: Egg | None = None
        self.dragging: bool  = False
        self.drag_sx:  float = 0.0
        self.drag_sy:  float = 0.0
        self.drag_ex:  float = 0.0
        self.drag_ey:  float = 0.0

        self.logs:       list[str]  = []
        self.winner:     int | None = None
        self.simulating: bool       = False

        self.reset()

    # ── 초기화 ────────────────────────────────────────────────────
    def reset(self, p1_types=None, p2_types=None, game_config=None):
        if game_config:
            p1_types       = game_config.get("p1_eggs")
            p2_types       = game_config.get("p2_eggs")
            self.map_index = game_config.get("map_index", 0)

        from core.map_system import build_map_barriers
        self.map_barriers = build_map_barriers(self.map_index)

        Egg._id_counter  = 0
        self.eggs        = _build_initial_eggs(p1_types, p2_types)
        self.barriers    = []
        self.mines       = []
        self.turn        = 0
        self.phase       = STATE_PLAY
        self.action_mode = ACTION_SHOOT
        self.ability_step    = 0
        self.ability_targets = []
        self.ability_egg     = None
        self._copy_delegate  = None
        self.selected_egg    = None
        self.dragging        = False
        self.simulating      = False
        self.winner          = None
        self.logs = ["게임 시작! P1(파랑) 먼저."]

    # ── 헬퍼 ──────────────────────────────────────────────────────
    def my_eggs(self, owner: int | None = None) -> list[Egg]:
        o = self.turn if owner is None else owner
        return [e for e in self.eggs if e.active and e.owner == o]

    def enemy_eggs(self) -> list[Egg]:
        return [e for e in self.eggs if e.active and e.owner != self.turn]

    def log(self, msg: str):
        self.logs.append(msg)
        if len(self.logs) > 40:
            self.logs = self.logs[-40:]

    # ── 물리 ──────────────────────────────────────────────────────
    def update_physics(self):
        if not self.simulating:
            return
        triggered = step_physics(self.eggs, self.barriers, self.mines,
                                 self.map_barriers)
        for mine in triggered:
            pushed = explode_mine(mine, self.eggs)
            if pushed:
                self.log(f"💥 지뢰 폭발! 알 {len(pushed)}개 밀려남")
            else:
                self.log("💥 지뢰 폭발!")

        for egg in self.eggs:
            if not egg.active:
                egg.vx = egg.vy = 0.0

        if all_still(self.eggs):
            self.simulating = False
            self._check_winner()
            if self.phase != STATE_GAMEOVER:
                self._next_turn()

    def _check_winner(self):
        if not self.my_eggs(0):
            self.winner = 1; self.phase = STATE_GAMEOVER
            self.log("🎉 P2 승리!")
        elif not self.my_eggs(1):
            self.winner = 0; self.phase = STATE_GAMEOVER
            self.log("🎉 P1 승리!")

    def _next_turn(self):
        # 봉인 턴 카운터 감소
        tick_seal(self.eggs)

        self.turn = 1 - self.turn
        self.selected_egg    = None
        self.action_mode     = ACTION_SHOOT
        self.ability_step    = 0
        self.ability_targets = []
        self.ability_egg     = None
        self._copy_delegate  = None
        self.log(f"── {'P1' if self.turn == 0 else 'P2'} 차례 ──")

    # ── 발사 ──────────────────────────────────────────────────────
    def try_shoot(self, egg: Egg, vx: float, vy: float) -> bool:
        if egg.sealed:
            self.log("❌ 봉인된 알은 발사할 수 없습니다.")
            return False
        if egg.owner != self.turn:
            return False

        # 복사알 위력 합산
        if egg.type == "copy" and egg.copy_mode == "power" \
                and egg.copied_vx is not None:
            vx += egg.copied_vx
            vy += egg.copied_vy
            egg.copied_vx = None
            egg.copied_vy = None
            egg.copy_mode = "none"
            self.log("복사한 위력이 합산되어 발사됩니다!")

        egg.vx = vx
        egg.vy = vy
        self.simulating   = True
        self.selected_egg = None
        self.log(f"{'P1' if self.turn==0 else 'P2'}: {EGG_INFO[egg.type]['name']} 발사!")
        return True

    # ── 능력 시작 ─────────────────────────────────────────────────
    def start_ability(self, egg: Egg) -> tuple[bool, str]:
        if egg.sealed:
            return False, "봉인된 알은 능력을 쓸 수 없습니다."
        if egg.owner != self.turn:
            return False, "자신의 알만 선택하세요."
        if egg.type == "normal":
            return False, "일반알은 능력이 없습니다."

        # ── 복사알 특수 처리 ──
        if egg.type == "copy":
            return self._start_copy_ability(egg)

        # ── 투명알 즉시 발동 ──
        if egg.type == "invisible":
            ok, msg = ability_invisible(egg)
            if ok:
                self.phase       = STATE_PLAY
                self.action_mode = ACTION_SHOOT
            return ok, msg

        # ── 분신알 즉시 발동 ──
        if egg.type == "clone":
            ok, msg = ability_clone(egg, self.eggs)
            if ok:
                self._end_ability_turn()
            return ok, msg

        # ── 자석알: 두 번 클릭 필요 ──
        self.ability_egg     = egg
        self.ability_step    = 0
        self.ability_targets = []
        self.phase           = STATE_ABILITY
        self._copy_delegate  = None
        return True, self._ability_prompt(egg)

    def _start_copy_ability(self, egg: Egg) -> tuple[bool, str]:
        """복사알 능력 사용: 저장값 유무에 따라 분기."""
        # 이미 저장한 능력/위력이 있으면 재사용
        if egg.copy_mode != "none":
            ok, msg, delegate = use_copied_ability(egg)
            if not ok:
                return False, msg
            if delegate == "power_ready":
                # 위력 합산 발사 — 발사 모드로 전환 안내
                return True, "저장된 위력이 준비됐습니다! 이제 발사하면 위력이 합산됩니다."
            if delegate:
                # 저장된 능력 타입을 대리 실행
                self._copy_delegate = delegate
                self.ability_egg     = egg
                self.ability_step    = 0
                self.ability_targets = []
                self.phase           = STATE_ABILITY
                return True, (f"저장된 능력 [{EGG_INFO[delegate]['name']}] 발동! "
                              + self._ability_prompt_for(delegate, 0))
            return ok, msg

        # 저장값 없음 → 복사 대상 선택 안내
        self.ability_egg     = egg
        self.ability_step    = 0
        self.ability_targets = []
        self.phase           = STATE_ABILITY
        self._copy_delegate  = None
        return True, "복사알: 능력을 복사할 적 알 또는 위력을 복사할 알을 클릭하세요."

    # ── 능력 프롬프트 ─────────────────────────────────────────────
    def _ability_prompt(self, egg: Egg) -> str:
        t = self._copy_delegate or egg.type
        return self._ability_prompt_for(t, self.ability_step)

    def _ability_prompt_for(self, t: str, step: int) -> str:
        prompts = {
            "barrier":   "방벽알: 보드의 빈 위치를 클릭하세요.",
            "seal":      "봉인알: 봉인할 알을 클릭하세요.",
            "copy":      "복사알: 능력 복사(적 알) 또는 위력 복사(아무 알) 클릭.",
            "bomb":      "폭탄알: 지뢰를 설치할 빈 위치를 클릭하세요.",
            "invisible": "투명알: 발동 중...",
            "clone":     "분신알: 발동 중...",
            "psycho":    "염력알: 파괴할 적 알을 클릭하세요.",
            "ice":       "얼음알: 슬립 상태를 부여할 알을 클릭하세요.",
        }
        if t == "magnet":
            return ("자석알: 연결할 첫 번째 알을 클릭하세요." if step == 0
                    else "자석알: 연결할 두 번째 알을 클릭하세요.")
        return prompts.get(t, "능력 발동 중...")

    # ── 능력 클릭(알) ─────────────────────────────────────────────
    def handle_ability_click_egg(self, clicked: Egg) -> tuple[bool, str]:
        egg = self.ability_egg
        if egg is None:
            return False, "능력 알이 없습니다."

        # 투명 알은 적의 능력 대상이 될 수 없음
        if clicked.invisible and clicked.owner != self.turn:
            return False, "투명 상태의 알에는 능력을 사용할 수 없습니다."

        # 복사알 저장 단계 (delegate 없음)
        if egg.type == "copy" and self._copy_delegate is None:
            if clicked.owner != self.turn:
                ok, msg = ability_copy_ability(egg, clicked)
            else:
                ok, msg = ability_copy_power(egg, clicked)
            if ok:
                self._end_ability_turn()
            return ok, msg

        # 대리 능력(저장된 능력 실행) 또는 일반 능력
        t = self._copy_delegate or egg.type

        if t == "seal":
            ok, msg = ability_seal(egg, clicked)
            if ok: self._end_ability_turn()
            return ok, msg

        if t == "psycho":
            if clicked.owner == self.turn:
                return False, "염력은 적 알에만 사용할 수 있습니다."
            ok, msg = ability_psycho(egg, clicked, self.eggs)
            if ok: self._end_ability_turn()
            return ok, msg

        if t == "ice":
            ok, msg = ability_ice(egg, clicked)
            if ok: self._end_ability_turn()
            return ok, msg

        if t == "magnet":
            self.ability_targets.append(clicked)
            if len(self.ability_targets) == 2:
                a, b = self.ability_targets
                ok, msg = ability_magnet(egg, a, b)
                if ok:
                    # 자석 연결 즉시 → simulating 활성화해서 당기기 시작
                    self.simulating = True
                    self._end_ability_turn_no_next()
                    return ok, msg
                else:
                    self.ability_targets = []
                return ok, msg
            else:
                self.ability_step = 1
                return True, self._ability_prompt_for("magnet", 1)

        # copy 능력 저장 단계에서 아군 알 클릭
        if t == "copy":
            ok, msg = ability_copy_power(egg, clicked)
            if ok: self._end_ability_turn()
            return ok, msg

        return False, "해당 능력은 알 클릭이 필요하지 않습니다."

    # ── 능력 클릭(위치) ───────────────────────────────────────────
    def handle_ability_click_pos(self, x: float, y: float) -> tuple[bool, str]:
        egg = self.ability_egg
        if egg is None:
            return False, ""
        t = self._copy_delegate or egg.type

        if t == "barrier":
            ok, msg = ability_barrier(egg, x, y, self.eggs, self.barriers)
            if ok: self._end_ability_turn()
            return ok, msg

        if t == "bomb":
            ok, msg = ability_bomb(egg, x, y, self.eggs, self.barriers, self.mines)
            if ok: self._end_ability_turn()
            return ok, msg

        return False, "위치 선택이 필요 없는 능력입니다."

    # ── 능력 확인 버튼 ────────────────────────────────────────────
    def handle_ability_confirm(self) -> tuple[bool, str]:
        # confirm 버튼은 더 이상 분신/투명에 쓰이지 않음(start_ability에서 즉시 처리)
        return False, "확인이 필요 없는 능력입니다."

    # ── 능력 종료 ─────────────────────────────────────────────────
    def _end_ability_turn(self):
        self.simulating      = False
        self.phase           = STATE_PLAY
        self.ability_egg     = None
        self.ability_targets = []
        self.ability_step    = 0
        self._copy_delegate  = None
        self._check_winner()
        if self.phase != STATE_GAMEOVER:
            self._next_turn()

    def _end_ability_turn_no_next(self):
        """자석: 물리 시뮬레이션을 유지하면서 능력 UI만 닫음."""
        self.phase           = STATE_PLAY
        self.ability_egg     = None
        self.ability_targets = []
        self.ability_step    = 0
        self._copy_delegate  = None
        self._check_winner()
        # simulating=True 상태로 물리가 끝나면 _next_turn 자동 호출

    def cancel_ability(self):
        self.phase           = STATE_PLAY
        self.ability_egg     = None
        self.ability_step    = 0
        self.ability_targets = []
        self._copy_delegate  = None