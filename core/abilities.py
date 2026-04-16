"""
알 능력 로직.
폭탄알 지뢰: 폭발 시 파괴 없음 — 최대발사력 절반으로 밀어냄 (광역).
"""
from __future__ import annotations
import math, random
from core.egg import Egg, Barrier, Mine
from core.constants import *


def pos_occupied(x: float, y: float, eggs: list[Egg],
                 barriers: list[Barrier], margin: int = 5) -> bool:
    for e in eggs:
        if e.active and math.hypot(e.x - x, e.y - y) < EGG_RADIUS * 2 + margin:
            return True
    for b in barriers:
        if b.active and math.hypot(b.x - x, b.y - y) < EGG_RADIUS * 2 + margin:
            return True
    return False


def _check_uses(user: Egg) -> tuple[bool, str]:
    if not user.can_use_ability():
        if user.uses_left <= 0:
            return False, f"능력 사용 횟수를 모두 소진했습니다. (0/{user.max_uses})"
        return False, "능력을 사용할 수 없습니다."
    user.consume_use()
    return True, ""


# ── 방벽알 ───────────────────────────────────────────────────────

def ability_barrier(user: Egg, tx: float, ty: float,
                    eggs: list[Egg], barriers: list[Barrier]) -> tuple[bool, str]:
    ok, msg = _check_uses(user)
    if not ok:
        return False, msg
    if pos_occupied(tx, ty, eggs, barriers):
        user.uses_left += 1
        return False, "그 위치에는 방벽을 놓을 수 없습니다."
    if not (BOARD_LEFT + EGG_RADIUS < tx < BOARD_RIGHT - EGG_RADIUS and
            BOARD_TOP  + EGG_RADIUS < ty < BOARD_BOTTOM - EGG_RADIUS):
        user.uses_left += 1
        return False, "보드 밖에는 방벽을 놓을 수 없습니다."
    barriers.append(Barrier(tx, ty))
    return True, f"방벽 생성! (남은 횟수: {user.uses_left}/{user.max_uses})"


# ── 봉인알 ───────────────────────────────────────────────────────

def ability_seal(user: Egg, target: Egg) -> tuple[bool, str]:
    ok, msg = _check_uses(user)
    if not ok:
        return False, msg
    if target.sealed:
        user.uses_left += 1
        return False, "이미 봉인된 알입니다."
    target.sealed     = True
    target.seal_turns = 1
    return True, f"알(id={target.id}) 봉인! (남은 횟수: {user.uses_left}/{user.max_uses})"


def tick_seal(eggs: list[Egg]):
    for egg in eggs:
        if egg.sealed and egg.seal_turns > 0:
            egg.seal_turns -= 1
            if egg.seal_turns <= 0:
                egg.sealed = False
                egg.seal_turns = 0


# ── 복사알 ───────────────────────────────────────────────────────

def ability_copy_ability(user: Egg, target: Egg) -> tuple[bool, str]:
    ok, msg = _check_uses(user)
    if not ok:
        return False, msg
    if target.type in ("normal", "copy"):
        user.uses_left += 1
        return False, f"{EGG_INFO[target.type]['name']}의 능력은 복사할 수 없습니다."
    user.copied_ability = target.type
    user.copy_mode      = "ability"
    return True, (f"{EGG_INFO[target.type]['name']} 능력 저장! "
                  f"(남은 횟수: {user.uses_left}/{user.max_uses})")


def ability_copy_power(user: Egg, target: Egg) -> tuple[bool, str]:
    ok, msg = _check_uses(user)
    if not ok:
        return False, msg
    spd = math.hypot(target.vx, target.vy)
    if spd < 0.1 and target.copied_vx is None:
        user.uses_left += 1
        return False, "움직이지 않는 알의 위력은 복사할 수 없습니다."
    vx = target.copied_vx if target.copied_vx is not None else target.vx
    vy = target.copied_vy if target.copied_vy is not None else target.vy
    user.copied_vx = vx
    user.copied_vy = vy
    user.copy_mode = "power"
    return True, (f"위력(속도 {math.hypot(vx,vy):.1f}) 저장! "
                  f"(남은 횟수: {user.uses_left}/{user.max_uses})")


def use_copied_ability(user: Egg) -> tuple[bool, str, str | None]:
    if user.copy_mode == "ability" and user.copied_ability:
        t = user.copied_ability
        user.copied_ability = None
        user.copy_mode      = "none"
        return True, f"저장된 {EGG_INFO[t]['name']} 능력 발동!", t
    if user.copy_mode == "power" and user.copied_vx is not None:
        return True, "위력 합산 발사 준비.", "power_ready"
    return False, "저장된 능력/위력이 없습니다. 먼저 복사하세요.", None


# ── 분신알 ───────────────────────────────────────────────────────

def ability_clone(user: Egg, eggs: list[Egg]) -> tuple[bool, str]:
    ok, msg = _check_uses(user)
    if not ok:
        return False, msg
    offsets = [(70,0),(-70,0),(0,70),(0,-70)]
    random.shuffle(offsets)
    clone = None
    for dx, dy in offsets:
        cx, cy = user.x + dx, user.y + dy
        if (BOARD_LEFT + EGG_RADIUS < cx < BOARD_RIGHT - EGG_RADIUS and
                BOARD_TOP + EGG_RADIUS < cy < BOARD_BOTTOM - EGG_RADIUS and
                not pos_occupied(cx, cy, eggs, [])):
            clone = Egg(cx, cy, user.owner, "clone")
            clone.is_clone = True
            break
    if clone is None:
        user.uses_left += 1
        return False, "분신을 소환할 공간이 없습니다."
    eggs.append(clone)
    if random.random() < 0.5:
        user.x, clone.x = clone.x, user.x
        user.y, clone.y = clone.y, user.y
    return True, f"분신 소환! (남은 횟수: {user.uses_left}/{user.max_uses})"


# ── 폭탄알 지뢰 ─────────────────────────────────────────────────

# 최대 발사력: MAX_LAUNCH_DIST * LAUNCH_POWER
_MAX_LAUNCH_SPD = MAX_LAUNCH_DIST * LAUNCH_POWER   # ≈ 22.4

def ability_bomb(user: Egg, tx: float, ty: float,
                 eggs: list[Egg], barriers: list[Barrier],
                 mines: list[Mine]) -> tuple[bool, str]:
    ok, msg = _check_uses(user)
    if not ok:
        return False, msg
    if pos_occupied(tx, ty, eggs, barriers):
        user.uses_left += 1
        return False, "그 위치에는 지뢰를 놓을 수 없습니다."
    if not (BOARD_LEFT < tx < BOARD_RIGHT and BOARD_TOP < ty < BOARD_BOTTOM):
        user.uses_left += 1
        return False, "보드 밖에는 지뢰를 놓을 수 없습니다."
    mines.append(Mine(tx, ty, user.owner))
    return True, f"지뢰 설치! (남은 횟수: {user.uses_left}/{user.max_uses})"


def explode_mine(mine: Mine, eggs: list[Egg]) -> list[Egg]:
    """
    폭탄알 지뢰 폭발: 파괴 없음.
    폭발 반경 내 모든 알(아군 포함 광역)을 최대발사력 절반 세기로 날림.
    날리는 방향: 지뢰 중심에서 바깥쪽으로.
    """
    pushed = []
    blast_spd = _MAX_LAUNCH_SPD * 0.5   # 최대 발사력의 절반

    for egg in eggs:
        if not egg.active:
            continue
        dx   = egg.x - mine.x
        dy   = egg.y - mine.y
        dist = math.hypot(dx, dy)
        if dist < mine.BLAST_RADIUS:
            if dist < 0.1:
                # 지뢰와 거의 같은 위치면 랜덤 방향으로 날림
                import random
                angle = random.uniform(0, math.pi * 2)
                dx, dy = math.cos(angle), math.sin(angle)
                dist   = 1.0
            nx, ny = dx / dist, dy / dist   # 지뢰→알 방향 (바깥쪽)
            # 거리에 따라 감쇠: 중심일수록 강하게
            ratio  = (mine.BLAST_RADIUS - dist) / mine.BLAST_RADIUS
            force  = blast_spd * ratio
            egg.vx += nx * force
            egg.vy += ny * force
            pushed.append(egg)
    mine.active = False
    return pushed


# ── 투명알 ───────────────────────────────────────────────────────

def ability_invisible(user: Egg) -> tuple[bool, str]:
    ok, msg = _check_uses(user)
    if not ok:
        return False, msg
    user.invisible = not user.invisible
    state = "투명해졌습니다!" if user.invisible else "투명 해제!"
    return True, f"{state} (남은 횟수: {user.uses_left}/{user.max_uses})"


# ── 염력알 ───────────────────────────────────────────────────────

def ability_psycho(user: Egg, target: Egg, eggs: list[Egg]) -> tuple[bool, str]:
    if user.uses_left <= 0:
        return False, "능력 사용 횟수를 모두 소진했습니다."
    if not target.active:
        return False, "이미 파괴된 알입니다."
    if target.owner == user.owner:
        return False, "염력은 적 알에만 사용할 수 있습니다."

    target.active = False
    msg = f"염력으로 알(id={target.id}) 파괴!"

    allies = [e for e in eggs
              if e.active and e.owner == user.owner and e.id != user.id]
    if allies:
        victim = random.choice(allies)
        victim.active = False
        msg += f" 반동 — 아군 알(id={victim.id}) 파괴."

    user.active    = False
    user.uses_left = 0
    msg += " 염력알 소멸."
    return True, msg


# ── 얼음알 ───────────────────────────────────────────────────────

def ability_ice(user: Egg, target: Egg) -> tuple[bool, str]:
    ok, msg = _check_uses(user)
    if not ok:
        return False, msg
    target.icy = True
    return True, f"알(id={target.id}) 슬립! (남은 횟수: {user.uses_left}/{user.max_uses})"


# ── 자석알 ───────────────────────────────────────────────────────

def ability_magnet(user: Egg, target_a: Egg, target_b: Egg) -> tuple[bool, str]:
    ok, msg = _check_uses(user)
    if not ok:
        return False, msg
    if target_a.id == target_b.id:
        user.uses_left += 1
        return False, "같은 알을 두 번 선택할 수 없습니다."
    target_a.magnet_pair = target_b
    target_b.magnet_pair = target_a
    _apply_initial_pull(target_a, target_b)
    return True, (f"알 {target_a.id}↔{target_b.id} 자석 연결! "
                  f"(남은 횟수: {user.uses_left}/{user.max_uses})")


def _apply_initial_pull(a: Egg, b: Egg, impulse: float = 3.0):
    dx   = b.x - a.x
    dy   = b.y - a.y
    dist = max(math.hypot(dx, dy), 1.0)
    nx, ny = dx / dist, dy / dist
    a.vx += nx * impulse;  a.vy += ny * impulse
    b.vx -= nx * impulse;  b.vy -= ny * impulse