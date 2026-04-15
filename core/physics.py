# core/physics.py
from __future__ import annotations
import math
from core.constants import *
from core.egg import Egg, Barrier, Mine


def resolve_egg_collision(a: Egg, b: Egg):
    """
    알까기 스타일 충돌:
      - 발사된 알(움직이는 쪽)의 법선 방향 속도를 맞은 알에 그대로 전달
      - 발사 알은 법선 방향 속도만 잃고 접선 방향은 유지 (당구공 원리)
      - 양쪽 모두 움직일 때는 등질량 탄성 충돌
    """
    dx = b.x - a.x
    dy = b.y - a.y
    dist = math.hypot(dx, dy)
    if dist < 0.001:
        import random
        angle = random.uniform(0, math.pi * 2)
        dx, dy, dist = math.cos(angle), math.sin(angle), 1.0

    nx, ny = dx / dist, dy / dist
    overlap = (a.r + b.r) - dist

    # 겹침 분리: 움직이는 쪽이 주로 밀려남
    a_moving = math.hypot(a.vx, a.vy) > MIN_SPEED
    b_moving = math.hypot(b.vx, b.vy) > MIN_SPEED

    if a_moving and not b_moving:
        # a가 발사, b가 정지 → a가 100% 밀려서 분리
        a.x -= nx * (overlap + 0.5)
        a.y -= ny * (overlap + 0.5)
    elif b_moving and not a_moving:
        b.x += nx * (overlap + 0.5)
        b.y += ny * (overlap + 0.5)
    else:
        sep = overlap * 0.51
        a.x -= nx * sep
        a.y -= ny * sep
        b.x += nx * sep
        b.y += ny * sep

    # 반발계수
    e = RESTITUTION
    if a.icy or b.icy:
        e = min(e * ICE_SLIP_MULT, 1.6)

    # ── 핵심: 발사 위력 전달 ──────────────────────────────────
    if a_moving and not b_moving:
        # a(발사알) → b(정지알) 법선 방향 속도 완전 전달
        # a의 법선 방향 속도 성분
        a_vn = a.vx * nx + a.vy * ny   # a가 b 방향으로 가는 속도
        if a_vn > 0:                   # b를 향해 달려오는 경우만
            # b는 a의 법선 방향 속도 * 반발계수 획득
            b.vx += nx * a_vn * e
            b.vy += ny * a_vn * e
            # a는 법선 방향 속도를 잃음 (접선은 유지 — 당구공)
            a.vx -= nx * a_vn
            a.vy -= ny * a_vn

    elif b_moving and not a_moving:
        # b(발사알) → a(정지알)
        b_vn = -(b.vx * nx + b.vy * ny)   # b가 a 방향으로 가는 속도
        if b_vn > 0:
            a.vx -= nx * b_vn * e
            a.vy -= ny * b_vn * e
            b.vx += nx * b_vn
            b.vy += ny * b_vn

    else:
        # 양쪽 모두 움직임 → 등질량 탄성 충돌
        dv_n = (a.vx - b.vx) * nx + (a.vy - b.vy) * ny
        if dv_n < 0:
            impulse = -(1.0 + e) * dv_n * 0.5
            a.vx -= impulse * nx
            a.vy -= impulse * ny
            b.vx += impulse * nx
            b.vy += impulse * ny


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