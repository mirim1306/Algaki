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


# ─────────────────────────────────────────────────────────────────
# 초기 알 배치
# ─────────────────────────────────────────────────────────────────

def _build_initial_eggs(p1_types: list[str] | None,
                        p2_types: list[str] | None,
                        formation: int,
                        egg_count: int) -> list[Egg]:
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


# ─────────────────────────────────────────────────────────────────
# GameState
# ─────────────────────────────────────────────────────────────────

class GameState:
    def __init__(self):
        self.eggs:       list[Egg]    = []
        self.barriers:   list[Barrier]= []
        self.mines:      list[Mine]   = []

        # 맵 오브젝트
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

    # ── 초기화 ─────────────────────────────────────────────────────
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
        self.selected_egg    = None
        self.dragging        = False
        self.simulating      = False
        self.winner          = None
        self.logs = ["게임 시작! P1(파랑) 먼저."]

    # ── 조회 ───────────────────────────────────────────────────────
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

    # ── 물리 업데이트 ──────────────────────────────────────────────
    def update_physics(self):
        if not self.simulating:
            return

        # 맵 배경 방벽 리스트 (Barrier 형태)
        map_barriers = list(self.map_obj.barriers)

        triggered = step_physics(self.eggs, self.barriers, self.mines, map_barriers)
        for mine in triggered:
            pushed = explode_mine(mine, self.eggs)
            self.log(f"💥 지뢰 폭발! {len(pushed)}개 알 밀림")

        # 맵 폭탄 처리
        self._process_map_bombs()
        # 타이어 처리
        self._process_tires()
        # 하수구 처리
        self._process_drains()

        for egg in self.eggs:
            if not egg.active:
                egg.vx = egg.vy = 0.0

        if all_still(self.eggs):
            self.simulating = False
            self._check_winner()
            if self.phase != STATE_GAMEOVER:
                self._next_turn()

    def _process_map_bombs(self):
        """맵 폭탄 — 알이 닿으면 폭발, 연쇄 가능."""
        active_eggs = [e for e in self.eggs if e.active]
        bombs       = self.map_obj.map_bombs

        # 폭발할 폭탄 탐색
        to_explode = set()
        for bi, bomb in enumerate(bombs):
            if not bomb.active:
                continue
            for egg in active_eggs:
                if bomb.overlaps_egg(egg):
                    to_explode.add(bi)
                    break

        if not to_explode:
            return

        # 연쇄 (폭발한 폭탄이 다른 폭탄 반경 안이면 연쇄)
        changed = True
        while changed:
            changed = False
            for bi in list(to_explode):
                for bj, bomb2 in enumerate(bombs):
                    if bj not in to_explode and bomb2.active:
                        if bombs[bi].in_blast(bomb2):
                            to_explode.add(bj)
                            changed = True

        for bi in to_explode:
            bomb = bombs[bi]
            if not bomb.active:
                continue
            bomb.active = False
            # 반경 내 알과 함께 파괴 (밀려남)
            for egg in active_eggs:
                dx   = egg.x - bomb.x
                dy   = egg.y - bomb.y
                dist = math.hypot(dx, dy)
                if dist < bomb.BLAST_RADIUS:
                    if dist < 0.1:
                        dx, dy, dist = 1.0, 0.0, 1.0
                    nx, ny = dx/dist, dy/dist
                    force  = (bomb.BLAST_RADIUS - dist) / bomb.BLAST_RADIUS * 20
                    egg.vx += nx * force
                    egg.vy += ny * force
            self.log(f"💥 맵 폭탄 폭발!")

    def _process_tires(self):
        """타이어 — 1.5배 반사, 수명 10회."""
        active_eggs = [e for e in self.eggs if e.active]
        for tire in self.map_obj.tires:
            if not tire.active:
                continue
            for egg in active_eggs:
                if not egg.is_moving():
                    continue
                if tire.overlaps_egg(egg):
                    dx   = egg.x - tire.x
                    dy   = egg.y - tire.y
                    dist = math.hypot(dx, dy)
                    if dist < 0.001:
                        dx, dy, dist = 1.0, 0.0, 1.0
                    nx, ny = dx/dist, dy/dist

                    # 겹침 분리
                    overlap = (egg.r + tire.r) - dist
                    egg.x += nx * (overlap + 0.5)
                    egg.y += ny * (overlap + 0.5)

                    # 1.5배 반사 (법선 방향 속도 성분만)
                    dot = egg.vx * nx + egg.vy * ny
                    if dot < 0:
                        egg.vx -= 2 * dot * nx * tire.BOOST
                        egg.vy -= 2 * dot * ny * tire.BOOST

                    expired = tire.register_hit()
                    if expired:
                        self.log("🔴 타이어 수명 소진! 사라집니다.")
                    break   # 한 프레임에 하나만

    def _process_drains(self):
        """하수구 — 반경 안에 들어온 알을 대각선 구멍으로 순간이동."""
        drains      = self.map_obj.drains
        active_eggs = [e for e in self.eggs if e.active]
        for di, drain in enumerate(drains):
            if not drain.active:
                continue
            partner = drains[drain.partner_idx]
            for egg in active_eggs:
                if drain.in_range(egg):
                    # 순간이동
                    egg.x = partner.x
                    egg.y = partner.y
                    # 속도 유지 (방향 유지)
                    self.log(f"🌀 하수구! 알이 대각선 구멍으로 순간이동!")
                    break

    # ── 승패 판정 ──────────────────────────────────────────────────
    def _check_winner(self):
        p0 = self.my_eggs(0)
        p1 = self.my_eggs(1)
        if not p0:
            self.winner = 1; self.phase = STATE_GAMEOVER
            self.log("🎉 P2 승리!")
        elif not p1:
            self.winner = 0; self.phase = STATE_GAMEOVER
            self.log("🎉 P1 승리!")

    def _next_turn(self):
        self.turn = 1 - self.turn
        self.selected_egg    = None
        self.action_mode     = ACTION_SHOOT
        self.ability_step    = 0
        self.ability_targets = []
        self.ability_egg     = None
        tick_seal(self.eggs)
        self.log(f"── {'P1' if self.turn == 0 else 'P2'} 차례 ──")

    # ── 발사 ───────────────────────────────────────────────────────
    def try_shoot(self, egg: Egg, vx: float, vy: float) -> bool:
        if egg.sealed:
            self.log("❌ 봉인된 알은 발사할 수 없습니다.")
            return False
        if egg.owner != self.turn:
            return False
        egg.vx = vx
        egg.vy = vy
        self.simulating   = True
        self.selected_egg = None
        self.log(f"{'P1' if self.turn==0 else 'P2'}: {EGG_INFO[egg.type]['name']} 발사!")
        return True

    # ── 능력 ───────────────────────────────────────────────────────
    def start_ability(self, egg: Egg) -> tuple[bool, str]:
        if egg.sealed:
            return False, "봉인된 알은 능력을 쓸 수 없습니다."
        if egg.owner != self.turn:
            return False, "자신의 알만 선택하세요."
        if egg.type == "normal":
            return False, "일반알은 능력이 없습니다."
        if egg.uses_left <= 0:
            return False, f"능력 사용 횟수를 모두 소진했습니다. (0/{egg.max_uses})"

        self.ability_egg     = egg
        self.ability_step    = 0
        self.ability_targets = []
        self.phase           = STATE_ABILITY
        return True, self._ability_prompt(egg)

    def _ability_prompt(self, egg: Egg) -> str:
        t = egg.type
        remain = f" [{egg.uses_left}/{egg.max_uses}회 남음]"
        prompts = {
            "barrier":   f"방벽알: 빈 위치 클릭{remain}",
            "seal":      f"봉인알: 봉인할 알 클릭{remain}",
            "copy":      f"복사알: 적 알=능력복사 / 아군 알=위력복사{remain}",
            "clone":     f"분신알: '확인/발동' 버튼{remain}",
            "bomb":      f"폭탄알: 지뢰 설치할 빈 위치 클릭{remain}",
            "invisible": f"투명알: '확인/발동' 버튼{remain}",
            "psycho":    f"염력알: 파괴할 적 알 클릭{remain}",
            "ice":       f"얼음알: 슬립 부여할 알 클릭{remain}",
        }
        if t == "magnet":
            step = self.ability_step
            return (f"자석알: {'첫 번째' if step==0 else '두 번째'} 알 클릭{remain}")
        return prompts.get(t, "능력 발동 중...")

    def handle_ability_click_egg(self, clicked: Egg) -> tuple[bool, str]:
        egg = self.ability_egg
        if egg is None:
            return False, "능력 알이 없습니다."
        t = egg.type

        if t == "seal":
            ok, msg = ability_seal(egg, clicked)
            if ok: self._end_ability_turn()
            return ok, msg

        if t == "copy":
            if clicked.owner != self.turn:
                ok, msg = ability_copy_ability(egg, clicked)
            else:
                ok, msg = ability_copy_power(egg, clicked)
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
                    self._end_ability_turn()
                else:
                    self.ability_targets = []
                return ok, msg
            self.ability_step = 1
            return True, self._ability_prompt(egg)

        return False, "해당 능력은 알 클릭이 필요하지 않습니다."

    def handle_ability_click_pos(self, x: float, y: float) -> tuple[bool, str]:
        egg = self.ability_egg
        if egg is None:
            return False, ""
        t = egg.type

        if t == "barrier":
            ok, msg = ability_barrier(egg, x, y, self.eggs, self.barriers)
            if ok: self._end_ability_turn()
            return ok, msg

        if t == "bomb":
            ok, msg = ability_bomb(egg, x, y, self.eggs, self.barriers, self.mines)
            if ok: self._end_ability_turn()
            return ok, msg

        return False, "위치 선택이 필요 없는 능력입니다."

    def handle_ability_confirm(self) -> tuple[bool, str]:
        egg = self.ability_egg
        if egg is None:
            return False, ""
        t = egg.type

        if t == "clone":
            ok, msg = ability_clone(egg, self.eggs)
            if ok: self._end_ability_turn()
            return ok, msg

        if t == "invisible":
            ok, msg = ability_invisible(egg)
            if ok:
                self.phase       = STATE_PLAY
                self.action_mode = ACTION_SHOOT
                self.ability_egg = None
            return ok, msg

        return False, "확인이 필요 없는 능력입니다."

    def _end_ability_turn(self):
        self.simulating      = False
        self.phase           = STATE_PLAY
        self.ability_egg     = None
        self.ability_targets = []
        self.ability_step    = 0
        self._check_winner()
        if self.phase != STATE_GAMEOVER:
            self._next_turn()

    def cancel_ability(self):
        self.phase           = STATE_PLAY
        self.ability_egg     = None
        self.ability_step    = 0
        self.ability_targets = []