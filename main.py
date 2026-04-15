# main.py
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
            renderer.render(gs)
            handler.update_hover(gs)
            handler.draw_buttons(screen, gs)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()