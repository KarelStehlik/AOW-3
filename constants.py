import pyglet

CHEATS = True
FACTION_LOCK=False
display = pyglet.canvas.Display()
screen = display.get_default_screen()
SCREEN_WIDTH = screen.width  # //2
SCREEN_HEIGHT = screen.height  # //2
SPRITE_SIZE_MULT = SCREEN_WIDTH / 1920
UNIT_SIZE = 20
FPS = 60
INV_FPS = 1 / FPS
TH_DISTANCE = 3000
UNIT_FORMATION_ROWS = 8  # *5
UNIT_FORMATION_COLUMNS = 15  # *5
CHUNK_SIZE = 64
INV_CHUNK_SIZE = 1 / CHUNK_SIZE
STARTING_MONEY = 50000000000 if CHEATS else 0
PASSIVE_INCOME = 1
STARTING_MANA = 50000000000 if CHEATS else 0
MAX_MANA = 50000000000 if CHEATS else 1500
PASSIVE_MANA = .08
ACTION_DELAY = 1
WAVE_INTERVAL = 60 * 75 **10
MAX_ANIMATIONS = 150
MOUNTAINRANGES =30
MOUNTAINS = 5
MOUNTAINSIZE = 400
MOUNTAINSIZE_VAR = 150
MOUNTAINSPREAD = 4000
MOUNTAIN_TH_DISTANCE = 750
MOUNTAIN_SLOWDOWN = 0.2
PATHING_CHUNK_SIZE = 10
# size   fps
# 30     40
# 40     50
# 50     60
# 60     70
# 70     70
# 100    50

# 30
