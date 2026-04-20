def _apply_ai_action(gs, action: dict, renderer=None):
    """AI 행동을 GameState에 적용."""
    from core.abilities import (
        ability_barrier, ability_seal, ability_clone,
        ability_bomb, ability_invisible, ability_psycho,
        ability_ice, ability_magnet, ability_copy_ability,
    )
    from core.constants import STATE_PLAY, STATE_GAMEOVER

    atype = action.get("type")

    if atype == "shoot":
        egg = action.get("egg")
        if egg is None or not egg.active:
            return
        vx = action.get("vx", 0)
        vy = action.get("vy", 0)
        gs.try_shoot(egg, vx, vy)

    elif atype == "ability":
        egg    = action.get("egg")
        params = action.get("params", {})
        if egg is None or not egg.active or egg.sealed:
            return

        ptype = params.get("type")

        if ptype == "instant":
            # clone, invisible
            t = egg.type
            if t == "clone":
                ok, msg = ability_clone(egg, gs.eggs)
                if ok:
                    gs.log(msg)
                    gs._end_ability_turn()
            elif t == "invisible":
                ok, msg = ability_invisible(egg)
                if ok:
                    gs.log(msg)
                    # 투명화 후 바로 발사
                    gs.phase       = STATE_PLAY
                    gs.action_mode = "shoot"
                    gs.ability_egg = None
                    gs._next_turn()

        elif ptype == "pos":
            x, y = params["x"], params["y"]
            t = egg.type
            if t == "barrier":
                ok, msg = ability_barrier(egg, x, y, gs.eggs, gs.barriers)
                if ok:
                    gs.log(msg)
                    gs._end_ability_turn()
            elif t == "bomb":
                ok, msg = ability_bomb(egg, x, y, gs.eggs, gs.barriers, gs.mines)
                if ok:
                    gs.log(msg)
                    gs._end_ability_turn()

        elif ptype == "egg":
            target = params.get("target")
            if target is None or not target.active:
                return
            t = egg.type
            if t == "seal":
                ok, msg = ability_seal(egg, target)
                if ok:
                    gs.log(msg)
                    gs._end_ability_turn()
            elif t == "psycho":
                ok, msg = ability_psycho(egg, target, gs.eggs)
                if ok:
                    gs.log(msg)
                    gs._end_ability_turn()
            elif t == "ice":
                ok, msg = ability_ice(egg, target)
                if ok:
                    gs.log(msg)
                    gs._end_ability_turn()
            elif t == "copy":
                ok, msg = ability_copy_ability(egg, target)
                if ok:
                    gs.log(msg)
                    gs._end_ability_turn()

        elif ptype == "two_eggs":
            a = params.get("a")
            b = params.get("b")
            if a is None or b is None or not a.active or not b.active:
                return
            ok, msg = ability_magnet(egg, a, b)
            if ok:
                gs.log(msg)
                gs.simulating = True
                gs._end_ability_turn_keep_sim()


"""
알까기 능력물 – 메인 엔트리
화면 흐름: 홈 → 모드선택 → 알선택 → 게임 플레이
           홈 → 설명 / 설정
"""
import sys
import pygame

from core.constants  import (update_layout, FPS, TITLE,
                              STATE_GAMEOVER,
                              STATE_MENU, STATE_HOWTOPLAY, STATE_SETTINGS,
                              STATE_MODE_SELECT, STATE_EGG_SELECT, STATE_PLAY)
from core.game_state import GameState
from core.ai_player  import AIPlayer
from ui.renderer      import Renderer
from ui.buttons       import make_action_buttons
from ui.input_handler import InputHandler
from ui.menu_screen   import MenuScreen
from ui.howto_screen  import HowToPlayScreen
from ui.settings_screen import SettingsScreen
from ui.mode_select_screen import ModeSelectScreen
from ui.egg_select_screen  import EggSelectScreen


def main():
    pygame.init()

    info = pygame.display.Info()
    sw, sh = info.current_w, info.current_h
    screen = pygame.display.set_mode((sw, sh), pygame.FULLSCREEN)
    pygame.display.set_caption(TITLE)

    update_layout(sw, sh)

    clock = pygame.time.Clock()

    app_state = STATE_MENU

    menu_scr       = MenuScreen(screen)
    howto_scr      = HowToPlayScreen(screen)
    settings_scr   = SettingsScreen(screen)
    mode_scr       = ModeSelectScreen(screen)
    egg_scr        = None
    selected_mode  = None

    gs       = GameState()
    renderer = Renderer(screen)
    buttons  = make_action_buttons()
    handler  = InputHandler(buttons)
    ai       = AIPlayer(owner=1)

    running = True
    while running:
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE and app_state == STATE_PLAY:
                    app_state = STATE_MENU
                    continue
                if event.key == pygame.K_r and app_state == STATE_PLAY:
                    gs.reset()
                    ai.reset()
                    continue

            if app_state == STATE_MENU:
                result = menu_scr.handle_event(event)
                if result == "quit":
                    running = False
                elif result == "howto":
                    howto_scr = HowToPlayScreen(screen)
                    app_state = STATE_HOWTOPLAY
                elif result == "settings":
                    settings_scr = SettingsScreen(screen)
                    app_state = STATE_SETTINGS
                elif result == "start":
                    mode_scr = ModeSelectScreen(screen)
                    app_state = STATE_MODE_SELECT

            elif app_state == STATE_HOWTOPLAY:
                if howto_scr.handle_event(event):
                    app_state = STATE_MENU

            elif app_state == STATE_SETTINGS:
                if settings_scr.handle_event(event):
                    app_state = STATE_MENU

            elif app_state == STATE_MODE_SELECT:
                result = mode_scr.handle_event(event)
                if result == "back":
                    app_state = STATE_MENU
                elif result in ("single", "multi"):
                    selected_mode = result
                    egg_scr = EggSelectScreen(screen, selected_mode)
                    app_state = STATE_EGG_SELECT

            elif app_state == STATE_EGG_SELECT:
                result = egg_scr.handle_event(event)
                if result == "back":
                    app_state = STATE_MODE_SELECT
                elif isinstance(result, dict):
                    gs.reset(game_config=result)
                    renderer = Renderer(screen)
                    buttons  = make_action_buttons()
                    handler  = InputHandler(buttons)
                    ai       = AIPlayer(owner=1)
                    app_state = STATE_PLAY

            elif app_state == STATE_PLAY:
                handler.handle_event(event, gs, renderer)

        if app_state == STATE_MENU:
            menu_scr.draw()
        elif app_state == STATE_HOWTOPLAY:
            howto_scr.draw()
        elif app_state == STATE_SETTINGS:
            settings_scr.draw()
        elif app_state == STATE_MODE_SELECT:
            mode_scr.draw()
        elif app_state == STATE_EGG_SELECT:
            egg_scr.draw()
        elif app_state == STATE_PLAY:
            gs.update_physics()

            # ── AI 턴 처리 (싱글모드, P2 차례, 시뮬레이션 없을 때) ──
            if (gs.game_mode == "single"
                    and gs.turn == 1
                    and not gs.simulating
                    and gs.phase not in ("gameover", "ability")):
                action = ai.decide(gs)
                if action is not None:
                    _apply_ai_action(gs, action, renderer)

            renderer.render(gs)
            handler.update_hover(gs)
            handler.draw_buttons(screen, gs)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()