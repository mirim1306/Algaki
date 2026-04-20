from __future__ import annotations
import math, random
from core.egg      import Egg, Barrier, Mine, calc_uses
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


def _build_initial_eggs(p1_types, p2_types, formation, egg_count) -> list[Egg]:
    from core.map_system import get_formation_positions
    eggs: list[Egg] = []
    types_pool = list(EGG_INFO.keys())

    def make_types(custom, n):
        if custom:
            return list(custom[:n])
        pool = types_pool[:]
        random.shuffle(pool)
        return pool[:n]

    def place(owner: int, types_list: list[str]):
        n         = len(types_list)
        positions = get_formation_positions(owner, n, formation)
        for i, t in enumerate(types_list):
            x, y = positions[i % len(positions)]
            eggs.append(Egg(x, y, owner, t, egg_count))

    n1 = len(p1_types) if p1_types else egg_count
    n2 = len(p2_types) if p2_types else egg_count
    place(0, make_types(p1_types, n1))
    place(1, make_types(p2_types, n2))
    return eggs


class GameState:
    def __init__(self):
        self.eggs:       list[Egg]    = []
        self.barriers:   list[Barrier]= []
        self.mines:      list[Mine]   = []

        from core.map_system import MapObjects
        self.map_obj:    MapObjects   = MapObjects()
        self.map_index:  int          = 0
        self.formation:  int          = 0
        self.egg_count:  int          = EGGS_PER_PLAYER

        self.turn:  int  = 0
        self.phase: str  = STATE_PLAY

        self.action_mode:     str  = ACTION_SHOOT
        self.ability_step:    int  = 0
        self.ability_targets: list = []
        self.ability_egg:  Egg | None = None

        #
        # copy_state: "idle" | "choose" | "stored_ability" | "stored_power"
        self.copy_state: str = "idle"

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

    def reset(self, p1_types=None, p2_types=None, game_config=None):
        if game_config:
            p1_types       = game_config.get("p1_eggs")
            p2_types       = game_config.get("p2_eggs")
            self.map_index = game_config.get("map_index", 0)
            self.formation = game_config.get("formation", 0)
            self.egg_count = game_config.get("egg_count", EGGS_PER_PLAYER)

        from core.map_system import build_map_objects
        self.map_obj = build_map_objects(self.map_index)

        Egg._id_counter  = 0
        self.eggs     = _build_initial_eggs(p1_types, p2_types,
                                            self.formation, self.egg_count)
        self.barriers = []
        self.mines    = []
        self.turn     = 0
        self.phase    = STATE_PLAY
        self.action_mode     = ACTION_SHOOT
        self.ability_step    = 0
        self.ability_targets = []
        self.ability_egg     = None
        self.copy_state      = "idle"
        self.selected_egg    = None
        self.dragging        = False
        self.simulating      = False
        self.winner          = None
        self.logs = ["게임 시작! P1(파랑) 먼저."]

    def my_eggs(self, owner: int | None = None) -> list[Egg]:
        o = self.turn if owner is None else owner
        return [e for e in self.eggs if e.active and e.owner == o]

    def enemy_eggs(self) -> list[Egg]:
        return [e for e in self.eggs if e.active and e.owner != self.turn]

    def log(self, msg: str):
        if msg:
            self.logs.append(msg)
            if len(self.logs) > 40:
                self.logs = self.logs[-40:]

    # --   ----------------------------------------------
    def update_physics(self):
        if not self.simulating:
            return

        triggered, bomb_events = step_physics(self.eggs, self.barriers,
                                              self.mines, self.map_obj)
        for mine in triggered:
            pushed = explode_mine(mine, self.eggs)
            if pushed:
                self.log(f"[폭발] 지뢰! {len(pushed)}개 밀림")
            else:
                self.log("[폭발] 지뢰!")

        for n_killed, n_pushed in bomb_events:
            if n_killed > 0:
                self.log(f"[폭발] 맵 폭탄! {n_killed}개 파괴, {n_pushed}개 밀림")
            else:
                self.log(f"[폭발] 맵 폭탄! {n_pushed}개 밀림")

        for egg in self.eggs:
            if not egg.active:
                egg.vx = egg.vy = 0.0

        if all_still(self.eggs):
            self.simulating = False
            self._check_winner()
            if self.phase != STATE_GAMEOVER:
                self._next_turn()

    def _check_winner(self):
        p0 = self.my_eggs(0)
        p1 = self.my_eggs(1)
        if not p0:
            self.winner = 1; self.phase = STATE_GAMEOVER
            self.log("P2 승리!")
        elif not p1:
            self.winner = 0; self.phase = STATE_GAMEOVER
            self.log("P1 승리!")

    def _next_turn(self):
        #     (   )
        tick_seal(self.eggs)
        self.turn = 1 - self.turn
        self.selected_egg    = None
        self.action_mode     = ACTION_SHOOT
        self.ability_step    = 0
        self.ability_targets = []
        self.ability_egg     = None
        self.copy_state      = "idle"
        self.log(f"-- {'P1' if self.turn == 0 else 'P2'} 차례 --")

    # --  -------------------------------------------------------
    def try_shoot(self, egg: Egg, vx: float, vy: float) -> bool:
        if egg.sealed:
            self.log("[봉인] 발사 불가")
            return False
        if egg.owner != self.turn:
            return False

        #
        if (egg.type == "copy" and egg.copy_mode == "power"
                and egg.copied_vx is not None):
            vx += egg.copied_vx
            vy += egg.copied_vy
            egg.copied_vx  = None
            egg.copied_vy  = None
            egg.copy_mode  = "none"
            self.log("[봉인] 발사 불가")

        egg.vx = vx
        egg.vy = vy
        self.simulating   = True
        self.selected_egg = None
        self.log(f"{'P1' if self.turn==0 else 'P2'}: {EGG_INFO[egg.type]['name']} !")
        return True

    # --   -------------------------------------------------
    def start_ability(self, egg: Egg) -> tuple[bool, str]:
        if egg.sealed:
            return False, "봉인된 알은 능력을 쓸 수 없습니다."
        if egg.owner != self.turn:
            return False, "자신의 알만 선택하세요."
        if egg.type == "normal":
            return False, "자신의 알만 선택하세요."
        if egg.is_clone:
            return False, "분신은 발사만 할 수 있습니다."
        if egg.uses_left <= 0:
            return False, f"능력 사용 횟수를 모두 소진했습니다. (0/{egg.max_uses})"

        # -- :   --
        if egg.type == "invisible":
            ok, msg = ability_invisible(egg)
            if ok:
                #     ( ),  UI
                pass
            return ok, msg

        # -- :      --
        if egg.type == "clone":
            ok, msg = ability_clone(egg, self.eggs)
            if ok:
                self._end_ability_turn()
            return ok, msg

        # -- :     --
        if egg.type == "copy":
            return self._start_copy_ability(egg)

        #  : STATE_ABILITY
        self.ability_egg     = egg
        self.ability_step    = 0
        self.ability_targets = []
        self.phase           = STATE_ABILITY
        return True, self._ability_prompt(egg)

    def _start_copy_ability(self, egg: Egg) -> tuple[bool, str]:
        """복사알 능력 시작 — 저장 상태에 따라 메뉴 분기."""
        if egg.copy_mode == "ability" and egg.copied_ability:
            #    →  or
            self.ability_egg     = egg
            self.ability_step    = 0
            self.ability_targets = []
            self.phase           = STATE_ABILITY
            self.copy_state      = "stored_ability"
            aname = EGG_INFO.get(egg.copied_ability, {}).get("name", "?")
            return True, (f"복사알: [저장 능력: {aname}]\n"
                          f"① 빈 보드 클릭 -> 저장 능력 발동  "
                          f"② 알 클릭 -> 새로 복사")

        if egg.copy_mode == "power" and egg.copied_vx is not None:
            # 저장된 위력 있음 -> 발사 시 합산, 또는 재복사
            self.ability_egg     = egg
            self.ability_step    = 0
            self.ability_targets = []
            self.phase           = STATE_ABILITY
            self.copy_state      = "stored_power"
            spd = math.hypot(egg.copied_vx, egg.copied_vy)
            return True, (f"복사알: [저장 위력: {spd:.1f}]\n"
                          f"① 발사 모드로 전환하면 위력 합산 발사  "
                          f"② 알 클릭 -> 새로 위력 복사")

        # 저장 없음 -> 복사할 대상 선택
        self.ability_egg     = egg
        self.ability_step    = 0
        self.ability_targets = []
        self.phase           = STATE_ABILITY
        self.copy_state      = "choose"
        remain = f"[{egg.uses_left}/{egg.max_uses}]"
        return True, (f"복사알 {remain}: 적 알=능력 복사 / 아군·적 알=위력 복사")

    # --   ---------------------------------------------
    def _ability_prompt(self, egg: Egg) -> str:
        t      = egg.type
        remain = f"[{egg.uses_left}/{egg.max_uses}]"
        prompts = {
            "barrier":  f"방벽알 {remain}: 빈 위치 클릭",
            "seal":     f"봉인알 {remain}: 봉인할 알 클릭",
            "bomb":     f"폭탄알 {remain}: 지뢰 설치할 빈 위치 클릭",
            "psycho":   f"염력알 {remain}: 파괴할 적 알 클릭",
            "ice":      f"얼음알 {remain}: 슬립 부여할 알 클릭",
        }
        if t == "magnet":
            step = self.ability_step
            return f"자석알 {remain}: {'첫' if step==0 else '두'} 번째 알 클릭"
        return prompts.get(t, "능력 발동 중...")

    # --   ( ) ---------------------------------------
    def handle_ability_click_egg(self, clicked: Egg) -> tuple[bool, str]:
        egg = self.ability_egg
        if egg is None:
            return False, "자신의 알만 선택하세요."

        #
        if clicked.invisible and clicked.owner != self.turn:
            return False, "투명 상태의 알에는 능력을 사용할 수 없습니다."

        t = egg.type

        # --   --
        if t == "copy":
            return self._handle_copy_click_egg(egg, clicked)

        if t == "seal":
            ok, msg = ability_seal(egg, clicked)
            if ok: self._end_ability_turn()
            return ok, msg

        if t == "psycho":
            if clicked.owner == self.turn:
                return False, "봉인된 알은 능력을 쓸 수 없습니다."
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
                    self.simulating = True
                    self._end_ability_turn_keep_sim()
                else:
                    self.ability_targets = []
                return ok, msg
            self.ability_step = 1
            return True, self._ability_prompt(egg)

        return False, "봉인된 알은 능력을 쓸 수 없습니다."

    def _handle_copy_click_egg(self, egg: Egg, clicked: Egg) -> tuple[bool, str]:
        """봉인된 알은 능력을 쓸 수 없습니다."""
        state = self.copy_state

        if state == "stored_ability":
            #      →
            stored = egg.copied_ability
            aname  = EGG_INFO.get(stored, {}).get("name", "?") if stored else "?"
            #
            if stored in ("seal", "psycho", "ice", "invisible", "clone", "magnet"):
                return self._fire_stored_ability_on_egg(egg, clicked)
            #   (barrier, bomb)
            ok, msg = (ability_copy_ability(egg, clicked)
                       if clicked.owner != self.turn
                       else ability_copy_power(egg, clicked))
            if ok:
                self.copy_state = ("stored_ability" if egg.copy_mode == "ability"
                                   else "stored_power")
                self._end_ability_turn()
            return ok, msg

        if state == "stored_power":
            #    →
            ok, msg = ability_copy_power(egg, clicked)
            if ok:
                self.copy_state = "stored_power"
                self._end_ability_turn()
            return ok, msg

        # state == "choose":
        if clicked.owner != self.turn:
            ok, msg = ability_copy_ability(egg, clicked)
        else:
            ok, msg = ability_copy_power(egg, clicked)
        if ok:
            self.copy_state = ("stored_ability" if egg.copy_mode == "ability"
                               else "stored_power")
            self._end_ability_turn()
        return ok, msg

    # --   ( ) --------------------------------------
    def handle_ability_click_pos(self, x: float, y: float) -> tuple[bool, str]:
        egg = self.ability_egg
        if egg is None:
            return False, ""
        t = egg.type

        #  -    (   )
        if t == "copy" and self.copy_state == "stored_ability":
            return self._fire_stored_ability(egg, x, y)

        if t == "barrier":
            ok, msg = ability_barrier(egg, x, y, self.eggs, self.barriers)
            if ok: self._end_ability_turn()
            return ok, msg

        if t == "bomb":
            ok, msg = ability_bomb(egg, x, y, self.eggs, self.barriers, self.mines)
            if ok: self._end_ability_turn()
            return ok, msg

        return False, "분신은 발사만 할 수 있습니다."

    def _fire_stored_ability(self, egg: Egg, x: float, y: float) -> tuple[bool, str]:
        """복사알이 저장한 능력을 위치 대상으로 사용."""
        stored = egg.copied_ability
        if not stored:
            return False, "자신의 알만 선택하세요."

        #    : barrier, bomb
        if stored == "barrier":
            ok, msg = ability_barrier(egg, x, y, self.eggs, self.barriers)
            if ok:
                egg.copied_ability = None
                egg.copy_mode = "none"
                self.copy_state = "idle"
                self._end_ability_turn()
            return ok, msg

        if stored == "bomb":
            ok, msg = ability_bomb(egg, x, y, self.eggs, self.barriers, self.mines)
            if ok:
                egg.copied_ability = None
                egg.copy_mode = "none"
                self.copy_state = "idle"
                self._end_ability_turn()
            return ok, msg

        #    :
        aname = EGG_INFO.get(stored, {}).get("name", "?")
        return False, f"저장된 [{aname}] 능력은 알을 클릭하면 발동됩니다."

    def _fire_stored_ability_on_egg(self, egg: Egg, target: Egg) -> tuple[bool, str]:
        """봉인된 알은 능력을 쓸 수 없습니다."""
        stored = egg.copied_ability
        if not stored:
            return False, "자신의 알만 선택하세요."

        ok, msg = False, ""
        if stored == "seal":
            ok, msg = ability_seal(egg, target)
        elif stored == "psycho":
            if target.owner == self.turn:
                return False, "봉인된 알은 능력을 쓸 수 없습니다."
            ok, msg = ability_psycho(egg, target, self.eggs)
        elif stored == "ice":
            ok, msg = ability_ice(egg, target)
        elif stored == "magnet":
            self.ability_targets.append(target)
            if len(self.ability_targets) == 2:
                a, b = self.ability_targets
                ok, msg = ability_magnet(egg, a, b)
                if ok:
                    egg.copied_ability = None
                    egg.copy_mode = "none"
                    self.copy_state = "idle"
                    self.simulating = True
                    self._end_ability_turn_keep_sim()
                else:
                    self.ability_targets = []
                return ok, msg
            else:
                self.ability_step = 1
                return True, "자석 연결: 두 번째 알을 클릭하세요."
        elif stored == "clone":
            ok, msg = ability_clone(egg, self.eggs)
        elif stored == "invisible":
            ok, msg = ability_invisible(egg)
        else:
            return False, f"[{stored}] 능력은 알 클릭 대상이 없습니다."

        if ok:
            egg.copied_ability = None
            egg.copy_mode = "none"
            self.copy_state = "idle"
            self._end_ability_turn()
        return ok, msg

    # --   -------------------------------------------------
    def handle_ability_confirm(self) -> tuple[bool, str]:
        egg = self.ability_egg
        if egg is None:
            return False, ""
        # confirm clone/invisible
        #
        return False, "확인이 필요 없는 능력입니다."

    # --   -------------------------------------------------
    def _end_ability_turn(self):
        self.simulating      = False
        self.phase           = STATE_PLAY
        self.ability_egg     = None
        self.ability_targets = []
        self.ability_step    = 0
        self.copy_state      = "idle"
        self._check_winner()
        if self.phase != STATE_GAMEOVER:
            self._next_turn()

    def _end_ability_turn_keep_sim(self):
        """자석처럼 simulating 유지가 필요한 경우."""
        self.phase           = STATE_PLAY
        self.ability_egg     = None
        self.ability_targets = []
        self.ability_step    = 0
        self.copy_state      = "idle"
        self._check_winner()

    def cancel_ability(self):
        self.phase           = STATE_PLAY
        self.ability_egg     = None
        self.ability_step    = 0
        self.ability_targets = []
        self.copy_state      = "idle"