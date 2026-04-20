# core/ai_player.py
"""
싱글플레이 AI (P2) - 업그레이드 버전

[업그레이드 내용]
1. 풀 물리 시뮬레이션 - 실제 물리 엔진을 그대로 돌려 반사/충돌 경로 예측
2. 맵 인식 - 타이어(반사 각도 이용), 폭탄(유도), 하수구(텔레포트 경로), 방벽 활용
3. 발사 위력 조절 - 목표까지 거리/장애물 상황에 따라 최적 세기(0.55x~1.0x) 계산
4. 능력 상황 판단 고도화 - 10종 알 각각 상황별 점수화
5. 상황 분석 - 수적 우세/열세, 초반/후반, 지뢰 위험 감지
"""
from __future__ import annotations
import math, random
from typing import Optional
import core.constants as _c
from core.egg import Egg, Barrier, Mine


# ===================================================================
# 경량 물리 시뮬레이션
# ===================================================================

def _copy_egg(egg: Egg) -> Egg:
    e = object.__new__(Egg)
    e.id = egg.id; e.x = egg.x; e.y = egg.y
    e.vx = egg.vx; e.vy = egg.vy
    e.owner = egg.owner; e.type = egg.type
    e.r = egg.r; e.active = egg.active
    e.sealed = egg.sealed; e.icy = egg.icy
    e.invisible = egg.invisible; e.is_clone = egg.is_clone
    e.magnet_pair = None
    e.copied_ability = None; e.copied_vx = None
    e.copied_vy = None; e.copy_mode = "none"
    e.uses_left = egg.uses_left; e.max_uses = egg.max_uses
    e.seal_turns = getattr(egg, 'seal_turns', 0)
    e._drain_cd = 0
    return e


def _sim_step_full(eggs, barriers, tires=None, drain_pairs=None):
    """1프레임 물리 (AI 시뮬레이션 전용)."""
    for egg in eggs:
        if not egg.active or math.hypot(egg.vx, egg.vy) <= _c.MIN_SPEED:
            continue
        egg.x += egg.vx; egg.y += egg.vy
        egg.vx *= _c.FRICTION; egg.vy *= _c.FRICTION
        if math.hypot(egg.vx, egg.vy) < _c.MIN_SPEED:
            egg.vx = egg.vy = 0.0
        if (egg.x + egg.r < _c.BOARD_LEFT or egg.x - egg.r > _c.BOARD_RIGHT or
                egg.y + egg.r < _c.BOARD_TOP  or egg.y - egg.r > _c.BOARD_BOTTOM):
            egg.active = False; egg.vx = egg.vy = 0.0

    active = [e for e in eggs if e.active]
    for i in range(len(active)):
        for j in range(i + 1, len(active)):
            a, b = active[i], active[j]
            dx = b.x - a.x; dy = b.y - a.y
            dist = math.hypot(dx, dy)
            if dist >= a.r + b.r or dist < 0.001:
                continue
            nx, ny = dx / dist, dy / dist
            overlap = (a.r + b.r) - dist
            a_mv = math.hypot(a.vx, a.vy) > _c.MIN_SPEED
            b_mv = math.hypot(b.vx, b.vy) > _c.MIN_SPEED
            if a_mv and not b_mv:
                a.x -= nx*(overlap+0.5); a.y -= ny*(overlap+0.5)
                vn = a.vx*nx + a.vy*ny
                if vn > 0:
                    e = _c.RESTITUTION * (_c.ICE_SLIP_MULT if b.icy else 1.0)
                    b.vx += nx*vn*e; b.vy += ny*vn*e
                    a.vx -= nx*vn;   a.vy -= ny*vn
            elif b_mv and not a_mv:
                b.x += nx*(overlap+0.5); b.y += ny*(overlap+0.5)
                vn = -(b.vx*nx + b.vy*ny)
                if vn > 0:
                    e = _c.RESTITUTION * (_c.ICE_SLIP_MULT if a.icy else 1.0)
                    a.vx -= nx*vn*e; a.vy -= ny*vn*e
                    b.vx += nx*vn;   b.vy += ny*vn
            else:
                sep = overlap*0.51
                a.x -= nx*sep; a.y -= ny*sep; b.x += nx*sep; b.y += ny*sep
                dv = (a.vx-b.vx)*nx + (a.vy-b.vy)*ny
                if dv < 0:
                    imp = -(1+_c.RESTITUTION)*dv*0.5
                    a.vx -= imp*nx; a.vy -= imp*ny
                    b.vx += imp*nx; b.vy += imp*ny

    for egg in [e for e in eggs if e.active]:
        for bar in barriers:
            if not bar.active: continue
            dx = egg.x-bar.x; dy = egg.y-bar.y
            dist = math.hypot(dx, dy)
            if dist < bar.r+egg.r and dist > 0.001:
                nx, ny = dx/dist, dy/dist
                egg.x += nx*((bar.r+egg.r-dist)+0.5)
                egg.y += ny*((bar.r+egg.r-dist)+0.5)
                dot = egg.vx*nx + egg.vy*ny
                if dot < 0:
                    egg.vx -= 2*dot*nx*_c.RESTITUTION
                    egg.vy -= 2*dot*ny*_c.RESTITUTION

    if tires:
        for egg in [e for e in eggs if e.active]:
            for (tx, ty, tr, boost) in tires:
                dx = egg.x-tx; dy = egg.y-ty
                dist = math.hypot(dx, dy)
                if dist < tr+egg.r and dist > 0.001:
                    nx, ny = dx/dist, dy/dist
                    egg.x += nx*((tr+egg.r-dist)+0.5)
                    egg.y += ny*((tr+egg.r-dist)+0.5)
                    dot = egg.vx*nx + egg.vy*ny
                    if dot < 0:
                        egg.vx -= 2*dot*nx*(_c.RESTITUTION*boost)
                        egg.vy -= 2*dot*ny*(_c.RESTITUTION*boost)

    if drain_pairs:
        for egg in [e for e in eggs if e.active]:
            if egg._drain_cd > 0:
                egg._drain_cd -= 1; continue
            for (x0,y0,x1,y1) in drain_pairs:
                if math.hypot(egg.x-x0, egg.y-y0) < 22:
                    egg.x = x1+2; egg.y = y1+2; egg._drain_cd = 30; break


def simulate_shot(shooter: Egg, vx: float, vy: float,
                  all_eggs: list, barriers: list,
                  map_obj=None, steps: int = 160) -> dict:
    """실제 물리 시뮬레이션으로 발사 결과 예측."""
    sim = [_copy_egg(e) for e in all_eggs]
    sim_sh = next(e for e in sim if e.id == shooter.id)
    sim_sh.vx = vx; sim_sh.vy = vy

    tires = None; drain_pairs = None
    bar_list = list(barriers)
    if map_obj:
        if hasattr(map_obj,'tires'):
            tires = [(t.x,t.y,t.r,getattr(t,'BOOST',1.5))
                     for t in map_obj.tires if t.active]
        if hasattr(map_obj,'drains') and map_obj.drains:
            dr = map_obj.drains
            drain_pairs = []
            for d in dr:
                if d.active and d.partner_idx < len(dr):
                    p = dr[d.partner_idx]
                    drain_pairs.append((d.x,d.y,p.x,p.y))
        if hasattr(map_obj,'barriers'):
            bar_list += [b for b in map_obj.barriers if b.active]

    before = {e.id: e.active for e in sim if e.active}

    for step in range(steps):
        _sim_step_full(sim, bar_list, tires, drain_pairs)
        if not sim_sh.active: break
        if math.hypot(sim_sh.vx, sim_sh.vy) < _c.MIN_SPEED and step > 15:
            break

    enemy_hit = enemy_out = ally_out = 0
    for e in sim:
        if not before.get(e.id): continue
        if e.owner != shooter.owner:
            if not e.active: enemy_out += 1
            elif math.hypot(e.vx, e.vy) > _c.MIN_SPEED*3: enemy_hit += 1
        else:
            if not e.active and e.id != shooter.id: ally_out += 1

    return {
        "enemy_hit": enemy_hit,
        "enemy_out": enemy_out,
        "ally_out":  ally_out,
        "shooter_out": not sim_sh.active,
    }


# ===================================================================
# 맵 분석기
# ===================================================================

class MapAnalyzer:
    def __init__(self, map_index: int, map_obj):
        self.idx   = map_index
        self.obj   = map_obj
        self.tires  = getattr(map_obj,'tires',   []) if map_obj else []
        self.bombs  = getattr(map_obj,'map_bombs',[]) if map_obj else []
        self.drains = getattr(map_obj,'drains',  []) if map_obj else []

    def tire_reflect_shot(self, shooter: Egg,
                          enemy_eggs: list) -> Optional[tuple]:
        """타이어에 맞고 반사돼 적을 노리는 발사 방향 반환."""
        active_tires = [t for t in self.tires if t.active]
        if not active_tires or not enemy_eggs:
            return None
        spd = _c.MAX_LAUNCH_DIST * _c.LAUNCH_POWER
        best_vx = best_vy = None; best_score = -1
        for tire in active_tires:
            # 발사 알 -> 타이어 방향
            dtx = tire.x - shooter.x; dty = tire.y - shooter.y
            dtd = max(math.hypot(dtx, dty), 1.0)
            vx = dtx/dtd*spd; vy = dty/dtd*spd
            # 타이어 법선 반사
            nx = dtx/dtd; ny = dty/dtd
            vn = vx*nx + vy*ny
            boost = getattr(tire,'BOOST',1.5)
            rvx = vx - 2*vn*nx*boost; rvy = vy - 2*vn*ny*boost
            # 반사 방향이 적 향하면 점수
            for enemy in enemy_eggs:
                ex = enemy.x - tire.x; ey = enemy.y - tire.y
                ed = max(math.hypot(ex, ey), 1.0)
                dot = (rvx*ex + rvy*ey) / (spd * ed)
                if dot > best_score:
                    best_score = dot
                    best_vx, best_vy = vx, vy
        if best_score > 0.65:
            return best_vx, best_vy
        return None

    def bomb_trigger_shot(self, shooter: Egg,
                          enemy_eggs: list) -> Optional[tuple]:
        """맵 폭탄 근처 적에게 적을 유도하는 발사 방향."""
        active = [b for b in self.bombs if b.active]
        if not active or not enemy_eggs:
            return None
        spd = _c.MAX_LAUNCH_DIST * _c.LAUNCH_POWER
        for b in active:
            for e in enemy_eggs:
                if math.hypot(e.x-b.x, e.y-b.y) < b.BLAST_RADIUS * 1.4:
                    dx = b.x - shooter.x; dy = b.y - shooter.y
                    dist = max(math.hypot(dx, dy), 1.0)
                    return dx/dist*spd, dy/dist*spd
        return None

    def drain_attack_shot(self, shooter: Egg,
                          enemy_eggs: list) -> Optional[tuple]:
        """하수구 입구 방향으로 쏴서 출구 근처 적 공격."""
        if not self.drains or not enemy_eggs:
            return None
        spd = _c.MAX_LAUNCH_DIST * _c.LAUNCH_POWER
        for d in self.drains:
            if not d.active: continue
            if d.partner_idx >= len(self.drains): continue
            partner = self.drains[d.partner_idx]
            for e in enemy_eggs:
                if math.hypot(e.x-partner.x, e.y-partner.y) < 250:
                    dx = d.x - shooter.x; dy = d.y - shooter.y
                    dist = max(math.hypot(dx, dy), 1.0)
                    return dx/dist*spd, dy/dist*spd
        return None

    def best_barrier_pos(self, my_eggs, enemy_eggs,
                         all_eggs, barriers) -> Optional[tuple]:
        """적 이동 경로 차단 최적 방벽 위치."""
        from core.abilities import pos_occupied
        if not enemy_eggs or not my_eggs: return None
        my_cx  = sum(e.x for e in my_eggs)    / len(my_eggs)
        my_cy  = sum(e.y for e in my_eggs)    / len(my_eggs)
        en_cx  = sum(e.x for e in enemy_eggs) / len(enemy_eggs)
        en_cy  = sum(e.y for e in enemy_eggs) / len(enemy_eggs)
        best_pos = None; best_score = -1
        for t_ratio in [0.30, 0.40, 0.50]:
            for jx, jy in [(0,0),(50,0),(-50,0),(0,50),(0,-50),(40,40),(-40,40)]:
                bx = en_cx + (my_cx-en_cx)*t_ratio + jx
                by = en_cy + (my_cy-en_cy)*t_ratio + jy
                bx = max(_c.BOARD_LEFT+_c.EGG_RADIUS+6,
                         min(_c.BOARD_RIGHT-_c.EGG_RADIUS-6, bx))
                by = max(_c.BOARD_TOP+_c.EGG_RADIUS+6,
                         min(_c.BOARD_BOTTOM-_c.EGG_RADIUS-6, by))
                if pos_occupied(bx, by, all_eggs, barriers): continue
                min_en = min(math.hypot(e.x-bx,e.y-by) for e in enemy_eggs)
                score = 1000 - min_en
                if score > best_score:
                    best_score = score; best_pos = (bx, by)
        return best_pos


# ===================================================================
# 상황 분석
# ===================================================================

class GameSituation:
    def __init__(self, gs, owner: int):
        all_e = [e for e in gs.eggs if e.active]
        self.my_eggs    = [e for e in all_e if e.owner == owner]
        self.enemy_eggs = [e for e in all_e if e.owner != owner]
        self.my_cnt     = len(self.my_eggs)
        self.en_cnt     = len(self.enemy_eggs)
        self.adv        = self.my_cnt - self.en_cnt
        self.early_game = len(gs.logs) < 10
        self.late_game  = self.my_cnt <= 3 or self.en_cnt <= 3
        self.danger_mines = [
            m for m in gs.mines
            if m.active and m.owner != owner
            and any(math.hypot(m.x-e.x, m.y-e.y) < m.BLAST_RADIUS*1.4
                    for e in self.my_eggs)
        ]
        self.enemy_ability_threat = sum(
            1 for e in self.enemy_eggs
            if e.type not in ("normal",) and e.uses_left > 0
        )


# ===================================================================
# 발사 최적화
# ===================================================================

def _score_shot(res: dict, situation: GameSituation) -> float:
    score  = res["enemy_out"]  * 5.0
    score += res["enemy_hit"]  * 1.5
    score -= res["ally_out"]   * 4.5
    score -= res["shooter_out"] * 2.0
    if situation.adv < 0:
        score += res["enemy_hit"] * 0.5
    return score


def find_best_shot(my_eggs, enemy_eggs, all_eggs,
                   barriers, map_obj,
                   ma: MapAnalyzer,
                   sit: GameSituation) -> Optional[dict]:
    candidates = [e for e in my_eggs if not e.sealed]
    if not candidates or not enemy_eggs:
        return None

    max_spd = _c.MAX_LAUNCH_DIST * _c.LAUNCH_POWER
    best = None; best_score = -999.0

    for shooter in candidates:
        # 직선 조준 - 세기 4단계
        for target in enemy_eggs:
            dx = target.x-shooter.x; dy = target.y-shooter.y
            dist = max(math.hypot(dx, dy), 1.0)
            nx, ny = dx/dist, dy/dist
            for power in [1.0, 0.80, 0.65, 0.50]:
                vx = nx*max_spd*power; vy = ny*max_spd*power
                res = simulate_shot(shooter, vx, vy, all_eggs, barriers, map_obj, 150)
                score = _score_shot(res, sit)
                if score > best_score:
                    best_score = score
                    best = {"egg":shooter,"vx":vx,"vy":vy,
                            "score":score,"reason":f"직선 {power:.0%}"}

        # 타이어 반사 (타이어 맵)
        if ma.idx == 2:
            bounce = ma.tire_reflect_shot(shooter, enemy_eggs)
            if bounce:
                vx, vy = bounce
                res = simulate_shot(shooter, vx, vy, all_eggs, barriers, map_obj, 200)
                score = _score_shot(res, sit) + 2.0
                if score > best_score:
                    best_score = score
                    best = {"egg":shooter,"vx":vx,"vy":vy,
                            "score":score,"reason":"타이어 반사"}

        # 폭탄 유도 (폭탄 맵)
        if ma.idx == 1:
            bomb_shot = ma.bomb_trigger_shot(shooter, enemy_eggs)
            if bomb_shot:
                vx, vy = bomb_shot
                res = simulate_shot(shooter, vx, vy, all_eggs, barriers, map_obj, 150)
                score = _score_shot(res, sit) + 2.5
                if score > best_score:
                    best_score = score
                    best = {"egg":shooter,"vx":vx,"vy":vy,
                            "score":score,"reason":"폭탄 유도"}

        # 하수구 텔레포트 (하수구 맵)
        if ma.idx == 3:
            drain_shot = ma.drain_attack_shot(shooter, enemy_eggs)
            if drain_shot:
                vx, vy = drain_shot
                res = simulate_shot(shooter, vx, vy, all_eggs, barriers, map_obj, 200)
                score = _score_shot(res, sit) + 2.0
                if score > best_score:
                    best_score = score
                    best = {"egg":shooter,"vx":vx,"vy":vy,
                            "score":score,"reason":"하수구 공격"}

        # 지뢰 위험 회피
        if sit.danger_mines:
            mine = sit.danger_mines[0]
            dx = shooter.x-mine.x; dy = shooter.y-mine.y
            dist = max(math.hypot(dx, dy), 1.0)
            vx = dx/dist*max_spd*0.6; vy = dy/dist*max_spd*0.6
            res = simulate_shot(shooter, vx, vy, all_eggs, barriers, map_obj, 60)
            score = _score_shot(res, sit) + 1.0
            if score > best_score:
                best_score = score
                best = {"egg":shooter,"vx":vx,"vy":vy,
                        "score":score,"reason":"지뢰 회피"}

    if best is None:
        shooter = random.choice(candidates)
        target  = min(enemy_eggs,
                      key=lambda e: math.hypot(e.x-shooter.x, e.y-shooter.y))
        dx = target.x-shooter.x; dy = target.y-shooter.y
        dist = max(math.hypot(dx, dy), 1.0)
        spd = max_spd * random.uniform(0.65, 1.0)
        best = {"egg":shooter,"vx":dx/dist*spd,"vy":dy/dist*spd,
                "score":0.0,"reason":"랜덤"}
    return best


# ===================================================================
# 능력 평가
# ===================================================================

THREAT_MAP = {
    "psycho":4.5,"bomb":4,"magnet":3.5,"invisible":3,
    "copy":3,"seal":2.5,"ice":2.5,"clone":2,"barrier":1.5,"normal":0,
}

def evaluate_abilities(my_eggs, enemy_eggs, all_eggs,
                       gs, ma: MapAnalyzer,
                       sit: GameSituation, barriers) -> list:
    results = []
    for egg in my_eggs:
        if egg.is_clone or egg.sealed or egg.uses_left <= 0:
            continue
        t = egg.type
        if t == "normal":
            continue
        entry = _eval_ability(egg, t, enemy_eggs, my_eggs,
                              all_eggs, gs, ma, sit, barriers)
        if entry and entry["score"] > 0:
            results.append(entry)
    results.sort(key=lambda x: x["score"], reverse=True)
    return results


def _eval_ability(egg, t, enemy_eggs, my_eggs, all_eggs,
                  gs, ma, sit, barriers):
    from core.abilities import pos_occupied

    if t == "barrier":
        pos = ma.best_barrier_pos(my_eggs, enemy_eggs, all_eggs, barriers)
        if not pos: return None
        score = 0.6 if sit.early_game else 1.5
        if sit.adv < -1: score = 2.8
        return {"egg":egg,"score":score,
                "params":{"type":"pos","x":pos[0],"y":pos[1]},
                "reason":"방벽 차단"}

    elif t == "seal":
        valid = [e for e in enemy_eggs
                 if not e.sealed and not e.invisible and e.uses_left > 0]
        if not valid: return None
        target = max(valid,
                     key=lambda e: e.uses_left * THREAT_MAP.get(e.type,1))
        threat = target.uses_left * THREAT_MAP.get(target.type,1)
        score  = 1.0 + threat*0.4
        if sit.late_game: score *= 1.5
        return {"egg":egg,"score":score,
                "params":{"type":"egg","target":target},
                "reason":f"봉인: {target.type}"}

    elif t == "copy":
        if egg.copy_mode != "none": return None
        copyable = [e for e in enemy_eggs
                    if e.type not in ("normal","copy")
                    and not e.invisible and e.uses_left > 0]
        if not copyable: return None
        copy_val = {"psycho":4.5,"bomb":4,"magnet":3.5,
                    "invisible":3,"ice":2.5,"seal":2.5,"clone":2,"barrier":1.5}
        target = max(copyable,
                     key=lambda e: copy_val.get(e.type,1)*e.uses_left)
        score = copy_val.get(target.type,1) * 0.8
        return {"egg":egg,"score":score,
                "params":{"type":"egg","target":target},
                "reason":f"능력 복사: {target.type}"}

    elif t == "clone":
        approaching = sum(1 for e in enemy_eggs
                          if math.hypot(e.x-egg.x, e.y-egg.y) < 300)
        score = 1.0 + approaching*0.5
        if sit.my_cnt <= 3: score += 1.5
        if sit.late_game:   score += 1.0
        return {"egg":egg,"score":score,
                "params":{"type":"instant"},
                "reason":"분신 교란"}

    elif t == "bomb":
        if not enemy_eggs: return None
        # 폭탄 맵: 맵 폭탄 연쇄 위치 우선
        if ma.idx == 1:
            for b in [x for x in ma.bombs if x.active]:
                for e in enemy_eggs:
                    midx = (b.x+e.x)*0.5; midy = (b.y+e.y)*0.5
                    if not pos_occupied(midx, midy, all_eggs, barriers):
                        return {"egg":egg,"score":3.5,
                                "params":{"type":"pos","x":midx,"y":midy},
                                "reason":"폭탄 연쇄 유발"}
        my_cx = sum(e.x for e in my_eggs)/len(my_eggs)
        my_cy = sum(e.y for e in my_eggs)/len(my_eggs)
        best_pos = None; best_d = 999999
        for e in enemy_eggs:
            for tr in [0.40, 0.55]:
                bx = e.x+(my_cx-e.x)*tr + random.uniform(-25,25)
                by = e.y+(my_cy-e.y)*tr + random.uniform(-25,25)
                bx = max(_c.BOARD_LEFT+5, min(_c.BOARD_RIGHT-5, bx))
                by = max(_c.BOARD_TOP+5,  min(_c.BOARD_BOTTOM-5, by))
                if not pos_occupied(bx, by, all_eggs, barriers):
                    d = math.hypot(bx-e.x, by-e.y)
                    if d < best_d: best_d=d; best_pos=(bx,by)
        if not best_pos: return None
        density = sum(1 for e in enemy_eggs
                      if math.hypot(e.x-best_pos[0],e.y-best_pos[1])<200)
        score = 1.5 + density*0.8 + (0.5 if sit.adv>0 else 0)
        return {"egg":egg,"score":score,
                "params":{"type":"pos","x":best_pos[0],"y":best_pos[1]},
                "reason":"경로 지뢰"}

    elif t == "invisible":
        if egg.invisible: return None
        score = 0.8 + sit.enemy_ability_threat*0.4
        if sit.my_cnt < sit.en_cnt: score += 1.0
        if sit.early_game: score *= 0.6
        return {"egg":egg,"score":score,
                "params":{"type":"instant"},"reason":"투명화"}

    elif t == "psycho":
        valid = [e for e in enemy_eggs if not e.invisible]
        if not valid: return None
        if sit.my_cnt <= sit.en_cnt: return None
        target = max(valid,
                     key=lambda e: (5 if e.uses_left>0 else 1)
                                    +(3 if sit.en_cnt==1 else 0))
        score = 2.0
        if sit.my_cnt - sit.en_cnt >= 2: score = 3.5
        if sit.en_cnt == 1: score = 4.5
        return {"egg":egg,"score":score,
                "params":{"type":"egg","target":target},"reason":"염력 파괴"}

    elif t == "ice":
        valid = [e for e in enemy_eggs if not e.icy and not e.invisible]
        if not valid: return None
        def edge_d(e):
            return min(e.x-_c.BOARD_LEFT, _c.BOARD_RIGHT-e.x,
                       e.y-_c.BOARD_TOP,  _c.BOARD_BOTTOM-e.y)
        target = min(valid, key=edge_d)
        score  = 1.5 + (1.0 if edge_d(target)<150 else 0)
        if ma.idx == 2: score += 0.8   # 타이어 맵 시너지
        return {"egg":egg,"score":score,
                "params":{"type":"egg","target":target},"reason":"얼음 슬립"}

    elif t == "magnet":
        def edge_d(e):
            return min(e.x-_c.BOARD_LEFT, _c.BOARD_RIGHT-e.x,
                       e.y-_c.BOARD_TOP,  _c.BOARD_BOTTOM-e.y)
        valid = [e for e in enemy_eggs
                 if e.magnet_pair is None and not e.invisible]
        if len(valid) >= 2:
            sv = sorted(valid, key=edge_d)
            a, b = sv[0], sv[min(1,len(sv)-1)]
            if a.id != b.id:
                score = 2.5+(1.0 if edge_d(a)<200 else 0)
                if sit.late_game: score += 0.8
                return {"egg":egg,"score":score,
                        "params":{"type":"two_eggs","a":a,"b":b},
                        "reason":"자석(적↔적)"}
        if valid and my_eggs:
            a = valid[0]
            if edge_d(a) < 150:
                bm = min(my_eggs,
                         key=lambda e: math.hypot(e.x-a.x,e.y-a.y))
                if bm.magnet_pair is None:
                    return {"egg":egg,"score":1.5,
                            "params":{"type":"two_eggs","a":a,"b":bm},
                            "reason":"자석(적↔아군)"}
        return None
    return None


# ===================================================================
# AI 메인
# ===================================================================

class AIPlayer:
    THINK_FRAMES = 35

    def __init__(self, owner: int = 1):
        self.owner    = owner
        self._wait    = self.THINK_FRAMES
        self._decided = None
        self._ma: Optional[MapAnalyzer] = None

    def reset(self):
        self._wait    = self.THINK_FRAMES
        self._decided = None
        self._ma      = None

    def decide(self, gs) -> Optional[dict]:
        if self._wait > 0:
            self._wait -= 1
            return None
        if self._decided is not None:
            result = self._decided
            self._decided = None
            self._wait = self.THINK_FRAMES
            return result
        self._decided = self._think(gs)
        return None

    def _think(self, gs) -> dict:
        my_eggs    = [e for e in gs.eggs if e.active and e.owner == self.owner]
        enemy_eggs = [e for e in gs.eggs if e.active and e.owner != self.owner]
        all_eggs   = [e for e in gs.eggs if e.active]
        if not my_eggs:
            return {"type":"shoot","egg":None,"vx":0,"vy":0}

        if self._ma is None or self._ma.idx != gs.map_index:
            self._ma = MapAnalyzer(gs.map_index, gs.map_obj)

        sit      = GameSituation(gs, self.owner)
        barriers = list(gs.barriers) + (
            [b for b in gs.map_obj.barriers if b.active]
            if gs.map_obj and hasattr(gs.map_obj,'barriers') else []
        )

        # 능력 평가
        ab_list = evaluate_abilities(my_eggs, enemy_eggs, all_eggs,
                                     gs, self._ma, sit, barriers)
        # 발사 평가
        shot = find_best_shot(my_eggs, enemy_eggs, all_eggs,
                               barriers, gs.map_obj,
                               self._ma, sit)
        shoot_score = shot["score"] if shot else 0.0

        # 결정
        if ab_list and ab_list[0]["score"] > shoot_score:
            ab = ab_list[0]
            gs.log(f"[AI] {ab['reason']} (점수:{ab['score']:.1f})")
            return {"type":"ability","egg":ab["egg"],"params":ab["params"]}

        if shot:
            gs.log(f"[AI] {shot['reason']} 발사 (점수:{shot['score']:.1f})")
            return {"type":"shoot","egg":shot["egg"],
                    "vx":shot["vx"],"vy":shot["vy"]}

        egg = my_eggs[0]
        angle = random.uniform(math.pi, 2*math.pi)
        spd   = _c.MAX_LAUNCH_DIST * _c.LAUNCH_POWER * 0.7
        return {"type":"shoot","egg":egg,
                "vx":math.cos(angle)*spd,"vy":math.sin(angle)*spd}