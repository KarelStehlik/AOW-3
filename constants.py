import pyglet
display = pyglet.canvas.Display()
screen = display.get_default_screen()
SCREEN_WIDTH=screen.width
SCREEN_HEIGHT=screen.height
SPRITE_SIZE_MULT=SCREEN_WIDTH/1280
FPS=144