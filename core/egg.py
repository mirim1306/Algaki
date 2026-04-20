from __future__ import annotations
import math
from core.constants import *

#   (EGGS_PER_PLAYER=5)
#   ±1   ±1 ,  1  5
#   (normal)  (psycho)
BASE_ABILITY_USES = {
    "normal":    0,   #
    "barrier":   3,
    "seal":      1,
    "copy":      3,
    "clone":     2,
    "bomb":      3,
    "invisible": 2,
    "psycho":    1,   #  —
    "ice":       2,
    "magnet":    1,
}
#     (  )
NO_SCALE_TYPES = {"normal", "psycho"}


def calc_uses(egg_type: str, egg_count: int) -> int:
    """egg_count에 따른 능력 사용 횟수 계산."""
    base = BASE_ABILITY_USES.get(egg_type, 0)
    if base == 0:
        return 0
    if egg_type in NO_SCALE_TYPES:
        return base
    delta = egg_count - EGGS_PER_PLAYER   #
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

        #
        _cnt = egg_count if egg_count is not None else EGGS_PER_PLAYER
        self.max_uses:  int = calc_uses(egg_type, _cnt)
        self.uses_left: int = self.max_uses

        #
        self.sealed:     bool = False
        self.seal_turns: int  = 0
        self.icy:        bool = False
        self.invisible:  bool = False
        self.is_clone:   bool = False
        self.magnet_pair: "Egg | None" = None

        #
        self.copied_ability: str | None   = None
        self.copied_vx:      float | None = None
        self.copied_vy:      float | None = None
        self.copy_mode: str = "none"   # "none" | "ability" | "power"

    # --     ----------------------------------------
    def can_use_ability(self) -> bool:
        if self.type == "normal":
            return False
        if self.sealed:
            return False
        return self.uses_left > 0

    def consume_use(self) -> bool:
        """ 1 .  True."""
        if self.uses_left <= 0:
            return False
        self.uses_left -= 1
        return True

    # --  ------------------------------------------------------
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
    BLAST_RADIUS = EGG_RADIUS * 6   # : 132px

    def __init__(self, x: float, y: float, owner: int):
        self.x = x
        self.y = y
        self.r = EGG_RADIUS // 2
        self.owner     = owner
        self.active    = True
        self.triggered = False

    def in_blast(self, egg: Egg) -> bool:
        return math.hypot(self.x - egg.x, self.y - egg.y) < self.BLAST_RADIUS# core/egg.py