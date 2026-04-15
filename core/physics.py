# core/physics.py
from __future__ import annotations
import math
from core.constants import *
from core.egg import Egg, Barrier, Mine

def resolve_egg_collision(a: Egg, b: Egg):
    dx = b.x - a.x
    dy = b.y - a.y
    dist = math.hypot(dx, dy)
    if dist == 0:
        dx, dy, dist = 1, 0, 1

    nx, ny = dx / dist, dy / dist
    overlap = (a.r + b.r) - dist

    a.x -= nx * overlap * 0.5
    a.y -= ny * overlap * 0.5
    b.x += nx * overlap * 0.5
    b.y += ny * overlap * 0.5

    dv_n = (a.vx - b.vx) * nx + (a.vy - b.vy) * ny
    if dv_n > 0:
        return

    e = RESTITUTION
    if b.icy:
        e = min(e * ICE_SLIP_MULT, 1.6)

    impulse = (1 + e) * dv_n / 2
    a.vx -= impulse * nx
    a.vy -= impulse * ny
    b.vx += impulse * nx
    b.vy += impulse * ny


def resolve_barrier_collision(egg: Egg, barrier: Barrier):
    dx = egg.x - barrier.x
    dy = egg.y - barrier.y
    dist = math.hypot(dx, dy)
    if dist == 0:
        dx, dy, dist = 1, 0, 1
    nx, ny = dx / dist, dy / dist

    overlap = (egg.r + barrier.r) - dist
    egg.x += nx * overlap
    egg.y += ny * overlap

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


def step_physics(eggs: list[Egg], barriers: list[Barrier], mines: list[Mine]):
    """한 프레임 물리. 반환: 폭발할 지뢰 목록"""
    triggered_mines: list[Mine] = []

    for egg in eggs:
        if not egg.active or not egg.is_moving():
            continue
        apply_magnet(egg)
        egg.x += egg.vx
        egg.y += egg.vy
        egg.apply_friction()
        egg.bounce_walls()   # 이제 탈락 처리 (반사 없음)

    # 알 ↔ 알 충돌
    active = [e for e in eggs if e.active]
    for i in range(len(active)):
        for j in range(i + 1, len(active)):
            a, b = active[i], active[j]
            if a.overlaps(b):
                resolve_egg_collision(a, b)

    # 알 ↔ 방벽 충돌
    for egg in active:
        for barrier in barriers:
            if barrier.active and barrier.overlaps_egg(egg):
                resolve_barrier_collision(egg, barrier)

    # 지뢰 발동 체크
    for mine in mines:
        if not mine.active or mine.triggered:
            continue
        for egg in active:
            if egg.owner != mine.owner and mine.in_blast(egg):
                mine.triggered = True
                triggered_mines.append(mine)
                break

    return triggered_mines


def all_still(eggs: list[Egg]) -> bool:
    return all(not e.is_moving() for e in eggs if e.active)