import pyglet

display = pyglet.canvas.Display()
screen = display.get_default_screen()
SCREEN_WIDTH = screen.width  # //2
SCREEN_HEIGHT = screen.height  # //2
SPRITE_SIZE_MULT = SCREEN_WIDTH / 1920
UNIT_SIZE = 20
FPS = 60
TH_DISTANCE = 1000
UNIT_FORMATION_ROWS = 10
UNIT_FORMATION_COLUMNS = 20
CHUNK_SIZE = 75
PASSIVE_INCOME = 1
ACTION_DELAY = 1
WAVE_INTERVAL=600
# size   fps
# 30     40
# 40     50
# 50     60
# 60     70
# 70     70
# 100    50
