import pyglet
import os
from pyglet.window import key
import time
import constants
import images
import groups
import random
from PIL import Image
from numba import njit

pyglet.gl.glClearColor(0, 0, 0, 255)


@njit
def transparency(R, G, B):
    m = max((R, G, B))
    if m == 0:
        return [0, 0, 0, 0]
    return [int(R * 255 / m), int(G * 255 / m), int(B * 255 / m), int(m)]


transparency(1, 1, 1)


def remove_bg(dat1):
    dat2 = []
    for i in range(int(len(dat1) / 4)):
        dat2 += transparency(*dat1[4 * i:4 * i + 3])
    return dat2


def make_image(dat1, name, index):
    dat2 = remove_bg(dat1)
    R = Image.new("L", (constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    G = Image.new("L", (constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    B = Image.new("L", (constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    A = Image.new("L", (constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    R.putdata(dat2[0::4])
    G.putdata(dat2[1::4])
    B.putdata(dat2[2::4])
    A.putdata(dat2[3::4])
    result = Image.merge("RGBA", (R, G, B, A)).transpose(Image.FLIP_TOP_BOTTOM)
    return result


class windoo(pyglet.window.Window):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.folder_name = "test"
        self.batch = pyglet.graphics.Batch()
        self.sec = time.time()
        self.frames = 0
        self.mouseheld = False
        self.keys = key.KeyStateHandler()
        self.push_handlers(self.keys)
        self.last_tick = time.time()
        self.batch = pyglet.graphics.Batch()
        self.animations = []
        self.ticks = 0
        self.done = False
        self.open = True
        self.recording = True

    def on_mouse_motion(self, x, y, dx, dy):
        pass

    def on_mouse_drag(self, x, y, dx, dy, button, modifiers):
        pass

    def on_close(self):
        self.open = False
        self.close()

    def error_close(self):
        self.close()

    def tick(self):
        self.dispatch_events()
        if not self.done:
            self.switch_to()
            pyglet.gl.glEnable(pyglet.gl.GL_BLEND)
            self.clear()
            [e.tick() for e in self.animations]
            self.batch.draw()
            if self.recording:
                a = pyglet.image.get_buffer_manager().get_color_buffer().get_image_data()
                dat1 = list(a.get_data("RGBA", 4 * a.width))
                i = make_image(dat1, "imagefolder/test/t", self.ticks)
                i.save("imagefolder/test/t" + str(self.ticks)+".png", "png")
            else:
                time.sleep(1/144)
            self.ticks += 1
            self.flip()
            self.last_tick = time.time()
            if not self.animations:
                self.done = True
        else:
            print("done")
            self.close()
            os._exit(0)
            return

    def on_key_press(self, symbol, modifiers):
        pass

    def on_key_release(self, symbol, modifiers):
        pass

    def on_mouse_release(self, x, y, button, modifiers):
        self.mouseheld = False

    def on_mouse_press(self, x, y, button, modifiers):
        self.mouseheld = True

    def on_mouse_scroll(self, x, y, scroll_x, scroll_y):
        pass


class animation_explosion:
    def __init__(self, x, y, size, speed, win):
        self.sprite = pyglet.sprite.Sprite(images.Fire, x=x,
                                           y=y,
                                           batch=win.batch, group=groups.g[6])
        self.sprite2 = pyglet.sprite.Sprite(images.Shockwave, x=x,
                                            y=y,
                                            batch=win.batch, group=groups.g[5])
        self.sprite.rotation = random.randint(0, 360)
        self.sprite.scale = 0
        self.x, self.y = x, y
        self.window = win
        self.size, self.speed = size, speed
        self.exists_time = 0
        win.animations.append(self)

    def tick(self):
        self.exists_time += self.speed
        if self.exists_time > 128:
            self.delete()
            return
        self.sprite.update(x=self.x, y=self.y,
                           scale=self.exists_time / 128 * self.size / images.Fire.width)
        self.sprite2.update(x=self.x, y=self.y,
                            scale=self.exists_time ** 1.6 / 256 * self.size / images.Shockwave.width)
        self.sprite.opacity = (256 - 2 * self.exists_time)
        self.sprite2.opacity = (256 - 2 * self.exists_time) * 0.6

    def delete(self):
        self.window.animations.remove(self)
        self.sprite.delete()
        self.sprite2.delete()

class animation_frost:
    def __init__(self, x, y, size, speed, win):
        self.sprite = pyglet.sprite.Sprite(images.Freeze, x=x,
                                           y=y,
                                           batch=win.batch, group=groups.g[6])
        self.sprite.rotation = random.randint(0, 360)
        self.sprite.scale = constants.SCREEN_HEIGHT/self.sprite.height*.95
        self.x, self.y = x, y
        self.window = win
        self.size, self.speed = size, speed
        self.exists_time = 0
        win.animations.append(self)

    def tick(self):
        self.exists_time += self.speed
        if self.exists_time > 128:
            self.delete()
            return
        self.sprite.update(x=self.x, y=self.y)
        self.sprite.opacity = (256 - 2 * self.exists_time)

    def delete(self):
        self.window.animations.remove(self)
        self.sprite.delete()


def main():
    place = windoo(caption='test', style=pyglet.window.Window.WINDOW_STYLE_BORDERLESS, width=constants.SCREEN_WIDTH,
                   height=constants.SCREEN_HEIGHT)

    animation_frost(constants.SCREEN_WIDTH / 2, constants.SCREEN_HEIGHT / 2, 500, 20, place)

    while place.open:
        try:
            place.tick()
        except Exception as e:
            place.error_close()
            raise e


if __name__ == '__main__':
    main()
