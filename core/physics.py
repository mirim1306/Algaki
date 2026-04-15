# core/physics.py
from __future__ import annotations
import math
from core.constants import *
from core.egg import Egg, Barrier, Mine


def resolve_egg_collision(a: Egg, b: Egg):
    """두 알 탄성 충돌 - 충돌 전달력 강화."""
    dx = b.x - a.x
    dy = b.y - a.y
    dist = math.hypot(dx, dy)
    if dist == 0:
        dx, dy, dist = 1, 0, 1

    nx, ny = dx / dist, dy / dist
    overlap = (a.r + b.r) - dist

    # 겹침 보정 (더 강하게)
    a.x -= nx * overlap * 0.52
    a.y -= ny * overlap * 0.52
    b.x += nx * overlap * 0.52
    b.y += ny * overlap * 0.52

    # 법선 방향 상대 속도
    dv_n = (a.vx - b.vx) * nx + (a.vy - b.vy) * ny
    if dv_n > 0:
        return

    # 얼음 슬립
    e = RESTITUTION
    if b.icy:
        e = min(e * ICE_SLIP_MULT, 1.6)
    if a.icy:
        e = min(e * ICE_SLIP_MULT, 1.6)

    # 등질량 충돌 — 운동량 완전 전달 (impulse 계수 1.0으로 높임)
    impulse = (1 + e) * dv_n / 2

    a.vx -= impulse * nx
    a.vy -= impulse * ny
    b.vx += impulse * nx
    b.vy += impulse * ny

    # 정지 알에 충돌 시 최소 속도 보장 (잘 안 밀리는 문제 해결)
    b_speed = math.hypot(b.vx, b.vy)
    a_speed = math.hypot(a.vx, a.vy)
    hit_speed = abs(dv_n)
    if b_speed < hit_speed * 0.3 and hit_speed > 0.5:
        scale = hit_speed * 0.3 / max(b_speed, 0.001)
        b.vx *= scale
        b.vy *= scale


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
    triggered_mines: list[Mine] = []

    for egg in eggs:
        if not egg.active or not egg.is_moving():
            continue
        apply_magnet(egg)
        egg.x += egg.vx
        egg.y += egg.vy
        egg.apply_friction()
        egg.bounce_walls()

    active = [e for e in eggs if e.active]
    for i in range(len(active)):
        for j in range(i + 1, len(active)):
            a, b = active[i], active[j]
            if a.overlaps(b):
                resolve_egg_collision(a, b)

    for egg in active:
        for barrier in barriers:
            if barrier.active and barrier.overlaps_egg(egg):
                resolve_barrier_collision(egg, barrier)

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