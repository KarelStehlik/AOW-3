from pyglet.gl import *

import groups
import images
import random
from constants import *
import math


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
necro_beam_group = TextureBindGroup(images.Beam, layer=1)


def do_nothing(*args):
    pass


class button:
    def __init__(self, func, x, y, width, height, batch, image=images.Button, text="", args=(), layer=5,
                 mouseover=do_nothing, mouseoff=do_nothing, mover_args=(), moff_args=()):
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
                                      batch=batch, group=groups.g[layer + 1], font_size=int(self.height / 2),
                                      anchor_x="center", align="center", anchor_y="center")
        self.down = False
        self.big = 0
        self.on_mouse_over = mouseover
        self.on_mouse_off = mouseoff
        self.mover_args = mover_args
        self.moff_args = moff_args

    def hide(self):
        self.text.batch = None
        self.sprite.batch = None

    def show(self):
        self.text.batch = self.batch
        self.sprite.batch = self.batch

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
        self.sprite.update(x=x + self.width / 2, y=y + self.height / 2)
        self.x, self.y = x, y
        self.text.x = x + self.width // 2
        self.text.y = y + self.height * 4 / 7

    def mouse_move(self, x, y):
        if not self.down:
            if (self.big == 1) == (self.x + self.width >= x >= self.x and self.y + self.height >= y >= self.y):
                return
            if self.big != 1:
                self.mouse_over()
                return
            self.mouse_off()

    def mouse_over(self):
        self.embiggen()
        self.on_mouse_over(*self.mover_args)

    def mouse_off(self):
        self.unbiggen()
        self.on_mouse_off(*self.moff_args)

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
        self.layer = layer
        if image is not None:
            self.sprite = pyglet.sprite.Sprite(image, x=x, y=y, batch=batch, group=groups.g[layer])
            self.sprite.scale_x = width / self.sprite.width
            self.sprite.scale_y = height / self.sprite.height
        else:
            self.sprite = None
        self.x, self.y, self.width, self.height = x, y, width, height
        self.batch = batch
        self.buttons = []

    def hide(self):
        [e.hide() for e in self.buttons]
        if self.sprite is not None:
            self.sprite.batch = None

    def show(self):
        [e.show() for e in self.buttons]
        if self.sprite is not None:
            self.sprite.batch = self.batch

    def add(self, func, x, y, width, height, image=images.Button, text="", args=(),
            mouseover=do_nothing, mouseoff=do_nothing, layer=1, mover_args=(), moff_args=()) -> button:
        a = button(func, x, y, width, height, self.batch,
                   image=image, text=text, args=args, layer=self.layer + layer, mouseover=mouseover, mouseoff=mouseoff,
                   mover_args=mover_args, moff_args=moff_args)
        self.buttons.append(a)
        return a

    def delete(self):
        [e.delete() for e in self.buttons]
        if self.sprite is not None:
            self.sprite.delete()

    def mouse_click(self, x, y, button=0, modifiers=0):
        if self.x + self.width >= x >= self.x and self.y + self.height >= y >= self.y:
            [e.mouse_click(x, y) for e in self.buttons]
            return True
        return False

    def mouse_move(self, x, y):
        if self.x + self.width >= x >= self.x and self.y + self.height >= y >= self.y:
            [e.mouse_move(x, y) for e in self.buttons]
        else:
            for e in self.buttons:
                if e.big == 1 or e.big == -1:
                    e.mouse_off()

    def mouse_drag(self, x, y, button=0, modifiers=0):
        if self.x + self.width >= x >= self.x and self.y + self.height >= y >= self.y:
            [e.mouse_move(x, y) for e in self.buttons]
            return True
        return False

    def mouse_release(self, x, y, button=0, modifiers=0):
        [e.mouse_release(x, y) for e in self.buttons]


class animation(pyglet.sprite.Sprite):
    img = images.Explosion2
    standalone = False
    layer=5

    def __init__(self, x, y, size, game, img=None, group=None, loop=False, duration=1):
        if self.standalone and len(game.animations) > MAX_ANIMATIONS:
            return
        super().__init__(self.img if img is None else img, x=x * SPRITE_SIZE_MULT - game.camx,
                         y=y * SPRITE_SIZE_MULT - game.camy,
                         batch=game.batch, group=groups.g[group if group is not None else self.layer])
        self.rotation = random.randint(0, 360)
        self.scale = size / (self.img if img is None else img).get_max_width()
        self.true_x, self.true_y = x, y
        self.game = game
        if self.standalone:
            game.animations.append(self)
        self.exists = True
        self.anim_time = 0
        self.max_duration = duration
        self.anim_frames = len(self.image.frames) - 1
        self.frame_duration = self.max_duration / self.anim_frames
        self.loop=loop


    def tick(self, dt):
        if not self.exists:
            return
        if dt > .5:
            self.delete()
            return
        self.update(x=self.true_x * SPRITE_SIZE_MULT - self.game.camx,
                    y=self.true_y * SPRITE_SIZE_MULT - self.game.camy)
        self.anim_time += dt
        frames = math.floor(self.anim_time / self.frame_duration)
        self.anim_time-=frames*self.frame_duration
        if frames==0:
            return
        self._frame_index += frames
        if self._frame_index >= len(self._animation.frames):
            self._frame_index = 0
            self.dispatch_event('on_animation_end')
            if self._vertex_list is None:
                return  # Deleted in event handler.
        frame = self._animation.frames[self._frame_index]
        self._set_texture(frame.image.get_texture())
        if frame.duration is None:
            self.dispatch_event('on_animation_end')

    def on_animation_end(self):
        if not self.exists or self.loop:
            return
        self.delete()

    def delete(self):
        if not self.exists:
            return
        self.exists = False
        if self.standalone:
            self.game.animations.remove(self)
        super().delete()

def dict_to_string(d):
    result=""
    for key,value in d.items():
        if result:
            result+=", "
        if isinstance(value,float):
            v=int(value)
        else:
            v=value
        result+=f"{key}: {v}"
    return result