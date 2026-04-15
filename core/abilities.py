# core/abilities.py
"""
각 알 능력의 실행 로직.
GameState 에 대한 순환 참조를 피하기 위해 필요한 데이터를 직접 인자로 받음.
"""
from __future__ import annotations
import math, random
from core.egg import Egg, Barrier, Mine
from core.constants import *

# ── 유틸 ──────────────────────────────────────────────────────────
def _find_egg_by_id(eggs: list[Egg], eid: int) -> Egg | None:
    for e in eggs:
        if e.id == eid and e.active:
            return e
    return None


def pos_occupied(x: float, y: float, eggs: list[Egg],
                 barriers: list[Barrier], margin: int = 5) -> bool:
    """해당 위치가 알이나 방벽으로 막혀 있으면 True."""
    for e in eggs:
        if e.active and math.hypot(e.x - x, e.y - y) < EGG_RADIUS * 2 + margin:
            return True
    for b in barriers:
        if b.active and math.hypot(b.x - x, b.y - y) < EGG_RADIUS * 2 + margin:
            return True
    return False


# ── 능력별 함수 ────────────────────────────────────────────────────

def ability_barrier(user: Egg,
                    target_x: float, target_y: float,
                    eggs: list[Egg], barriers: list[Barrier]) -> tuple[bool, str]:
    """방벽알: 빈 위치에 방벽 생성."""
    if pos_occupied(target_x, target_y, eggs, barriers):
        return False, "그 위치에는 방벽을 놓을 수 없습니다."
    if not (BOARD_LEFT + EGG_RADIUS < target_x < BOARD_RIGHT - EGG_RADIUS and
            BOARD_TOP  + EGG_RADIUS < target_y < BOARD_BOTTOM - EGG_RADIUS):
        return False, "보드 밖에는 방벽을 놓을 수 없습니다."
    barriers.append(Barrier(target_x, target_y))
    return True, "방벽이 생성됐습니다!"


def ability_seal(user: Egg, target: Egg) -> tuple[bool, str]:
    """봉인알: 대상 알을 봉인 상태로 만듦."""
    if target.sealed:
        return False, "이미 봉인된 알입니다."
    target.sealed = True
    return True, f"알(id={target.id})을 봉인했습니다!"


def ability_copy_ability(user: Egg, target: Egg) -> tuple[bool, str]:
    """복사알: 상대 알의 능력 타입을 복사."""
    if target.type == "normal":
        return False, "일반알의 능력은 복사할 수 없습니다."
    user.copied_ability = target.type
    return True, f"{EGG_INFO[target.type]['name']}의 능력을 복사했습니다!"


def ability_copy_power(user: Egg, target: Egg) -> tuple[bool, str]:
    """복사알: 자신에게 부딪힌 알의 발사 위력(방향/속도) 복사."""
    if abs(target.vx) < 0.01 and abs(target.vy) < 0.01:
        return False, "움직이지 않는 알의 위력은 복사할 수 없습니다."
    user.copied_vx = target.vx
    user.copied_vy = target.vy
    return True, "발사 위력을 복사했습니다! 능력 사용 시 동시에 발사됩니다."


def ability_clone(user: Egg, eggs: list[Egg]) -> tuple[bool, str]:
    """분신알: 주위 4방향에 분신 소환 후 랜덤 섞기."""
    clones: list[Egg] = []
    offsets = [(60, 0), (-60, 0), (0, 60), (0, -60)]
    for dx, dy in offsets:
        cx, cy = user.x + dx, user.y + dy
        # 보드 안에 있고 비어 있으면 생성
        if (BOARD_LEFT + EGG_RADIUS < cx < BOARD_RIGHT - EGG_RADIUS and
                BOARD_TOP + EGG_RADIUS < cy < BOARD_BOTTOM - EGG_RADIUS and
                not pos_occupied(cx, cy, eggs, [])):
            clone = Egg(cx, cy, user.owner, "clone")
            clone.is_clone = True
            clones.append(clone)

    if not clones:
        return False, "분신을 소환할 공간이 없습니다."

    eggs.extend(clones)

    # 원본 + 분신 위치 섞기 (어느 게 진짜인지 모르게)
    pool = [user] + clones
    positions = [(e.x, e.y) for e in pool]
    random.shuffle(positions)
    for e, (px, py) in zip(pool, positions):
        e.x, e.y = px, py

    return True, f"분신 {len(clones)}개 소환 후 섞였습니다!"


def ability_bomb(user: Egg, target_x: float, target_y: float,
                 eggs: list[Egg], barriers: list[Barrier],
                 mines: list[Mine]) -> tuple[bool, str]:
    """폭탄알: 빈 위치에 지뢰 설치."""
    if pos_occupied(target_x, target_y, eggs, barriers):
        return False, "그 위치에는 지뢰를 놓을 수 없습니다."
    if not (BOARD_LEFT < target_x < BOARD_RIGHT and
            BOARD_TOP  < target_y < BOARD_BOTTOM):
        return False, "보드 밖에는 지뢰를 놓을 수 없습니다."
    mines.append(Mine(target_x, target_y, user.owner))
    return True, "지뢰를 설치했습니다!"


def explode_mine(mine: Mine, eggs: list[Egg]) -> list[Egg]:
    """지뢰 폭발: 폭발 범위 내 적 알 밀어냄. 파괴된 알 목록 반환."""
    destroyed = []
    for egg in eggs:
        if not egg.active or egg.owner == mine.owner:
            continue
        dx = egg.x - mine.x
        dy = egg.y - mine.y
        dist = math.hypot(dx, dy)
        if dist < mine.BLAST_RADIUS:
            if dist < 0.1:
                dx, dy, dist = 1, 0, 1
            nx, ny = dx / dist, dy / dist
            force = (mine.BLAST_RADIUS - dist) / mine.BLAST_RADIUS * 18
            egg.vx += nx * force
            egg.vy += ny * force
            if dist < EGG_RADIUS * 1.5:
                egg.active = False
                destroyed.append(egg)
    mine.active = False
    return destroyed


def ability_invisible(user: Egg) -> tuple[bool, str]:
    """투명알: 투명화 토글."""
    user.invisible = not user.invisible
    state = "투명해졌습니다!" if user.invisible else "투명이 해제됐습니다."
    return True, state


def ability_psycho(user: Egg, target: Egg,
                   eggs: list[Egg]) -> tuple[bool, str]:
    """염력알: 대상 파괴 + 자신의 랜덤 아군 알 파괴 + 염력알 자폭."""
    if not target.active:
        return False, "이미 파괴된 알입니다."

    target.active = False
    msg = f"염력으로 알(id={target.id})을 파괴했습니다!"

    # 자신의 아군 중 랜덤 하나 파괴 (자기 자신 제외)
    allies = [e for e in eggs if e.active and e.owner == user.owner and e.id != user.id]
    if allies:
        victim = random.choice(allies)
        victim.active = False
        msg += f" 반동으로 아군 알(id={victim.id})도 파괴됐습니다."

    # 염력알 자폭
    user.active = False
    msg += " 염력알도 소멸했습니다."
    return True, msg


def ability_ice(user: Egg, target: Egg) -> tuple[bool, str]:
    """얼음알: 대상 알에 icy 상태 부여."""
    target.icy = True
    return True, f"알(id={target.id})이 얼음 상태가 됐습니다! (더 잘 밀림)"


def ability_magnet(user: Egg,
                   target_a: Egg, target_b: Egg) -> tuple[bool, str]:
    """자석알: 두 알을 자석으로 연결."""
    if target_a.id == target_b.id:
        return False, "같은 알을 두 번 선택할 수 없습니다."
    target_a.magnet_pair = target_b
    target_b.magnet_pair = target_a
    return True, f"알 {target_a.id}↔{target_b.id}이 자석으로 연결됐습니다!"