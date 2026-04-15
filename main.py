# main.py
"""
조작법:
    [발사 모드]  자신의 알을 클릭 → 드래그 → 발사
    [능력 모드]  알 선택 후 '능력 사용' 버튼, 이후 안내에 따라 클릭
    R: 재시작 / ESC: 종료
"""
import sys
import pygame

from core.constants  import update_layout, FPS, TITLE, STATE_GAMEOVER
from core.game_state import GameState
from ui.renderer     import Renderer
from ui.buttons      import make_action_buttons
from ui.input_handler import InputHandler


def main():
    pygame.init()

    # 전체 화면
    info = pygame.display.Info()
    sw, sh = info.current_w, info.current_h
    screen = pygame.display.set_mode((sw, sh), pygame.FULLSCREEN)
    pygame.display.set_caption(TITLE)

    # 보드 레이아웃을 실제 해상도에 맞게 업데이트
    update_layout(sw, sh)

    clock   = pygame.time.Clock()
    gs      = GameState()
    renderer = Renderer(screen)
    buttons  = make_action_buttons()
    handler  = InputHandler(buttons)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            handler.handle_event(event, gs, renderer)

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