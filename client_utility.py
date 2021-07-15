from pyglet.gl import *

import groups
import images
from constants import *


def sprite_with_scale(img, scale, scale_x, scale_y, *args, **kwargs) -> pyglet.sprite.Sprite:
    a = pyglet.sprite.Sprite(img, *args, **kwargs)
    a.update(scale=scale, scale_x=scale_x, scale_y=scale_y)
    return a


class TextureEnableGroup(pyglet.graphics.OrderedGroup):
    def set_state(self):
        glEnable(GL_TEXTURE_2D)

    def unset_state(self):
        glDisable(GL_TEXTURE_2D)


texture_enable_groups = [TextureEnableGroup(i) for i in range(10)]


class TextureBindGroup(pyglet.graphics.Group):
    def __init__(self, texture, layer=0):
        super(TextureBindGroup, self).__init__(parent=texture_enable_groups[layer])
        self.texture = texture

    def set_state(self):
        glBindTexture(GL_TEXTURE_2D, self.texture.id)

    # No unset_state method required.
    def __eq__(self, other):
        return (self.__class__ is other.__class__ and
                self.texture.id == other.texture.id and
                self.texture.target == other.texture.target and
                self.parent == other.parent)

    def __hash__(self):
        return hash((self.texture.id, self.texture.target))


wall_group = TextureBindGroup(images.Wall, layer=1)
wall_crack_group = TextureBindGroup(images.WallCrack, layer=2)


class button:
    def __init__(self, func, x, y, width, height, batch, image=images.Button, text="", args=(), layer=5):
        self.sprite = pyglet.sprite.Sprite(image, x=x + width / 2, y=y + height / 2, batch=batch, group=groups.g[layer])
        self.layer = layer
        self.sprite.scale_x = width / self.sprite.width
        self.sprite.scale_y = height / self.sprite.height
        self.func = func
        self.fargs = args
        self.batch = batch
        self.x, self.y, self.width, self.height = x, y, width, height
        self.ogx, self.ogy = x, y
        self.text = pyglet.text.Label(text, x=self.x + self.width // 2,
                                      y=self.y + self.height * 4 / 7, color=(255, 255, 0, 255),
                                      batch=batch, group=groups.g[layer+1], font_size=int(SPRITE_SIZE_MULT * self.height / 2),
                                      anchor_x="center", align="center", anchor_y="center")
        self.down = False
        self.big = 0

    def set_image(self, img):
        self.sprite = pyglet.sprite.Sprite(img, x=self.x + self.width / 2, y=self.y + self.height / 2, batch=self.batch,
                                           group=groups.g[self.layer])
        self.sprite.scale_x = self.width / self.sprite.width
        self.sprite.scale_y = self.height / self.sprite.height

    def embiggen(self):
        self.big = 1
        self.sprite.scale = 1.1

    def unbiggen(self):
        self.big = 0
        self.sprite.scale = 1

    def smallen(self):
        self.big = -1
        self.sprite.scale = 0.9

    def update(self, x, y):
        self.sprite.update(x=x+self.width / 2, y=y + self.height / 2)
        self.x, self.y = x, y
        self.text.x = x + self.width // 2
        self.text.y = y + self.height * 4 / 7

    def mouse_move(self, x, y):
        if not self.down:
            if (self.big == 1) == (self.x + self.width >= x >= self.x and self.y + self.height >= y >= self.y):
                return
            if self.big != 1:
                self.embiggen()
                return
            self.unbiggen()

    def mouse_click(self, x, y):
        if self.x + self.width >= x >= self.x and self.y + self.height >= y >= self.y:
            self.smallen()
            self.down = True
            return True
        return False

    def mouse_release(self, x, y):
        if self.down:
            self.down = False
            self.unbiggen()
            if self.x + self.width >= x >= self.x and self.y + self.height >= y >= self.y:
                self.func(*self.fargs)

    def delete(self):
        self.sprite.delete()
        self.text.delete()


class toolbar:
    def __init__(self, x, y, width, height, batch, image=images.Toolbar, layer=6):
        if image is not None:
            self.sprite = pyglet.sprite.Sprite(image, x=x, y=y, batch=batch, group=groups.g[layer])
            self.layer = layer
            self.sprite.scale_x = width / self.sprite.width
            self.sprite.scale_y = height / self.sprite.height
        else:
            self.sprite = None
        self.x, self.y, self.width, self.height = x, y, width, height
        self.batch = batch
        self.buttons = []

    def add(self, func, x, y, width, height, image=images.Button, text="", args=()) -> button:
        a = button(func, x, y, width, height, self.batch,
                   image=image, text=text, args=args, layer=self.layer + 1)
        self.buttons.append(a)
        return a

    def delete(self):
        [e.delete() for e in self.buttons]
        if self.sprite is not None:
            self.sprite.delete()

    def mouse_click(self, x, y):
        if self.x + self.width >= x >= self.x and self.y + self.height >= y >= self.y:
            [e.mouse_click(x, y) for e in self.buttons]
            return True
        return False

    def mouse_move(self, x, y):
        if self.x + self.width >= x >= self.x and self.y + self.height >= y >= self.y:
            [e.mouse_move(x, y) for e in self.buttons]
        else:
            for e in self.buttons:
                if e.big==1 or e.big == -1:
                    e.unbiggen()

    def mouse_drag(self, x, y):
        if self.x + self.width >= x >= self.x and self.y + self.height >= y >= self.y:
            [e.mouse_move for e in self.buttons]
            return True
        return False

    def mouse_release(self, x, y):
        [e.mouse_release(x, y) for e in self.buttons]
