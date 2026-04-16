from __future__ import annotations
import math
from core.constants import *
from core.egg import Egg, Barrier, Mine


def resolve_egg_collision(a: Egg, b: Egg):
    """알까기 스타일: 발사 알의 위력을 정지 알에 전달 (당구공 원리)."""
    dx = b.x - a.x
    dy = b.y - a.y
    dist = math.hypot(dx, dy)
    if dist < 0.001:
        import random
        angle = random.uniform(0, math.pi * 2)
        dx, dy, dist = math.cos(angle), math.sin(angle), 1.0

    nx, ny = dx / dist, dy / dist
    overlap = (a.r + b.r) - dist

    a_moving = math.hypot(a.vx, a.vy) > MIN_SPEED
    b_moving = math.hypot(b.vx, b.vy) > MIN_SPEED

    if a_moving and not b_moving:
        a.x -= nx * (overlap + 0.5)
        a.y -= ny * (overlap + 0.5)
    elif b_moving and not a_moving:
        b.x += nx * (overlap + 0.5)
        b.y += ny * (overlap + 0.5)
    else:
        sep = overlap * 0.51
        a.x -= nx * sep;  a.y -= ny * sep
        b.x += nx * sep;  b.y += ny * sep

    e = RESTITUTION
    if a.icy or b.icy:
        e = min(e * ICE_SLIP_MULT, 1.6)

    if a_moving and not b_moving:
        a_vn = a.vx * nx + a.vy * ny
        if a_vn > 0:
            b.vx += nx * a_vn * e
            b.vy += ny * a_vn * e
            a.vx -= nx * a_vn
            a.vy -= ny * a_vn

    elif b_moving and not a_moving:
        b_vn = -(b.vx * nx + b.vy * ny)
        if b_vn > 0:
            a.vx -= nx * b_vn * e
            a.vy -= ny * b_vn * e
            b.vx += nx * b_vn
            b.vy += ny * b_vn

    else:
        dv_n = (a.vx - b.vx) * nx + (a.vy - b.vy) * ny
        if dv_n < 0:
            impulse = -(1.0 + e) * dv_n * 0.5
            a.vx -= impulse * nx;  a.vy -= impulse * ny
            b.vx += impulse * nx;  b.vy += impulse * ny


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
    triggered: list[Mine] = []
    all_barriers = list(barriers)
    if map_barriers:
        all_barriers.extend(map_barriers)

    import core.constants as _c
    for egg in eggs:
        if not egg.active or not egg.is_moving():
            continue
        apply_magnet(egg)
        egg.x += egg.vx
        egg.y += egg.vy
        egg.apply_friction()
        out = (egg.x + egg.r < _c.BOARD_LEFT  or
               egg.x - egg.r > _c.BOARD_RIGHT or
               egg.y + egg.r < _c.BOARD_TOP   or
               egg.y - egg.r > _c.BOARD_BOTTOM)
        if out:
            egg.active = False
            egg.vx = egg.vy = 0.0

    active = [e for e in eggs if e.active]
    for i in range(len(active)):
        for j in range(i + 1, len(active)):
            a, b = active[i], active[j]
            if a.overlaps(b):
                resolve_egg_collision(a, b)

    for egg in [e for e in eggs if e.active]:
        for barrier in all_barriers:
            if barrier.active and barrier.overlaps_egg(egg):
                resolve_barrier_collision(egg, barrier)

    for mine in mines:
        if not mine.active or mine.triggered:
            continue
        for egg in [e for e in eggs if e.active]:
            if egg.owner != mine.owner and mine.in_blast(egg):
                mine.triggered = True
                triggered.append(mine)
                break

    return triggered


def all_still(eggs: list[Egg]) -> bool:
    return all(not e.is_moving() for e in eggs if e.active)