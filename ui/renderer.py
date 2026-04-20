"""pygame 화면 렌더러."""
from __future__ import annotations
import math, pygame
from core.constants import *
from core.egg import Egg, Barrier, Mine
from core.game_state import GameState

# --   -----------------------------------------------------
def _dk(color, f=0.55):
    return tuple(int(c * f) for c in color[:3])

def _lt(color, f=1.4):
    return tuple(min(255, int(c * f)) for c in color[:3])

def _blend(c1, c2, t=0.5):
    return tuple(int(c1[i] * (1 - t) + c2[i] * t) for i in range(3))


class Renderer:
    # UI
    TOP_BAR_H   = 56   #   → /
    SIDE_PAD    = 8    #
    BTN_ZONE_H  = 56   #
    LOG_H       = 60   #

    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.w = screen.get_width()
        self.h = screen.get_height()
        self._tick = 0
        self._load_fonts()
        self.particles: list[dict] = []

    def _load_fonts(self):
        pygame.font.init()
        try:
            self.font_lg = pygame.font.SysFont("malgungothic", 24, bold=True)
            self.font_md = pygame.font.SysFont("malgungothic", 17)
            self.font_sm = pygame.font.SysFont("malgungothic", 13)
            self.font_xl = pygame.font.SysFont("malgungothic", 46, bold=True)
        except Exception:
            self.font_lg = pygame.font.Font(None, 26)
            self.font_md = pygame.font.Font(None, 19)
            self.font_sm = pygame.font.Font(None, 15)
            self.font_xl = pygame.font.Font(None, 50)

    def _snap(self):
        import core.constants as _c
        self._BL = _c.BOARD_LEFT
        self._BT = _c.BOARD_TOP
        self._BR = _c.BOARD_RIGHT
        self._BB = _c.BOARD_BOTTOM
        self._MX = _c.MID_X

    # --  ----------------------------------------------------
    def spawn_particles(self, x, y, color, count=10):
        import random
        for _ in range(count):
            a = random.uniform(0, 2 * math.pi)
            sp = random.uniform(1.5, 5.5)
            self.particles.append({
                "x": x, "y": y,
                "vx": math.cos(a) * sp,
                "vy": math.sin(a) * sp,
                "life": 32, "max": 32,
                "color": color[:3], "r": random.randint(2, 5)
            })

    def _update_particles(self):
        alive = []
        for p in self.particles:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["vy"] += 0.14
            p["life"] -= 1
            if p["life"] > 0:
                alive.append(p)
        self.particles = alive

    def _draw_particles(self):
        for p in self.particles:
            pygame.draw.circle(self.screen, p["color"],
                               (int(p["x"]), int(p["y"])), p["r"])

    # --   -------------------------------------------------
    def render(self, gs: GameState):
        self._tick += 1
        self._snap()
        self._update_particles()
        self.screen.fill(C_BG)
        self._draw_board(gs)
        self._draw_map_barriers(gs)
        self._draw_map_specials(gs)
        self._draw_mines(gs)
        self._draw_barriers(gs)
        self._draw_magnet_lines(gs)
        self._draw_eggs(gs)
        self._draw_particles()
        self._draw_aim(gs)
        self._draw_hud(gs)
        if gs.phase == STATE_GAMEOVER:
            self._draw_gameover(gs)

    # --  ------------------------------------------------------
    def _draw_board(self, gs: GameState):
        from core.map_system import MAP_DEFS
        md = MAP_DEFS[gs.map_index]
        bg_col   = md["bg"]
        bord_col = md["line"]

        board_rect = pygame.Rect(self._BL, self._BT,
                                 self._BR - self._BL,
                                 self._BB - self._BT)
        pygame.draw.rect(self.screen, bg_col, board_rect, border_radius=6)
        pygame.draw.rect(self.screen, bord_col, board_rect, 2, border_radius=6)
        #
        pygame.draw.line(self.screen, bord_col,
                         (self._MX, self._BT), (self._MX, self._BB), 1)

    # --    ----------------------------------------------
    def _draw_map_barriers(self, gs: GameState):
        for b in gs.map_obj.barriers:
            if not b.active:
                continue
            self._draw_barrier_shape(b, static=True)

    # --   -----------------------------------------------
    def _draw_barriers(self, gs: GameState):
        for b in gs.barriers:
            if not b.active:
                continue
            self._draw_barrier_shape(b, static=False)


    # --    ------------------------------------------
    def _draw_map_specials(self, gs: GameState):
        self._draw_map_bombs(gs)
        self._draw_tires(gs)
        self._draw_drains(gs)

    def _draw_map_bombs(self, gs: GameState):
        for bomb in gs.map_obj.map_bombs:
            if not bomb.active:
                continue
            cx, cy = int(bomb.x), int(bomb.y)
            #
            pygame.draw.circle(self.screen, (100, 40, 10), (cx, cy), bomb.r + 5)
            pygame.draw.circle(self.screen, (220, 80, 30), (cx, cy), bomb.r)
            pygame.draw.circle(self.screen, (255, 150, 60), (cx, cy), bomb.r - 4)
            #
            pygame.draw.line(self.screen, (200, 200, 80),
                             (cx, cy - bomb.r), (cx + 5, cy - bomb.r - 8), 2)
            txt = self.font_sm.render("[봉]", True, C_WHITE)
            self.screen.blit(txt, txt.get_rect(center=(cx, cy)))

    def _draw_tires(self, gs: GameState):
        for tire in gs.map_obj.tires:
            if not tire.active:
                continue
            cx, cy = int(tire.x), int(tire.y)
            #   ( )
            pygame.draw.circle(self.screen, (20, 20, 20), (cx, cy), tire.r)
            #   ( )
            pygame.draw.circle(self.screen, (80, 55, 20), (cx, cy), tire.r - 6)
            #
            pygame.draw.circle(self.screen, (140, 120, 60), (cx, cy), 8)
            #   ( )
            remain = tire.MAX_HITS - tire.hits
            col = (100, 255, 100) if remain > 6 else (255, 200, 60) if remain > 3 else (255, 80, 80)
            txt = self.font_sm.render(f"{remain}", True, col)
            self.screen.blit(txt, txt.get_rect(center=(cx, cy - tire.r - 10)))
            txt2 = self.font_sm.render("", True, (180, 160, 80))
            self.screen.blit(txt2, txt2.get_rect(center=(cx, cy)))

    def _draw_drains(self, gs: GameState):
        import math
        for di, drain in enumerate(gs.map_obj.drains):
            if not drain.active:
                continue
            cx, cy = int(drain.x), int(drain.y)
            #
            t = self._tick * 0.05
            pygame.draw.circle(self.screen, (10, 30, 35), (cx, cy), drain.r)
            pygame.draw.circle(self.screen, (20, 80, 90), (cx, cy), drain.r, 2)
            #
            for i in range(4):
                angle = t + i * math.pi / 2
                x2 = cx + int(math.cos(angle) * (drain.r - 4))
                y2 = cy + int(math.sin(angle) * (drain.r - 4))
                pygame.draw.line(self.screen, (40, 160, 180), (cx, cy), (x2, y2), 2)
            #  (  )
            partner = drain.partner_idx
            txt = self.font_sm.render(f"{partner}", True, (80, 200, 220))
            self.screen.blit(txt, txt.get_rect(center=(cx, cy)))

    def _draw_barrier_shape(self, b: Barrier, static: bool):
        cx, cy = int(b.x), int(b.y)
        col = (60, 130, 80) if not static else (100, 80, 130)
        pts = [(cx + int(b.r * math.cos(math.radians(60*i - 30))),
                cy + int(b.r * math.sin(math.radians(60*i - 30))))
               for i in range(6)]
        fill = _dk(col, 0.45)
        pygame.draw.polygon(self.screen, fill, pts)
        pygame.draw.polygon(self.screen, col, pts, 2)
        sym = "" if not static else ""
        txt = self.font_sm.render(sym, True, col)
        self.screen.blit(txt, txt.get_rect(center=(cx, cy)))

    # --  ------------------------------------------------------
    def _draw_mines(self, gs: GameState):
        for mine in gs.mines:
            if not mine.active:
                continue
            col = C_P1 if mine.owner == 0 else C_P2
            cx, cy = int(mine.x), int(mine.y)
            pygame.draw.circle(self.screen, _dk(col, 0.4), (cx, cy), mine.r + 4)
            pygame.draw.circle(self.screen, col, (cx, cy), mine.r)
            pygame.draw.circle(self.screen, (20, 20, 20), (cx, cy), mine.r - 3)
            for ang in range(0, 360, 45):
                rad = math.radians(ang)
                x2 = cx + int(math.cos(rad) * (mine.r + 5))
                y2 = cy + int(math.sin(rad) * (mine.r + 5))
                pygame.draw.line(self.screen, col, (cx, cy), (x2, y2), 2)
            txt = self.font_sm.render("[봉]", True, C_WHITE)
            self.screen.blit(txt, txt.get_rect(center=(cx, cy)))

    # --   ---------------------------------------------------
    def _draw_magnet_lines(self, gs: GameState):
        drawn = set()
        for egg in gs.eggs:
            if egg.active and egg.magnet_pair and egg.magnet_pair.active:
                key = tuple(sorted([egg.id, egg.magnet_pair.id]))
                if key in drawn:
                    continue
                drawn.add(key)
                pygame.draw.line(self.screen, (180, 120, 240),
                                 (int(egg.x), int(egg.y)),
                                 (int(egg.magnet_pair.x), int(egg.magnet_pair.y)), 2)

    # --  --------------------------------------------------------
    def _draw_eggs(self, gs: GameState):
        for egg in gs.eggs:
            if egg.active:
                self._draw_single_egg(egg, gs)

    def _draw_single_egg(self, egg: Egg, gs: GameState):
        cx, cy    = int(egg.x), int(egg.y)
        selected  = (egg is gs.selected_egg or egg is gs.ability_egg)
        col       = egg.base_color
        owner_col = C_P1 if egg.owner == 0 else C_P2

        # --   --
        if egg.invisible:
            is_own = (egg.owner == gs.turn)
            if is_own:
                surf = pygame.Surface((egg.r*2+4, egg.r*2+4), pygame.SRCALPHA)
                pygame.draw.circle(surf, (*col, 80), (egg.r+2, egg.r+2), egg.r)
                ow_c = C_P1 if egg.owner == 0 else C_P2
                pygame.draw.circle(surf, (*ow_c, 50), (egg.r+2, egg.r+2), egg.r+2, 2)
                self.screen.blit(surf, (cx-egg.r-2, cy-egg.r-2))
                icon = self.font_sm.render("유령", True, (200, 200, 255))
                self.screen.blit(icon, (cx-7, cy-7))
            return

        # --   --
        if selected:
            pygame.draw.circle(self.screen, _lt(col, 2.0), (cx, cy), egg.r+7)

        # --   --
        pygame.draw.circle(self.screen, owner_col, (cx, cy), egg.r+3)

        # --   --
        draw_col = (85, 88, 105) if egg.sealed else col
        pygame.draw.circle(self.screen, _dk(draw_col, 0.5), (cx, cy), egg.r)
        pygame.draw.circle(self.screen, draw_col, (cx, cy), egg.r-2)

        # --   --
        if egg.icy:
            ice = pygame.Surface((egg.r*2, egg.r*2), pygame.SRCALPHA)
            pygame.draw.circle(ice, (100, 220, 255, 80), (egg.r, egg.r), egg.r)
            self.screen.blit(ice, (cx-egg.r, cy-egg.r))

        # --     --
        if egg.type == "copy" and egg.copy_mode != "none":
            pulse = abs(math.sin(self._tick * 0.08)) * 0.6 + 0.4
            glow  = tuple(int(c * pulse) for c in (255, 220, 60))
            pygame.draw.circle(self.screen, glow, (cx, cy), egg.r+5, 2)

        # --  --
        pygame.draw.circle(self.screen, _lt(col, 1.6),
                           (cx - egg.r//3, cy - egg.r//3), egg.r//3)

        # --   --
        if gs.phase == STATE_ABILITY and egg in gs.ability_targets:
            pygame.draw.circle(self.screen, C_HIGHLIGHT, (cx, cy), egg.r+5, 2)

        # --  --
        name = EGG_INFO[egg.type]["name"][:2]
        txt  = self.font_sm.render(name, True, C_WHITE)
        self.screen.blit(txt, txt.get_rect(center=(cx, cy)))

        # --   --
        ix, iy = cx + egg.r - 5, cy - egg.r - 2
        if egg.icy:
            self.screen.blit(self.font_sm.render("얼음", True, (100, 230, 255)), (ix, iy))
            iy += 14
        if egg.sealed:
            #    +
            seal_txt = self.font_sm.render(f"봉인{egg.seal_turns}", True, (230, 180, 60))
            self.screen.blit(seal_txt, (ix - 6, iy))
            iy += 14

        #    ( )
        if egg.type == "copy" and egg.copy_mode == "ability" and egg.copied_ability:
            label = EGG_INFO.get(egg.copied_ability, {}).get("name", "?")[:2]
            ct = self.font_sm.render(f"[{label}]", True, (255, 220, 60))
            self.screen.blit(ct, (cx - ct.get_width()//2, cy + egg.r + 2))
        elif egg.type == "copy" and egg.copy_mode == "power":
            spd = math.hypot(egg.copied_vx or 0, egg.copied_vy or 0)
            ct = self.font_sm.render(f"[위:{spd:.0f}]", True, (100, 255, 180))
            self.screen.blit(ct, (cx - ct.get_width()//2, cy + egg.r + 2))

    # --  ----------------------------------------------------
    def _draw_aim(self, gs: GameState):
        if not gs.dragging or gs.selected_egg is None:
            return
        egg = gs.selected_egg
        ex, ey = int(egg.x), int(egg.y)
        dx = gs.drag_sx - gs.drag_ex
        dy = gs.drag_sy - gs.drag_ey
        dist = math.hypot(dx, dy)
        if dist < 2:
            return

        scale = min(dist / MAX_LAUNCH_DIST, 1.0)
        nx, ny = dx/dist, dy/dist

        for i in range(0, 80, 12):
            t = i / 80
            px = int(ex + nx * i * scale)
            py = int(ey + ny * i * scale)
            r = max(2, int(5*(1-t)))
            c = _blend(C_AIM_LINE, C_BG, t*0.7)
            pygame.draw.circle(self.screen, c, (px, py), r)

        end_x = int(ex + nx*90*scale)
        end_y = int(ey + ny*90*scale)
        pygame.draw.circle(self.screen, C_AIM_LINE, (end_x, end_y), 5)
        pct = int(scale * 100)
        txt = self.font_sm.render(f"발사력: {pct}%", True, C_AIM_LINE)
        self.screen.blit(txt, (end_x+8, end_y-10))

    # -- HUD -------------------------------------------------------
    #  ( ):
    #  [0 ~ BT-TOP_BAR_H-4]  :
    #  [BT-TOP_BAR_H .. BT]  : /  (TOP_BAR_H px)
    #  [BT .. BB]             :
    #  [BB+2 .. BB+BTN_ZONE_H]:   (input_handler )
    #  [BB+BTN_ZONE_H+4 ..]   :   (LOG_H px)
    #  [ 0..BL]           : P1
    #  [ BR..w]           : P2

    def _draw_hud(self, gs: GameState):
        self._draw_top_bar(gs)
        self._draw_side_panel(gs, 0)
        self._draw_side_panel(gs, 1)
        self._draw_log(gs)

    def _draw_top_bar(self, gs: GameState):
        cx = self.w // 2
        bar_y = self._BT - self.TOP_BAR_H
        bar_h = self.TOP_BAR_H - 2

        #
        pygame.draw.rect(self.screen, C_UI_BG,
                         (self._BL, bar_y, self._BR - self._BL, bar_h),
                         border_radius=6)

        #
        turn_name = "P1 (파랑)" if gs.turn == 0 else "P2 (빨강)"
        turn_col  = C_P1        if gs.turn == 0 else C_P2
        txt = self.font_lg.render(f"{turn_name} 차례", True, turn_col)
        self.screen.blit(txt, txt.get_rect(center=(cx, bar_y + 16)))

        #
        if gs.phase == STATE_ABILITY and gs.ability_egg:
            egg  = gs.ability_egg
            desc = EGG_INFO.get(egg.type, {}).get("name", "")
            #
            extra = ""
            if egg.type == "copy":
                if egg.copy_mode == "ability" and egg.copied_ability:
                    aname = EGG_INFO.get(egg.copied_ability, {}).get("name", "?")
                    extra = f"  |  : [{aname}]"
                elif egg.copy_mode == "power" and egg.copied_vx is not None:
                    import math as _m
                    spd = _m.hypot(egg.copied_vx, egg.copied_vy)
                    extra = f"  |  : [{spd:.0f}]"
                else:
                    extra = "모드: 발사 | 능력"
            mode_t = self.font_md.render(f"능력: {desc}{extra}", True, C_HIGHLIGHT)
        elif gs.action_mode == ACTION_SHOOT:
            mode_t = self.font_md.render("모드: 발사", True, C_GRAY)
        else:
            mode_t = self.font_md.render("모드: 능력", True, (200, 160, 255))
        self.screen.blit(mode_t, mode_t.get_rect(center=(cx, bar_y + 38)))

    def _draw_side_panel(self, gs: GameState, owner: int):
        if owner == 0:
            px      = self.SIDE_PAD
            panel_w = self._BL - self.SIDE_PAD * 2
        else:
            px      = self._BR + self.SIDE_PAD
            panel_w = self.w - self._BR - self.SIDE_PAD * 2

        py    = self._BT
        col   = C_P1 if owner == 0 else C_P2
        label = "P1" if owner == 0 else "P2"

        alive = [e for e in gs.eggs if e.active and e.owner == owner]

        #
        panel_h = self._BB - self._BT
        pygame.draw.rect(self.screen, C_UI_BG,
                         (px, py, panel_w, panel_h), border_radius=6)
        pygame.draw.rect(self.screen, col,
                         (px, py, panel_w, panel_h), 1, border_radius=6)

        #
        hdr = self.font_md.render(f"{label}: {len(alive)}개", True, col)
        self.screen.blit(hdr, (px+6, py+6))

        #   (    )
        max_lines = max(1, (panel_h - 30) // 22)
        y = py + 28
        for egg in alive[:max_lines]:
            is_sel = (egg is gs.selected_egg or egg is gs.ability_egg)
            bg = C_BTN_ACT if is_sel else (28, 34, 60)
            row_rect = pygame.Rect(px+2, y, panel_w-4, 20)
            pygame.draw.rect(self.screen, bg, row_rect, border_radius=3)

            #
            ec = egg.base_color
            pygame.draw.circle(self.screen, ec, (px+12, y+10), 6)

            flags = ("[]" if egg.sealed else "") + ("[]" if egg.icy else "")
            info  = EGG_INFO[egg.type]
            nm_col = C_HIGHLIGHT if is_sel else C_WHITE
            nm = self.font_sm.render(f"{flags}{info['name']}", True, nm_col)
            self.screen.blit(nm, (px+22, y+3))
            #
            if egg.max_uses > 0:
                uses_col = (100,255,100) if egg.uses_left > 0 else (180,60,60)
                ut = self.font_sm.render(f"{egg.uses_left}/{egg.max_uses}", True, uses_col)
                self.screen.blit(ut, (px + panel_w - ut.get_width() - 4, y+3))
            y += 22

        #
        extra = len(alive) - max_lines
        if extra > 0:
            et = self.font_sm.render(f"+{extra}개 더", True, C_GRAY)
            self.screen.blit(et, (px+6, y+2))

    def _draw_log(self, gs: GameState):
        btn_zone_h = self.BTN_ZONE_H
        log_y = self._BB + btn_zone_h + 4
        log_h = self.h - log_y - 4
        if log_h < 20:
            return
        log_x = self.SIDE_PAD
        log_w = self.w - self.SIDE_PAD * 2

        pygame.draw.rect(self.screen, C_UI_BG,
                         (log_x, log_y, log_w, log_h), border_radius=6)
        pygame.draw.rect(self.screen, C_UI_BORDER,
                         (log_x, log_y, log_w, log_h), 1, border_radius=6)

        n_lines = max(1, log_h // 18)
        recent  = gs.logs[-n_lines:]
        for i, msg in enumerate(recent):
            brightness = min(255, 160 + i * 20)
            txt = self.font_sm.render(msg, True,
                                      (brightness, brightness, brightness))
            self.screen.blit(txt, (log_x+8, log_y+4+i*18))

    # --  --------------------------------------------------
    def _draw_gameover(self, gs: GameState):
        ov = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 160))
        self.screen.blit(ov, (0, 0))

        winner  = "P1 (파랑)" if gs.winner == 0 else "P2 (빨강)"
        col     = C_P1         if gs.winner == 0 else C_P2
        txt1 = self.font_xl.render(f"{winner} 승리!", True, col)
        txt2 = self.font_md.render("R: 재시작  |  ESC: 메뉴", True, C_GRAY)
        self.screen.blit(txt1, txt1.get_rect(center=(self.w//2, self.h//2-30)))
        self.screen.blit(txt2, txt2.get_rect(center=(self.w//2, self.h//2+30)))