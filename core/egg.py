from __future__ import annotations
import math
from core.constants import *

# 기본 알 개수(EGGS_PER_PLAYER=5) 기준 능력 사용 횟수
# 알 개수가 ±1 될 때마다 ±1 조정, 최소 1 최대 5
# 능력 없는 알(normal) 및 자폭형(psycho)은 횟수 조정 없음
BASE_ABILITY_USES = {
    "normal":    0,   # 능력 없음
    "barrier":   3,
    "seal":      1,
    "copy":      3,
    "clone":     2,
    "bomb":      3,
    "invisible": 2,
    "psycho":    1,   # 자폭형 — 조정 없음
    "ice":       2,
    "magnet":    1,
}
# 횟수 조정 제외 타입 (능력이 없거나 자폭형)
NO_SCALE_TYPES = {"normal", "psycho"}


def calc_uses(egg_type: str, egg_count: int) -> int:
    """egg_count에 따른 능력 사용 횟수 계산."""
    base = BASE_ABILITY_USES.get(egg_type, 0)
    if base == 0:
        return 0
    if egg_type in NO_SCALE_TYPES:
        return base
    delta = egg_count - EGGS_PER_PLAYER   # 기본값 대비 차이
    uses  = base + delta
    return max(1, min(5, uses))


class Egg:
    _id_counter = 0

    def __init__(self, x: float, y: float, owner: int,
                 egg_type: str = "normal", egg_count: int | None = None):
        Egg._id_counter += 1
        self.id:    int   = Egg._id_counter
        self.x:    float  = x
        self.y:    float  = y
        self.vx:   float  = 0.0
        self.vy:   float  = 0.0
        self.owner: int   = owner
        self.type:  str   = egg_type
        self.r:     int   = EGG_RADIUS
        self.active: bool = True

        # 능력 사용 횟수
        _cnt = egg_count if egg_count is not None else EGGS_PER_PLAYER
        self.max_uses:  int = calc_uses(egg_type, _cnt)
        self.uses_left: int = self.max_uses

        # 상태 플래그
        self.sealed:     bool = False
        self.seal_turns: int  = 0
        self.icy:        bool = False
        self.invisible:  bool = False
        self.is_clone:   bool = False
        self.magnet_pair: "Egg | None" = None

        # 복사알 저장값
        self.copied_ability: str | None   = None
        self.copied_vx:      float | None = None
        self.copied_vy:      float | None = None
        self.copy_mode: str = "none"   # "none" | "ability" | "power"

    # ── 능력 사용 가능 여부 ────────────────────────────────────────
    def can_use_ability(self) -> bool:
        if self.type == "normal":
            return False
        if self.sealed:
            return False
        return self.uses_left > 0

    def consume_use(self) -> bool:
        """능력 1회 소모. 성공하면 True."""
        if self.uses_left <= 0:
            return False
        self.uses_left -= 1
        return True

    # ── 물리 ──────────────────────────────────────────────────────
    @property
    def speed(self) -> float:
        return math.hypot(self.vx, self.vy)

    def is_moving(self) -> bool:
        return self.speed > MIN_SPEED

    def apply_friction(self):
        self.vx *= FRICTION
        self.vy *= FRICTION
        if self.speed < MIN_SPEED:
            self.vx = 0.0
            self.vy = 0.0

    def dist_to(self, other: "Egg") -> float:
        return math.hypot(self.x - other.x, self.y - other.y)

    def overlaps(self, other: "Egg") -> bool:
        return self.dist_to(other) < self.r + other.r

    def bounce_walls(self) -> bool:
        out = (self.x + self.r < BOARD_LEFT  or
               self.x - self.r > BOARD_RIGHT or
               self.y + self.r < BOARD_TOP   or
               self.y - self.r > BOARD_BOTTOM)
        if out:
            self.active = False
            return True
        return False

    @property
    def base_color(self):
        return EGG_COLORS.get(self.type, (180, 180, 180))

    def __repr__(self):
        return (f"Egg(id={self.id}, type={self.type}, owner={self.owner}, "
                f"uses={self.uses_left}/{self.max_uses})")


class Barrier:
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y
        self.r = EGG_RADIUS
        self.active = True

    def overlaps_egg(self, egg: Egg) -> bool:
        return math.hypot(self.x - egg.x, self.y - egg.y) < self.r + egg.r

    def overlaps_point(self, px: float, py: float) -> bool:
        return math.hypot(self.x - px, self.y - py) < self.r


class Mine:
    BLAST_RADIUS = EGG_RADIUS * 4

    def __init__(self, x: float, y: float, owner: int):
        self.x = x
        self.y = y
        self.r = EGG_RADIUS // 2
        self.owner     = owner
        self.active    = True
        self.triggered = False

    def in_blast(self, egg: Egg) -> bool:
        return math.hypot(self.x - egg.x, self.y - egg.y) < self.BLAST_RADIUS# core/egg.py