# core/constants.py

SCREEN_W = 1920
SCREEN_H = 1080
FPS      = 60
TITLE    = "알까기 능력물"

# ── 물리 ─────────────────────────────────────────────
EGG_RADIUS      = 22
FRICTION        = 0.975          # 마찰 증가 (0.985→0.975)
RESTITUTION     = 0.85           # 반발계수 약간 올림
MIN_SPEED       = 0.08
MAX_LAUNCH_DIST = 160
LAUNCH_POWER    = 0.14           # 발사력 감소 (0.22→0.14)
ICE_SLIP_MULT   = 2.0
MAGNET_DIST     = 280
MAGNET_FORCE    = 0.45

# ── 보드 (update_layout으로 동적 설정) ───────────────
BOARD_LEFT   = 200
BOARD_TOP    = 110
BOARD_RIGHT  = 1720
BOARD_BOTTOM = 940
MID_X        = (BOARD_LEFT + BOARD_RIGHT) // 2

def update_layout(sw: int, sh: int):
    import core.constants as _c
    _c.SCREEN_W     = sw
    _c.SCREEN_H     = sh
    _c.BOARD_LEFT   = int(sw * 0.10)
    _c.BOARD_TOP    = int(sh * 0.12)
    _c.BOARD_RIGHT  = sw - int(sw * 0.10)
    _c.BOARD_BOTTOM = sh - int(sh * 0.17)
    _c.MID_X        = (_c.BOARD_LEFT + _c.BOARD_RIGHT) // 2

# ── 알 개수 ──────────────────────────────────────────
EGGS_PER_PLAYER = 5   # 기본 5개
MIN_EGGS        = 3   # 최소 3개
MAX_EGGS        = 10  # 최대 10개

# ── 색상 팔레트 ───────────────────────────────────────
C_BG          = (18,  22,  40)
C_BOARD       = (28,  32,  55)
C_LINE        = (60,  70, 110)
C_WHITE       = (255, 255, 255)
C_GRAY        = (140, 150, 170)
C_DARK        = ( 10,  12,  25)

C_P1     = ( 90, 140, 230)
C_P2     = (220,  80,  80)

EGG_COLORS = {
    "normal":   (110, 160, 240),
    "barrier":  ( 80, 200, 120),
    "seal":     (170,  80, 200),
    "copy":     (240, 200,  60),
    "clone":    (240, 140,  60),
    "bomb":     (230,  70,  50),
    "invisible":(160, 200, 220),
    "psycho":   (200,  60, 160),
    "ice":      (100, 220, 240),
    "magnet":   (180, 120, 240),
}

C_UI_BG     = ( 22,  26,  48)
C_UI_BORDER = ( 60,  70, 120)
C_BTN       = ( 50,  60, 100)
C_BTN_HOV   = ( 70,  85, 140)
C_BTN_ACT   = ( 90, 130, 220)
C_HIGHLIGHT = (255, 210,  50)
C_AIM_LINE  = (255, 255, 180)

EGG_INFO = {
    "normal":    {"name": "일반알",  "desc": "발사만 가능"},
    "barrier":   {"name": "방벽알",  "desc": "빈 칸에 방벽 생성"},
    "seal":      {"name": "봉인알",  "desc": "지정 알 행동 불가"},
    "copy":      {"name": "복사알",  "desc": "상대 능력/위력 복사"},
    "clone":     {"name": "분신알",  "desc": "분신 소환 후 섞임"},
    "bomb":      {"name": "폭탄알",  "desc": "빈 칸에 지뢰 설치"},
    "invisible": {"name": "투명알",  "desc": "투명화 + 발사"},
    "psycho":    {"name": "염력알",  "desc": "지정 알 파괴(자폭 포함)"},
    "ice":       {"name": "얼음알",  "desc": "지정 알 슬립 상태"},
    "magnet":    {"name": "자석알",  "desc": "두 알을 붙여서 당김"},
}

STATE_MENU        = "menu"
STATE_PLAY        = "play"
STATE_ABILITY     = "ability"
STATE_GAMEOVER    = "gameover"
STATE_HOWTOPLAY   = "howtoplay"
STATE_SETTINGS    = "settings"
STATE_MODE_SELECT = "mode_select"
STATE_EGG_SELECT  = "egg_select"

ACTION_SHOOT    = "shoot"
ACTION_ABILITY  = "ability"

MODE_SINGLE = "single"
MODE_MULTI  = "multi"