# core/abilities.py
"""
재정의된 알 능력 로직.

일반알   : 발사만 가능
방벽알   : 빈 위치에 방벽 생성
봉인알   : 지정 알 1개를 1턴 동안 행동 불가
복사알   : ① 적 알 클릭 → 능력 저장(재사용 시 저장 능력 발동)
           ② 아군 알 클릭(또는 충돌 시) → 위력 저장(재사용 시 위력 합산하여 발사)
분신알   : 주위에 분신 1개만 소환, 원본·분신 위치 랜덤 섞기
폭탄알   : 빈 위치에 지뢰 설치, 적 알 접근 시 폭발(밀려남)
투명알   : 투명화 토글. 투명 상태 = 적이 능력 사용 불가
염력알   : 지정 적 파괴 → 아군 1개 랜덤 파괴 → 자폭
얼음알   : 지정 알 슬립(더 잘 밀림)
자석알   : 두 알 선택 → 즉시 서로 당기기 시작
"""
from __future__ import annotations
import math, random
from core.egg import Egg, Barrier, Mine
from core.constants import *


# ── 유틸 ─────────────────────────────────────────────────────────

def pos_occupied(x: float, y: float, eggs: list[Egg],
                 barriers: list[Barrier], margin: int = 5) -> bool:
    for e in eggs:
        if e.active and math.hypot(e.x - x, e.y - y) < EGG_RADIUS * 2 + margin:
            return True
    for b in barriers:
        if b.active and math.hypot(b.x - x, b.y - y) < EGG_RADIUS * 2 + margin:
            return True
    return False


# ── 방벽알 ───────────────────────────────────────────────────────

def ability_barrier(user: Egg, tx: float, ty: float,
                    eggs: list[Egg], barriers: list[Barrier]) -> tuple[bool, str]:
    if pos_occupied(tx, ty, eggs, barriers):
        return False, "그 위치에는 방벽을 놓을 수 없습니다."
    if not (BOARD_LEFT + EGG_RADIUS < tx < BOARD_RIGHT - EGG_RADIUS and
            BOARD_TOP  + EGG_RADIUS < ty < BOARD_BOTTOM - EGG_RADIUS):
        return False, "보드 밖에는 방벽을 놓을 수 없습니다."
    barriers.append(Barrier(tx, ty))
    return True, "방벽이 생성됐습니다!"


# ── 봉인알 ───────────────────────────────────────────────────────

def ability_seal(user: Egg, target: Egg) -> tuple[bool, str]:
    """대상을 1턴 동안 봉인."""
    if target.sealed:
        return False, "이미 봉인된 알입니다."
    target.sealed     = True
    target.seal_turns = 1          # 1턴 후 자동 해제
    return True, f"알(id={target.id})을 1턴 봉인했습니다!"


def tick_seal(eggs: list[Egg]):
    """턴이 바뀔 때 호출 — 봉인 카운터 감소, 0 되면 해제."""
    for egg in eggs:
        if egg.sealed and egg.seal_turns > 0:
            egg.seal_turns -= 1
            if egg.seal_turns <= 0:
                egg.sealed     = False
                egg.seal_turns = 0


# ── 복사알 ───────────────────────────────────────────────────────

def ability_copy_ability(user: Egg, target: Egg) -> tuple[bool, str]:
    """적 알의 능력 타입 저장."""
    if target.type == "normal":
        return False, "일반알의 능력은 복사할 수 없습니다."
    if target.type == "copy":
        return False, "복사알의 능력은 복사할 수 없습니다."
    user.copied_ability = target.type
    user.copy_mode      = "ability"
    return True, (f"{EGG_INFO[target.type]['name']}의 능력을 저장했습니다! "
                  f"다음 능력 사용 시 {EGG_INFO[target.type]['name']} 능력이 발동됩니다.")


def ability_copy_power(user: Egg, target: Egg) -> tuple[bool, str]:
    """알의 발사 위력(속도 벡터) 저장."""
    spd = math.hypot(target.vx, target.vy)
    if spd < 0.1 and (target.copied_vx is None):
        return False, "움직이지 않는 알의 위력은 복사할 수 없습니다."
    # 이미 저장된 위력이 있으면 그것을 사용, 없으면 현재 속도
    vx = target.copied_vx if target.copied_vx is not None else target.vx
    vy = target.copied_vy if target.copied_vy is not None else target.vy
    user.copied_vx  = vx
    user.copied_vy  = vy
    user.copy_mode  = "power"
    spd_val = math.hypot(vx, vy)
    return True, (f"위력(속도 {spd_val:.1f})을 저장했습니다! "
                  f"다음 발사 시 저장 위력이 합산됩니다.")


def use_copied_ability(user: Egg) -> tuple[bool, str, str | None]:
    """
    저장된 능력/위력 사용.
    반환: (성공 여부, 메시지, 능력 타입 or None)
      능력 타입이 반환되면 GameState가 해당 능력 흐름을 이어서 처리.
    """
    if user.copy_mode == "ability" and user.copied_ability:
        t = user.copied_ability
        # 사용 후 초기화
        user.copied_ability = None
        user.copy_mode      = "none"
        return True, f"저장된 {EGG_INFO[t]['name']} 능력 발동!", t

    if user.copy_mode == "power" and user.copied_vx is not None:
        return True, "위력 합산 발사 준비 완료.", "power_ready"

    return False, "저장된 능력/위력이 없습니다. 먼저 복사해 주세요.", None


# ── 분신알 ───────────────────────────────────────────────────────

def ability_clone(user: Egg, eggs: list[Egg]) -> tuple[bool, str]:
    """분신 1개만 소환, 위치 랜덤 섞기."""
    offsets = [(70, 0), (-70, 0), (0, 70), (0, -70)]
    random.shuffle(offsets)

    clone = None
    for dx, dy in offsets:
        cx, cy = user.x + dx, user.y + dy
        if (BOARD_LEFT + EGG_RADIUS < cx < BOARD_RIGHT - EGG_RADIUS and
                BOARD_TOP  + EGG_RADIUS < cy < BOARD_BOTTOM - EGG_RADIUS and
                not pos_occupied(cx, cy, eggs, [])):
            clone = Egg(cx, cy, user.owner, "clone")
            clone.is_clone = True
            break

    if clone is None:
        return False, "분신을 소환할 공간이 없습니다."

    eggs.append(clone)

    # 원본 ↔ 분신 위치 50% 확률로 교환
    if random.random() < 0.5:
        user.x, clone.x = clone.x, user.x
        user.y, clone.y = clone.y, user.y

    return True, "분신 1개 소환! 위치가 섞였습니다."


# ── 폭탄알 ───────────────────────────────────────────────────────

def ability_bomb(user: Egg, tx: float, ty: float,
                 eggs: list[Egg], barriers: list[Barrier],
                 mines: list[Mine]) -> tuple[bool, str]:
    if pos_occupied(tx, ty, eggs, barriers):
        return False, "그 위치에는 지뢰를 놓을 수 없습니다."
    if not (BOARD_LEFT < tx < BOARD_RIGHT and BOARD_TOP < ty < BOARD_BOTTOM):
        return False, "보드 밖에는 지뢰를 놓을 수 없습니다."
    mines.append(Mine(tx, ty, user.owner))
    return True, "지뢰를 설치했습니다! 적 알이 접근하면 폭발합니다."


def explode_mine(mine: Mine, eggs: list[Egg]) -> list[Egg]:
    """지뢰 폭발 — 폭발 범위 내 적 알을 강하게 밀어냄. 파괴는 없음(밀려남만)."""
    pushed = []
    for egg in eggs:
        if not egg.active or egg.owner == mine.owner:
            continue
        dx   = egg.x - mine.x
        dy   = egg.y - mine.y
        dist = math.hypot(dx, dy)
        if dist < mine.BLAST_RADIUS:
            if dist < 0.1:
                dx, dy, dist = 1.0, 0.0, 1.0
            nx, ny = dx / dist, dy / dist
            # 거리에 반비례한 폭발력
            force = (mine.BLAST_RADIUS - dist) / mine.BLAST_RADIUS * 22
            egg.vx += nx * force
            egg.vy += ny * force
            pushed.append(egg)
    mine.active = False
    return pushed


# ── 투명알 ───────────────────────────────────────────────────────

def ability_invisible(user: Egg) -> tuple[bool, str]:
    """투명화 토글. 투명 상태 = 적의 능력 사용 불가."""
    user.invisible = not user.invisible
    if user.invisible:
        return True, "투명해졌습니다! 적이 능력을 사용할 수 없습니다."
    return True, "투명 상태가 해제됐습니다."


# ── 염력알 ───────────────────────────────────────────────────────

def ability_psycho(user: Egg, target: Egg,
                   eggs: list[Egg]) -> tuple[bool, str]:
    """지정 적 파괴 → 아군 1개 랜덤 파괴 → 자폭."""
    if not target.active:
        return False, "이미 파괴된 알입니다."
    if target.owner == user.owner:
        return False, "염력은 적 알에만 사용할 수 있습니다."

    target.active = False
    msg = f"염력으로 알(id={target.id})을 파괴!"

    allies = [e for e in eggs
              if e.active and e.owner == user.owner and e.id != user.id]
    if allies:
        victim = random.choice(allies)
        victim.active = False
        msg += f" 반동으로 아군 알(id={victim.id}) 파괴."

    user.active = False
    msg += " 염력알도 소멸."
    return True, msg


# ── 얼음알 ───────────────────────────────────────────────────────

def ability_ice(user: Egg, target: Egg) -> tuple[bool, str]:
    """대상 알에 slippy 상태 부여 — 충돌 반발계수 증가."""
    target.icy = True
    return True, f"알(id={target.id})이 슬립 상태! 더 잘 밀립니다."


# ── 자석알 ───────────────────────────────────────────────────────

def ability_magnet(user: Egg, target_a: Egg,
                   target_b: Egg) -> tuple[bool, str]:
    """두 알을 자석 연결 → 즉시 서로 당기기 시작(물리 엔진이 매 프레임 처리)."""
    if target_a.id == target_b.id:
        return False, "같은 알을 두 번 선택할 수 없습니다."
    target_a.magnet_pair = target_b
    target_b.magnet_pair = target_a
    # 즉시 초기 인력 부여 (시각적으로 바로 움직임)
    _apply_initial_magnet_pull(target_a, target_b)
    return True, f"알 {target_a.id}↔{target_b.id} 자석 연결! 즉시 당기기 시작합니다."


def _apply_initial_magnet_pull(a: Egg, b: Egg, impulse: float = 3.0):
    """자석 연결 직후 즉각적인 인력 충격량 부여."""
    dx   = b.x - a.x
    dy   = b.y - a.y
    dist = max(math.hypot(dx, dy), 1.0)
    nx, ny = dx / dist, dy / dist
    a.vx += nx * impulse
    a.vy += ny * impulse
    b.vx -= nx * impulse
    b.vy -= ny * impulse