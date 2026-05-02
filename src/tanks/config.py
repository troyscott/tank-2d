SCREEN_W = 1024
SCREEN_H = 640
FPS = 60

TERRAIN_ROUGHNESS = 0.6
TERRAIN_BASE_Y = int(SCREEN_H * 0.65)
TERRAIN_MAX_DISP = int(SCREEN_H * 0.30)
TERRAIN_MIN_Y = int(SCREEN_H * 0.30)
TERRAIN_MAX_Y = int(SCREEN_H * 0.90)

SKY_COLOR = (24, 32, 54)
TERRAIN_COLOR = (96, 72, 48)
TERRAIN_TOP_COLOR = (132, 168, 84)

PLAYER_X = 150
AI_X = SCREEN_W - 150
PLAYER_COLOR = (88, 156, 232)
AI_COLOR = (216, 88, 88)

TANK_BODY_W = 32
TANK_BODY_H = 10
TANK_TURRET_W = 16
TANK_TURRET_H = 8
TANK_BARREL_LEN = 22
TANK_BARREL_W = 4
DEFAULT_ANGLE_DEG = 60.0

GRAVITY = 400.0
WIND_RANGE = (-50.0, 50.0)  # px/s² horizontal, randomized per round
POWER_MIN = 100.0
POWER_MAX = 800.0
DEFAULT_POWER = 400.0
ANGLE_MIN = 0.0
ANGLE_MAX = 180.0

AI_TURN_DELAY = 0.8  # seconds AI takes between turn-start and firing
AI_DEFAULT_DIFFICULTY = "medium"

# After a projectile impact, hold the screen for this long so the player can
# see the crater + hear the bang before the next turn starts. Without this,
# turn transitions feel abrupt and audio doesn't line up with what's on
# screen.
IMPACT_SETTLE_DURATION = 0.55

ROUNDS_TO_WIN = 3  # best-of-5: first player to 3 round wins takes the match

AUDIO_SAMPLE_RATE = 22050
AUDIO_BUFFER = 512
AIM_TICK_INTERVAL = 0.08  # seconds between successive aim "tick" sounds

MENU_TITLE_FONT_SIZE = 56
MENU_LINE_FONT_SIZE = 26

ANGLE_RATE_DEG_PER_SEC = 60.0
POWER_RATE_PER_SEC = 300.0

PROJECTILE_RADIUS = 3
PROJECTILE_COLOR = (240, 220, 120)

TANK_HP = 100
EXPLOSION_RADIUS = 35.0
EXPLOSION_DAMAGE = 60.0

HP_BAR_W = TANK_BODY_W
HP_BAR_H = 3
HP_BAR_Y_OFFSET = 8
HP_BAR_BG_COLOR = (40, 40, 40)
TANK_DEAD_COLOR = (90, 90, 90)

HUD_FONT_SIZE = 20
HUD_COLOR = (240, 240, 240)
HUD_DIM_COLOR = (160, 160, 160)
ROUND_OVER_FONT_SIZE = 40
ROUND_OVER_COLOR = (245, 245, 245)
