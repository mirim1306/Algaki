"""
맵 0: 기본 맵   — 장애물 없음
맵 1: 폭탄 맵   — 중앙 5개 폭탄 일렬 (알이 닿으면 폭발, 근거리=파괴, 광역=밀려남)
맵 2: 타이어 맵 — 모서리4 + 중앙1 타이어 (1.5배 반발, 수명 10회)
맵 3: 하수구 맵 — 모서리 4개 구멍 (알이 들어가면 대각선 구멍으로 순간이동)
"""
from __future__ import annotations
import math
import core.constants as _c
from core.egg import Barrier, Egg

MAP_DEFS = [
    {"name": "기본 맵",  "desc": "장애물 없는 순수 실력전",       "color": (28, 36, 70),  "bg": (18, 24, 50),  "line": (60, 70, 110)},
    {"name": "폭탄 맵",  "desc": "중앙 5폭탄 — 연쇄 폭발 주의",  "color": (80, 38, 20),  "bg": (38, 16,  8),  "line": (180, 80, 40)},
    {"name": "타이어 맵","desc": "5타이어 — 1.5배 반발 수명10",    "color": (50, 50, 20),  "bg": (22, 22,  8),  "line": (160,160, 40)},
    {"name": "하수구 맵","desc": "4구석 구멍 — 대각 순간이동",     "color": (20, 50, 50),  "bg": ( 8, 24, 24),  "line": (40, 160,160)},
]

FORMATION_DEFS = [
    {"name": "─자 포진", "desc": "수평 일렬 배치"},
    {"name": "W자 포진", "desc": "파형 위볼록"},
    {"name": "M자 포진", "desc": "파형 아래볼록"},
    {"name": "U자 포진", "desc": "U형 (양끝 높음)"},
]


class MapBomb:
    """맵 폭탄 — 알이 닿으면 폭발.
    KILL_RADIUS 이내 알은 즉시 파괴,
    BLAST_RADIUS 이내 알은 강하게 밀려남.
    연쇄 가능.
    """
    KILL_RADIUS  = 50   # 즉시 파괴 반경
    BLAST_RADIUS = 120  # 밀어내기 반경

    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y
        self.r = 18
        self.active = True

    def overlaps_egg(self, egg: Egg) -> bool:
        return math.hypot(self.x - egg.x, self.y - egg.y) < self.r + egg.r

    def in_blast(self, other: "MapBomb") -> bool:
        return math.hypot(self.x - other.x, self.y - other.y) < self.BLAST_RADIUS


class Tire:
    BOOST    = 1.5
    MAX_HITS = 10

    def __init__(self, x: float, y: float):
        self.x = x; self.y = y; self.r = 28
        self.active = True; self.hits = 0

    def overlaps_egg(self, egg: Egg) -> bool:
        return math.hypot(self.x - egg.x, self.y - egg.y) < self.r + egg.r

    def register_hit(self) -> bool:
        self.hits += 1
        if self.hits >= self.MAX_HITS:
            self.active = False
            return True
        return False


class Drain:
    SUCK_DIST = 22

    def __init__(self, x: float, y: float, partner_idx: int):
        self.x = x; self.y = y; self.r = 26
        self.active = True; self.partner_idx = partner_idx

    def in_range(self, egg: Egg) -> bool:
        return math.hypot(self.x - egg.x, self.y - egg.y) < self.SUCK_DIST


class MapObjects:
    def __init__(self):
        self.barriers:  list[Barrier]  = []
        self.map_bombs: list[MapBomb]  = []
        self.tires:     list[Tire]     = []
        self.drains:    list[Drain]    = []


def build_map_objects(map_index: int) -> MapObjects:
    obj = MapObjects()
    if   map_index == 1: _build_bomb_map(obj)
    elif map_index == 2: _build_tire_map(obj)
    elif map_index == 3: _build_drain_map(obj)
    return obj


def _build_bomb_map(obj: MapObjects):
    cx = _c.MID_X
    bh = _c.BOARD_BOTTOM - _c.BOARD_TOP
    n  = 5
    spacing = bh // (n + 1)
    for i in range(1, n + 1):
        obj.map_bombs.append(MapBomb(float(cx), float(_c.BOARD_TOP + i * spacing)))


def _build_tire_map(obj: MapObjects):
    pad = 90
    bl, bt = _c.BOARD_LEFT, _c.BOARD_TOP
    br, bb = _c.BOARD_RIGHT, _c.BOARD_BOTTOM
    cx, cy = _c.MID_X, (bt + bb) // 2
    for x, y in [(bl+pad, bt+pad), (br-pad, bt+pad),
                 (bl+pad, bb-pad), (br-pad, bb-pad), (cx, cy)]:
        obj.tires.append(Tire(float(x), float(y)))


def _build_drain_map(obj: MapObjects):
    pad = 70
    bl, bt = _c.BOARD_LEFT, _c.BOARD_TOP
    br, bb = _c.BOARD_RIGHT, _c.BOARD_BOTTOM
    positions = [
        (bl+pad, bt+pad, 3), (br-pad, bt+pad, 2),
        (bl+pad, bb-pad, 1), (br-pad, bb-pad, 0),
    ]
    for x, y, partner in positions:
        obj.drains.append(Drain(float(x), float(y), partner))


def explode_map_bomb(bomb: MapBomb, eggs: list[Egg],
                     all_bombs: list[MapBomb]) -> tuple[list[Egg], list[Egg]]:
    """
    맵 폭탄 폭발 처리.
    반환: (파괴된 알 목록, 밀린 알 목록)
    연쇄: BLAST_RADIUS 내 다른 폭탄도 폭발 예약(active=True인 것만).
    """
    if not bomb.active:
        return [], []
    bomb.active = False

    killed  = []
    pushed  = []

    for egg in eggs:
        if not egg.active:
            continue
        dx   = egg.x - bomb.x
        dy   = egg.y - bomb.y
        dist = math.hypot(dx, dy)

        if dist < bomb.KILL_RADIUS:
            # 즉시 파괴
            egg.active = False
            egg.vx = egg.vy = 0.0
            killed.append(egg)
        elif dist < bomb.BLAST_RADIUS:
            # 밀려남
            if dist < 0.1:
                dx, dy, dist = 1.0, 0.0, 1.0
            nx, ny = dx / dist, dy / dist
            force  = (bomb.BLAST_RADIUS - dist) / bomb.BLAST_RADIUS * 28
            egg.vx += nx * force
            egg.vy += ny * force
            pushed.append(egg)

    # 연쇄 폭발 예약 (실제 폭발은 step_physics에서 처리)
    for other in all_bombs:
        if other is bomb or not other.active:
            continue
        if bomb.in_blast(other):
            other._chain_pending = True   # 다음 루프에서 처리

    return killed, pushed


def get_formation_positions(owner: int, n: int, formation: int) -> list[tuple[float, float]]:
    bl, bt = _c.BOARD_LEFT, _c.BOARD_TOP
    br, bb = _c.BOARD_RIGHT, _c.BOARD_BOTTOM
    mx = _c.MID_X
    r  = _c.EGG_RADIUS

    zone_cx = (bl + mx) // 2 if owner == 0 else (mx + br) // 2
    cy      = (bt + bb) // 2
    zone_h  = bb - bt
    step    = min(58, max(r * 2 + 6, (zone_h - r * 4) // max(n - 1, 1)))
    total_h = step * (n - 1)
    y_start = cy - total_h // 2
    offset_x = 55

    positions = []
    for i in range(n):
        y = y_start + i * step
        if   formation == 0: dx = 0
        elif formation == 1: dx = offset_x  if i % 2 == 0 else -offset_x
        elif formation == 2: dx = -offset_x if i % 2 == 0 else  offset_x
        elif formation == 3:
            mid = (n - 1) / 2.0
            t   = abs(i - mid) / max(mid, 1.0)
            dx  = int(offset_x * t) - offset_x // 2
        else: dx = 0

        if owner == 1:
            dx = -dx

        x = float(zone_cx + dx)
        x_min = bl + r + 4
        x_max = (mx - r - 10) if owner == 0 else (br - r - 4)
        x = max(x_min, min(x_max, x))
        y = max(float(bt + r + 4), min(float(bb - r - 4), float(y)))
        positions.append((x, y))

    return positions