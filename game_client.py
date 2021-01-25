from imports import *
import groups
from constants import *
import images
from client_utility import button, toolbar, TextureBindGroup


class Game:
    def __init__(self, side, batch, connection, time0):
        self.side, self.batch = side, batch
        self.players = [player(), player()]
        self.connection = connection
        self.batch = batch
        self.cam_move_speed = 3
        self.start_time = time0
        self.ticks = 0
        print(time.time(), self.start_time)
        self.camx, self.camy = 0, 0
        self.camx_moving, self.camy_moving = 0, 0
        self.background_texgroup = TextureBindGroup(images.Background, layer=0)
        self.background = batch.add(
            4, pyglet.gl.GL_QUADS, self.background_texgroup,
            ("v2i", (0, 0, SCREEN_WIDTH, 0,
                     SCREEN_WIDTH, SCREEN_HEIGHT, 0, SCREEN_HEIGHT)),
            ("t2f", (0, 0, SCREEN_WIDTH / 512, 0, SCREEN_WIDTH / 512, SCREEN_HEIGHT / 512,
                     0, SCREEN_HEIGHT / 512))
        )
        self.UI_bottomBar = UI_bottom_bar(self)
        self.UI_categories = UI_categories(self, self.UI_bottomBar)
        self.UI_toolbars = [self.UI_bottomBar, self.UI_categories]
        self.selected = selection_none(self)
        self.unit_formation_rows = 5
        self.unit_formation_columns = 10
        self.unit_formation = UI_formation(self)

    def select(self, sel):
        self.selected.end()
        self.selected = sel(self)

    def tick(self):
        while self.ticks < FPS * (time.time() - self.start_time):
            self.players[0].tick()
            self.players[1].tick()
            self.ticks += 1
        self.update_cam()
        self.batch.draw()

    def network(self, data):
        if "action" in data:
            if data["action"] == "place_tower":
                Tower(data["ID"], data["xy"][0], data["xy"][1], data["side"], self)
            elif data["action"] == "place_wall":
                Wall(data["ID"], self.find_tower(data["ID1"], data["side"]),
                     self.find_tower(data["ID2"], data["side"]), data["side"], self)

    def mouse_move(self, x, y, dx, dy):
        [e.mouse_move(x, y) for e in self.UI_toolbars]
        self.selected.mouse_move(x, y)

    def mouse_drag(self, x, y, dx, dy, button, modifiers):
        pass

    def key_press(self, symbol, modifiers):
        if symbol == key.A:
            self.camx_moving = max(self.camx_moving - self.cam_move_speed, -self.cam_move_speed)
        elif symbol == key.S:
            self.camy_moving = max(self.camy_moving - self.cam_move_speed, -self.cam_move_speed)
        elif symbol == key.D:
            self.camx_moving = min(self.camx_moving + self.cam_move_speed, self.cam_move_speed)
        elif symbol == key.W:
            self.camy_moving = min(self.camy_moving + self.cam_move_speed, self.cam_move_speed)

    def key_release(self, symbol, modifiers):
        if symbol == key.D:
            self.camx_moving = max(self.camx_moving - self.cam_move_speed, -self.cam_move_speed)
        elif symbol == key.W:
            self.camy_moving = max(self.camy_moving - self.cam_move_speed, -self.cam_move_speed)
        elif symbol == key.A:
            self.camx_moving = min(self.camx_moving + self.cam_move_speed, self.cam_move_speed)
        elif symbol == key.S:
            self.camy_moving = min(self.camy_moving + self.cam_move_speed, self.cam_move_speed)

    def mouse_press(self, x, y, button, modifiers):
        if True in [e.mouse_click(x, y) for e in self.UI_toolbars]:
            return
        self.selected.mouse_click(x, y)

    def mouse_release(self, x, y, button, modifiers):
        [e.mouse_release(x, y) for e in self.UI_toolbars]
        self.selected.mouse_release(x, y)

    def mouse_scroll(self, x, y, scroll_x, scroll_y):
        pass

    def update_cam(self):
        self.camx += self.camx_moving
        self.camy += self.camy_moving
        x, y = self.camx / 512, self.camy / 512
        self.background.tex_coords = (x, y, x + SCREEN_WIDTH / 512, y, x + SCREEN_WIDTH / 512,
                                      y + SCREEN_HEIGHT / 512, x, y + SCREEN_HEIGHT / 512)
        [e.update_cam(self.camx, self.camy) for e in self.players]
        self.selected.update_cam(self.camx, self.camy)

    def find_tower(self, ID, side):
        for e in self.players[side].towers:
            if e.ID == ID:
                return e
        return None

    def find_wall(self, ID, side):
        for e in self.players[side].walls:
            if e.ID == ID:
                return e
        return None

    def find_unit(self, ID, side):
        for e in self.players[side].units:
            if e.ID == ID:
                return e
        return None


class UI_bottom_bar(toolbar):
    def __init__(self, game):
        super().__init__(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT / 5, game.batch)
        self.game = game
        self.page = 0
        self.load_page(0)

    def load_page(self, n):
        self.unload_page()
        i = 0
        for e in selects_all[n]:
            self.add(self.game.select, SCREEN_WIDTH * (0.01 + 0.1 * i), SCREEN_WIDTH * 0.01,
                     SCREEN_WIDTH * 0.09, SCREEN_WIDTH * 0.09, e.img, args=(e,))
            i += 1

    def unload_page(self):
        [e.delete() for e in self.buttons]
        self.buttons = []


class UI_formation(toolbar):
    def __init__(self, game):
        self.rows, self.columns = game.unit_formation_rows, game.unit_formation_columns
        self.dot_size = SCREEN_HEIGHT / 5 / self.rows
        super().__init__(SCREEN_WIDTH - self.dot_size * self.columns, 0, self.dot_size * self.columns,
                         SCREEN_HEIGHT / 5, game.batch, image=None)
        self.units = [[None for _ in range(self.columns)] for _ in range(self.rows)]


class UI_categories(toolbar):
    def __init__(self, game, bb):
        super().__init__(0, bb.height, SCREEN_WIDTH, SCREEN_HEIGHT * 0.05, game.batch)
        i = 0
        for _ in selects_all:
            self.add(bb.load_page, SCREEN_WIDTH * (0.01 + 0.1 * i), bb.height + SCREEN_HEIGHT * 0.005,
                     SCREEN_WIDTH * 0.09, SCREEN_HEIGHT * 0.04, args=(i,))
            i += 1


class player():
    def __init__(self):
        self.walls = []
        self.units = []
        self.towers = []

    def tick(self):
        [e.tick() for e in self.units]
        [e.tick() for e in self.towers]

    def update_cam(self, x, y):
        [e.update_cam(x, y) for e in self.units]
        [e.update_cam(x, y) for e in self.towers]
        [e.update_cam(x, y) for e in self.walls]


##################   ---/core---  #################
##################  ---selects---  #################

class selection:
    def __init__(self, game):
        self.cancelbutton = button(self.end, SCREEN_WIDTH * 0.01, SCREEN_HEIGHT * 0.9,
                                   SCREEN_WIDTH * 0.1, SCREEN_HEIGHT * 0.09, game.batch,
                                   image=images.Cancelbutton)

    def mouse_move(self, x, y):
        pass

    def mouse_click(self, x, y):
        pass

    def mouse_release(self, x, y):
        pass

    def end(self):
        self.cancelbutton.delete()

    def update_cam(self, x, y):
        pass


class selection_none(selection):
    def __init__(self, game):
        pass

    def end(self):
        pass


class selection_tower(selection):
    img = images.Towerbutton

    def __init__(self, game):
        super().__init__(game)
        self.game = game
        self.camx, self.camy = 0, 0
        self.size = unit_stats["Tower"]["size"]
        self.sprite = pyglet.sprite.Sprite(images.Intro, x=0,
                                           y=0, batch=game.batch,
                                           group=groups.g[2])
        self.sprite.scale = self.size / self.sprite.width
        self.sprite.opacity = 100
        self.update_cam(self.game.camx, self.game.camy)

    def mouse_move(self, x, y):
        self.sprite.update(x=x - self.size / 2, y=y - self.size / 2)
        self.cancelbutton.mouse_move(x, y)

    def mouse_click(self, x, y):
        if not self.cancelbutton.mouse_click(x, y):
            self.game.connection.Send({"action": "place_tower", "xy": [x + self.camx, y + self.camy]})
            self.end()

    def mouse_release(self, x, y):
        self.cancelbutton.mouse_release(x, y)

    def end(self):
        self.game.selected = selection_none(self.game)
        self.sprite.delete()
        super().end()

    def update_cam(self, x, y):
        self.camx, self.camy = x, y


class selection_wall(selection):
    img = images.Towerbutton

    def __init__(self, game):
        super().__init__(game)
        self.game = game
        self.selected1, self.selected1 = None, None
        self.buttons = []
        self.camx, self.camy = game.camx, game.camy
        for e in game.players[game.side].towers:
            self.buttons.append(button(self.select, e.x - 20, e.y - 20, 40, 40,
                                       self.game.batch, args=(e.ID,)))
        self.sprite = None
        self.update_cam(self.game.camx, self.game.camy)

    def select(self, ID):
        if self.selected1 is None or self.selected1 == ID:
            self.selected1 = ID
            return
        self.selected2 = ID
        self.game.connection.Send({"action": "place_wall", "ID1": self.selected1,
                                   "ID2": self.selected2})
        self.end()

    def mouse_move(self, x, y):
        pass

    def mouse_click(self, x, y):
        if not self.cancelbutton.mouse_click(x, y):
            [e.mouse_click(x, y) for e in self.buttons]

    def mouse_release(self, x, y):
        self.cancelbutton.mouse_release(x, y)
        [e.mouse_release(x, y) for e in self.buttons]

    def end(self):
        self.game.selected = selection_none(self.game)
        super().end()
        [e.delete() for e in self.buttons]

    def update_cam(self, x, y):
        [e.update(e.ogx - x, e.ogy - y) for e in self.buttons]
        self.camx, self.camy = x, y


class selection_unit(selection):
    img = images.gunmanR

    def __init__(self, game):
        super().__init__(game)

    def mouse_move(self, x, y):
        pass

    def mouse_click(self, x, y):
        pass

    def mouse_release(self, x, y):
        self.cancelbutton.mouse_release(x, y)

    def end(self):
        super().end()

    def update_cam(self, x, y):
        pass


selects_p1 = [selection_tower, selection_wall]
selects_all = [selects_p1, [selection_unit]]


################## ---/selects--- #################
##################   ---units---  #################   

class Tower():
    name = "Tower"

    def __init__(self, ID, x, y, side, game):
        self.x, self.y = x, y
        self.ID = ID
        self.side = side
        self.size = unit_stats[self.name]["size"]
        self.hp = unit_stats[self.name]["hp"]
        self.sprite = pyglet.sprite.Sprite(images.Intro, x=x - self.size / 2,
                                           y=y - self.size / 2, batch=game.batch,
                                           group=groups.g[2])
        self.sprite.scale = self.size / self.sprite.width
        self.l = game.players[side].towers
        self.l.append(self)
        self.game = game
        self.update_cam(self.game.camx, self.game.camy)
        self.spinspeed = 600 / FPS

    def tick(self):
        self.sprite.rotation += self.spinspeed

    def update_cam(self, x, y):
        self.sprite.update(x=self.x - self.size / 2 - x, y=self.y - self.size / 2 - y)

    def delete(self):
        self.l.remove(self)
        self.sprite.delete()


class Wall:
    name = "Wall"

    def __init__(self, ID, t1, t2, side, game):
        self.ID = ID
        self.x1, self.y1, self.x2, self.y2 = t1.x, t1.y, t2.x, t2.y
        self.side = side
        self.width = unit_stats[self.name]["width"]
        self.hp = unit_stats[self.name]["hp"]
        self.game = game
        self.l = game.players[side].walls
        self.l.append(self)
        x = self.width / 2 / math.sqrt((self.x1 - self.x2) ** 2 + (self.y1 - self.y2) ** 2)
        a = x * (self.y2 - self.y1)
        b = x * (self.x1 - self.x2)
        self.texgroup = TextureBindGroup(images.Wall, layer=1)
        pyglet.gl.glEnable(pyglet.gl.GL_BLEND)
        self.vertices_no_cam = (
            self.x1 - a, self.y1 - b, self.x1 + a, self.y1 + b, self.x2 + a, self.y2 + b, self.x2 - a, self.y2 - b)
        self.sprite = game.batch.add(
            4, pyglet.gl.GL_QUADS, self.texgroup,
            ("v2f", self.vertices_no_cam),
            ("t2f", (0, 0, 1, 0, 1, 0.5 / x,
                     0, 0.5 / x))
        )
        self.update_cam(self.game.camx, self.game.camy)

    def update_cam(self, x, y):
        self.sprite.vertices = [(self.vertices_no_cam[i] - (x if i % 2 == 0 else y)) for i in range(8)]


class Unit:
    pass


class Swordsman(Unit):
    image = images.gunmanG

##################  ---/units---  #################
