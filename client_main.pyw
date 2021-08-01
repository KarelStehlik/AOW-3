from PodSixNet.Connection import connection, ConnectionListener

import constants
import game_client as game_stuff
import groups
import images
import client_utility
from imports import *

pyglet.options['debug_gl'] = False
pyglet.gl.glEnable(pyglet.gl.GL_BLEND)

connection.DoConnect(('192.168.1.237', 5071))


#connection.DoConnect(('127.0.0.1', 5071))


class MyNetworkListener(ConnectionListener):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.start = False
        self.mode = None

    def set_mode(self, m):
        self.mode = m

    def Network(self, data):
        # print(data)
        self.mode.network(data)


nwl = MyNetworkListener()


class mode:
    def __init__(self, win, batch):
        self.batch = batch
        self.mousex = self.mousey = 0
        self.win = win

    def mouse_move(self, x, y, dx, dy):
        self.mousex = x
        self.mousey = y

    def mouse_drag(self, x, y, dx, dy, button, modifiers):
        self.mouse_move(x, y, dx, dy)

    def tick(self):
        pass

    def key_press(self, symbol, modifiers):
        pass

    def key_release(self, symbol, modifiers):
        pass

    def resize(self, width, height):
        pass

    def mouse_press(self, x, y, button, modifiers):
        pass

    def mouse_release(self, x, y, button, modifiers):
        pass

    def mouse_scroll(self, x, y, scroll_x, scroll_y):
        pass


class mode_intro(mode):
    def __init__(self, win, batch, nwl):
        super().__init__(win, batch)
        nwl.set_mode(self)
        self.buttons = []
        self.buttons.append(
            client_utility.button(self.join, constants.SCREEN_WIDTH * 2 / 5, constants.SCREEN_HEIGHT / 3,
                                  constants.SCREEN_WIDTH * 1 / 5, constants.SCREEN_HEIGHT / 7, batch, text="Play"))
        self.bg = pyglet.sprite.Sprite(images.Intro, x=0, y=0, group=groups.g[0], batch=batch)
        self.bg.scale_x, self.bg.scale_y = constants.SCREEN_WIDTH / self.bg.width, constants.SCREEN_HEIGHT / self.bg.height
        self.joined = False

    def mouse_press(self, x, y, button, modifiers):
        [e.mouse_click(x, y) for e in self.buttons]

    def mouse_release(self, x, y, button, modifiers):
        [e.mouse_release(x, y) for e in self.buttons]

    def mouse_move(self, x, y, dx, dy):
        self.mousex = x
        self.mousey = y
        [e.mouse_move(x, y) for e in self.buttons]

    def join(self):
        print(time.time())
        if not self.joined:
            connection.Send({"action": "join"})
            self.joined = True

    def mouse_drag(self, x, y, dx, dy, button, modifiers):
        self.mouse_move(x, y, dx, dy)

    def tick(self):
        super().tick()
        self.batch.draw()

    def end(self):
        self.bg.delete()
        while len(self.buttons) >= 1:
            self.buttons.pop(0).delete()

    def network(self, data):
        if "action" in data and data["action"] == "start_game":
            newgame = game_stuff.Game(data["side"], self.batch, connection, float(data["time0"]))
            self.end()
            self.win.start_game(newgame)


class mode_main(mode):
    def __init__(self, win, batch, nwl, game):
        super().__init__(win, batch)
        nwl.set_mode(self)
        self.game = game

    def tick(self):
        self.game.tick()
        super().tick()

    def network(self, data):
        self.game.network(data)

    def mouse_move(self, x, y, dx, dy):
        self.game.mouse_move(x, y, dx, dy)

    def mouse_drag(self, x, y, dx, dy, button, modifiers):
        self.game.mouse_drag(x, y, dx, dy, button, modifiers)

    def key_press(self, symbol, modifiers):
        self.game.key_press(symbol, modifiers)

    def key_release(self, symbol, modifiers):
        self.game.key_release(symbol, modifiers)

    def mouse_press(self, x, y, button, modifiers):
        self.game.mouse_press(x, y, button, modifiers)

    def mouse_release(self, x, y, button, modifiers):
        self.game.mouse_release(x, y, button, modifiers)

    def mouse_scroll(self, x, y, scroll_x, scroll_y):
        self.game.mouse_scroll(x, y, scroll_x, scroll_y)


class windoo(pyglet.window.Window):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.nwl = nwl
        self.batch = pyglet.graphics.Batch()
        self.sec = time.time()
        self.frames = 0
        self.fpscount = pyglet.text.Label(x=5, y=5, text="0", color=(255, 255, 255, 255),
                                          group=groups.g[9], batch=self.batch)
        self.mouseheld = False
        self.current_mode = mode_intro(self, self.batch, self.nwl)
        self.keys = key.KeyStateHandler()
        self.push_handlers(self.keys)
        self.last_tick = time.time()

    def start_game(self, game):
        self.current_mode = mode_main(self, self.batch, self.nwl, game)

    def on_mouse_motion(self, x, y, dx, dy):
        self.current_mode.mouse_move(x, y, dx, dy)

    def on_mouse_drag(self, x, y, dx, dy, button, modifiers):
        self.current_mode.mouse_drag(x, y, dx, dy, button, modifiers)

    def on_close(self):
        self.close()
        connection.close()
        os._exit(0)

    def error_close(self):
        self.close()
        connection.close()

    def tick(self):
        self.dispatch_events()
        self.check()
        self.switch_to()
        self.clear()
        self.current_mode.tick()
        self.flip()
        self.last_tick = time.time()

    def on_key_press(self, symbol, modifiers):
        self.current_mode.key_press(symbol, modifiers)

    def on_key_release(self, symbol, modifiers):
        self.current_mode.key_release(symbol, modifiers)

    def on_mouse_release(self, x, y, button, modifiers):
        self.mouseheld = False
        self.current_mode.mouse_release(x, y, button, modifiers)

    def on_mouse_press(self, x, y, button, modifiers):
        self.mouseheld = True
        self.current_mode.mouse_press(x, y, button, modifiers)

    def on_mouse_scroll(self, x, y, scroll_x, scroll_y):
        self.current_mode.mouse_scroll(x, y, scroll_x, scroll_y)

    # def on_deactivate(self):
    #    self.minimize()

    def check(self):
        self.frames += 1
        if time.time() - self.sec >= 1:
            self.sec += 1
            self.fpscount.text = str(self.frames)
            self.frames = 0


# place = windoo(caption='test', fullscreen=True)
place = windoo(caption='test', style=pyglet.window.Window.WINDOW_STYLE_BORDERLESS, width=constants.SCREEN_WIDTH,
               height=constants.SCREEN_HEIGHT)
place.set_location(0, 0)

while True:
    try:
        connection.Pump()
        place.nwl.Pump()
        place.tick()
    except Exception as e:
        place.error_close()
        raise e
