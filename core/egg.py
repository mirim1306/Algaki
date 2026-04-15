# core/egg.py
from __future__ import annotations
import math
from core.constants import *


class Egg:
    _id_counter = 0

    def __init__(self, x: float, y: float, owner: int, egg_type: str = "normal"):
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

        # 상태 플래그
        self.sealed:    bool = False
        self.seal_turns: int = 0        # 봉인 남은 턴 수
        self.icy:       bool = False
        self.invisible: bool = False
        self.is_clone:  bool = False
        self.magnet_pair: "Egg | None" = None

        # 복사알 저장값
        self.copied_ability: str | None   = None   # 저장된 능력 타입
        self.copied_vx:      float | None = None   # 저장된 위력 x
        self.copied_vy:      float | None = None   # 저장된 위력 y

        # 복사알 상태
        self.copy_mode: str = "none"  # "none" | "ability" | "power"

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
        out_left   = self.x + self.r < BOARD_LEFT
        out_right  = self.x - self.r > BOARD_RIGHT
        out_top    = self.y + self.r < BOARD_TOP
        out_bottom = self.y - self.r > BOARD_BOTTOM
        if out_left or out_right or out_top or out_bottom:
            self.active = False
            return True
        return False

    @property
    def base_color(self):
        return EGG_COLORS.get(self.type, (180, 180, 180))

    def __repr__(self):
        return f"Egg(id={self.id}, type={self.type}, owner={self.owner})"


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
        return math.hypot(self.x - egg.x, self.y - egg.y) < self.BLAST_RADIUS