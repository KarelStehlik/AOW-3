import pyglet

CHEATS = True
display = pyglet.canvas.Display()
screen = display.get_default_screen()
SCREEN_WIDTH = screen.width  # //2
SCREEN_HEIGHT = screen.height  # //2
SPRITE_SIZE_MULT = SCREEN_WIDTH / 1920
UNIT_SIZE = 20
FPS = 60
INV_FPS = 1 / FPS
TH_DISTANCE = 3000
UNIT_FORMATION_ROWS = 8
UNIT_FORMATION_COLUMNS = 16
CHUNK_SIZE = 75
STARTING_MONEY = 500000000.0 if CHEATS else 0.0
PASSIVE_INCOME = 1
STARTING_MANA = 500000000.0 if CHEATS else 0.0
PASSIVE_MANA = .08
ACTION_DELAY = 1
WAVE_INTERVAL = 60 * 150
# size   fps
# 30     40
# 40     50
# 50     60
# 60     70
# 70     70
# 100    50
