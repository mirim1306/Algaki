from __future__ import annotations
import math
from core.constants import *
from core.egg import Egg, Barrier, Mine


def resolve_egg_collision(a: Egg, b: Egg):
    dx = b.x - a.x;  dy = b.y - a.y
    dist = math.hypot(dx, dy)
    if dist < 0.001:
        import random
        angle = random.uniform(0, math.pi * 2)
        dx, dy, dist = math.cos(angle), math.sin(angle), 1.0
    nx, ny  = dx / dist, dy / dist
    overlap = (a.r + b.r) - dist
    a_moving = math.hypot(a.vx, a.vy) > MIN_SPEED
    b_moving = math.hypot(b.vx, b.vy) > MIN_SPEED
    if a_moving and not b_moving:
        a.x -= nx * (overlap + 0.5);  a.y -= ny * (overlap + 0.5)
    elif b_moving and not a_moving:
        b.x += nx * (overlap + 0.5);  b.y += ny * (overlap + 0.5)
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
            b.vx += nx * a_vn * e;  b.vy += ny * a_vn * e
            a.vx -= nx * a_vn;      a.vy -= ny * a_vn
    elif b_moving and not a_moving:
        b_vn = -(b.vx * nx + b.vy * ny)
        if b_vn > 0:
            a.vx -= nx * b_vn * e;  a.vy -= ny * b_vn * e
            b.vx += nx * b_vn;      b.vy += ny * b_vn
    else:
        dv_n = (a.vx - b.vx) * nx + (a.vy - b.vy) * ny
        if dv_n < 0:
            impulse = -(1.0 + e) * dv_n * 0.5
            a.vx -= impulse * nx;  a.vy -= impulse * ny
            b.vx += impulse * nx;  b.vy += impulse * ny


def resolve_barrier_collision(egg: Egg, barrier: Barrier):
    dx = egg.x - barrier.x;  dy = egg.y - barrier.y
    dist = math.hypot(dx, dy)
    if dist < 0.001:
        dx, dy, dist = 1, 0, 1
    nx, ny  = dx / dist, dy / dist
    overlap = (egg.r + barrier.r) - dist
    egg.x  += nx * (overlap + 0.5);  egg.y += ny * (overlap + 0.5)
    dot     = egg.vx * nx + egg.vy * ny
    if dot < 0:
        egg.vx -= 2 * dot * nx * RESTITUTION
        egg.vy -= 2 * dot * ny * RESTITUTION


def apply_magnet(egg: Egg):
    partner = egg.magnet_pair
    if partner is None or not partner.active:
        egg.magnet_pair = None
        return
    dx = partner.x - egg.x;  dy = partner.y - egg.y
    dist = math.hypot(dx, dy)
    if dist < egg.r + partner.r + 2:
        return
    f = MAGNET_FORCE / max(dist, 1)
    egg.vx += dx * f;  egg.vy += dy * f


def _is_out_of_board(egg: Egg) -> bool:
    """알 중심이 보드 경계를 넘으면 파괴."""
    import core.constants as _c
    #     =
    return (egg.x < _c.BOARD_LEFT   or
            egg.x > _c.BOARD_RIGHT  or
            egg.y < _c.BOARD_TOP    or
            egg.y > _c.BOARD_BOTTOM)


def step_physics(eggs: list[Egg], barriers: list[Barrier], mines: list[Mine],
                 map_objects=None):
    """
      .
    : (triggered_mines, map_bomb_events)
    """
    triggered:       list[Mine]            = []
    map_bomb_events: list[tuple[int, int]] = []

    all_barriers: list[Barrier] = list(barriers)
    map_bombs = []
    tires     = []
    drains    = []
    if map_objects is not None:
        map_bombs = [b for b in map_objects.map_bombs if b.active]
        tires     = [t for t in map_objects.tires     if t.active]
        drains    = [d for d in map_objects.drains     if d.active]
        all_barriers.extend(map_objects.barriers)

    # --  &   -----------------------------------------
    for egg in eggs:
        if not egg.active or not egg.is_moving():
            continue
        apply_magnet(egg)
        egg.x += egg.vx
        egg.y += egg.vy
        egg.apply_friction()
        if _is_out_of_board(egg):
            egg.active = False
            egg.vx = egg.vy = 0.0

    # --     -------------------------------------------
    active = [e for e in eggs if e.active]
    for i in range(len(active)):
        for j in range(i + 1, len(active)):
            a, b = active[i], active[j]
            if a.overlaps(b):
                resolve_egg_collision(a, b)

    # --     -----------------------------------------
    for egg in [e for e in eggs if e.active]:
        for barrier in all_barriers:
            if barrier.active and barrier.overlaps_egg(egg):
                resolve_barrier_collision(egg, barrier)

    # --    ---------------------------------------------
    for egg in [e for e in eggs if e.active]:
        for tire in tires:
            if not tire.active:
                continue
            dx = egg.x - tire.x;  dy = egg.y - tire.y
            dist = math.hypot(dx, dy)
            if dist < tire.r + egg.r:
                if dist < 0.001:
                    dx, dy, dist = 1, 0, 1
                nx, ny  = dx / dist, dy / dist
                overlap = (tire.r + egg.r) - dist
                egg.x  += nx * (overlap + 0.5);  egg.y += ny * (overlap + 0.5)
                dot     = egg.vx * nx + egg.vy * ny
                if dot < 0:
                    egg.vx -= 2 * dot * nx * (RESTITUTION * tire.BOOST)
                    egg.vy -= 2 * dot * ny * (RESTITUTION * tire.BOOST)
                tire.register_hit()

    # --     ( ,   ) -----------------
    if map_bombs:
        from core.map_system import explode_map_bomb
        for bomb in list(map_bombs):
            if not bomb.active:
                continue
            for egg in [e for e in eggs if e.active]:
                if bomb.overlaps_egg(egg):
                    killed, pushed = explode_map_bomb(bomb, eggs)
                    map_bomb_events.append((len(killed), len(pushed)))
                    break   #    ,

    # --   —    ------------------
    if drains:
        for egg in [e for e in eggs if e.active]:
            # drain_cooldown:
            if not hasattr(egg, 'drain_cooldown'):
                egg.drain_cooldown = 0
            if egg.drain_cooldown > 0:
                egg.drain_cooldown -= 1
                continue   #
            for drain in drains:
                if not drain.active:
                    continue
                if drain.in_range(egg):
                    partner = drains[drain.partner_idx]
                    if partner.active:
                        #
                        dx_out = egg.vx if abs(egg.vx) > 0.1 else 1.0
                        dy_out = egg.vy if abs(egg.vy) > 0.1 else 0.0
                        dist_out = max(math.hypot(dx_out, dy_out), 0.1)
                        nx_out = dx_out / dist_out
                        ny_out = dy_out / dist_out
                        # partner drain   (SUCK_DIST + egg.r + 5)
                        clearance = drain.SUCK_DIST + egg.r + 5
                        egg.x = partner.x + nx_out * clearance
                        egg.y = partner.y + ny_out * clearance
                        #  :
                        egg.drain_cooldown = 30   #  0.5(60fps )
                    break

    # --    ---------------------------------------
    _MAX_BLAST_SPD = MAX_LAUNCH_DIST * LAUNCH_POWER * 1.5
    for mine in mines:
        if not mine.active or mine.triggered:
            continue
        for egg in [e for e in eggs if e.active]:
            #    ()
            if egg.owner != mine.owner and mine.in_blast(egg):
                mine.triggered = True
                triggered.append(mine)
                #   (  )
                for target in [e for e in eggs if e.active]:
                    dx2 = target.x - mine.x
                    dy2 = target.y - mine.y
                    d2  = math.hypot(dx2, dy2)
                    if d2 < mine.BLAST_RADIUS:
                        if d2 < 0.1:
                            import random as _r
                            a2 = _r.uniform(0, math.pi * 2)
                            dx2, dy2, d2 = math.cos(a2), math.sin(a2), 1.0
                        nx2, ny2 = dx2 / d2, dy2 / d2
                        ratio2   = (mine.BLAST_RADIUS - d2) / mine.BLAST_RADIUS
                        force2   = _MAX_BLAST_SPD * ratio2
                        target.vx += nx2 * force2
                        target.vy += ny2 * force2
                break

    return triggered, map_bomb_events


def all_still(eggs: list[Egg]) -> bool:
    return all(not e.is_moving() for e in eggs if e.active)