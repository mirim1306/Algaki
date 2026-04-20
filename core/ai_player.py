# core/ai_player.py
"""
싱글플레이 AI (P2).

설계 원칙:
- 매 턴 '발사 점수'와 '능력 점수'를 각각 평가해 높은 쪽을 선택
- 발사: 각 내 알에서 각 적 알 방향으로 조준 시뮬레이션 → 예상 히트 수로 점수화
- 능력: 알 종류별 상황 판단 함수로 최적 대상 선택
- 단계별 AI 레벨: 0=랜덤, 1=기본조준, 2=전략적 (기본은 1)
"""
from __future__ import annotations
import math, random
import core.constants as _c
from core.egg import Egg, Barrier, Mine


# ── 유틸 ─────────────────────────────────────────────────────────

def _dist(ax, ay, bx, by) -> float:
    return math.hypot(ax - bx, ay - by)

def _active_mine_enemies(gs, owner: int) -> list[Mine]:
    """활성 상태인 적 지뢰 목록."""
    return [m for m in gs.mines if m.active and m.owner != owner]

def _simulate_shot(shooter: Egg, vx: float, vy: float,
                   eggs: list[Egg], steps: int = 120) -> int:
    """
    간단 선형 궤적 시뮬레이션.
    발사 알이 몇 개의 적 알 근처를 지나가는지 반환 (히트 예상 수).
    """
    x, y = shooter.x, shooter.y
    hits = set()
    for _ in range(steps):
        x += vx
        y += vy
        vx *= _c.FRICTION
        vy *= _c.FRICTION
        if (x < _c.BOARD_LEFT or x > _c.BOARD_RIGHT or
                y < _c.BOARD_TOP or y > _c.BOARD_BOTTOM):
            break
        spd = math.hypot(vx, vy)
        if spd < _c.MIN_SPEED:
            break
        for i, egg in enumerate(eggs):
            if not egg.active or egg.owner == shooter.owner:
                continue
            if i in hits:
                continue
            if _dist(x, y, egg.x, egg.y) < _c.EGG_RADIUS * 2.2:
                hits.add(i)
    return len(hits)


def _best_shot(my_eggs: list[Egg], enemy_eggs: list[Egg],
               all_eggs: list[Egg]) -> tuple[Egg, float, float] | None:
    """
    발사 점수가 가장 높은 (발사 알, vx, vy) 반환.
    조준 방향: 적 알 중심 + 약간의 스프레드 각도도 평가.
    """
    best_score = -1
    best = None

    candidates = [e for e in my_eggs if e.active and not e.sealed]
    if not candidates:
        return None

    for shooter in candidates:
        for target in enemy_eggs:
            if not target.active:
                continue
            # 기본 방향: 적 알 중심
            dx = target.x - shooter.x
            dy = target.y - shooter.y
            dist = max(math.hypot(dx, dy), 1.0)
            nx, ny = dx / dist, dy / dist

            # 최대 발사력으로 시뮬레이션
            max_spd = _c.MAX_LAUNCH_DIST * _c.LAUNCH_POWER
            vx = nx * max_spd
            vy = ny * max_spd

            score = _simulate_shot(shooter, vx, vy, all_eggs)
            # 보드 밖으로 나갈 가능성 보너스 (적이 모서리 근처이면)
            edge_bonus = 0
            edge_margin = _c.EGG_RADIUS * 4
            if (target.x < _c.BOARD_LEFT + edge_margin or
                    target.x > _c.BOARD_RIGHT - edge_margin or
                    target.y < _c.BOARD_TOP + edge_margin or
                    target.y > _c.BOARD_BOTTOM - edge_margin):
                edge_bonus = 0.5

            total = score + edge_bonus
            if total > best_score:
                best_score = total
                best = (shooter, vx, vy)

    # 점수 0이면 랜덤 발사
    if best is None or best_score <= 0:
        shooter = random.choice(candidates)
        # 가장 가까운 적 방향으로
        if enemy_eggs:
            target = min(enemy_eggs, key=lambda e: _dist(shooter.x, shooter.y, e.x, e.y))
            dx = target.x - shooter.x
            dy = target.y - shooter.y
            dist = max(math.hypot(dx, dy), 1.0)
            spd = _c.MAX_LAUNCH_DIST * _c.LAUNCH_POWER * random.uniform(0.6, 1.0)
            vx = dx / dist * spd
            vy = dy / dist * spd
        else:
            angle = random.uniform(0, math.pi * 2)
            spd = _c.MAX_LAUNCH_DIST * _c.LAUNCH_POWER * 0.7
            vx, vy = math.cos(angle) * spd, math.sin(angle) * spd
        best = (shooter, vx, vy)

    return best


# ── 능력별 판단 함수 ───────────────────────────────────────────────

def _eval_ability(egg: Egg, gs) -> tuple[float, dict]:
    """
    능력 알의 상황 점수와 실행 파라미터 반환.
    점수가 높을수록 지금 능력을 쓰는 게 유리.
    반환: (score, params)
    params 예:
        barrier: {"type":"pos", "x":x, "y":y}
        seal:    {"type":"egg", "target":Egg}
        psycho:  {"type":"egg", "target":Egg}
        ice:     {"type":"egg", "target":Egg}
        clone:   {"type":"instant"}
        invisible: {"type":"instant"}
        bomb:    {"type":"pos", "x":x, "y":y}
        magnet:  {"type":"two_eggs", "a":Egg, "b":Egg}
        copy:    {"type":"egg", "target":Egg}  or {"type":"instant"}
    """
    t = egg.type
    my_eggs      = [e for e in gs.eggs if e.active and e.owner == egg.owner]
    enemy_eggs   = [e for e in gs.eggs if e.active and e.owner != egg.owner]
    all_eggs     = [e for e in gs.eggs if e.active]

    if t == "barrier":
        # 내 진영 앞에 방벽 설치 → 적이 많은 방향
        if not enemy_eggs:
            return 0.0, {}
        # 적 중심 방향으로 내 진영 전방에 방벽
        ex = sum(e.x for e in enemy_eggs) / len(enemy_eggs)
        ey = sum(e.y for e in enemy_eggs) / len(enemy_eggs)
        mx = sum(e.x for e in my_eggs) / len(my_eggs)
        my = sum(e.y for e in my_eggs) / len(my_eggs)
        # 내 중심과 적 중심 사이 1/3 지점
        bx = mx + (ex - mx) * 0.35
        by = my + (ey - my) * 0.35
        # 보드 안 clamp
        bx = max(_c.BOARD_LEFT + _c.EGG_RADIUS + 5,
                 min(_c.BOARD_RIGHT - _c.EGG_RADIUS - 5, bx))
        by = max(_c.BOARD_TOP + _c.EGG_RADIUS + 5,
                 min(_c.BOARD_BOTTOM - _c.EGG_RADIUS - 5, by))
        # 이미 뭔가 있으면 살짝 이동
        from core.abilities import pos_occupied
        for attempt in range(8):
            bx2 = bx + random.uniform(-50, 50)
            by2 = by + random.uniform(-50, 50)
            bx2 = max(_c.BOARD_LEFT + _c.EGG_RADIUS + 5,
                      min(_c.BOARD_RIGHT - _c.EGG_RADIUS - 5, bx2))
            by2 = max(_c.BOARD_TOP + _c.EGG_RADIUS + 5,
                      min(_c.BOARD_BOTTOM - _c.EGG_RADIUS - 5, by2))
            if not pos_occupied(bx2, by2, all_eggs, gs.barriers):
                bx, by = bx2, by2
                break
        score = 1.5 if len(enemy_eggs) >= 2 else 0.8
        return score, {"type": "pos", "x": bx, "y": by}

    elif t == "seal":
        # 능력 많이 남은 적 알 봉인
        valid = [e for e in enemy_eggs if not e.sealed and e.uses_left > 0 and not e.invisible]
        if not valid:
            return 0.0, {}
        target = max(valid, key=lambda e: e.uses_left)
        score  = 2.0 + target.uses_left * 0.3
        return score, {"type": "egg", "target": target}

    elif t == "copy":
        if egg.copy_mode == "none" and egg.uses_left > 0:
            # 강력한 적 능력 복사
            copyable = [e for e in enemy_eggs
                        if e.type not in ("normal", "copy") and not e.invisible]
            if copyable:
                target = max(copyable, key=lambda e: e.uses_left)
                return 1.8, {"type": "egg", "target": target}
        return 0.0, {}

    elif t == "clone":
        # 내 알이 3개 이하면 분신으로 교란
        score = 2.5 if len(my_eggs) <= 3 else 0.6
        return score, {"type": "instant"}

    elif t == "bomb":
        # 적 알이 밀집된 지점 근처에 지뢰
        if not enemy_eggs:
            return 0.0, {}
        from core.abilities import pos_occupied
        # 적 알 중 가장 밀집된 알의 이동 예상 경로 앞에 설치
        target = min(enemy_eggs, key=lambda e: _dist(
            e.x, e.y, sum(x.x for x in my_eggs)/max(len(my_eggs),1),
            sum(x.y for x in my_eggs)/max(len(my_eggs),1)))
        # 적과 내 알 중간 지점
        mx_avg = sum(e.x for e in my_eggs) / len(my_eggs)
        my_avg = sum(e.y for e in my_eggs) / len(my_eggs)
        bx = target.x + (mx_avg - target.x) * 0.4 + random.uniform(-30, 30)
        by = target.y + (my_avg - target.y) * 0.4 + random.uniform(-30, 30)
        bx = max(_c.BOARD_LEFT + 5, min(_c.BOARD_RIGHT - 5, bx))
        by = max(_c.BOARD_TOP + 5, min(_c.BOARD_BOTTOM - 5, by))
        if pos_occupied(bx, by, all_eggs, gs.barriers):
            return 0.0, {}
        score = 2.0 if len(enemy_eggs) >= 2 else 1.2
        return score, {"type": "pos", "x": bx, "y": by}

    elif t == "invisible":
        # 내가 많이 불리할 때 투명화
        if egg.invisible:
            return 0.0, {}   # 이미 투명
        score = 2.0 if len(my_eggs) < len(enemy_eggs) else 0.5
        return score, {"type": "instant"}

    elif t == "psycho":
        # 적 알 즉시 파괴 — 반동이 크므로 유불리 계산
        valid = [e for e in enemy_eggs if not e.invisible]
        if not valid:
            return 0.0, {}
        # 내 알이 더 많을 때만 사용 (반동 감수)
        if len(my_eggs) > len(enemy_eggs):
            target = random.choice(valid)
            return 3.0, {"type": "egg", "target": target}
        elif len(my_eggs) == len(enemy_eggs) and len(my_eggs) >= 3:
            target = random.choice(valid)
            return 2.0, {"type": "egg", "target": target}
        return 0.0, {}

    elif t == "ice":
        # 가장 가까운 내 알에 얼음 → 적이 치면 멀리 튀어나감
        # 아니면 적 알에 얼음 → 내가 치면 멀리 날아감
        # 적 알에 사용하는 게 공격적으로 유리
        valid = [e for e in enemy_eggs if not e.icy and not e.invisible]
        if not valid:
            # 내 알 중 보드 가운데 근처에 있는 알에 사용
            valid_my = [e for e in my_eggs if not e.icy]
            if valid_my:
                t2 = min(valid_my, key=lambda e: _dist(
                    e.x, e.y, _c.MID_X,
                    (_c.BOARD_TOP + _c.BOARD_BOTTOM) // 2))
                return 1.0, {"type": "egg", "target": t2}
            return 0.0, {}
        # 가장 가까운 적 알
        target = min(valid, key=lambda e: _dist(
            egg.x, egg.y, e.x, e.y))
        score = 1.8
        return score, {"type": "egg", "target": target}

    elif t == "magnet":
        # 두 적 알을 연결 → 서로 당겨져 한쪽이 보드 밖으로 나갈 수도
        if len(enemy_eggs) >= 2:
            a, b = enemy_eggs[0], enemy_eggs[1]
            # 이미 연결됐으면 스킵
            if a.magnet_pair is None and b.magnet_pair is None:
                # 보드 끝 쪽에 있는 알 선호
                def edge_score(e):
                    return min(e.x - _c.BOARD_LEFT, _c.BOARD_RIGHT - e.x,
                               e.y - _c.BOARD_TOP, _c.BOARD_BOTTOM - e.y)
                sorted_e = sorted(enemy_eggs, key=edge_score)
                a, b = sorted_e[0], sorted_e[min(1, len(sorted_e)-1)]
                if a.id != b.id:
                    return 2.2, {"type": "two_eggs", "a": a, "b": b}
        # 적이 1명이면 내 알과 연결 (상대 당김)
        if enemy_eggs and my_eggs:
            a = enemy_eggs[0]
            b_my = min(my_eggs, key=lambda e: _dist(a.x, a.y, e.x, e.y))
            if a.magnet_pair is None and b_my.magnet_pair is None:
                return 1.5, {"type": "two_eggs", "a": a, "b": b_my}
        return 0.0, {}

    return 0.0, {}


# ── AI 메인 클래스 ────────────────────────────────────────────────

class AIPlayer:
    """
    싱글플레이 P2 AI.
    owner = 1 (P2).

    사용법:
        ai = AIPlayer(owner=1)
        action = ai.decide(gs)
        # action: {"type": "shoot", "egg":Egg, "vx":f, "vy":f}
        #      or {"type": "ability", "egg":Egg, "params":{...}}
        #      or None  (아직 결정 중 — 딜레이)
    """

    THINK_FRAMES = 30   # 행동 전 대기 프레임 (자연스러운 딜레이)

    def __init__(self, owner: int = 1):
        self.owner = owner
        self._wait = self.THINK_FRAMES
        self._decided: dict | None = None

    def reset(self):
        self._wait    = self.THINK_FRAMES
        self._decided = None

    def decide(self, gs) -> dict | None:
        """
        gs.simulating==False이고 gs.turn==self.owner일 때 호출.
        딜레이 후 결정을 반환.
        """
        # 딜레이
        if self._wait > 0:
            self._wait -= 1
            return None

        if self._decided is not None:
            result = self._decided
            self._decided = None
            self._wait = self.THINK_FRAMES
            return result

        # 결정
        action = self._think(gs)
        self._decided = action
        return None   # 다음 프레임에 반환

    def _think(self, gs) -> dict:
        """능력 vs 발사 점수 비교 후 최적 행동 결정."""
        my_eggs     = [e for e in gs.eggs if e.active and e.owner == self.owner and not e.sealed]
        enemy_eggs  = [e for e in gs.eggs if e.active and e.owner != self.owner]

        if not my_eggs:
            return {"type": "shoot", "egg": None, "vx": 0, "vy": 0}

        # ── 능력 평가 ──────────────────────────────────────────────
        best_ab_score = 0.0
        best_ab_egg   = None
        best_ab_params = {}

        for egg in my_eggs:
            if egg.type == "normal" or egg.is_clone:
                continue
            if egg.uses_left <= 0:
                continue
            score, params = _eval_ability(egg, gs)
            if score > best_ab_score and params:
                best_ab_score  = score
                best_ab_egg    = egg
                best_ab_params = params

        # ── 발사 평가 ──────────────────────────────────────────────
        shot = _best_shot(my_eggs, enemy_eggs, list(gs.eggs))
        # 발사 기본 점수: 예상 히트 수 (시뮬레이션 내부에서 계산됨)
        shoot_score = 1.0   # 기본 발사 점수
        if shot:
            shooter, vx, vy = shot
            sim_hits = _simulate_shot(shooter, vx, vy, list(gs.eggs))
            shoot_score = max(0.8, sim_hits * 1.5)

        # ── 결정: 능력 점수 > 발사 점수면 능력 사용 ───────────────
        if best_ab_egg is not None and best_ab_score > shoot_score:
            return {
                "type":   "ability",
                "egg":    best_ab_egg,
                "params": best_ab_params,
            }

        # ── 발사 ───────────────────────────────────────────────────
        if shot:
            shooter, vx, vy = shot
            return {"type": "shoot", "egg": shooter, "vx": vx, "vy": vy}

        # fallback
        egg = my_eggs[0]
        return {"type": "shoot", "egg": egg,
                "vx": random.uniform(-5, 5),
                "vy": random.uniform(-5, 5)}