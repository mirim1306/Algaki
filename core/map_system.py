"""
맵 0: 기본 맵   — 장애물 없음
맵 1: 폭탄 맵   — 중앙 5개 폭탄 일렬 (알이 닿으면 폭발, 연쇄 가능)
맵 2: 타이어 맵 — 모서리4 + 중앙1 타이어 (1.5배 반발, 수명 10회)
맵 3: 하수구 맵 — 모서리 4개 구멍 (알이 들어가면 대각선 구멍으로 순간이동)

포진 0: ─자  수평 일렬
포진 1: W자  파형 위볼록 (홀=앞, 짝=뒤)
포진 2: M자  파형 아래볼록 (홀=뒤, 짝=앞)
포진 3: U자  U형 (양끝 앞, 중앙 뒤)
"""
from __future__ import annotations
import math
import core.constants as _c
from core.egg import Barrier


# ─────────────────────────────────────────────────────────────────
# 맵 메타
# ─────────────────────────────────────────────────────────────────
MAP_DEFS = [
    {"name": "기본 맵",  "desc": "장애물 없는 순수 실력전",        "color": (28, 36, 70),  "bg": (18, 24, 50),  "line": (60, 70, 110)},
    {"name": "폭탄 맵",  "desc": "중앙 5폭탄 — 연쇄 폭발 주의",   "color": (80, 38, 20),  "bg": (38, 16,  8),  "line": (180, 80, 40)},
    {"name": "타이어 맵","desc": "5타이어 — 1.5배 반발 수명10",     "color": (50, 50, 20),  "bg": (22, 22,  8),  "line": (160,160, 40)},
    {"name": "하수구 맵","desc": "4구석 구멍 — 대각 순간이동",      "color": (20, 50, 50),  "bg": ( 8, 24, 24),  "line": (40, 160,160)},
]

# 포진 메타
FORMATION_DEFS = [
    {"name": "─자 포진", "desc": "수평 일렬 배치"},
    {"name": "W자 포진", "desc": "파형 위볼록"},
    {"name": "M자 포진", "desc": "파형 아래볼록"},
    {"name": "U자 포진", "desc": "U형 (양끝 높음)"},
]


# ─────────────────────────────────────────────────────────────────
# 특수 오브젝트 클래스
# ─────────────────────────────────────────────────────────────────

class MapBomb:
    """맵 폭탄 — 알이 닿으면 폭발, 연쇄 가능."""
    BLAST_RADIUS = 90

    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y
        self.r = 18
        self.active = True

    def overlaps_egg(self, egg) -> bool:
        return math.hypot(self.x - egg.x, self.y - egg.y) < self.r + egg.r

    def in_blast(self, other) -> bool:
        return math.hypot(self.x - other.x, self.y - other.y) < self.BLAST_RADIUS


class Tire:
    """타이어 — 1.5배 반발, 수명 10회."""
    BOOST    = 1.5
    MAX_HITS = 10

    def __init__(self, x: float, y: float):
        self.x    = x
        self.y    = y
        self.r    = 28
        self.active = True
        self.hits = 0

    def overlaps_egg(self, egg) -> bool:
        return math.hypot(self.x - egg.x, self.y - egg.y) < self.r + egg.r

    def register_hit(self) -> bool:
        """히트 등록. 수명 초과 시 active=False 반환 True."""
        self.hits += 1
        if self.hits >= self.MAX_HITS:
            self.active = False
            return True
        return False


class Drain:
    """하수구 — 반경 안 들어오면 대각선 구멍으로 순간이동."""
    SUCK_DIST = 22

    def __init__(self, x: float, y: float, partner_idx: int):
        self.x           = x
        self.y           = y
        self.r           = 26
        self.active      = True
        self.partner_idx = partner_idx  # 대각선 구멍 인덱스

    def in_range(self, egg) -> bool:
        return math.hypot(self.x - egg.x, self.y - egg.y) < self.SUCK_DIST


# ─────────────────────────────────────────────────────────────────
# 맵 오브젝트 컨테이너
# ─────────────────────────────────────────────────────────────────

class MapObjects:
    def __init__(self):
        self.barriers:  list[Barrier] = []
        self.map_bombs: list[MapBomb] = []
        self.tires:     list[Tire]    = []
        self.drains:    list[Drain]   = []


# ─────────────────────────────────────────────────────────────────
# 맵 생성
# ─────────────────────────────────────────────────────────────────

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
    bl, bt = _c.BOARD_LEFT,  _c.BOARD_TOP
    br, bb = _c.BOARD_RIGHT, _c.BOARD_BOTTOM
    cx, cy = _c.MID_X, (bt + bb) // 2
    for x, y in [(bl+pad, bt+pad), (br-pad, bt+pad),
                  (bl+pad, bb-pad), (br-pad, bb-pad),
                  (cx, cy)]:
        obj.tires.append(Tire(float(x), float(y)))


def _build_drain_map(obj: MapObjects):
    pad = 70
    bl, bt = _c.BOARD_LEFT,  _c.BOARD_TOP
    br, bb = _c.BOARD_RIGHT, _c.BOARD_BOTTOM
    # 인덱스: 0=좌상, 1=우상, 2=좌하, 3=우하
    # 대각선 짝: 0↔3, 1↔2
    positions = [
        (bl+pad, bt+pad, 3),
        (br-pad, bt+pad, 2),
        (bl+pad, bb-pad, 1),
        (br-pad, bb-pad, 0),
    ]
    for x, y, partner in positions:
        obj.drains.append(Drain(float(x), float(y), partner))


# ─────────────────────────────────────────────────────────────────
# 포진 계산
# ─────────────────────────────────────────────────────────────────

def get_formation_positions(owner: int, n: int, formation: int) -> list[tuple[float, float]]:
    """각 플레이어의 알 초기 위치 반환."""
    bl, bt = _c.BOARD_LEFT,  _c.BOARD_TOP
    br, bb = _c.BOARD_RIGHT, _c.BOARD_BOTTOM
    mx = _c.MID_X
    r  = _c.EGG_RADIUS

    # 플레이어 구역 중심
    zone_cx = (bl + mx) // 2 if owner == 0 else (mx + br) // 2
    cy      = (bt + bb) // 2

    # 세로 간격
    zone_h = bb - bt
    step   = min(58, max(r * 2 + 6, (zone_h - r * 4) // max(n - 1, 1)))
    total_h = step * (n - 1)
    y_start = cy - total_h // 2

    offset_x = 55  # 포진 깊이

    positions = []
    for i in range(n):
        y = y_start + i * step

        if   formation == 0:  # ─자: 일렬
            dx = 0
        elif formation == 1:  # W자: 홀=앞, 짝=뒤
            dx = offset_x if i % 2 == 0 else -offset_x
        elif formation == 2:  # M자: 홀=뒤, 짝=앞
            dx = -offset_x if i % 2 == 0 else offset_x
        elif formation == 3:  # U자: 양끝=앞, 중앙=뒤
            mid = (n - 1) / 2.0
            t   = abs(i - mid) / max(mid, 1.0)
            dx  = int(offset_x * t) - offset_x // 2
        else:
            dx = 0

        # P2는 x 방향 반전
        if owner == 1:
            dx = -dx

        x = float(zone_cx + dx)

        # 보드 안 clamp
        x_min = bl + r + 4
        x_max = (mx - r - 10) if owner == 0 else (br - r - 4)
        x = max(x_min, min(x_max, x))
        y = max(float(bt + r + 4), min(float(bb - r - 4), float(y)))

        positions.append((x, y))

    return positions