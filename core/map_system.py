# core/map_system.py
"""
맵 정의 및 맵별 장애물(정적 방벽) 생성.
맵 0: 기본 맵 — 장애물 없음, 넓은 오픈 필드
맵 1: 협곡 맵 — 중앙 세로 장벽 2개 (좁은 통로)
맵 2: 미러 맵 — 4구석에 고정 블록, 중앙 십자 패턴
"""
from __future__ import annotations
import math
from core.egg import Barrier
import core.constants as _c


# 맵 메타 정보 (egg_select_screen과 공유)
MAP_DEFS = [
    {
        "name":  "기본 맵",
        "desc":  "장애물 없는 오픈 필드",
        "color": (28, 36, 70),
        "bg":    (18, 24, 50),
        "line":  (60, 70, 110),
    },
    {
        "name":  "협곡 맵",
        "desc":  "중앙 세로 장벽 — 좁은 통로로 싸워라",
        "color": (20, 50, 30),
        "bg":    (10, 28, 18),
        "line":  (40, 110, 60),
    },
    {
        "name":  "미러 맵",
        "desc":  "4구석 블록 + 중앙 십자 장애물",
        "color": (50, 20, 60),
        "bg":    (28, 10, 40),
        "line":  (110, 50, 140),
    },
]


def build_map_barriers(map_index: int) -> list[Barrier]:
    """맵별 정적 방벽 목록 반환."""
    _c_snap()  # 최신 상수 반영
    if map_index == 0:
        return _map0()
    elif map_index == 1:
        return _map1()
    elif map_index == 2:
        return _map2()
    return []


def _c_snap():
    pass  # 임포트 시 _c가 이미 최신값이므로 별도 작업 불필요


def _map0() -> list[Barrier]:
    """기본 맵: 장애물 없음."""
    return []


def _map1() -> list[Barrier]:
    """협곡 맵: 중앙 y축 위아래에 방벽 블록 2열."""
    barriers = []
    r = _c.EGG_RADIUS
    cx = _c.MID_X
    board_h = _c.BOARD_BOTTOM - _c.BOARD_TOP

    # 위쪽 벽
    top_start = _c.BOARD_TOP + int(board_h * 0.10)
    top_end   = _c.BOARD_TOP + int(board_h * 0.38)
    y = top_start
    while y < top_end:
        barriers.append(Barrier(cx, y))
        y += r * 2 + 2

    # 아래쪽 벽
    bot_start = _c.BOARD_TOP + int(board_h * 0.62)
    bot_end   = _c.BOARD_TOP + int(board_h * 0.90)
    y = bot_start
    while y < bot_end:
        barriers.append(Barrier(cx, y))
        y += r * 2 + 2

    return barriers


def _map2() -> list[Barrier]:
    """미러 맵: 4구석 L블록 + 중앙 십자."""
    barriers = []
    r = _c.EGG_RADIUS
    pad = r * 3 + 10

    # 보드 범위
    bl, bt = _c.BOARD_LEFT, _c.BOARD_TOP
    br, bb = _c.BOARD_RIGHT, _c.BOARD_BOTTOM
    cx = _c.MID_X
    cy = (bt + bb) // 2

    # 4구석 2×2 블록
    corners = [
        (bl + pad,       bt + pad),
        (br - pad,       bt + pad),
        (bl + pad,       bb - pad),
        (br - pad,       bb - pad),
    ]
    for (ox, oy) in corners:
        for dx in [-r - 1, r + 1]:
            for dy in [-r - 1, r + 1]:
                barriers.append(Barrier(ox + dx, oy + dy))

    # 중앙 십자 (4방향 각 2개)
    for i in range(1, 3):
        off = i * (r * 2 + 4)
        barriers.append(Barrier(cx + off, cy))
        barriers.append(Barrier(cx - off, cy))
        barriers.append(Barrier(cx,       cy + off))
        barriers.append(Barrier(cx,       cy - off))

    return barriers