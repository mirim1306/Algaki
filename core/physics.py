# core/physics.py
from __future__ import annotations
import math
from core.constants import *
from core.egg import Egg, Barrier, Mine


def resolve_egg_collision(a: Egg, b: Egg):
    """두 알 탄성 충돌 — 정면/비껴맞기 모두 확실히 밀림."""
    dx = b.x - a.x
    dy = b.y - a.y
    dist = math.hypot(dx, dy)
    if dist < 0.001:
        # 완전히 겹쳤을 때 랜덤 방향으로 밀어냄
        import random
        angle = random.uniform(0, math.pi * 2)
        dx, dy, dist = math.cos(angle), math.sin(angle), 1.0

    nx, ny = dx / dist, dy / dist
    overlap = (a.r + b.r) - dist

    # 겹침 완전 분리 (비율 50:50)
    sep = overlap * 0.51
    a.x -= nx * sep
    a.y -= ny * sep
    b.x += nx * sep
    b.y += ny * sep

    # 법선 방향 상대 속도 (양수 = 멀어지는 중 → 충돌 처리 불필요)
    dv_n = (a.vx - b.vx) * nx + (a.vy - b.vy) * ny
    if dv_n >= 0:
        return

    # 반발계수: 얼음 상태면 더 탄력적
    e = RESTITUTION
    if a.icy or b.icy:
        e = min(e * ICE_SLIP_MULT, 1.6)

    # 등질량 충돌 impulse
    impulse = -(1.0 + e) * dv_n * 0.5

    a.vx -= impulse * nx
    a.vy -= impulse * ny
    b.vx += impulse * nx
    b.vy += impulse * ny

    # 정지 알이 거의 안 밀릴 때 최소 속도 강제 부여
    b_spd = math.hypot(b.vx, b.vy)
    if b_spd < 0.8 and abs(dv_n) > 0.5:
        scale = max(abs(dv_n) * 0.5, 1.2) / max(b_spd, 0.001)
        b.vx *= scale
        b.vy *= scale

    a_spd = math.hypot(a.vx, a.vy)
    if a_spd < 0.8 and abs(dv_n) > 0.5:
        scale = max(abs(dv_n) * 0.3, 0.8) / max(a_spd, 0.001)
        a.vx *= scale
        a.vy *= scale


def resolve_barrier_collision(egg: Egg, barrier: Barrier):
    dx = egg.x - barrier.x
    dy = egg.y - barrier.y
    dist = math.hypot(dx, dy)
    if dist < 0.001:
        dx, dy, dist = 1, 0, 1
    nx, ny = dx / dist, dy / dist

    overlap = (egg.r + barrier.r) - dist
    egg.x += nx * (overlap + 0.5)
    egg.y += ny * (overlap + 0.5)

    dot = egg.vx * nx + egg.vy * ny
    if dot < 0:
        egg.vx -= 2 * dot * nx * RESTITUTION
        egg.vy -= 2 * dot * ny * RESTITUTION


def apply_magnet(egg: Egg):
    partner = egg.magnet_pair
    if partner is None or not partner.active:
        egg.magnet_pair = None
        return
    dx = partner.x - egg.x
    dy = partner.y - egg.y
    dist = math.hypot(dx, dy)
    if dist < egg.r + partner.r + 2:
        return
    f = MAGNET_FORCE / max(dist, 1)
    egg.vx += dx * f
    egg.vy += dy * f


def step_physics(eggs: list[Egg], barriers: list[Barrier], mines: list[Mine],
                 map_barriers: list | None = None):
    """한 프레임 물리. 반환: 폭발할 지뢰 목록"""
    triggered_mines: list[Mine] = []
    all_barriers = list(barriers)
    if map_barriers:
        all_barriers.extend(map_barriers)

    for egg in eggs:
        if not egg.active:
            continue
        if not egg.is_moving():
            continue
        apply_magnet(egg)
        egg.x += egg.vx
        egg.y += egg.vy
        egg.apply_friction()

        # 벽 밖으로 나가면 즉시 파괴
        import core.constants as _c
        out = (egg.x + egg.r < _c.BOARD_LEFT or
               egg.x - egg.r > _c.BOARD_RIGHT or
               egg.y + egg.r < _c.BOARD_TOP or
               egg.y - egg.r > _c.BOARD_BOTTOM)
        if out:
            egg.active = False
            egg.vx = 0.0
            egg.vy = 0.0

    # 알 ↔ 알 충돌 (비활성 제외)
    active = [e for e in eggs if e.active]
    for i in range(len(active)):
        for j in range(i + 1, len(active)):
            a, b = active[i], active[j]
            if a.overlaps(b):
                resolve_egg_collision(a, b)

    # 알 ↔ 방벽 충돌
    for egg in [e for e in eggs if e.active]:
        for barrier in all_barriers:
            if barrier.active and barrier.overlaps_egg(egg):
                resolve_barrier_collision(egg, barrier)

    # 지뢰 발동 체크
    for mine in mines:
        if not mine.active or mine.triggered:
            continue
        for egg in [e for e in eggs if e.active]:
            if egg.owner != mine.owner and mine.in_blast(egg):
                mine.triggered = True
                triggered_mines.append(mine)
                break

    return triggered_mines


def all_still(eggs: list[Egg]) -> bool:
    return all(not e.is_moving() for e in eggs if e.active)